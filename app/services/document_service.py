from pathlib import Path
from docx import Document as DocxDocument
from pypdf import PdfReader
import pandas as pd
from sqlalchemy import delete
from zipfile import BadZipFile, ZipFile
from fastapi import HTTPException, UploadFile
from app.models.document_chunk import DocumentChunk
from app.services.text_service import split_text
from app.db.session import SessionLocal
from app.models.document import Document
from app.services.ai_service import summarize_document
from app.services.embedding_service import create_embeddings
from app.services.document_status_service import record_document_status






def extract_docx_text(file_path: Path) -> str:
    document = DocxDocument(file_path)

    paragraphs = []

    for paragraph in document.paragraphs:
        if paragraph.text.strip():
            paragraphs.append(paragraph.text)

    return "\n".join(paragraphs)





def extract_txt_text(file_path: Path) -> str:
    return file_path.read_text(
        encoding="utf-8",
        errors="ignore"
    )





def extract_pdf_text(file_path: Path) -> str:
    reader = PdfReader(file_path)

    pages_text = []

    for page in reader.pages:
        text = page.extract_text()

        if text:
            pages_text.append(text)

    return "\n".join(pages_text)



def extract_document_text(
    file_path: Path,
    file_type: str
) -> str:

    if file_type == "pdf":
        return extract_pdf_text(file_path)

    if file_type == "docx":
        return extract_docx_text(file_path)

    if file_type == "txt":
        return extract_txt_text(file_path)

    if file_type in ["csv", "xlsx"]:
        return extract_spreadsheet_text(
            file_path,
            file_type
        )

    raise ValueError(
        f"Unsupported file type: {file_type}"
    )





def process_document(
    document_id: int,
    file_path: Path
):
    db = SessionLocal()

    try:
        document = db.get(
            Document,
            document_id
        )

        if not document:
            return

        record_document_status(
            db,
            document,
            status="processing",
            stage="extracting",
            progress=15,
            message="Extracting document content",
        )
        db.commit()
        
        db.execute(
            delete(DocumentChunk).where(
                DocumentChunk.document_id == document.id
            )
        )

        # PDF → keep page numbers
        if document.file_type == "pdf":
            pages = extract_pdf_pages(
                file_path
            )

            extracted_text = "\n\n".join(
                page["text"]
                for page in pages
            )

            record_document_status(
                db,
                document,
                status="processing",
                stage="chunking",
                progress=40,
                message="Preparing document sections",
            )
            db.commit()

            chunk_data = []

            for page in pages:
                page_chunks = split_text(
                    page["text"]
                )

                for chunk in page_chunks:
                    chunk_data.append({
                        "content": chunk,
                        "page_number": page["page_number"]
                    })

        # Other file types → no reliable page number
        else:
            extracted_text = extract_document_text(
                file_path,
                document.file_type
            )

            record_document_status(
                db,
                document,
                status="processing",
                stage="chunking",
                progress=40,
                message="Preparing document sections",
            )
            db.commit()

            chunks = split_text(
                extracted_text
            )

            chunk_data = [
                {
                    "content": chunk,
                    "page_number": None
                }
                for chunk in chunks
            ]

        # Only send chunk text to embedding API
        chunk_contents = [
            chunk["content"]
            for chunk in chunk_data
        ]

        record_document_status(
            db,
            document,
            status="processing",
            stage="analyzing",
            progress=60,
            message="Analyzing document content",
        )
        db.commit()

        embeddings = create_embeddings(
            chunk_contents
        )

        chunk_records = []

        for index, (chunk, embedding) in enumerate(
            zip(chunk_data, embeddings)
        ):
            chunk_records.append(
                DocumentChunk(
                    document_id=document.id,
                    chunk_index=index,
                    page_number=chunk["page_number"],
                    content=chunk["content"],
                    embedding=embedding
                )
            )

        db.add_all(
            chunk_records
        )

        # Generate document summary
        record_document_status(
            db,
            document,
            status="processing",
            stage="generating_summary",
            progress=85,
            message="Generating document summary",
        )
        db.commit()

        summary = summarize_document(
            extracted_text
        )

        document.extracted_text = extracted_text
        document.summary = summary
        record_document_status(
            db,
            document,
            status="completed",
            stage="completed",
            progress=100,
            message="Document processing completed",
        )

        db.commit()

    except Exception:
        db.rollback()
        document = db.get(
            Document,
            document_id
        )

        if document:
            record_document_status(
                db,
                document,
                status="failed",
                stage="failed",
                progress=None,
                message="Document processing failed",
            )
            db.commit()

        raise

    finally:
        db.close()






