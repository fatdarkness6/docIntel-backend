# Document Intelligence Backend

A FastAPI backend for secure document upload, asynchronous processing, AI summaries, retrieval-augmented question answering, spreadsheet analysis, PDF reports, organization, and real-time processing updates through Server-Sent Events (SSE).

The API is user-scoped: documents, folders, tags, questions, reports, and live status streams are accessible only to the authenticated owner.

## What the application does

- Registers users and authenticates them with bearer JWT access tokens
- Accepts PDF, DOCX, TXT, CSV, and XLSX uploads up to 20 MB
- Extracts text and splits it into searchable chunks
- Creates 512-dimensional OpenAI embeddings stored with pgvector
- Generates concise AI document summaries
- Answers document questions using semantic retrieval and source citations
- Preserves short question history for follow-up questions
- Calculates spreadsheet statistics and generates cached AI insights
- Creates downloadable PDF reports
- Organizes documents with folders, tags, favorites, search, and pagination
- Streams durable processing updates over authenticated SSE connections
- Removes associated chunks, questions, status events, uploads, and reports when a document is deleted

## Architecture

```mermaid
flowchart LR
    Client["Frontend client"] -->|"Bearer JWT"| API["FastAPI /api/v1"]
    API --> DB[("PostgreSQL + pgvector")]
    API --> Files["Local uploads/ and reports/"]
    API --> Tasks["FastAPI background processing"]
    Tasks --> Extract["Extract and chunk"]
    Extract --> OpenAI["OpenAI summaries and embeddings"]
    OpenAI --> DB
    Tasks --> Events["Durable status event log"]
    Events --> DB
    DB -->|"SSE status stream"| Client
```

Document processing follows this lifecycle:

| Stage                | Progress | Description                                              |
| -------------------- | -------: | -------------------------------------------------------- |
| `queued`             |       0% | The document is waiting for background processing        |
| `extracting`         |      15% | Text or spreadsheet content is being extracted           |
| `chunking`           |      40% | Extracted content is being split into sections           |
| `analyzing`          |      60% | Embeddings are being generated                           |
| `generating_summary` |      85% | The AI summary is being created                          |
| `completed`          |     100% | Processing finished successfully                         |
| `failed`             |        — | Processing failed; only a safe public message is exposed |

Every state transition updates the document's latest status and appends a durable event to PostgreSQL. SSE subscribers therefore work across multiple API or processing workers without relying on a process-local queue.

## Tech stack

| Area            | Technology                                               |
| --------------- | -------------------------------------------------------- |
| API             | FastAPI, Uvicorn, Pydantic                               |
| Authentication  | OAuth2 password flow, JWT, pwdlib password hashing       |
| Database        | PostgreSQL, SQLAlchemy 2, Alembic                        |
| Vector search   | pgvector, cosine distance                                |
| AI              | OpenAI Responses API and Embeddings API                  |
| Processing      | pypdf, python-docx, pandas, openpyxl                     |
| Reports         | ReportLab                                                |
| Realtime status | Server-Sent Events with FastAPI `StreamingResponse`      |
| Tests           | Python `unittest`, FastAPI `TestClient`, isolated SQLite |

The application currently uses:

- `gpt-5-nano` for summaries, document answers, and dataset insights
- `text-embedding-3-small` with 512 dimensions for semantic retrieval

## Project structure

```text
app/
├── api/
│   ├── dependencies.py
│   ├── router.py
│   └── routes/
│       ├── auth.py
│       ├── documents.py
│       ├── folders.py
│       ├── health.py
│       └── tags.py
├── core/
│   ├── config.py
│   └── security.py
├── db/
│   └── session.py
├── models/
│   ├── document.py
│   ├── document_chunk.py
│   ├── document_question.py
│   ├── document_status_event.py
│   ├── document_tag.py
│   ├── folder.py
│   ├── tag.py
│   └── user.py
├── schemas/
└── services/
    ├── ai_service.py
    ├── analytics_service.py
    ├── document_service.py
    ├── document_status_service.py
    ├── embedding_service.py
    ├── report_service.py
    └── text_service.py
migrations/
tests/
uploads/
reports/
```

Route functions handle HTTP concerns, while focused services own extraction, chunking, AI calls, embeddings, analytics, report generation, and status streaming.

## Getting started

### Prerequisites

- Python 3.11 or newer
- PostgreSQL
- The pgvector PostgreSQL extension
- An OpenAI API key

### 1. Clone and enter the project

