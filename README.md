# DocMind

A robust, multi-tenant RAG (Retrieval-Augmented Generation) Knowledge Base system. DocMind seamlessly handles document ingestion, vector storage, and conversational retrieval with proper user data isolation.

## 🌟 Key Features

- **Multi-Tenant Architecture**: User registration, JWT-based authentication, and proper data isolation (users are tied to specific Knowledge Bases).
- **Advanced RAG Pipelines**: Orchestrated via **LangGraph** for both document ingestion and conversational retrieval workflows.
- **Relational Metadata Management**: Uses SQLite to efficiently track Users, Knowledge Bases, and Document upload histories.
- **High-Performance Vector Search**: Uses **Qdrant** for scalable and fast similarity searches with dynamic collection creation per knowledge base.
- **Flexible LLM & Embeddings**: Built-in support for local embeddings via **Ollama** (`nomic-embed-text`) and external LLMs via OpenAI-compatible endpoints (e.g., **OpenRouter**).

## 🏗️ Architecture & Tech Stack

- **Backend Framework**: Python 3.12+, FastAPI, Pydantic, Uvicorn
- **Package Manager**: `uv` - An extremely fast Python package manager
- **Workflow Orchestration**: LangGraph, LangChain
- **Vector Database**: Qdrant (Docker)
- **Local Embedding Model**: Ollama (Docker) - `nomic-embed-text`
- **Relational DB**: SQLite

## 📂 Project Structure

```text
DocMind/
├── backend/                  # Backend application source code
│   ├── docmind/
│   │   ├── api/              # FastAPI endpoints and routers (auth, chat, ingest, kb)
│   │   ├── auth/             # JWT authentication and role-based access control
│   │   ├── core/             # Configuration, logging, exception handling
│   │   ├── db/               # SQLite database setup, DDL models, and Repositories
│   │   ├── ingestion/        # LangGraph workflow for document chunking and vectorDB insertion
│   │   ├── retrieval/        # LangGraph workflow for question answering and source retrieval
│   │   ├── tools/            # Reusable AI sub-tools
│   │   └── vectorstore/      # Qdrant abstraction layer
│   ├── data/                 # Local directory for SQLite and Qdrant volume data
│   ├── logs/                 # Application rotating logs
│   ├── Makefile              # Helper commands for running and deployment
│   ├── docker-compose.yml    # Infrastructure definitions (Qdrant & Ollama)
│   └── pyproject.toml        # uv dependencies configuration
└── frontend/                 # Frontend application (Planned/WIP)
```

## 🚀 Quick Start

### 1. Prerequisites

- [Docker & Docker Compose](https://docs.docker.com/get-docker/) (For running Qdrant and Ollama)
- [uv](https://github.com/astral-sh/uv) (For ultra-fast Python dependency management)

### 2. Start Infrastructure 

All commands should be run from the `backend/` directory:

```bash
cd backend
```

**First time only** (Creates containers & pulls the embedding model):
```bash
make infra-init
```

**Subsequent runs** (Starts existing containers):
```bash
make infra-up
```

### 3. Configure Environment

Copy the example environment file and configure your API keys:

```bash
cp .env.example .env
```
Ensure you edit `.env` and set your `LLM_API_KEY` (e.g. OpenRouter key) and generate a secure `JWT_SECRET_KEY`.

### 4. Run the API Server

Start the FastAPI application with watch-mode enabled:

```bash
make dev
```
The server will be available at `http://localhost:8000`.
Visit `http://localhost:8000/docs` to interact with the interactive Swagger API documentation.

## 💻 Usage & API Reference

DocMind provides a complete RESTful API, accessible via the interactive `/docs` UI.
Key flows include:
1. **Authentication**: Use `POST /auth/register` and `POST /auth/login` to obtain a JWT.
2. **Knowledge Base Management**: Super-admins can create KBs via `POST /kb`.
3. **Ingestion**: Upload documents using `POST /ingest` (kicks off the LangGraph ingestion pipeline).
4. **Chat**: Query your Knowledge Base using `POST /chat` (triggers the LangGraph retrieval workflow).

### Utility Commands

| Command | Description |
| ------- | ----------- |
| `make dev` | Start API server with hot reload |
| `make infra-init` | **First time**: create containers + pull embedding model |
| `make infra-up` | Start existing containers (subsequent runs) |
| `make infra-down` | Stop running containers (keeps data volumes intact) |
| `docker compose ps` | Check container status |
| `docker compose down -v` | ⚠️ Stop and delete containers + volumes (data loss) |

## 🗺️ Roadmap

- [ ] **Frontend UI** — Build a responsive web interface covering core user flows: knowledge base management, document ingestion, and conversational chat.
- [ ] **Document Storage with MinIO** — Persist uploaded documents to an object store during ingestion, exposing a download endpoint for users to retrieve original files.
- [ ] **LLM-based Document Pre-processing** — Introduce a pre-ingestion pipeline utilizing an LLM to normalize document structure and improve chunking quality before vectorization.
