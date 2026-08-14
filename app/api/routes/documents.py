from math import ceil
from pathlib import Path
from uuid import uuid4

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user
from app.db.session import get_db

from app.models.document import Document
from app.models.document_chunk import DocumentChunk
from app.models.document_question import DocumentQuestion
from app.models.folder import Folder
from app.models.tag import Tag
from app.models.user import User

from app.schemas.document import (
    DashboardStatsResponse,
    DatasetAnalysisResponse,
    DatasetInsightsResponse,
    DocumentFolderUpdate,
    DocumentResponse,
    DocumentTagUpdate,
    DocumentUpdate,
    FavoriteUpdate,
    PaginatedDocumentsResponse,
    QuestionHistoryResponse,
    QuestionRequest,
    QuestionResponse,
)

from app.services.ai_service import (
    ask_document_question,
    generate_dataset_insights,
)
from app.services.analytics_service import analyze_spreadsheet
from app.services.document_service import (
    process_document,
    save_upload_file,
    validate_file_content,
)
from app.services.embedding_service import create_embeddings
from app.services.report_service import generate_document_report


router = APIRouter()

UPLOAD_DIR = Path("uploads")
REPORT_DIR = Path("reports")

ALLOWED_EXTENSIONS = {
    ".pdf": "pdf",
    ".docx": "docx",
    ".txt": "txt",
    ".csv": "csv",
    ".xlsx": "xlsx",
}

UPLOAD_DIR.mkdir(
    parents=True,
    exist_ok=True,
)


# =========================================================
# Helpers
# =========================================================


def get_user_document(
    db: Session,
    document_id: int,
    user_id: int,
) -> Document:
    document = db.execute(
        select(Document).where(
            Document.id == document_id,
            Document.user_id == user_id,
        )
    ).scalar_one_or_none()

    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )

    return document


# =========================================================
# Upload
# =========================================================


@router.post(
    "/upload",
    response_model=DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    tags=["Documents"],
    summary="Upload a document",
)
def upload_document(
    file: UploadFile,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    extension = Path(file.filename).suffix.lower()

    if extension not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF, DOCX, TXT, CSV and XLSX files are supported",
        )

    file_type = ALLOWED_EXTENSIONS[extension]
    stored_name = f"{uuid4()}{extension}"
    file_path = UPLOAD_DIR / stored_name

    size_bytes = save_upload_file(
        file,
        file_path,
    )

    try:
        validate_file_content(
            file_path,
            file_type,
        )

    except Exception:
        file_path.unlink(
            missing_ok=True,
        )
        raise

    document = Document(
        user_id=current_user.id,
        filename=file.filename,
        stored_name=stored_name,
        file_type=file_type,
        size_bytes=size_bytes,
        status="processing",
    )

    db.add(document)
    db.commit()
    db.refresh(document)

    background_tasks.add_task(
        process_document,
        document.id,
        file_path,
    )

    return document


# =========================================================
# Documents
# =========================================================