```bash
git clone https://github.com/fatdarkness6/document-intelligence-backend.git
cd document-intelligence-backend
```

### 2. Create and activate a virtual environment

Windows PowerShell:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

macOS or Linux:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install dependencies

```bash
python -m pip install fastapi "uvicorn[standard]" sqlalchemy alembic "psycopg[binary]" pgvector openai pydantic-settings pyjwt "pwdlib[argon2]" python-multipart email-validator pypdf python-docx pandas openpyxl reportlab httpx
```

### 4. Create the PostgreSQL database

Create a database, connect to it, and enable pgvector:

```sql
CREATE DATABASE document_intelligence;
\c document_intelligence
CREATE EXTENSION IF NOT EXISTS vector;
```

### 5. Configure environment variables

Copy `.env.example` to `.env` and provide real values:

```env
DATABASE_URL=postgresql+psycopg://postgres:password@localhost:5432/document_intelligence
JWT_SECRET_KEY=replace-with-a-long-random-secret
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
OPENAI_API_KEY=sk-...
FRONTEND_URL=http://localhost:3000

SSE_POLL_INTERVAL_SECONDS=1
SSE_HEARTBEAT_INTERVAL_SECONDS=20
SSE_MAX_CONNECTION_SECONDS=1800
```

| Variable                         | Purpose                                       |
| -------------------------------- | --------------------------------------------- |
| `DATABASE_URL`                   | SQLAlchemy PostgreSQL connection URL          |
| `JWT_SECRET_KEY`                 | Secret used to sign access tokens             |
| `JWT_ALGORITHM`                  | JWT signing algorithm; defaults to `HS256`    |
| `ACCESS_TOKEN_EXPIRE_MINUTES`    | Access-token lifetime; defaults to 30 minutes |
| `OPENAI_API_KEY`                 | OpenAI API credential                         |
| `FRONTEND_URL`                   | The origin allowed by CORS                    |
| `SSE_POLL_INTERVAL_SECONDS`      | Delay between durable event-log checks        |
| `SSE_HEARTBEAT_INTERVAL_SECONDS` | Interval between SSE heartbeat events         |
| `SSE_MAX_CONNECTION_SECONDS`     | Maximum lifetime of one SSE connection        |

Do not commit the real `.env` file.

### 6. Apply migrations

```bash
alembic upgrade head
```

### 7. Start the API

```bash
uvicorn app.main:app --reload
```

The local API is available at:

- API: http://127.0.0.1:8000
- Swagger UI: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc
- OpenAPI schema: http://127.0.0.1:8000/openapi.json

## Authentication

All document, folder, and tag operations require:

```http
Authorization: Bearer <access-token>
```

Register:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d "{\"email\":\"user@example.com\",\"password\":\"strong-password\"}"
```

Login uses OAuth2 form data. Send the email in the `username` field:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/auth/login \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=user@example.com&password=strong-password"
```

Example response:

```json
{
  "access_token": "<jwt>",
  "token_type": "bearer"
}
```

Tokens must be sent in the authorization header. Do not place access tokens in query strings.

## Uploading and processing documents

Upload a supported file as multipart form data:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/documents/upload \
  -H "Authorization: Bearer <access-token>" \
  -F "file=@example.pdf"
