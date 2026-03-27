# Runtime Settings Refactor Plan

## Purpose

Refactor backend configuration so that:

1. Startup-critical config still comes from `.env`
2. Business/runtime config is persisted in `system_settings`
3. Runtime code continues reading from one in-memory global config object
4. The admin page uses one unified save action instead of multiple module-specific saves

This is a persistence refactor, not a "read from DB on every request" design.

Target model:

1. Read startup-critical env config at process boot
2. Initialize SQLite
3. Initialize runtime settings cache from `system_settings` (write hardcoded defaults for any missing runtime-defaulted keys)
4. Business code reads from the cache
5. If a runtime-required value is empty when a feature is used, raise `ConfigError` immediately — no DB re-read
6. Admin updates write to DB, then atomically refresh the runtime cache

---

## Main Configuration Categories

We standardize all backend config into three categories.

### 1. Startup-required

These must exist before the process can safely start. Missing values should fail fast and stop boot.

### 2. Runtime-required but not startup-required

These may be empty at startup. The app can boot, but the related feature must fail with a clear `ConfigError` when used.

### 3. Runtime config with business defaults

These do not need to be manually configured for the system to behave reasonably. If missing in `system_settings`, the system writes the hardcoded default into the DB at startup and exposes it in the System Settings page.

This means:

- no hidden runtime fallback for critical external dependencies
- clear current values in the UI for defaultable settings
- no need to query SQLite on every request

---

## Global Config Model

The runtime model should remain "read from one global config object in memory".

Recommended split:

- `app_settings`
  - loaded from `.env`
  - startup-only
- `runtime_settings`
  - loaded from `system_settings` table at startup
  - cached in memory as a typed object
  - refreshed atomically after admin updates (use a lock to protect the swap)

Normal request flow:

- business code reads `runtime_settings`
- does not directly query `system_settings`

Error behavior:

- if a runtime-required field is empty in cache when a feature is invoked, raise `ConfigError` immediately
- no lazy DB re-read — the cache is the only source of truth at runtime
- the admin page is the only way to populate runtime-required values

Cache refresh safety:

- use a `threading.Lock` when replacing the cache object after an admin save
- background workers (IngestionQueueWorker, ConfluenceSyncWorker) may be reading the cache concurrently

---

## Configuration Summary Table

| Config                                | Category          | Required    | Default                | Behavior if missing                         |
| ------------------------------------- | ----------------- | ----------- | ---------------------- | ------------------------------------------- |
| `JWT_SECRET_KEY`                      | startup-required  | yes         | none                   | app must not start                          |
| `JWT_ALGORITHM`                       | startup-required  | no          | `HS256`                | use default                                 |
| `JWT_EXPIRE_MINUTES`                  | startup-required  | no          | `1440` (24 hours)      | use default                                 |
| `LOG_DIR`                             | startup-required  | no          | fixed code default     | use default                                 |
| `LOG_LEVEL`                           | startup-required  | no          | `INFO`                 | use default                                 |
| `CORS_ORIGINS`                        | startup-required  | no          | `*`                    | use default                                 |
| `SUPER_ADMIN_USERNAMES`               | startup-required  | yes         | none                   | app must not start                          |
| `DOCMIND_DB_PATH`                     | startup-required  | no          | code default path      | use default                                 |
| `qdrant_url`                          | runtime-required  | yes         | none                   | vector features fail when used              |
| `llm_base_url`                        | runtime-required  | yes         | none                   | chat / generation fail when used            |
| `llm_api_key`                         | runtime-required  | yes         | none                   | chat / generation fail when used            |
| `llm_model`                           | runtime-required  | yes         | none                   | chat / generation fail when used            |
| `confluence_base_url`                 | runtime-required  | conditional | none                   | confluence disabled / unavailable           |
| `confluence_pat`                      | runtime-required  | conditional | none                   | confluence disabled / unavailable           |
| `ingestion_image_vision_api_key`      | runtime-required  | conditional | none                   | multimodal image processing unavailable     |
| `ingestion_image_vision_model`        | runtime-required  | conditional | none                   | multimodal image processing unavailable     |
| `ingestion_image_vision_base_url`     | runtime-required  | conditional | none                   | multimodal image processing unavailable     |
| `ingestion_chunk_size`                | runtime-defaulted | no          | `500`                  | default written into DB at startup          |
| `ingestion_chunk_overlap`             | runtime-defaulted | no          | `50`                   | default written into DB at startup          |
| `ingestion_enable_code_summarization` | runtime-defaulted | no          | `false`                | default written into DB at startup          |
| `ingestion_image_processor`           | runtime-defaulted | no          | `none`                 | default written into DB at startup          |
| `retrieval_top_k`                     | runtime-defaulted | no          | `3`                    | default written into DB at startup          |
| `chat_max_messages`                   | runtime-defaulted | no          | `20`                   | default written into DB at startup          |
| `retrieval_max_full_docs`             | runtime-defaulted | no          | `2`                    | default written into DB at startup          |
| `retrieval_max_full_doc_chars`        | runtime-defaulted | no          | `8000`                 | default written into DB at startup          |

