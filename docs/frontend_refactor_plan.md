# Frontend Refactor Plan

## Goal

Refactor the frontend so that

- `views/` focus on page composition, route entry, and top-level permissions
- `composables/` own page-level state, async workflows, polling, streaming, and mutation flows
- `components/feature/` render domain-specific UI blocks with clear `props/emits` boundaries
- `utils/` hold pure functions, route contracts, data transforms, validation helpers, and formatters

This plan is intended to be executed incrementally by an AI or engineer without changing product behavior unless explicitly noted.

## Current Problems

### 1. Views are too heavy

Some views currently act as both page containers and business orchestrators

- `frontend/src/views/ChatView.vue`
- `frontend/src/views/KbDetailView.vue`
- `frontend/src/views/UserProfileView.vue`
- `frontend/src/views/SearchView.vue`
- `frontend/src/components/ingestion/DocumentList.vue`

These files currently mix

- async data fetching
- cache management
- abort / polling / streaming control
- route assembly
- UI rendering
- side effects such as notifications and navigation

### 2. Cross-module contracts are implicit

Examples

- document detail route query fields are manually built in one file and manually parsed in another
- chat source rendering depends on ad hoc string parsing
- multiple modules reimplement date formatting and small shared rules

These contracts should be explicit and centralized.

### 3. Infrastructure is coupled to UI

`frontend/src/api/http.js` currently mixes

- transport concerns
- auth invalidation
- router redirection
- Element Plus notifications
- direct `localStorage` access

This makes testing and reuse harder and spreads app behavior across low-level modules.

## Target Structure

```text
frontend/src/
  api/
    http.js
    auth.js
    kb.js
    chats.js
    ingest.js
    search.js
    admin.js
    apiKeys.js

  stores/
    auth.js
    kb.js

  composables/
    auth/
      useAuthSession.js
    chat/
      useChatSessions.js
      useChatStreaming.js
    kb/
      useKbDetail.js
      useKbConfluenceSync.js
      useKbEmbeddingForm.js
    documents/
      useDocumentList.js
      useDocumentDetail.js
    search/
      useSearchPage.js
    profile/
      useApiKeys.js

  components/
    common/
      EmptyState.vue
      LoadingBlock.vue
      ConfirmActionButton.vue
    feature/
      chat/
        ChatSidebar.vue
        ChatThread.vue
        ChatComposer.vue
        ChatSources.vue
      kb/
        KbCard.vue
        KbOverviewPanel.vue
        KbInfoDialog.vue
        KbConnectionDialog.vue
        KbConfluenceDialog.vue
        KbSyncHistoryDrawer.vue
        CreateKbDialog.vue
      documents/
        DocumentList.vue
        DocumentListItem.vue
        UploadZone.vue
        DocumentMetaCard.vue
        ChunkList.vue
      profile/
        ApiKeyTable.vue
        CreateApiKeyDialog.vue
      search/
        SearchToolbar.vue
        SearchResultList.vue
        SearchResultCard.vue

  utils/
    format/
      date.js
      number.js
    chat/
      sources.js
    documents/
      route.js
      file.js
    kb/
      labels.js
      validators.js
    http/
      errors.js
    auth/
      storage.js
```

Notes

- Do not force every file above to exist immediately.
- This is the target direction, not a mandatory one-shot migration.
- Preserve existing design language and API behavior unless a task explicitly requests UI changes.

## Layer Responsibilities

### `views/`

A view should

- read route params
- instantiate composables
- wire components together
- pass `props`
- listen to `emits`

A view should not own

- low-level polling logic
- stream lifecycle logic
- route contract parsing logic
- reusable data transforms

### `composables/`

A composable should own

- `ref/reactive/computed`
- loading and error state
- fetch / mutation orchestration
- optimistic updates when appropriate
- abort controllers
- polling timers
- derived page state

A composable should not

- render UI
- depend directly on template structure

### `components/feature/`

Feature components should

- render business-domain UI
- receive data via `props`
- communicate user intent via `emits`

They should avoid

- direct router navigation unless the component is explicitly navigation-specific
- direct API calls when the same logic is useful elsewhere
- direct access to global stores unless it is a deliberate domain boundary

### `utils/`

Utils should be pure and side-effect free.

Use them for

- route contract builders/parsers
- formatters
- validation helpers
- source parsing
- label mapping
- small shared transforms

Do not put

