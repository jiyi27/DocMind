# DocMind

RAG Knowledge Base powered by LangGraph — document ingestion, vector storage, and conversational retrieval.

## Quick Start

### 1. Start infrastructure

```bash
docker compose up -d
```

This starts Qdrant (vector DB) and Ollama (embedding model).

### 2. Pull embedding model

```bash
docker exec ollama ollama pull nomic-embed-text:latest
```

### 3. Create Qdrant collection

```bash
curl -X PUT http://localhost:6333/collections/knowledge_base \
  -H "Content-Type: application/json" \
  -d '{
    "vectors": {
      "size": 768,
      "distance": "Cosine"
    }
  }'
```

### 4. Configure environment

```bash
cp .env.example .env
# Edit .env with your OpenRouter API key
```

### 5. Run the API server

```bash
uv run dev
```

The server starts at http://localhost:8000. API docs at http://localhost:8000/docs.

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
uv run python scripts/ingest_file.py document.pdf --title "My Document"
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
