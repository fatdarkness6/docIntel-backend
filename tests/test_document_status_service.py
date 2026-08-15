import asyncio
import unittest
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.dependencies import get_stream_current_user_id
from app.db.session import Base
from app.main import app
from app.models.document import Document
from app.models.document_status_event import DocumentStatusEvent
from app.models.folder import Folder
from app.models.user import User
from app.services.document_status_service import (
    DocumentStatusRepository,
    DocumentStatusSnapshot,
    DocumentStatusStreamService,
    record_document_status,
)


def snapshot(
    event_id: int,
    status: str = "processing",
    stage: str = "extracting",
    progress: int | None = 20,
) -> DocumentStatusSnapshot:
    return DocumentStatusSnapshot(
        document_id=123,
        event_id=event_id,
        status=status,
        stage=stage,
        progress=progress,
        message=f"Document is {stage}",
        updated_at=datetime(2026, 8, 15, 10, 30, tzinfo=timezone.utc),
    )


class FakeRequest:
    def __init__(self):
        self.disconnected = False
        self.checks = 0

    async def is_disconnected(self) -> bool:
        self.checks += 1
        return self.disconnected


class FakeRepository:
    def __init__(self, events=None):
        self.events = list(events or [])
        self.reads = 0

    def get_for_user(self, document_id: int, user_id: int):
        return None

    def get_after(self, document_id: int, event_id: int):
        self.reads += 1
        return [event for event in self.events if event.event_id > event_id]


async def collect(stream) -> list[str]:
    return [chunk async for chunk in stream]


class DocumentStatusStreamTests(unittest.IsolatedAsyncioTestCase):
    def service(self, events=None, **overrides):
        return DocumentStatusStreamService(
            FakeRepository(events),
            poll_interval=overrides.get("poll_interval", 0.001),
            heartbeat_interval=overrides.get("heartbeat_interval", 60),
            max_connection_seconds=overrides.get("max_connection_seconds", 0.1),
        )

    async def test_immediate_initial_status_event(self):
        service = self.service([snapshot(2, "completed", "completed", 100)])
        chunks = await collect(service.stream(FakeRequest(), snapshot(1)))

        self.assertIn("event: status", chunks[0])
        self.assertIn("id: 1", chunks[0])
        self.assertIn('"status":"processing"', chunks[0])

    async def test_processing_updates_and_completed_event_close_stream(self):
        events = [
            snapshot(2, stage="analyzing", progress=60),
            snapshot(3, "completed", "completed", 100),
        ]
        service = self.service(events)
        chunks = await collect(service.stream(FakeRequest(), snapshot(1)))

        self.assertEqual(3, len(chunks))
        self.assertIn("event: status", chunks[1])
        self.assertIn("id: 2", chunks[1])
        self.assertIn("event: completed", chunks[2])
        self.assertIn("id: 3", chunks[2])
        self.assertEqual(0, service.active_stream_count)

    async def test_failed_event_closes_stream(self):
        failed = snapshot(2, "failed", "failed", None)
        service = self.service([failed])
        chunks = await collect(service.stream(FakeRequest(), snapshot(1)))

        self.assertEqual(2, len(chunks))
        self.assertIn("event: failed", chunks[-1])
        self.assertIn('"progress":null', chunks[-1])

    async def test_initial_terminal_state_closes_immediately(self):
        service = self.service()
        chunks = await collect(
            service.stream(
                FakeRequest(),
                snapshot(8, "completed", "completed", 100),
            )
        )

        self.assertEqual(1, len(chunks))
        self.assertIn("event: completed", chunks[0])
        self.assertEqual(0, service.repository.reads)

    async def test_client_disconnection_cleans_up_stream(self):
        service = self.service()
        request = FakeRequest()
        stream = service.stream(request, snapshot(1))

        await anext(stream)
        self.assertEqual(1, service.active_stream_count)
        request.disconnected = True

        with self.assertRaises(StopAsyncIteration):
            await anext(stream)

        self.assertGreater(request.checks, 0)
        self.assertEqual(0, service.active_stream_count)

    async def test_reconnection_always_sends_latest_snapshot(self):
        service = self.service([snapshot(6, "completed", "completed", 100)])
        chunks = await collect(
            service.stream(
                FakeRequest(),
                snapshot(5),
                last_event_id="2",
            )
        )

        self.assertIn("id: 5", chunks[0])
        self.assertIn("id: 6", chunks[1])

    async def test_heartbeat_is_emitted(self):
        service = self.service(
            heartbeat_interval=0.001,
            max_connection_seconds=0.006,
        )
        chunks = await collect(service.stream(FakeRequest(), snapshot(1)))

        self.assertTrue(any("event: ping" in chunk for chunk in chunks))
        self.assertEqual(0, service.active_stream_count)

    async def test_multiple_simultaneous_subscribers_receive_terminal_event(self):
        completed = snapshot(2, "completed", "completed", 100)
        service = self.service([completed])

        first, second = await asyncio.gather(
            collect(service.stream(FakeRequest(), snapshot(1))),
            collect(service.stream(FakeRequest(), snapshot(1))),
        )

        self.assertIn("event: completed", first[-1])
        self.assertIn("event: completed", second[-1])
        self.assertEqual(0, service.active_stream_count)


class DocumentStatusRepositoryTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.engine = create_engine(
            "sqlite+pysqlite:///:memory:",
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
        )
        Base.metadata.create_all(
            cls.engine,
            tables=[
                User.__table__,
                Folder.__table__,
                Document.__table__,
                DocumentStatusEvent.__table__,
            ],
        )
        cls.session_factory = sessionmaker(bind=cls.engine)

        with cls.session_factory() as db:
            owner = User(email="owner@example.com", password_hash="hash")
            other = User(email="other@example.com", password_hash="hash")
            db.add_all([owner, other])
            db.flush()
            document = Document(
                user_id=owner.id,
                filename="private.txt",
                stored_name="private.txt",
                file_type="txt",
                size_bytes=7,
                status="processing",
            )
            db.add(document)
            db.commit()
            cls.owner_id = owner.id
            cls.other_id = other.id
            cls.document_id = document.id

    @classmethod
    def tearDownClass(cls):
        cls.engine.dispose()

    def test_owner_can_read_snapshot(self):
        repository = DocumentStatusRepository(self.session_factory)
        result = repository.get_for_user(self.document_id, self.owner_id)
        self.assertIsNotNone(result)
        self.assertEqual(self.document_id, result.document_id)

    def test_invalid_document_id_is_hidden(self):
        repository = DocumentStatusRepository(self.session_factory)
        self.assertIsNone(repository.get_for_user(9999, self.owner_id))

    def test_another_users_document_is_hidden(self):
        repository = DocumentStatusRepository(self.session_factory)
        self.assertIsNone(
            repository.get_for_user(self.document_id, self.other_id)
        )

    def test_terminal_status_does_not_discard_pending_document_content(self):
        with self.session_factory() as db:
            document = db.get(Document, self.document_id)
            document.extracted_text = "Persisted extracted text"
            document.summary = "Persisted AI summary"

            event = record_document_status(
                db,
                document,
                status="completed",
                stage="completed",
                progress=100,
                message="Document processing completed",
            )
            # SQLite does not auto-increment a BIGINT primary key. PostgreSQL
            # uses BIGSERIAL for this column in the production migration.
            event.id = 1
            db.commit()

        with self.session_factory() as db:
            document = db.get(Document, self.document_id)
            self.assertEqual("Persisted extracted text", document.extracted_text)
            self.assertEqual("Persisted AI summary", document.summary)
            self.assertEqual("completed", document.status)


class DocumentStatusRouteTests(unittest.TestCase):
    def setUp(self):
        self.client = TestClient(app)

    def tearDown(self):
        app.dependency_overrides.clear()

    def test_missing_authentication_returns_401(self):
        response = self.client.get("/api/v1/documents/123/events")
        self.assertEqual(401, response.status_code)

    def _assert_hidden_document_returns_404(self, user_id: int):
        app.dependency_overrides[get_stream_current_user_id] = lambda: user_id

        with patch(
            "app.api.routes.documents.document_status_stream.get_initial_snapshot",
            new=AsyncMock(return_value=None),
        ):
            response = self.client.get("/api/v1/documents/999/events")

        self.assertEqual(404, response.status_code)

    def test_invalid_document_id_returns_404(self):
        self._assert_hidden_document_returns_404(user_id=1)

    def test_another_users_document_returns_404(self):
        self._assert_hidden_document_returns_404(user_id=2)

    def test_sse_headers_and_terminal_response(self):
        app.dependency_overrides[get_stream_current_user_id] = lambda: 1

        with patch(
            "app.api.routes.documents.document_status_stream.get_initial_snapshot",
            new=AsyncMock(
                return_value=snapshot(3, "completed", "completed", 100)
            ),
        ):
            response = self.client.get(
                "/api/v1/documents/123/events",
                headers={"Authorization": "Bearer test-token"},
            )

        self.assertEqual(200, response.status_code)
        self.assertTrue(response.headers["content-type"].startswith("text/event-stream"))
        self.assertEqual("no-cache", response.headers["cache-control"])
        self.assertEqual("no", response.headers["x-accel-buffering"])
        self.assertIn("event: completed", response.text)


if __name__ == "__main__":
    unittest.main()
