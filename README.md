# 📄 AI Document Intelligence Platform — Backend

A production-oriented backend for an AI-powered document intelligence platform built with **Python, FastAPI, PostgreSQL, SQLAlchemy, pgvector, Pandas, and OpenAI**.

The backend allows users to securely upload documents, extract and process their content, generate AI summaries, ask questions using Retrieval-Augmented Generation, analyze spreadsheets, organize files, and generate downloadable reports.

This repository contains the **backend API and AI/data-processing system**.

---

## ✨ Features

### 🔐 Authentication

The backend provides JWT-based user authentication.

Features include:

- User registration
- User login
- Password hashing
- JWT access tokens
- Protected API routes
- Current-user retrieval
- User-specific resource authorization
- OAuth2-compatible Swagger authentication

Authentication is implemented using:

```text
JWT
+
FastAPI OAuth2
+
Password Hashing
```

Login uses:

```text
POST /api/v1/auth/login
```

with:

```text
application/x-www-form-urlencoded
```

The user's email is submitted through the OAuth2 `username` field.

Authenticated requests use:

```http
Authorization: Bearer ACCESS_TOKEN
```

---

# 📄 Document Management

Users can upload and manage multiple document formats.

Supported files:

```text
PDF
DOCX
TXT
CSV
XLSX
```

Maximum upload size:

```text
20 MB
```

Document functionality includes:

- Upload documents
- Validate uploaded files
- Store original filenames
- Generate UUID-based stored filenames
- Search documents
- Pagination
- Rename documents
- Delete documents
- Favorite documents
- Organize with folders
- Organize with tags
- Reprocess documents
- Track processing states
- Generate reports

Documents belong to individual users and ownership is checked before protected operations.

---

# 🛡️ Upload Validation

Uploads are validated before document processing starts.

Validation includes:

- Supported file-extension checks
- Maximum file-size enforcement
- PDF signature validation
- DOCX archive structure validation
- XLSX archive structure validation
- Basic TXT/CSV validation
- Automatic cleanup when validation fails

Uploaded files are stored locally under:

```text
uploads/
```

The database stores:

```text
Original filename
Stored UUID filename
File type
File size
Owner
Processing status
```

---

# ⚙️ Background Document Processing

Documents are processed using FastAPI background tasks.

Upload requests return quickly while processing continues separately.

Processing flow:

```text
Document Upload
      ↓
File Validation
      ↓
Save File
      ↓
Create Document Record
      ↓
status = processing
      ↓
Background Processing
      ↓
Text Extraction
      ↓
Text Chunking
      ↓
Embedding Generation
      ↓
Store Chunks in PostgreSQL
      ↓
Generate AI Summary
      ↓
status = completed
```

If processing fails:

```text
status = failed
```

The API also provides a reprocessing endpoint so documents can be processed again without uploading them again.

---

# 📝 Text Extraction

The backend extracts content based on document type.

### PDF

Powered by:

```text
pypdf
```

PDF files are extracted **page by page**, allowing document chunks to preserve their original page numbers.

---

### DOCX

Powered by:

```text
python-docx
```

Paragraph text is extracted and converted into processable document content.

---

### TXT

Plain text files are read directly using Python.

---

### CSV / XLSX

Spreadsheet files are processed using:

```text
Pandas
openpyxl
```

Spreadsheet data is converted into a compact textual representation that can also be used for summaries and AI processing.

---

# 🧩 Document Chunking

Large documents are not sent blindly to the AI model as one massive prompt.

Instead:

```text
Extracted Document
        ↓
Text Chunking
        ↓
Chunk 0
Chunk 1
Chunk 2
Chunk 3
...
```

Chunks contain:

```text
id
document_id
chunk_index
page_number
content
embedding
```

Chunk overlap is used to reduce information loss around chunk boundaries.

For PDFs, chunks preserve:

```text
page_number
```

For formats without reliable page concepts, the value can be:

```text
null
```

---

# 🧠 AI Document Summaries

Uploaded documents can automatically receive AI-generated summaries.