- `ref`, `watch`, `onMounted`
- router access
- notifications
- API calls

## Refactor Workstreams

### Workstream 1: Extract shared utils first

Do this before large component splitting.

Create

- `frontend/src/utils/format/date.js`
- `frontend/src/utils/format/number.js`
- `frontend/src/utils/chat/sources.js`
- `frontend/src/utils/documents/route.js`
- `frontend/src/utils/documents/file.js`
- `frontend/src/utils/kb/validators.js`
- `frontend/src/utils/auth/storage.js`

Move the following logic into utils

- repeated `formatDate` and `formatDateTime`
- chat source string parsing
- document detail route building/parsing
- file icon / file type helpers
- Confluence URL validation helpers
- auth-related storage reads/writes

Acceptance criteria

- no repeated date-format helper copies remain in views/components
- route query field names for document detail exist in one shared place
- chat source parsing is no longer embedded inside UI components

### Workstream 2: Refactor Chat into composables + feature components

Current source

- `frontend/src/views/ChatView.vue`
- `frontend/src/components/chat/ChatMain.vue`
- `frontend/src/components/chat/ChatSidebar.vue`
- `frontend/src/services/chat.js`

Create

- `frontend/src/composables/chat/useChatSessions.js`
- `frontend/src/composables/chat/useChatStreaming.js`
- `frontend/src/components/feature/chat/ChatThread.vue`
- `frontend/src/components/feature/chat/ChatComposer.vue`
- `frontend/src/components/feature/chat/ChatSources.vue`

Suggested ownership split

`useChatSessions.js`

- chat list loading
- chat pagination
- active session selection
- detail cache
- reusable empty chat lookup
- deletion behavior and next-session selection

`useChatStreaming.js`

- current send state
- `AbortController`
- stream message lifecycle
- assistant placeholder message
- title polling after first turn

`ChatThread.vue`

- render messages only

`ChatComposer.vue`

- input box and send interaction only

`ChatSources.vue`

- render parsed sources only

Target result

- `ChatView.vue` becomes a thin composition shell
- no stream orchestration remains directly in the template file

Acceptance criteria

- chat behavior remains unchanged
- switching sessions while streaming still behaves correctly
- deleting the active chat still selects the next valid chat

### Workstream 3: Refactor KB detail page into bounded modules

Current source

- `frontend/src/views/KbDetailView.vue`

Create

- `frontend/src/composables/kb/useKbDetail.js`
- `frontend/src/composables/kb/useKbConfluenceSync.js`
- `frontend/src/components/feature/kb/KbOverviewPanel.vue`
- `frontend/src/components/feature/kb/KbInfoDialog.vue`
- `frontend/src/components/feature/kb/KbConnectionDialog.vue`
- `frontend/src/components/feature/kb/KbConfluenceDialog.vue`
- `frontend/src/components/feature/kb/KbSyncHistoryDrawer.vue`

Suggested ownership split

`useKbDetail.js`

- load KB detail
- info form state
- embedding connection form state
- update operations for KB metadata and embedding connection

`useKbConfluenceSync.js`

- Confluence form state
- root page resolve flow
- sync preview flow
- sync trigger flow
- history polling
- sync records loading
- status/label mapping via shared utils

UI components should be presentational and emit actions upward.

Acceptance criteria

- KB detail page no longer contains all operational logic in one script block
- Confluence sync logic is isolated from general KB metadata editing
- dialogs are independently understandable and testable

### Workstream 4: Refactor documents flow

Current source

- `frontend/src/components/ingestion/DocumentList.vue`
- `frontend/src/views/DocumentDetailView.vue`
- `frontend/src/components/ingestion/UploadZone.vue`

Create

- `frontend/src/composables/documents/useDocumentList.js`
- `frontend/src/composables/documents/useDocumentDetail.js`
- `frontend/src/components/feature/documents/DocumentList.vue`
- `frontend/src/components/feature/documents/DocumentListItem.vue`
- `frontend/src/components/feature/documents/DocumentMetaCard.vue`
- `frontend/src/components/feature/documents/ChunkList.vue`

Suggested ownership split

`useDocumentList.js`

- document fetch
- conditional polling for pending/processing items
- delete flow

`useDocumentDetail.js`

- metadata loading
- chunk pagination
- derived values for displayed counts and labels

`utils/documents/route.js`

- build document detail route
- parse document detail preset

Acceptance criteria