Notes:

- Only `JWT_SECRET_KEY` and `SUPER_ADMIN_USERNAMES` are hard-required in `.env`. All other startup-required fields have safe code defaults.
- "default written into DB at startup" means the system persists the hardcoded default into `system_settings` on first run. This is internal initialization, not an env-seed mechanism. `.env` plays no role in runtime settings.
- For runtime-required values, no implicit fallback exists. The admin page is the only way to configure them.

---

## Runtime Settings Keys

All system-level runtime keys live in `system_settings`.

### Qdrant

- `qdrant_url`

### LLM

- `llm_base_url`
- `llm_api_key`
- `llm_model`

### Ingestion

- `ingestion_chunk_size`
- `ingestion_chunk_overlap`
- `ingestion_enable_code_summarization`
- `ingestion_image_processor`
- `ingestion_image_vision_api_key`
- `ingestion_image_vision_model`
- `ingestion_image_vision_base_url`

### Retrieval

- `retrieval_top_k`
- `chat_max_messages`
- `retrieval_max_full_docs`
- `retrieval_max_full_doc_chars`

### Confluence

- `confluence_base_url`
- `confluence_pat`

---

## Default Value Strategy

Runtime-defaulted settings are materialized into the database at startup.

Why:

- the admin page can display the real current value
- backend logic is simpler
- there is one source of truth for effective runtime behavior
- operators do not need to infer whether a value comes from code or persistence

Therefore:

- startup-required values stay in `.env` (only `JWT_SECRET_KEY` and `SUPER_ADMIN_USERNAMES` are mandatory)
- runtime-required values stay empty in DB until configured via admin page
- runtime-defaulted values are written into `system_settings` at startup if missing

`.env` has no role in runtime settings. There is no env-seed mechanism. All runtime configuration is managed exclusively through the admin page.

Project assumption for this refactor:

- this project is not yet in production
- we do not need backward-compatible migration behavior for existing deployments
- we do not need to auto-import old runtime env values into `system_settings`

That means:

- old env-backed runtime settings can be removed directly
- if a local dev environment upgrades to the new model, the operator must re-enter runtime-required values in the admin page
- this is acceptable because the goal is to simplify the architecture before release

---

## Runtime Validation Model

The runtime settings registry should define more than just key names and defaults.

For each runtime key, declare:

- key
- group
- category (`runtime-required` or `runtime-defaulted`)
- value type (`str`, `int`, `bool`)
- sensitive flag
- default value if applicable
- validation rules such as `min`, `max`, or allowed enum values
- conditional dependency rules when a key is only required in a specific mode

Examples:

- `ingestion_image_processor` should be constrained to a fixed enum such as `multimodal`, `ocr`, or `none`
- `retrieval_top_k` should enforce a minimum integer bound
- `chat_max_messages` should enforce a non-negative integer bound
- `confluence_base_url` and `confluence_pat` should be validated as a pair
- if `ingestion_image_processor == multimodal`, then all image vision settings become required

Validation timing:

- validate on runtime cache load
- validate again on admin save before writing invalid values into `system_settings`
- fail with `ConfigError` when a required runtime dependency is incomplete at feature-use time

This keeps invalid DB state from silently becoming the new source of truth.

---

## Unified Admin Save Model

Current system settings saves are module-specific. After refactor, use one unified save endpoint:

- `GET /admin/settings`
- `PUT /admin/settings`

System-level runtime settings should be edited and saved together from one page-level form.

This does not change KB-level configuration boundaries. KB-specific config such as KB embedding options or KB-level Confluence sync settings should remain under KB APIs.

Sensitive field semantics must be explicit in the unified save contract.

Recommended behavior:

- omitted field: keep existing stored value unchanged
- `null`: keep existing stored value unchanged
- empty string `""`: explicitly clear the stored value
- non-empty string: overwrite with the new value

This is especially important for:

- `llm_api_key`
- `confluence_pat`
- `ingestion_image_vision_api_key`

Without this rule, the unified form cannot safely support both "leave unchanged" and "clear current secret".

---

## Cache And Worker Semantics

The runtime cache should be modeled as one immutable typed object, not a mutable dict that changes field-by-field.

Recommended semantics:

- readers access the current `RuntimeSettings` object without locking
- admin save builds a fresh validated `RuntimeSettings` object from DB state
- cache replacement swaps the whole object under a `threading.Lock`
- no reader should ever observe a partially updated config

Side effects after successful save:

- if any LLM runtime setting changed, clear the LLM client cache
- if Qdrant URL changed, clear the Qdrant store cache
- if image vision runtime settings changed, clear the image LLM cache as well