The summarization pipeline supports both small and large documents.

For larger documents:

```text
Document
   ↓
Split into chunks
   ↓
Summarize individual sections
   ↓
Combine section summaries
   ↓
Generate final concise summary
```

Summaries are designed to remain concise and UI-friendly rather than reproducing the entire document.

The final format focuses on:

```text
Overview
+
Key Points
```

Generated summaries are stored in PostgreSQL so they do not need to be regenerated on every request.

---

# 💬 Chat With Documents

Users can ask natural-language questions about uploaded documents.

Endpoint:

```text
POST /api/v1/documents/{document_id}/ask
```

Example request:

```json
{
  "question": "How does Docker isolate applications?"
}
```

The backend performs semantic retrieval before sending context to the language model.

---

# 🔎 Semantic Search

Document questions use embeddings rather than simple keyword matching.

This means the system can understand semantically similar language.

Example:

```text
Document:
"Containers isolate processes."

Question:
"How does Docker keep applications separated?"
```

Even though the exact words differ, semantic retrieval can identify the relevant section.

---

# 🧠 Embeddings

Document chunks are converted into embeddings using:

```text
OpenAI text-embedding-3-small
```

Current embedding dimensions:

```text
512
```

The ingestion pipeline is:

```text
Document
   ↓
Extract Text
   ↓
Create Chunks
   ↓
Generate Embeddings
   ↓
Store in PostgreSQL
```

Chunk embeddings are generated **once during document processing**.

They are not regenerated every time the user asks a question.

---

# 🐘 PostgreSQL + pgvector

Semantic search is powered directly by PostgreSQL using:

```text
pgvector
```

The `document_chunks.embedding` column uses:

```text
VECTOR(512)
```

When a user asks a question:

```text
Question
   ↓
Question Embedding
   ↓
PostgreSQL + pgvector
   ↓
Cosine Distance
   ↓
Top Relevant Chunks
```

SQLAlchemy performs vector ordering using:

```python
DocumentChunk.embedding.cosine_distance(
    question_embedding
)
```

The backend currently retrieves approximately:

```text
Top 3 relevant chunks
```

before calling the language model.

---

# 🤖 Retrieval-Augmented Generation

The application implements a practical basic **RAG pipeline**.

```text
User Question
      ↓
Generate Question Embedding
      ↓
PostgreSQL + pgvector
      ↓
Semantic Similarity Search
      ↓
Retrieve Relevant Chunks
      ↓
Build Context
      ↓
LLM
      ↓
Grounded Answer
```

The language model is instructed to answer using the retrieved document context rather than relying blindly on outside knowledge.

If the requested information cannot be found, the assistant is instructed to say so.

---

# 📚 Source Citations

Retrieved chunks are returned alongside AI answers.

A source can contain:

```text
chunk_id
chunk_index
page_number
preview
```

Example:

```json
{
  "answer": "Containers isolate running processes.",
  "sources": [
    {
      "chunk_id": 108,
      "chunk_index": 9,
      "page_number": 10,
      "preview": "Containers isolate processes..."
    }
  ]
}
```

For PDF documents, this allows the frontend to display meaningful citations such as:

```text
Sources

Page 10
Page 14
```

Internal chunk identifiers remain available for debugging and retrieval tracking.

---

# 💬 Conversation History

Document conversations are stored in PostgreSQL.

The backend keeps:

```text
Question
Answer
Document
User
Created time
```

Question history can be retrieved through:

```text
GET /api/v1/documents/{document_id}/questions
```

Previous questions are also used as limited conversational context for follow-up questions.

Example:

```text
User:
What is Docker?

User:
Why is it useful?
```

The second question can use recent conversation context to understand what `"it"` refers to.

---

# 📊 Spreadsheet Intelligence

CSV and XLSX documents receive additional data-analysis functionality.

Spreadsheet analysis is powered by:

```text
Pandas
```

The backend can calculate:

- Row count
- Column count
- Column names
- Column data types
- Missing-value counts
- Numeric summaries
- Mean
- Standard deviation
- Minimum
- Maximum
- Quartiles

