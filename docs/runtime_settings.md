## Main Configuration Categories

We standardize all backend config into three categories.

### 1. Startup-required

These must exist before the process can safely start. Missing values should fail fast and stop boot.

### 2. Runtime-required but not startup-required

These may be empty at startup. The app can boot, but the related feature must fail with a clear `ConfigError` when used.

### 3. Runtime config with business defaults

These do not need to be manually configured for the system to behave reasonably. If missing in `system_settings`, the system writes the hardcoded default into the DB at startup and exposes it in the System Settings page.

This means

- no hidden runtime fallback for critical external dependencies
- clear current values in the UI for defaultable settings
- no need to query SQLite on every request

## Configuration Summary

### 1. Startup-required

Set in `.env`. Missing required values cause the process to exit immediately on boot.

| Config | Required | Default |
| ----------------------- | -------- | ----------------- |
| `JWT_SECRET_KEY` | yes | — |
| `SUPER_ADMIN_USERNAMES` | yes | — |
| `JWT_ALGORITHM` | no | `HS256` |
| `JWT_EXPIRE_MINUTES` | no | `1440` (24 hours) |
| `LOG_LEVEL` | no | `INFO` |
| `LOG_DIR` | no | `logs` |
| `CORS_ORIGINS` | no | `*` |
| `DOCMIND_DB_PATH` | no | `data/docmind.db` |

### 2. Runtime-required

Configured via the admin UI and stored in SQLite. The app boots without them, but the related feature raises a `ConfigError` when used.

| Config | Required | Behavior if missing |
| --------------------------------- | ----------- | --------------------------------------- |
| `qdrant_url` | yes | vector features fail when used |
| `llm_base_url` | yes | chat / generation fail when used |
| `llm_api_key` | yes | chat / generation fail when used |
| `llm_model` | yes | chat / generation fail when used |
| `confluence_base_url` | conditional | Confluence disabled / unavailable |
| `confluence_pat` | conditional | Confluence disabled / unavailable |
| `ingestion_image_vision_api_key` | conditional | multimodal image processing unavailable |
| `ingestion_image_vision_model` | conditional | multimodal image processing unavailable |
| `ingestion_image_vision_base_url` | conditional | multimodal image processing unavailable |

### 3. Runtime-defaulted

Configured via the admin UI and stored in SQLite. On every startup, `_bootstrap_system_settings` inserts the hardcoded default via `INSERT OR IGNORE` — only takes effect if the key is not yet present in the DB.

| Config | Default |
| ------------------------------------- | ------- |
| `ingestion_chunk_size` | `500` |
| `ingestion_chunk_overlap` | `50` |
| `ingestion_enable_code_summarization` | `false` |
| `ingestion_image_processor` | `none` |
| `retrieval_top_k` | `3` |
| `retrieval_max_full_docs` | `2` |
| `retrieval_max_full_doc_chars` | `8000` |
| `chat_max_messages` | `20` |

Notes

- Only `JWT_SECRET_KEY` and `SUPER_ADMIN_USERNAMES` are hard-required in `.env`. All other startup-required fields have safe code defaults.
- "default written into DB at startup" means `_bootstrap_system_settings` runs on every startup via `INSERT OR IGNORE` — it only inserts a row when the key is absent from `system_settings`. Existing values are never overwritten. Only the eight `runtime-defaulted` settings listed above are bootstrapped; `runtime-required` settings (qdrant, llm, confluence, image vision) are never seeded.
- For runtime-required values, no implicit fallback exists. The admin page is the only way to configure them.
