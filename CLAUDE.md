# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Build And Test (Backend)
*Run all from the `/backend` directory*
- Dev Server: `make dev` (or `uv run uvicorn docmind.api.main:app --reload`)
- Lint & Format: `uv run ruff check .` and `uv run ruff format .`
- Test All: `uv run pytest test/`
- Test Single: `uv run pytest test/test_file.py::test_function_name`
- CLI Ingestion: `make ingest FILE=path/to/file.md TITLE="My Doc"`

**CRITICAL DIRECTIVE**: This is a monorepo. ALL backend commands must be run from the `/backend` directory. ALL frontend commands must be run from the `/frontend` directory. Do not run `uv` or `pnpm` commands from the root directory.

## Build And Test (Frontend)
*Run all from the `/frontend` directory*
- Install: `pnpm install`
- Dev: `pnpm dev`
- Build: `pnpm build`

## Architecture Boundaries (Backend)
- HTTP handlers live in `docmind/api/`
- **Do not put business/domain logic in API handlers**
- LangGraph workflows live in `docmind/ingestion/` and `docmind/retrieval/`
- Relational database (SQLite) operations live in `docmind/db/`
- Vector database (Qdrant) abstractions live in `docmind/vectorstore/`

## Architecture Boundaries (Frontend)
- API calls and Axios clients live in `src/api/`
- Global state management lives in `src/stores/` (Pinia)
- Page-level configurations live in `src/views/`
- Reusable UI elements live in `src/components/`

## Coding Conventions
- **Backend Types**: Use strict Python 3.12+ typing (e.g., `list[str]`, `dict[str, Any]` instead of `typing.List`).
- **Backend Naming**: `snake_case` for variables/functions/modules, `PascalCase` for classes.
- **Code Comments**: Prefer purpose-driven comments that explain intent or constraints, not comments that just restate variable names or obvious code behavior.
- **Backend Errors**: Raise standard exceptions in core logic; catch and translate to `HTTPException` inside `docmind/api/`.
- **Backend Defaults**: Define business defaults in exactly one place. Prefer API/schema defaults for request-time behavior, or shared constants/config for cross-layer defaults. Do not repeat literal defaults like `"chunk"` or `True` across router/node/worker code.
- **Frontend Paradigm**: Use Vue 3 Composition API (`<script setup>`) exclusively.
- **Frontend Naming**: Component files must use `PascalCase` (e.g., `ChatMain.vue`).
- **Frontend Styling**: Prefer Tailwind CSS utility classes over custom CSS/SCSS blocks.

## Safety Rails

### NEVER
- Write raw `axios` or `fetch` calls directly inside Vue components (always use `src/api/` modules).
- Use the Vue Options API.
- Modify `docker-compose.yml` or `docmind.db` schemas without analyzing the impact and gaining explicit approval.
- Expose raw internal Python exceptions directly to the frontend API responses.

### ALWAYS
- Group Python imports properly (Standard library -> Third-party -> Local `docmind.*` modules).
- Understand the custom LangGraph state-machine behavior before altering `docmind/ingestion/` nodes.
- When adding or changing config/default values, keep `.env`, `.env.example`, and the startup validation path consistent so missing values fail fast instead of silently falling back.
- When changing KB embedding persistence or lookup behavior, keep `GET /kb/embedding-options` and the create/edit KB UX aligned so provider-specific requirements stay consistent across backend and frontend.
- Display API errors using Element Plus notifications (`ElMessage`) on the frontend.
- Check `.env.example` to ensure required runtime settings and API keys are present in `.env`.
- If code is modified, provide a concise English git commit message at the end of the response.

## Verification Strategy

**DO NOT** write unit tests for every single function. It is bloated and inefficient. Instead, follow this funnel:

1. **Static Analysis (Always First)**
   - Backend: Must run from `backend/` directory (`cd backend && uv run ruff check .` and `uv run ruff format .`) to catch syntax/import errors.
   - Frontend: Must run from `frontend/` directory (`cd frontend && pnpm build`) to catch unresolvable imports and template compilation errors.

2. **Disposable Scripts (For Internal Logic)**
   - When modifying DB queries, core logic, or LangGraph nodes, write a quick `tmp_verify.py` script inside the `backend/` directory to test the specific function.
   - Run it (`cd backend && uv run python tmp_verify.py`), verify the `print()` output in the terminal, and **DELETE** the script before committing.

3. **API Slice Testing (For Endpoints)**
   - When modifying FastAPI endpoints, prefer using FastAPI's `TestClient` in a single pytest file (run via `cd backend && uv run pytest test/path_to_test.py`) to verify the HTTP cycle.

4. **Targeted Unit Tests (For Complex Domain)**
   - Only write permanent `pytest` unit tests for complex, pure functions (e.g., custom Markdown splitters, complex LangGraph state reducers) where edge cases are frequent. Always run these from the `backend/` directory.
