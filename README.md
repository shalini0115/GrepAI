# AI Log Observability and Root Cause Analysis

## Stack
- FastAPI for REST endpoints
- Celery and Redis for asynchronous ingestion
- ChromaDB for vector storage and metadata filtering
- LangChain and OpenAI for retrieval-augmented generation
- Docker Compose for service deployment

## Run directly from the repository root

Install dependencies into the Python installation selected by `python3`:

    python3 -m pip install -r requirements.txt

Set the LLM key in the shell when using OpenAI:

    export OPENAI_API_KEY="your-key"

Start Redis and ChromaDB:

    docker compose up -d redis chromadb

Start the API:

    python3 -m uvicorn app.main:app --reload

Start the worker in another terminal:

    python3 -m celery -A app.tasks:celery_app worker --loglevel=INFO

API documentation: http://localhost:8000/docs

## Important status

This repository contains a partial implementation. Upload validation, basic log parsing,
and initial tests exist. Celery dispatch, durable job tracking, embedding/indexing,
metadata-filtered retrieval, and RCA still require implementation.

The Docker Compose services use containers, but no local Python virtual environment
is required. API keys are supplied through shell environment variables, not files.