def dataframe_to_context(df: pd.DataFrame) -> str:

    rows, columns = df.shape

    column_info = []

    for column in df.columns:
        column_info.append(
            f"- {column}: {df[column].dtype}"
        )

    missing_values = df.isnull().sum()

    missing_info = []

    for column, count in missing_values.items():
        missing_info.append(
            f"- {column}: {count}"
        )

    numeric_summary = df.describe(
        include="number"
    ).to_string()

    preview = df.head(20).to_string(
        index=False
    )

    return f"""
Dataset information

Rows: {rows}
Columns: {columns}

Column types:
{chr(10).join(column_info)}

Missing values:
{chr(10).join(missing_info)}

Numeric statistics:
{numeric_summary}

First 20 rows:
{preview}
"""





def extract_spreadsheet_text(
    file_path: Path,
    file_type: str
) -> str:

    if file_type == "csv":
        df = pd.read_csv(file_path)

    elif file_type == "xlsx":
        df = pd.read_excel(file_path)

    else:
        raise ValueError(
            f"Unsupported spreadsheet type: {file_type}"
        )

    return dataframe_to_context(df)







def extract_pdf_pages(
    file_path: Path
) -> list[dict]:
    reader = PdfReader(file_path)

    pages = []

    for page_number, page in enumerate(
        reader.pages,
        start=1
    ):
        text = page.extract_text() or ""

        if text.strip():
            pages.append({
                "page_number": page_number,
                "text": text
            })

    return pages













MAX_FILE_SIZE = 20 * 1024 * 1024  # 20 MB
CHUNK_SIZE = 1024 * 1024          # 1 MB


def save_upload_file(
    file: UploadFile,
    file_path: Path
) -> int:
    total_size = 0

    try:
        with file_path.open("wb") as buffer:
            while chunk := file.file.read(CHUNK_SIZE):
                total_size += len(chunk)

                if total_size > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail="File is too large. Maximum size is 20 MB."
                    )

                buffer.write(chunk)

        return total_size

    except Exception:
        if file_path.exists():
            file_path.unlink()

        raise








def validate_pdf(file_path: Path):
    with file_path.open("rb") as file:
        header = file.read(5)

    if header != b"%PDF-":
        raise HTTPException(
            status_code=400,
            detail="Invalid PDF file"
        )

def validate_docx(file_path: Path):
    try:
        with ZipFile(file_path) as archive:
            files = archive.namelist()

            if "word/document.xml" not in files:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid DOCX file"
                )

    except BadZipFile:
        raise HTTPException(
            status_code=400,
            detail="Invalid DOCX file"
        )

def validate_xlsx(file_path: Path):
    try:
        with ZipFile(file_path) as archive:
            files = archive.namelist()

            if "xl/workbook.xml" not in files:
                raise HTTPException(
                    status_code=400,
                    detail="Invalid XLSX file"
                )

    except BadZipFile:
        raise HTTPException(
            status_code=400,
            detail="Invalid XLSX file"
        )

def validate_text_file(file_path: Path):
    with file_path.open("rb") as file:
        sample = file.read(4096)

    if b"\x00" in sample:
        raise HTTPException(
            status_code=400,
            detail="Invalid text file"
        )

def validate_file_content(
    file_path: Path,
    file_type: str
):
    if file_type == "pdf":
        validate_pdf(file_path)

    elif file_type == "docx":
        validate_docx(file_path)

    elif file_type == "xlsx":
        validate_xlsx(file_path)

    elif file_type in ["txt", "csv"]:
        validate_text_file(file_path)