```

Supported formats:

| Extension | Processing                                                    |
| --------- | ------------------------------------------------------------- |
| `.pdf`    | Text extraction with page-aware chunks and citations          |
| `.docx`   | Paragraph text extraction                                     |
| `.txt`    | UTF-8 text extraction with invalid binary-content checks      |
| `.csv`    | pandas loading, text conversion, and spreadsheet analysis     |
| `.xlsx`   | Workbook validation, pandas loading, and spreadsheet analysis |

Uploads are validated by extension and file structure or content. Files larger than 20 MB are rejected. The upload request creates the document with a `processing` status and schedules background work.

The existing `GET /api/v1/documents/{document_id}` endpoint exposes the latest status as a fallback and includes:

- `status`
- `processing_stage`
- `processing_progress`
- `status_message`
- `status_updated_at`
- `status_event_id`

## Real-time status with SSE

Subscribe at:

```http
GET /api/v1/documents/{document_id}/events
Authorization: Bearer <access-token>
Accept: text/event-stream
```

The endpoint verifies authentication and ownership before opening the stream. Unknown documents and documents owned by another user both return `404` to avoid leaking resource existence. Missing or invalid authentication returns `401`.

Response headers include:

```http
Content-Type: text/event-stream
Cache-Control: no-cache
Connection: keep-alive
X-Accel-Buffering: no
```

The server immediately sends the latest database state. Processing updates then arrive with increasing per-document event IDs:

```text
event: status
id: 3
data: {"document_id":123,"status":"processing","stage":"analyzing","progress":60,"message":"Analyzing document content","updated_at":"2026-08-15T10:30:00Z"}
```

Available event names:

| Event       | Behavior                                         |
| ----------- | ------------------------------------------------ |
| `status`    | Queued or in-progress update                     |
| `completed` | Final success update; the connection closes      |
| `failed`    | Safe final failure update; the connection closes |
| `ping`      | Heartbeat while processing continues             |

Clients may reconnect with the `Last-Event-ID` header. The latest durable snapshot is always sent first, so clients can compare event IDs and deduplicate an already handled event. A connection closes on a terminal event, client disconnection, or the configured maximum duration.

Native `EventSource` cannot attach an authorization header. A fetch-based client can:

```js
async function watchDocument(documentId, token, lastEventId) {
  const headers = {
    Authorization: "Bearer " + token,
    Accept: "text/event-stream",
  };

  if (lastEventId) {
    headers["Last-Event-ID"] = String(lastEventId);
  }

  const response = await fetch("/api/v1/documents/" + documentId + "/events", {
    headers,
  });

  if (!response.ok || !response.body) {
    throw new Error("SSE subscription failed: " + response.status);
  }

  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader();

  let buffer = "";

  while (true) {
    const result = await reader.read();
    if (result.done) return;

    buffer += result.value;
    const frames = buffer.split("\n\n");
    buffer = frames.pop() || "";

    for (const frame of frames) {
      const fields = {};

      for (const line of frame.split("\n")) {
        const separator = line.indexOf(":");
        if (separator === -1) continue;
        fields[line.slice(0, separator)] = line
          .slice(separator + 1)
          .trimStart();
      }

      const data = JSON.parse(fields.data);

      if (fields.id) {
        lastEventId = fields.id;
      }

      if (fields.event !== "ping") {
        console.log(fields.event, data);
      }
    }
  }
}
```

If SSE cannot be established, fetch the document detail endpoint once as a fallback rather than continuously polling it.

## Document question answering

Questions can be asked only after processing completes:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/documents/123/ask \
  -H "Authorization: Bearer <access-token>" \
  -H "Content-Type: application/json" \
  -d "{\"question\":\"What are the main conclusions?\"}"
```

The RAG flow:

1. Embeds the question using the same 512-dimensional embedding model.
2. Retrieves the five nearest document chunks by cosine distance.
3. Removes chunks that are too far from the best match.
4. Sends up to three relevant chunks to the language model.
5. Returns the answer with chunk, page, and preview citations.
6. Stores the question, answer, and sources for conversation history.

The latest two questions are supplied as conversational context. Previous answers help resolve references but are not treated as factual evidence.

## Spreadsheet intelligence

CSV and XLSX documents support:

- Row and column counts
- Column data types
- Missing-value counts
- Numeric descriptive statistics
- AI-generated observations, trends, anomalies, and data-quality notes
- Cached AI insights to prevent repeated model calls

Spreadsheet-only endpoints return `400` when used with other document types.

## API reference

All routes use the `/api/v1` prefix.

### Health

| Method | Endpoint           | Authentication | Description           |
| ------ | ------------------ | -------------- | --------------------- |
| GET    | `/health`          | No             | Application health    |
| GET    | `/health/database` | No             | Database connectivity |

### Authentication

| Method | Endpoint                | Authentication | Description                  |
| ------ | ----------------------- | -------------- | ---------------------------- |
| POST   | `/auth/register`        | No             | Register a user              |
| POST   | `/auth/login`           | No             | Obtain a bearer access token |
| GET    | `/auth/me`              | Bearer         | Get the current user         |
| POST   | `/auth/change-password` | Bearer         | Change the current password  |

### Documents and AI