Endpoint:

```text
GET /api/v1/documents/{document_id}/analysis
```

This endpoint works only for:

```text
CSV
XLSX
```

---

# 🤖 AI Spreadsheet Insights

Spreadsheet statistics can also be analyzed by an LLM.

Endpoint:

```text
GET /api/v1/documents/{document_id}/insights
```

Flow:

```text
CSV / XLSX
     ↓
Pandas
     ↓
Structured Statistics
     ↓
LLM
     ↓
Dataset Insights
```

Possible insights include:

- Important observations
- Unusual values
- Trends
- Missing-data problems
- Potential business insights

The model receives calculated statistics rather than the raw spreadsheet blindly.

---

# ⚡ AI Result Caching

Generated spreadsheet insights are stored in PostgreSQL.

If insights already exist:

```text
Request
   ↓
Check Database
   ↓
Existing Insights Found
   ↓
Return Cached Result
```

No additional AI request is made.

This reduces:

```text
API cost
Latency
Unnecessary model usage
```

---

# 📁 Folders

Documents can be organized into folders.

Folder functionality includes:

- Create folders
- List folders
- Rename folders
- Delete folders
- Move documents between folders
- Remove documents from folders
- Filter documents by folder

A document can belong to:

```text
One folder
```

or:

```text
No folder
```

Deleting a folder does not delete its documents.

Instead:

```text
folder_id = null
```

---

# 🏷️ Tags

Documents can also be organized using tags.

Unlike folders:

```text
One document → many tags

One tag → many documents
```

This is implemented using a many-to-many relationship.

The association table is:

```text
document_tags
```

Users can:

- Create tags
- List tags
- Rename tags
- Delete tags
- Add tags to documents
- Remove tags from documents
- Filter documents by tag

Tags are organizational metadata and are currently separate from the RAG retrieval logic.

---

# ⭐ Favorites

Documents can be marked as favorites.

Endpoint:

```text
PATCH /api/v1/documents/{document_id}/favorite
```

Example:

```json
{
  "is_favorite": true
}
```

The documents endpoint supports filtering by favorite status.

---

# 🔍 Document Search & Filtering

The main document listing endpoint supports:

```text
Search
Favorites
Folders
Tags
Pagination
```

Example:

```text
GET /api/v1/documents
    ?search=python
    &favorite=true
    &folder_id=2
    &tag_id=4
    &page=1
    &per_page=10
```

The response contains pagination metadata:

```json
{
  "items": [],
  "total": 42,
  "page": 1,
  "per_page": 10,
  "total_pages": 5
}
```

---

# 📈 Dashboard Statistics

The backend exposes aggregated statistics for the application dashboard.

Endpoint:

```text
GET /api/v1/documents/stats
```

Statistics include:

- Total documents
- PDF documents
- DOCX documents
- TXT documents
- Spreadsheet documents
- Processing documents
- Failed documents
- Total questions asked

All statistics are filtered by the authenticated user.

---

# 🔄 Document Reprocessing

Documents can be processed again without requiring another upload.

Endpoint:

```text
POST /api/v1/documents/{document_id}/reprocess
```

Reprocessing:

```text
Existing Document
       ↓
status = processing
       ↓
Delete Old Chunks
       ↓
Extract Again
       ↓
Create New Chunks
       ↓
Generate New Embeddings
       ↓
Generate New Summary
       ↓
status = completed
```

Old chunks are removed before regeneration to prevent duplicate retrieval results.

---

# 🗑️ Clean Document Deletion

Deleting a document removes more than the main database row.

The cleanup process includes:

```text
Document
├── Database record
├── Document chunks
├── Question history
├── Tag relationships
├── Uploaded file
└── Generated report
```

Database-related child records use cascading foreign-key behavior where appropriate.

Physical files are removed separately by Python.

---

# 📑 PDF Report Generation

The backend generates downloadable PDF reports using:

```text
ReportLab
```

Endpoint:

```text
GET /api/v1/documents/{document_id}/report
```

