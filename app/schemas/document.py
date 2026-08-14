from datetime import datetime
from app.schemas.tag import TagResponse
from pydantic import BaseModel
from pydantic import Field


class DocumentResponse(BaseModel):
    id: int
    filename: str
    file_type: str
    size_bytes: int
    created_at: datetime
    is_favorite: bool
    status: str
    summary: str | None
    folder_id: int | None

    tags: list[TagResponse] = Field(default_factory=list)

    model_config = {
        "from_attributes": True
    }

class QuestionRequest(BaseModel):
    question: str


class CitationResponse(BaseModel):
    chunk_id: int
    chunk_index: int
    page_number: int | None = None
    preview: str

class QuestionResponse(BaseModel):
    answer: str
    sources: list[CitationResponse]

class QuestionHistoryResponse(BaseModel):
    id: int
    question: str
    answer: str
    sources: list[CitationResponse] | None = None
    created_at: datetime

    model_config = {
        "from_attributes": True
    }

class ColumnAnalysis(BaseModel):
    name: str
    type: str
    missing_values: int


class DatasetAnalysisResponse(BaseModel):
    rows: int
    columns: int
    column_info: list[ColumnAnalysis]
    numeric_summary: dict[str, dict[str, float]]

class DatasetInsightsResponse(BaseModel):
    insights: str

class PaginatedDocumentsResponse(BaseModel):
    items: list[DocumentResponse]
    total: int
    page: int
    per_page: int
    total_pages: int


class DashboardStatsResponse(BaseModel):
    total_documents: int
    pdf_documents: int
    docx_documents: int
    text_documents: int
    spreadsheet_documents: int
    processing_documents: int
    failed_documents: int
    total_questions: int

class DocumentUpdate(BaseModel):
    filename: str

class FavoriteUpdate(BaseModel):
    is_favorite: bool

class DocumentFolderUpdate(BaseModel):
    folder_id: int | None

class DocumentTagUpdate(BaseModel):
    tag_id: int




