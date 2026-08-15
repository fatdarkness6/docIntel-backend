import asyncio
import json
from dataclasses import dataclass
from datetime import datetime, timezone
from time import monotonic
from typing import Callable

from fastapi import Request
from sqlalchemy import select
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.core.config import settings
from app.db.session import SessionLocal
from app.models.document import Document
from app.models.document_status_event import DocumentStatusEvent


VALID_STATUSES = {"processing", "completed", "failed"}
TERMINAL_STATUSES = {"completed", "failed"}


@dataclass(frozen=True)
class DocumentStatusSnapshot:
    document_id: int
    event_id: int
    status: str
    stage: str | None
    progress: int | None
    message: str | None
    updated_at: datetime

    @property
    def event_name(self) -> str:
        if self.status in TERMINAL_STATUSES:
            return self.status
        return "status"

    def payload(self) -> dict:
        return {
            "document_id": self.document_id,
            "status": self.status,
            "stage": self.stage,
            "progress": self.progress,
            "message": self.message,
            "updated_at": _format_utc(self.updated_at),
        }


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _format_utc(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).isoformat().replace("+00:00", "Z")


def encode_sse(
    event_name: str,
    payload: dict,
    event_id: int | None = None,
) -> str:
    lines = [f"event: {event_name}"]
    if event_id is not None:
        lines.append(f"id: {event_id}")
    lines.append(
        "data: "
        + json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
        )
    )
    return "\n".join(lines) + "\n\n"


def record_document_status(
    db: Session,
    document: Document,
    *,
    status: str,
    stage: str | None,
    progress: int | None,
    message: str | None,
) -> DocumentStatusEvent:
    if status not in VALID_STATUSES:
        raise ValueError(f"Unsupported document status: {status}")
    if progress is not None and not 0 <= progress <= 100:
        raise ValueError("Document progress must be between 0 and 100")

    # SessionLocal disables autoflush. Persist pending fields such as
    # a new document ID, extracted_text, and summary before populate_existing
    # refreshes the row. Otherwise the refresh would restore stale DB state.
    db.flush()

    # Serialize state-version allocation for a document. This prevents two
    # processing workers (for example, an upload and a reprocess) from writing
    # the same event ID.
    document = db.execute(
        select(Document)
        .where(Document.id == document.id)
        .with_for_update()
        .execution_options(populate_existing=True)
    ).scalar_one()

    updated_at = utc_now()
    next_event_id = (document.status_event_id or 0) + 1

    document.status = status
    document.processing_stage = stage
    document.processing_progress = progress
    document.status_message = message
    document.status_updated_at = updated_at
    document.status_event_id = next_event_id

    event = DocumentStatusEvent(
        document_id=document.id,
        event_id=next_event_id,
        status=status,
        stage=stage,
        progress=progress,
        message=message,
        updated_at=updated_at,
    )
    db.add(event)
    return event


class DocumentStatusRepository:
    def __init__(self, session_factory: Callable[[], Session] = SessionLocal):
        self._session_factory = session_factory

    def get_for_user(
        self,
        document_id: int,
        user_id: int,
    ) -> DocumentStatusSnapshot | None:
        with self._session_factory() as db:
            row = db.execute(
                select(
                    Document.id,
                    Document.status_event_id,
                    Document.status,
                    Document.processing_stage,
                    Document.processing_progress,
                    Document.status_message,
                    Document.status_updated_at,
                ).where(
                    Document.id == document_id,
                    Document.user_id == user_id,
                )
            ).one_or_none()

            if row is None:
                return None

            return DocumentStatusSnapshot(
                document_id=row.id,
                event_id=row.status_event_id,
                status=row.status,
                stage=row.processing_stage,
                progress=row.processing_progress,
                message=row.status_message,
                updated_at=row.status_updated_at,
            )

    def get_after(
        self,
        document_id: int,
        event_id: int,
    ) -> list[DocumentStatusSnapshot]:
        with self._session_factory() as db:
            events = db.execute(
                select(DocumentStatusEvent)
                .where(
                    DocumentStatusEvent.document_id == document_id,
                    DocumentStatusEvent.event_id > event_id,
                )
                .order_by(DocumentStatusEvent.event_id)
            ).scalars().all()

            return [
                DocumentStatusSnapshot(
                    document_id=event.document_id,
                    event_id=event.event_id,
                    status=event.status,
                    stage=event.stage,
                    progress=event.progress,
                    message=event.message,
                    updated_at=event.updated_at,
                )
                for event in events
            ]


class DocumentStatusStreamService:
    def __init__(
        self,
        repository: DocumentStatusRepository | None = None,
        *,
        poll_interval: float | None = None,
        heartbeat_interval: float | None = None,
        max_connection_seconds: float | None = None,
    ):
        self.repository = repository or DocumentStatusRepository()
        self.poll_interval = poll_interval or settings.sse_poll_interval_seconds
        self.heartbeat_interval = (
            heartbeat_interval or settings.sse_heartbeat_interval_seconds
        )
        self.max_connection_seconds = (
            max_connection_seconds or settings.sse_max_connection_seconds
        )
        self._active_streams = 0

    @property
    def active_stream_count(self) -> int:
        return self._active_streams

    async def get_initial_snapshot(
        self,
        document_id: int,
        user_id: int,
    ) -> DocumentStatusSnapshot | None:
        return await run_in_threadpool(
            self.repository.get_for_user,
            document_id,
            user_id,
        )

    async def stream(
        self,
        request: Request,
        initial: DocumentStatusSnapshot,
        last_event_id: str | None = None,
    ):
        # Last-Event-ID is intentionally accepted even though the latest durable
        # database snapshot is always sent first. Its ID lets clients deduplicate.
        _parse_last_event_id(last_event_id)

        self._active_streams += 1
        started_at = monotonic()
        last_heartbeat_at = started_at
        cursor = initial.event_id

        try:
            yield encode_sse(
                initial.event_name,
                initial.payload(),
                initial.event_id,
            )

            if initial.status in TERMINAL_STATUSES:
                return

            while monotonic() - started_at < self.max_connection_seconds:
                if await request.is_disconnected():
                    return

                events = await run_in_threadpool(
                    self.repository.get_after,
                    initial.document_id,
                    cursor,
                )

                for event in events:
                    cursor = event.event_id
                    yield encode_sse(
                        event.event_name,
                        event.payload(),
                        event.event_id,
                    )
                    if event.status in TERMINAL_STATUSES:
                        return

                now = monotonic()
                if now - last_heartbeat_at >= self.heartbeat_interval:
                    yield encode_sse(
                        "ping",
                        {"timestamp": _format_utc(utc_now())},
                    )
                    last_heartbeat_at = now

                await asyncio.sleep(self.poll_interval)
        finally:
            self._active_streams -= 1


def _parse_last_event_id(value: str | None) -> int | None:
    if value is None:
        return None
    try:
        parsed = int(value)
    except ValueError:
        return None
    return parsed if parsed >= 0 else None


document_status_stream = DocumentStatusStreamService()