Reports can contain:

- Document filename
- Document summary
- Spreadsheet insights when available

Generated files are stored under:

```text
reports/
```

The endpoint responds with:

```text
application/pdf
```

---

# 🛠️ Tech Stack

## Backend

- Python
- FastAPI
- Pydantic
- SQLAlchemy
- Alembic
- PostgreSQL
- psycopg
- pgvector
- JWT
- pwdlib
- OpenAI API
- Pandas
- NumPy
- pypdf
- python-docx
- openpyxl
- ReportLab

---

## AI

- OpenAI Responses API
- OpenAI Embeddings API
- `gpt-5-nano`
- `text-embedding-3-small`
- Retrieval-Augmented Generation
- Semantic Search
- Vector Similarity Search

---

## Database

```text
PostgreSQL
+
SQLAlchemy ORM
+
Alembic Migrations
+
pgvector
```

---

# 🧠 AI Architecture

The primary document-processing workflow is:

```text
Document Upload
      ↓
File Validation
      ↓
Text Extraction
      ↓
Page-Aware Processing
      ↓
Text Chunking
      ↓
Embedding Generation
      ↓
PostgreSQL + pgvector
      ↓
AI Summary
```

Question answering:

```text
Question
    ↓
Question Embedding
    ↓
Semantic Search
    ↓
Relevant Chunks
    ↓
Context Construction
    ↓
LLM
    ↓
Grounded Answer + Sources
```

Spreadsheet processing:

```text
CSV / XLSX
     ↓
Pandas
     ↓
Statistics
     ↓
AI Analysis
     ↓
Insights
```

---

# 🏗️ Backend Architecture

The backend uses a layered architecture:

```text
HTTP Request
     ↓
FastAPI Route
     ↓
Dependencies / Authentication
     ↓
Service Layer
     ↓
SQLAlchemy
     ↓
PostgreSQL
```

AI-related processing follows:

```text
Route
  ↓
Document / Embedding / AI Service
  ↓
OpenAI API
  ↓
PostgreSQL
```

This keeps endpoint logic separated from document-processing, AI, analytics, and report-generation logic.

---

# 📂 Project Structure

```text
app/
├── api/
│   ├── routes/
│   │   ├── auth.py
│   │   ├── documents.py
│   │   ├── folders.py
│   │   ├── tags.py
│   │   └── health.py
│   │
│   ├── dependencies.py
│   └── router.py
│
├── core/
│   ├── config.py
│   └── security.py
│
├── db/
│   └── session.py
│
├── models/
│   ├── user.py
│   ├── document.py
│   ├── document_chunk.py
│   ├── document_question.py
│   ├── folder.py
│   ├── tag.py
│   └── document_tag.py
│
├── schemas/
│   ├── user.py
│   ├── document.py
│   ├── folder.py
│   └── tag.py
│
├── services/
│   ├── document_service.py
│   ├── text_service.py
│   ├── ai_service.py
│   ├── embedding_service.py
│   ├── analytics_service.py
│   └── report_service.py
│
├── main.py
└── __init__.py

migrations/
├── versions/
└── env.py

uploads/
reports/

.env
.env.example
.gitignore
alembic.ini
requirements.txt
README.md
```

---

# 🗄️ Database Structure

Main tables include:

```text
users
documents
document_chunks
document_questions
folders
tags
document_tags
alembic_version
```

Relationship overview:

```text
User
│
├── Documents
│      │
│      ├── Document Chunks
│      │
│      ├── Document Questions
│      │
│      ├── Folder
│      │
│      └── Tags
│      │
│      └── Embeddings
│
├── Folders
│
└── Tags
```

---

# 🚀 Getting Started

## 1. Clone the repository

```bash
git clone YOUR_REPOSITORY_URL
```

Then:

```bash
cd document-intelligence-backend
```

---

## 2. Create a virtual environment

Windows:

```bash
py -m venv .venv
```

Activate it:

```powershell
.\.venv\Scripts\Activate.ps1
```

macOS / Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

---

