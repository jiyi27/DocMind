# DocMind

RAG Knowledge Base powered by LangGraph — document ingestion, vector storage, and conversational retrieval.

## Quick Start

### 1. Start infrastructure

**First time** (creates containers + pulls embedding model):
```bash
make infra-init
```

**Subsequent runs** (containers already exist):
```bash
make infra-up
```

This starts Qdrant (vector DB) and Ollama (embedding model).
The Qdrant collection is created automatically on first API request.

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your OpenRouter API key
```

### 5. Run the API server

```bash
make dev
```

The server starts at http://localhost:8000. API docs at http://localhost:8000/docs.

## Makefile Commands

| Command                                   | Description                                              |
| ----------------------------------------- | -------------------------------------------------------- |
| `make dev`                                | Start API server with hot reload                         |
| `make infra-init`                         | **First time**: create containers + pull embedding model |
| `make infra-up`                           | Start existing containers (subsequent runs)              |
| `make infra-down`                         | Stop containers (keeps data volumes intact)              |
| `docker compose ps`                       | Check container status                                   |
| `docker compose down -v`                  | ⚠️ Stop and delete containers + volumes (data loss)       |
| `make ingest FILE=doc.pdf TITLE="My Doc"` | Ingest a document via CLI                                |

## Usage

### Ingest a document

```bash
curl -X POST http://localhost:8000/ingest \
  -F "file=@document.pdf" \
  -F "title=My Document" \
  -F "url=https://example.com/doc"
```

Or via CLI:

```bash
make ingest FILE=document.pdf TITLE="My Document"
```

### Chat with your knowledge base

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"chatInput": "What is...", "sessionId": "user-123"}'
```

## Project Structure

```
docmind/
├── core/           # Configuration, embedding model
├── ingestion/      # Document loading, splitting, vector storage (LangGraph)
├── retrieval/      # RAG chat with citations (LangGraph)
├── tools/          # Reusable tools (search, etc.)
├── vectorstore/    # Vector DB abstraction layer
└── api/            # FastAPI endpoints
```