- `DocumentList.vue` is no longer both fetch layer and view layer
- document detail route query parsing is centralized
- polling timer ownership is isolated in a composable

### Workstream 5: Refactor search page

Current source

- `frontend/src/views/SearchView.vue`

Create

- `frontend/src/composables/search/useSearchPage.js`
- `frontend/src/components/feature/search/SearchToolbar.vue`
- `frontend/src/components/feature/search/SearchResultList.vue`
- `frontend/src/components/feature/search/SearchResultCard.vue`

`useSearchPage.js` should own

- query state
- last query
- selected KB
- topK
- result state machine
- default KB selection
- search execution

Acceptance criteria

- `SearchView.vue` mainly wires toolbar and result list
- score formatting and coloring are not embedded directly in the page

### Workstream 6: Refactor profile API key management

Current source

- `frontend/src/views/UserProfileView.vue`

Create

- `frontend/src/composables/profile/useApiKeys.js`
- `frontend/src/components/feature/profile/ApiKeyTable.vue`
- `frontend/src/components/feature/profile/CreateApiKeyDialog.vue`

`useApiKeys.js` should own

- key list loading
- create flow
- revoke flow
- copy-to-clipboard flow

Acceptance criteria

- user profile page becomes a page assembler
- API key CRUD is isolated behind one composable

### Workstream 7: Clean up auth and HTTP boundaries

Current sources

- `frontend/src/api/http.js`
- `frontend/src/api/chats.js`
- `frontend/src/stores/auth.js`
- `frontend/src/router/index.js`

Required changes

1. Centralize auth storage access

- all direct `localStorage` reads/writes should move behind `utils/auth/storage.js`

2. Reduce `http.js` coupling

- normalize response envelopes
- normalize API errors
- avoid direct Element Plus UI dependencies where possible
- avoid owning application-level redirect policy unless explicitly unavoidable

3. Remove duplicate token sources

- choose one authoritative path for auth state
- prefer store + storage utility, not ad hoc reads scattered across modules

4. Revisit SSE auth token access

- `frontend/src/api/chats.js` should use the same auth token provider abstraction as other API modules

Acceptance criteria

- no direct `localStorage.getItem('token')` scattered across the app
- auth expiry behavior is defined in one place
- HTTP transport logic is cleaner and more portable

## Recommended Execution Order

Implement in this order

1. Shared utils extraction
2. `useApiKeys`
3. `useSearchPage`
4. `useDocumentList` and `useDocumentDetail`
5. Chat composables and chat feature split
6. KB detail composables and feature split
7. Auth/HTTP cleanup

Reason

- early steps are lower-risk and establish shared patterns
- chat and KB detail are the largest refactors and should reuse the same conventions
- auth/HTTP cleanup should happen after shared abstractions are available

## Guardrails For The Implementing AI

- Do not change backend API contracts unless explicitly requested
- Do not move raw `axios` or `fetch` calls into Vue components
- Keep Vue 3 Composition API with `<script setup>`
- Preserve existing route names and user-visible behavior
- Avoid large visual redesign during architecture refactor
- Prefer incremental edits over one massive rewrite
- When splitting files, keep imports grouped and use existing alias conventions
- Do not remove existing success/error feedback unless replaced with an equivalent mechanism
- Keep frontend commands running from `frontend/`

## Verification Requirements

After each workstream

1. Run

```bash
cd frontend && pnpm build
```

2. If a refactor changes runtime flow significantly, manually verify at least

- login/logout still work
- chat can load, send, stream, and delete sessions
- KB detail can edit metadata and open sync history
- document list still polls processing items
- document detail still loads chunks
- search still executes and renders results
- API key create/revoke still work

## Definition Of Done

The frontend refactor is considered complete when

- heavy views are reduced to page composition shells
- page-level business logic lives primarily in composables
- pure helpers and route contracts live in utils
- feature components are focused on rendering and interaction boundaries
- auth and HTTP concerns have clearer ownership
- duplicated small helper logic has been consolidated
- `cd frontend && pnpm build` passes

## Suggested Commit Breakdown

Use small commits such as

1. `refactor(frontend): extract shared formatters and route helpers`
2. `refactor(frontend): move search page state into composable`
3. `refactor(frontend): split document list into composable and feature components`
4. `refactor(frontend): separate chat session and streaming logic`
5. `refactor(frontend): modularize kb detail workflows`
6. `refactor(frontend): centralize auth storage and http error handling`