## 3. Install dependencies

```bash
pip install -r requirements.txt
```

---

# ⚙️ Environment Variables

Create:

```text
.env
```

Example configuration:

```env
DATABASE_URL=postgresql+psycopg://postgres:YOUR_PASSWORD@localhost:5432/document_intelligence

JWT_SECRET_KEY=YOUR_SECRET_KEY
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30

OPENAI_API_KEY=YOUR_OPENAI_API_KEY

FRONTEND_URL=http://localhost:3000
```

Never commit the real `.env` file.

Use:

```text
.env.example
```

to document required configuration without exposing secrets.

---

# 🐘 PostgreSQL Setup

Create a PostgreSQL database for the project.

Example:

```text
document_intelligence
```

Update:

```env
DATABASE_URL=
```

with the correct credentials.

---

# 🧠 pgvector Setup

The project requires the PostgreSQL:

```text
vector
```

extension.

After pgvector is installed on the PostgreSQL server, enable it inside the project database:

```sql
CREATE EXTENSION IF NOT EXISTS vector;
```

Verify:

```sql
SELECT extversion
FROM pg_extension
WHERE extname = 'vector';
```

The Python pgvector integration is also required:

```bash
pip install pgvector
```

---

# 🗃️ Database Migrations

This project uses:

```text
Alembic
```

Apply migrations:

```bash
alembic upgrade head
```

Create a migration after changing SQLAlchemy models:

```bash
alembic revision --autogenerate -m "migration description"
```

Then apply it:

```bash
alembic upgrade head
```

Migration files under:

```text
migrations/versions/
```

should be committed to Git.

---

# ▶️ Running the Development Server

Run:

```bash
fastapi dev app/main.py
```

Alternatively:

```bash
uvicorn app.main:app --reload
```

The API will normally be available at:

```text
http://127.0.0.1:8000
```

---

# 📚 API Documentation

FastAPI automatically generates interactive API documentation.

Swagger UI:

```text
http://127.0.0.1:8000/docs
```

OpenAPI schema:

```text
http://127.0.0.1:8000/openapi.json
```

---

# 🔌 API Base URL

Main development API prefix:

```text
http://127.0.0.1:8000/api/v1
```

Example:

```text
GET /api/v1/documents
```

---

# 🔐 Authentication Flow

Registration:

```text
Client
  ↓
POST /auth/register
  ↓
Hash Password
  ↓
Store User
```

Login:

```text
Client
  ↓
POST /auth/login
  ↓
Verify Credentials
  ↓
Create JWT
  ↓
Return Access Token
```

Protected request:

```text
Client
  ↓
Authorization: Bearer TOKEN
  ↓
Decode JWT
  ↓
Load User
  ↓
Verify Ownership
  ↓
Execute Request
```

---

# 📡 Main API Areas

The backend exposes routes for:

```text
Authentication
Documents
Document AI
Spreadsheet Analysis
Folders
Tags
Reports
Dashboard Statistics
Health Checks
```

Typical document routes include:

```text
POST   /documents/upload
GET    /documents
GET    /documents/stats
GET    /documents/{id}
PATCH  /documents/{id}
DELETE /documents/{id}

POST   /documents/{id}/ask
GET    /documents/{id}/questions

POST   /documents/{id}/reprocess

PATCH  /documents/{id}/favorite
PATCH  /documents/{id}/folder

POST   /documents/{id}/tags
DELETE /documents/{id}/tags/{tag_id}

GET    /documents/{id}/analysis
GET    /documents/{id}/insights
GET    /documents/{id}/report
```

All routes are available through Swagger for development and testing.

---

# 🌐 CORS

FastAPI is configured with CORS middleware so the frontend can communicate directly with the backend.

Development frontend:

```text
http://localhost:3000
```

Architecture:

```text
Nuxt
  ↓
HTTP API
  ↓
FastAPI
```

Allowed frontend origins are configured through:

```env
FRONTEND_URL=
```

The production frontend URL can therefore be changed without modifying application code.

---

# 🔒 Security