@router.get(
    "",
    response_model=PaginatedDocumentsResponse,
    tags=["Documents"],
    summary="List documents",
)
def get_documents(
    search: str | None = None,
    favorite: bool | None = None,
    folder_id: int | None = None,
    tag_id: int | None = None,
    page: int = Query(
        default=1,
        ge=1,
    ),
    per_page: int = Query(
        default=10,
        ge=1,
        le=100,
    ),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    filters = [
        Document.user_id == current_user.id,
    ]

    if search:
        filters.append(
            Document.filename.ilike(
                f"%{search}%"
            )
        )

    if favorite is not None:
        filters.append(
            Document.is_favorite == favorite
        )

    if folder_id is not None:
        filters.append(
            Document.folder_id == folder_id
        )

    if tag_id is not None:
        filters.append(
            Document.tags.any(
                Tag.id == tag_id
            )
        )

    total = db.execute(
        select(
            func.count(Document.id)
        ).where(*filters)
    ).scalar_one()

    offset = (page - 1) * per_page

    documents = db.execute(
        select(Document)
        .where(*filters)
        .order_by(
            Document.created_at.desc()
        )
        .offset(offset)
        .limit(per_page)
    ).scalars().all()

    return {
        "items": documents,
        "total": total,
        "page": page,
        "per_page": per_page,
        "total_pages": ceil(
            total / per_page
        ),
    }


@router.get(
    "/stats",
    response_model=DashboardStatsResponse,
    tags=["Documents"],
    summary="Get dashboard statistics",
)
def get_dashboard_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    user_id = current_user.id

    total_documents = db.execute(
        select(
            func.count(Document.id)
        ).where(
            Document.user_id == user_id
        )
    ).scalar_one()

    pdf_documents = db.execute(
        select(
            func.count(Document.id)
        ).where(
            Document.user_id == user_id,
            Document.file_type == "pdf",
        )
    ).scalar_one()

    docx_documents = db.execute(
        select(
            func.count(Document.id)
        ).where(
            Document.user_id == user_id,
            Document.file_type == "docx",
        )
    ).scalar_one()

    text_documents = db.execute(
        select(
            func.count(Document.id)
        ).where(
            Document.user_id == user_id,
            Document.file_type == "txt",
        )
    ).scalar_one()

    spreadsheet_documents = db.execute(
        select(
            func.count(Document.id)
        ).where(
            Document.user_id == user_id,
            Document.file_type.in_(
                ["csv", "xlsx"]
            ),
        )
    ).scalar_one()

    processing_documents = db.execute(
        select(
            func.count(Document.id)
        ).where(
            Document.user_id == user_id,
            Document.status == "processing",
        )
    ).scalar_one()

    failed_documents = db.execute(
        select(
            func.count(Document.id)
        ).where(
            Document.user_id == user_id,
            Document.status == "failed",
        )
    ).scalar_one()

    total_questions = db.execute(
        select(
            func.count(DocumentQuestion.id)
        ).where(
            DocumentQuestion.user_id == user_id
        )
    ).scalar_one()

    return {
        "total_documents": total_documents,
        "pdf_documents": pdf_documents,
        "docx_documents": docx_documents,
        "text_documents": text_documents,
        "spreadsheet_documents": spreadsheet_documents,
        "processing_documents": processing_documents,
        "failed_documents": failed_documents,
        "total_questions": total_questions,
    }


@router.get(
    "/{document_id}",
    response_model=DocumentResponse,
    tags=["Documents"],
    summary="Get a document",
)
def get_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    return get_user_document(
        db,
        document_id,
        current_user.id,
    )


@router.patch(
    "/{document_id}",
    response_model=DocumentResponse,
    tags=["Documents"],
    summary="Rename a document",
)
def update_document(
    document_id: int,
    data: DocumentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = get_user_document(
        db,
        document_id,
        current_user.id,
    )

    new_filename = data.filename.strip()

    if not new_filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Filename cannot be empty",
        )

    document.filename = new_filename

    db.commit()
    db.refresh(document)

    return document


@router.delete(
    "/{document_id}",
    tags=["Documents"],
    summary="Delete a document",
)
def delete_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = get_user_document(
        db,
        document_id,
        current_user.id,
    )

    upload_path = (
        UPLOAD_DIR
        / document.stored_name
    )

    report_path = (
        REPORT_DIR
        / f"document-{document.id}.pdf"
    )

    db.delete(document)
    db.commit()

    upload_path.unlink(
        missing_ok=True,
    )

    report_path.unlink(
        missing_ok=True,
    )

    return {
        "message": "Document deleted successfully",
    }


# =========================================================
# Reprocessing
# =========================================================


@router.post(
    "/{document_id}/reprocess",
    tags=["Documents"],
    summary="Reprocess a document",
)
def reprocess_document(
    document_id: int,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = get_user_document(
        db,
        document_id,
        current_user.id,
    )

    file_path = (
        UPLOAD_DIR
        / document.stored_name
    )

    if not file_path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Original file was not found",
        )

    document.status = "processing"
    document.summary = None

    db.commit()

    background_tasks.add_task(
        process_document,
        document.id,
        file_path,
    )

    return {
        "message": "Document reprocessing started",
        "document_id": document.id,
        "status": "processing",
    }


# =========================================================
# AI / Document Questions
# =========================================================


@router.post(
    "/{document_id}/ask",
    response_model=QuestionResponse,
    tags=["Document AI"],
    summary="Ask a question about a document",
)
def ask_document(
    document_id: int,
    data: QuestionRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = get_user_document(
        db,
        document_id,
        current_user.id,
    )

    if document.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document is still processing",
        )

    if not document.extracted_text:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document contains no extracted text",
        )

    previous_questions = db.execute(
        select(DocumentQuestion)
        .where(
            DocumentQuestion.document_id == document.id,
            DocumentQuestion.user_id == current_user.id,
        )
        .order_by(
            DocumentQuestion.created_at.desc()
        )
        .limit(3)
    ).scalars().all()

    previous_questions.reverse()

    history = [
        {
            "question": item.question,
            "answer": item.answer,
        }
        for item in previous_questions
    ]

    question_embedding = create_embeddings(
        [data.question]
    )[0]

    relevant_chunks = db.execute(
        select(DocumentChunk)
        .where(
            DocumentChunk.document_id == document.id,
            DocumentChunk.embedding.is_not(None),
        )
        .order_by(
            DocumentChunk.embedding.cosine_distance(
                question_embedding
            )
        )
        .limit(3)
    ).scalars().all()

    chunk_contents = [
        {
            "chunk_index": chunk.chunk_index,
            "content": chunk.content,
        }
        for chunk in relevant_chunks
    ]

    if not chunk_contents:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No searchable chunks found",
        )

    answer = ask_document_question(
        chunk_contents,
        data.question,
        history,
    )

    question_record = DocumentQuestion(
        document_id=document.id,
        user_id=current_user.id,
        question=data.question,
        answer=answer,
    )

    db.add(question_record)
    db.commit()

    sources = [
        {
            "chunk_id": chunk.id,
            "chunk_index": chunk.chunk_index,
            "page_number": chunk.page_number,
            "preview": chunk.content[:300],
        }
        for chunk in relevant_chunks
    ]

    return {
        "answer": answer,
        "sources": sources,
    }


