# DocMind - Agent Instruction Manual (AGENTS.md)

Welcome! This document provides the guidelines, structure, and standard commands required to operate effectively within the DocMind codebase.

## 1. Build, Lint, and Test Commands

### Backend commands
The backend is a Python 3.12+ project managed with `uv`. All commands must be run from the `/backend` directory.

- **Start Dev Server**: `make dev` (or `uv run uvicorn docmind.api.main:app --reload`)
- **Linting & Formatting**: `uv run ruff check .` and `uv run ruff format .`
- **Type Checking**: (If mypy is added, use `uv run mypy .`)
- **Run all tests**: `uv run pytest test/`
- **Run a single test**: `uv run pytest test/test_file.py::test_function_name`

### Frontend commands
The frontend is a Vue 3 project managed by `pnpm`. All commands must be run from the `/frontend` directory.

- **Install Dependencies**: `pnpm install`
- **Start Dev Server**: `pnpm dev`
- **Build for Production**: `pnpm build`
- **Linting**: Run ESLint and Prettier via package scripts (if configured) or your standard extension formatting.

---

## 2. Project Structure

### Backend Directory Layout
The backend is located in `/backend` and focuses on a LangGraph + FastAPI architecture.

- **`docmind/api/`**: Contains FastAPI routers, endpoints, and middleware. This is the entry point for all REST requests. Keep business logic out of here.
- **`docmind/auth/`**: Manages user authentication, JWT handling, and Role-Based Access Control (RBAC).
- **`docmind/core/`**: Houses global configurations, environment parsing (Pydantic settings), and logging setups.
- **`docmind/db/`**: Relational database operations (SQLite). Contains schemas, models, and repository patterns for Users, Knowledge Bases, and Chat histories.
- **`docmind/ingestion/`**: LangGraph workflows responsible for document chunking, code summarization, and saving to Qdrant.
- **`docmind/retrieval/`**: LangGraph workflows responsible for vector search, RAG pipelines, and conversational chat generation.
- **`docmind/vectorstore/`**: Abstractions over the Qdrant client for similarity search and metadata filtering.
- **`scripts/`**: One-off scripts and CLI utilities (e.g., local ingestion).
- **`test/`**: Pytest directory for backend unit/integration testing.

### Frontend Directory Layout
The frontend is located in `/frontend` and focuses on Vue 3, Vite, and Element Plus.

- **`src/api/`**: Centralized Axios modules. Every backend endpoint has a corresponding function here.
- **`src/components/`**: Reusable Vue UI components (e.g., buttons, modals, chat bubbles).
- **`src/stores/`**: Pinia state management modules (e.g., user session, active knowledge base).
- **`src/views/`**: Page-level Vue components that map directly to router definitions.
- **`src/router/`**: Vue Router 5 configuration and navigation guards.

---

## 3. Code Style Guidelines

### Python (Backend)
- **Types**: Always use strict typing (Python 3.12+ features). Rely on standard collections (`list[str]`, `dict[str, Any]`) instead of `typing.List`.
- **Imports**: Group imports properly. Standard library first, third-party second, local application modules last. Rely on `ruff` to automatically sort.
- **Naming Conventions**: `snake_case` for variables, functions, and modules. `PascalCase` for classes. `UPPER_SNAKE_CASE` for constants.
- **Error Handling**: Use custom HTTPExceptions in the API layer. In core logic, raise standard or custom Python exceptions, then catch and translate them in the API endpoints to maintain a clean abstraction.
- **Docstrings**: Add concise docstrings for complex graph nodes and database repository methods.

### Vue (Frontend)
- **Component Naming**: Use `PascalCase` for component file names (e.g., `ChatMain.vue`, `ChatSidebar.vue`). Also use `PascalCase` for component references in templates.
- **Composition API**: Use Vue 3 Composition API exclusively (`<script setup>`). Do not use the Options API.
- **State Management**: Use **Pinia** (located in `src/stores/`). Global state (like authentication tokens or the currently selected Knowledge Base) belongs in a Pinia store. Local UI state belongs in the component's `ref` or `reactive`.
- **API Calls Location**: **NEVER** write raw `axios` or `fetch` calls directly inside Vue components. All API calls must be defined as functions in `src/api/` (using the centralized `http.js` client) and imported into your components or stores. This ensures a single source of truth for base URLs and interceptors.
- **Tailwind CSS**: Use Tailwind utility classes for styling whenever possible instead of custom CSS/SCSS blocks, unless using Element Plus specific style overrides.
- **Error Handling**: Catch API errors in the component or store and display meaningful Element Plus notifications/messages (`ElMessage`).

---

## 4. Operational Directives for Agents

1. **Self-Verification**: When writing backend changes, use the provided `pytest` command to test single functions before delivering.
2. **Safety Check**: Be cautious of executing modifications on `docmind.db` without understanding the SQLite schema. Read `db/` models first.
3. **Environment**: We use Ollama (`nomic-embed-text`) and Qdrant in Docker. Avoid modifying `docker-compose.yml` unless specifically asked. Ensure API keys are checked against `.env.example`.