The current MVP includes:

- Password hashing
- JWT authentication
- Token expiration
- Protected endpoints
- Document ownership verification
- Folder ownership verification
- Tag ownership verification
- File-type validation
- File-size limits
- UUID-based stored filenames
- Environment-based secrets
- User-isolated document queries
- Cascade cleanup for related database records
- CORS origin configuration

Sensitive values such as:

```text
Database passwords
JWT secrets
OpenAI API keys
```

must never be committed to Git.

---

# 💰 AI Cost Awareness

The project intentionally minimizes unnecessary AI calls.

Examples:

```text
Chunk embeddings
→ generated once during ingestion

Spreadsheet AI insights
→ cached in PostgreSQL

Existing document summary
→ stored in PostgreSQL

Document retrieval
→ PostgreSQL pgvector handles similarity search
```

This prevents repeated model calls for information that has already been generated.

---

# 🧪 Development Status

The current MVP includes:

```text
✅ Authentication
✅ PostgreSQL integration
✅ SQLAlchemy ORM
✅ Alembic migrations
✅ File uploads
✅ Upload validation
✅ Document extraction
✅ Background processing
✅ Text chunking
✅ AI summaries
✅ OpenAI embeddings
✅ pgvector
✅ Semantic retrieval
✅ Basic RAG
✅ Document chat
✅ Conversation history
✅ PDF page citations
✅ Spreadsheet analysis
✅ AI spreadsheet insights
✅ Cached insights
✅ PDF report generation
✅ Folders
✅ Tags
✅ Favorites
✅ Search
✅ Pagination
✅ Dashboard statistics
✅ Reprocessing
✅ File cleanup
✅ CORS
```

---

# 🚧 Future Improvements

Potential future additions include:

- Multi-document knowledge bases
- Cross-document semantic search
- OCR for scanned PDFs
- Streaming AI responses
- Advanced RAG pipelines
- Hybrid search
- Retrieval reranking
- HNSW / IVFFlat indexes for larger datasets
- Redis caching
- Celery or another worker system
- Background job queues
- Cloud object storage
- S3-compatible file storage
- Rate limiting
- Usage/token tracking
- AI model configuration
- Advanced document search
- Citation highlighting
- Shared knowledge bases
- Team workspaces
- Automated tests
- Docker deployment
- Production monitoring

These are intentionally outside the current MVP and should be added only when the workload justifies them.

---

# 🎯 Project Goal

This project was created to explore and demonstrate practical integration between:

```text
Python Backend Engineering
+
REST API Development
+
PostgreSQL
+
Document Processing
+
Data Analysis
+
Vector Databases
+
Semantic Search
+
Retrieval-Augmented Generation
+
LLM Integration
```

The project is intentionally more than a simple AI API wrapper.

It focuses on building the complete infrastructure around AI:

```text
Authentication
+
File Management
+
Data Persistence
+
Background Processing
+
Document Extraction
+
Chunking
+
Embeddings
+
Vector Retrieval
+
AI Generation
+
Source Tracking
+
Analytics
+
Reports
```

The goal is to demonstrate how AI capabilities can be integrated into a real full-stack application architecture.

---

# 🖥️ Frontend

The frontend is maintained in a separate repository and is built using:

- Nuxt
- Vue
- TypeScript
- Quasar
- Pinia
- vee-validate
- Yup
- SCSS

The frontend communicates directly with this backend through the FastAPI REST API.

---

# 📸 Screenshots / API Examples

Additional API examples, Swagger screenshots, architecture diagrams, and application demonstrations can be added as the project evolves.

Potential additions:

```text
Swagger API
Document Upload
RAG Question Answering
pgvector Retrieval
Spreadsheet Analysis
Generated Reports
Database Structure
Architecture Diagram
```

---

# 📄 License

This project is currently intended for educational, portfolio, and development purposes.

---

## 👨‍💻 Author

**Arsam**

Full-stack developer focused on modern web development, Python backend engineering, and AI-powered applications.

GitHub: https://github.com/fatdarkness6
