# DocMind Project Contract

## Build And Test (Backend)
*Run all from the `/backend` directory*
- Dev Server: `make dev` (or `uv run uvicorn docmind.api.main:app --reload`)
- Lint & Format: `uv run ruff check .` and `uv run ruff format .`
- Test All: `uv run pytest test/`
- Test Single: `uv run pytest test/test_file.py::test_function_name`
- CLI Ingestion: `make ingest FILE=path/to/file.md TITLE="My Doc"`

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
- **Backend Errors**: Raise standard exceptions in core logic; catch and translate to `HTTPException` inside `docmind/api/`.
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
- Display API errors using Element Plus notifications (`ElMessage`) on the frontend.
- Check `.env.example` to ensure required embedding and LLM API keys are present in `.env`.

## Verification
- Test single backend functions using the specific `pytest` command before delivering.
- Run `uv run ruff format .` and `uv run ruff check .` after making backend modifications.
- Ensure the frontend builds without errors (`pnpm build`) after structural UI changes.