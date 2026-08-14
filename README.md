# AI Document Intelligence Backend

A FastAPI-based backend for an AI-powered document intelligence platform.

The application allows users to upload documents, automatically extract and process their content, generate AI summaries, ask questions about documents, perform semantic search using embeddings and PostgreSQL `pgvector`, analyze spreadsheet data, and generate downloadable reports.

## Core Features

- JWT authentication
- PDF, DOCX, TXT, CSV, and XLSX uploads
- Background document processing
- AI-generated document summaries
- Document Q&A and conversation history
- RAG-based semantic search
- OpenAI embeddings
- PostgreSQL + pgvector
- PDF page-aware citations
- CSV/XLSX analysis with Pandas
- AI-generated spreadsheet insights
- Folders, tags, and favorites
- PDF report generation
- Document reprocessing
- Pagination, filtering, and search

## Tech Stack

**Backend:** FastAPI, Python
**Database:** PostgreSQL, SQLAlchemy, Alembic
**AI:** OpenAI API, Embeddings, RAG
**Vector Search:** pgvector
**Data Processing:** Pandas, pypdf, python-docx, openpyxl
**Authentication:** JWT

This project is being built as a practical exploration of Python backend development, AI engineering, document processing, and Retrieval-Augmented Generation.