| Method | Endpoint                                 | Description                               |
| ------ | ---------------------------------------- | ----------------------------------------- |
| POST   | `/documents/upload`                      | Upload and queue a document               |
| GET    | `/documents`                             | List and filter the user's documents      |
| GET    | `/documents/stats`                       | Get dashboard statistics                  |
| GET    | `/documents/{document_id}`               | Get document details and latest status    |
| PATCH  | `/documents/{document_id}`               | Rename a document                         |
| DELETE | `/documents/{document_id}`               | Delete a document and related resources   |
| GET    | `/documents/{document_id}/events`        | Stream processing status with SSE         |
| POST   | `/documents/{document_id}/reprocess`     | Reprocess the original upload             |
| POST   | `/documents/{document_id}/ask`           | Ask a grounded document question          |
| GET    | `/documents/{document_id}/questions`     | Get question history                      |
| GET    | `/documents/{document_id}/analysis`      | Analyze a CSV or XLSX document            |
| GET    | `/documents/{document_id}/insights`      | Get or create cached spreadsheet insights |
| GET    | `/documents/{document_id}/report`        | Download a generated PDF report           |
| PATCH  | `/documents/{document_id}/favorite`      | Set favorite status                       |
| PATCH  | `/documents/{document_id}/folder`        | Move into or out of a folder              |
| POST   | `/documents/{document_id}/tags`          | Attach a tag                              |
| DELETE | `/documents/{document_id}/tags/{tag_id}` | Remove a tag                              |

Document-list query parameters:

| Parameter   | Default | Description                      |
| ----------- | ------: | -------------------------------- |
| `search`    |       — | Case-insensitive filename search |
| `favorite`  |       — | Filter by favorite status        |
| `folder_id` |       — | Filter by folder                 |
| `tag_id`    |       — | Filter by tag                    |
| `page`      |       1 | Page number                      |
| `per_page`  |      10 | Results per page, from 1 to 100  |

### Folders and tags

| Method | Endpoint               | Description     |
| ------ | ---------------------- | --------------- |
| POST   | `/folders`             | Create a folder |
| GET    | `/folders`             | List folders    |
| PATCH  | `/folders/{folder_id}` | Rename a folder |
| DELETE | `/folders/{folder_id}` | Delete a folder |
| POST   | `/tags`                | Create a tag    |
| GET    | `/tags`                | List tags       |

All endpoints in these sections are scoped to the authenticated user.

## Data model

| Table                    | Purpose                                                                |
| ------------------------ | ---------------------------------------------------------------------- |
| `users`                  | Accounts and password hashes                                           |
| `documents`              | File metadata, extracted content, summary, insights, and latest status |
| `document_chunks`        | Searchable text chunks, page numbers, and vector embeddings            |
| `document_questions`     | Question history, answers, and citation JSON                           |
| `document_status_events` | Durable, ordered processing transitions                                |
| `folders`                | User-owned folders                                                     |
| `tags`                   | User-owned tags                                                        |
| `document_tags`          | Document-to-tag association                                            |

Document deletion cascades to chunks, questions, tags associations, and status events. The uploaded file and generated report are also removed from local storage.

## Security behavior

- Passwords are hashed and never stored in plaintext.
- JWTs expire according to `ACCESS_TOKEN_EXPIRE_MINUTES`.
- Protected resources are filtered by the authenticated user's ID.
- Cross-user document access is rejected.
- SSE authentication uses the bearer header, never a query parameter.
- Failed SSE payloads contain only a generic message, not stack traces or internal paths.
- Uploads use generated storage names and validated file contents.
- CORS permits only the configured `FRONTEND_URL` origin.

Use a strong JWT secret, HTTPS, managed secret storage, and production-safe database credentials outside local development.

## Testing

Run the test suite:

```bash
python -m unittest discover -s tests -v
```

The current suite covers:

- Missing SSE authentication
- Invalid and cross-user document access
- Immediate initial state
- Processing, completed, and failed events
- Terminal connection closure
- Client disconnection cleanup
- Reconnection behavior
- Heartbeats
- Multiple simultaneous subscribers
- Resource cleanup after disconnect
- Repository-level ownership filtering

## Operational notes

- Uploaded files are stored under `uploads/`.
- Generated reports are stored under `reports/`.
- Processing currently runs through FastAPI `BackgroundTasks`. For heavy production workloads, move processing to a dedicated task system such as Celery, Dramatiq, or RQ.
- SSE state and event history are durable in PostgreSQL, but subscribers check that event log at the configured polling interval. Redis Pub/Sub or PostgreSQL notifications can later reduce polling latency without changing the API contract.
- Status event history grows over time. Production deployments should define an event-retention policy.
- Local file storage is suitable for development and single-host deployments. Multi-host production deployments should use shared object storage.
- The document detail endpoint remains available as a one-time fallback when SSE is unavailable.

## License

This project does not currently include an explicit license file. Add one before distributing or accepting external contributions.

## Author

Arsam — full-stack Engineer focused on modern web development, Python backend engineering, and AI-powered applications.

GitHub: https://github.com/fatdarkness6