@router.get(
    "/{document_id}/questions",
    response_model=list[QuestionHistoryResponse],
    tags=["Document AI"],
    summary="Get document question history",
)
def get_document_questions(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = get_user_document(
        db,
        document_id,
        current_user.id,
    )

    questions = db.execute(
        select(DocumentQuestion)
        .where(
            DocumentQuestion.document_id == document.id,
            DocumentQuestion.user_id == current_user.id,
        )
        .order_by(
            DocumentQuestion.created_at
        )
    ).scalars().all()

    return questions


# =========================================================
# Spreadsheet Analysis
# =========================================================


@router.get(
    "/{document_id}/analysis",
    response_model=DatasetAnalysisResponse,
    tags=["Spreadsheet Analysis"],
    summary="Analyze a spreadsheet",
)
def analyze_document(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = get_user_document(
        db,
        document_id,
        current_user.id,
    )

    if document.file_type not in {
        "csv",
        "xlsx",
    }:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Analysis is only available for CSV and XLSX files",
        )

    file_path = (
        UPLOAD_DIR
        / document.stored_name
    )

    return analyze_spreadsheet(
        file_path,
        document.file_type,
    )


@router.get(
    "/{document_id}/insights",
    response_model=DatasetInsightsResponse,
    tags=["Spreadsheet Analysis"],
    summary="Generate AI spreadsheet insights",
)
def get_dataset_insights(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = get_user_document(
        db,
        document_id,
        current_user.id,
    )

    if document.file_type not in {
        "csv",
        "xlsx",
    }:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Insights are only available for CSV and XLSX files",
        )

    if document.insights:
        return {
            "insights": document.insights,
        }

    file_path = (
        UPLOAD_DIR
        / document.stored_name
    )

    analysis = analyze_spreadsheet(
        file_path,
        document.file_type,
    )

    insights = generate_dataset_insights(
        analysis
    )

    document.insights = insights
    db.commit()

    return {
        "insights": insights,
    }


# =========================================================
# Reports
# =========================================================


@router.get(
    "/{document_id}/report",
    tags=["Documents"],
    summary="Download document report",
)
def download_document_report(
    document_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = get_user_document(
        db,
        document_id,
        current_user.id,
    )

    if document.status != "completed":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Document is still processing",
        )

    report_path = generate_document_report(
        document
    )

    return FileResponse(
        path=report_path,
        media_type="application/pdf",
        filename=(
            f"{Path(document.filename).stem}-report.pdf"
        ),
    )


# =========================================================
# Organization
# =========================================================


@router.patch(
    "/{document_id}/favorite",
    response_model=DocumentResponse,
    tags=["Document Organization"],
    summary="Update document favorite status",
)
def update_favorite(
    document_id: int,
    data: FavoriteUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = get_user_document(
        db,
        document_id,
        current_user.id,
    )

    document.is_favorite = (
        data.is_favorite
    )

    db.commit()
    db.refresh(document)

    return document


@router.patch(
    "/{document_id}/folder",
    response_model=DocumentResponse,
    tags=["Document Organization"],
    summary="Move document to a folder",
)
def move_document_to_folder(
    document_id: int,
    data: DocumentFolderUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = get_user_document(
        db,
        document_id,
        current_user.id,
    )

    if data.folder_id is not None:
        folder = db.execute(
            select(Folder).where(
                Folder.id == data.folder_id,
                Folder.user_id == current_user.id,
            )
        ).scalar_one_or_none()

        if not folder:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Folder not found",
            )

    document.folder_id = data.folder_id

    db.commit()
    db.refresh(document)

    return document


@router.post(
    "/{document_id}/tags",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Document Organization"],
    summary="Add a tag to a document",
)
def add_document_tag(
    document_id: int,
    data: DocumentTagUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = get_user_document(
        db,
        document_id,
        current_user.id,
    )

    tag = db.execute(
        select(Tag).where(
            Tag.id == data.tag_id,
            Tag.user_id == current_user.id,
        )
    ).scalar_one_or_none()

    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found",
        )

    if tag not in document.tags:
        document.tags.append(tag)
        db.commit()


@router.delete(
    "/{document_id}/tags/{tag_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Document Organization"],
    summary="Remove a tag from a document",
)
def remove_document_tag(
    document_id: int,
    tag_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    document = get_user_document(
        db,
        document_id,
        current_user.id,
    )

    tag = db.execute(
        select(Tag).where(
            Tag.id == tag_id,
            Tag.user_id == current_user.id,
        )
    ).scalar_one_or_none()

    if not tag:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Tag not found",
        )

    if tag in document.tags:
        document.tags.remove(tag)
        db.commit()