Worker behavior:

- `IngestionQueueWorker` should always start
- `ConfluenceSyncWorker` should also start safely even when Confluence credentials are empty
- workers should read runtime configuration from the shared cache at execution time, not from startup-only env state
- if required runtime config is missing, workers should skip the affected operation and record a clear `ConfigError`

This is intentionally a single-process hot-refresh design. Admin updates only guarantee cache refresh in the current process.

---

## Non-Goals

This refactor should not expand scope into unrelated config redesign.

Specifically:

- KB-level embedding configuration remains under KB APIs and DB tables, not `system_settings`
- KB-level Confluence sync settings remain KB-scoped, not system-scoped
- the Qdrant collection prefix stays a code-level constant, not an admin setting
- this refactor does not introduce per-request DB reads for runtime settings
- this refactor does not attempt cross-process or cross-instance config synchronization

---

## High-Level Implementation Plan

### Step 1. Split config boundaries

- shrink `core/config.py`
- keep only startup-required env config there
- give safe defaults to all non-critical startup fields (`JWT_ALGORITHM`, `JWT_EXPIRE_MINUTES`, `LOG_DIR`, `LOG_LEVEL`, `CORS_ORIGINS`, `DOCMIND_DB_PATH`)
- remove runtime business config from startup validation entirely

### Step 2. Expand runtime settings registry

- define all `system_settings` keys in one place (e.g. `core/runtime_settings.py`)
- for each key, declare: category (runtime-required / runtime-defaulted), sensitive flag, value type, validation rules, conditional requirements, and default value if applicable
- move all runtime defaults to code constants owned by the runtime settings registry, not to env-backed `settings`

### Step 3. Build the global runtime config cache

- create a typed `RuntimeSettings` dataclass or similar
- load all runtime settings from DB after `init_db()` completes
- keep one process-wide cache instance
- expose typed getters for each runtime config group (LLM, Qdrant, ingestion, retrieval, Confluence)
- model the cache as an immutable object and replace it atomically under a `threading.Lock`
- allow readers to use the current object without per-read locking

### Step 4. Materialize defaultable settings

- during runtime settings initialization, for each runtime-defaulted key that is missing in `system_settings`, insert the hardcoded default value into the DB
- load the now-complete set into cache

### Step 5. Remove lazy refresh — raise immediately on missing required values

- if a runtime-required field is empty in cache when a feature is invoked, raise `ConfigError` immediately
- do not re-read from DB at request time
- this keeps the error path simple and predictable

### Step 6. Migrate backend call sites

> **Implementation note for AI**: Before implementing this step, run a codebase-wide search for all references to the current config object (e.g. `settings.llm_`, `settings.qdrant_`, `settings.ingestion_`, `settings.retrieval_`, `settings.confluence_`, `settings.chat_`). Enumerate every call site, then replace each one with the corresponding typed getter from the new `RuntimeSettings` cache. Also remove any import-time schema defaults that duplicate runtime-configurable values.

- replace direct reads from env-backed config objects
- switch Qdrant, LLM, ingestion, retrieval, and Confluence code to runtime getters
- remove import-time schema defaults for runtime-configurable values

### Step 7. Unify admin settings API

- remove module-specific save endpoints
- implement one `PUT /admin/settings`
- return one grouped payload from `GET /admin/settings`
- define explicit secret-field semantics: omitted or `null` means "keep existing", `""` means "clear", non-empty string means "replace"

### Step 8. Add cache invalidation side effects

- after `PUT /admin/settings` writes to DB, atomically reload and replace the runtime cache (under lock)
- clear LLM client cache when LLM config changes
- clear Qdrant store cache when Qdrant URL changes
- clear image LLM cache when image vision config changes

### Step 9. Update frontend system settings page

- switch to one form
- switch to one Save button
- show grouped status and current values from `GET /admin/settings`

### Step 10. Update workers and diagnostics

- allow app startup even when runtime-required modules are unconfigured
- make ingestion worker surface clear `ConfigError` messages when LLM or Qdrant is not configured
- allow Confluence worker to start safely and skip sync when not configured
- remove startup-time worker gating based on old env-backed integration flags
- ensure health and diagnostics endpoints report runtime config gaps clearly rather than treating them as startup failures

---

## Expected End State

After this refactor:

- the app fails fast only for true startup-critical config (`JWT_SECRET_KEY`, `SUPER_ADMIN_USERNAMES`)
- the app starts normally even when runtime integrations are not yet configured
- runtime features fail with a clear `ConfigError` when used without configuration — no silent fallbacks
- runtime features read from an in-memory typed cache — no per-request DB queries
- defaultable settings have visible persisted values in the admin page
- `.env` is not involved in runtime settings at all
- system settings use one unified save flow
- runtime settings validation rules live in one registry and are enforced consistently on load and save
- workers and caches observe atomic runtime config refresh within the current process
