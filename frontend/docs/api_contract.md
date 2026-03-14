# DocMind API Contract Specification (Frontend Reference)

This document defines the core API endpoints provided by the DocMind backend. It serves as a reference for frontend developers (and AI agents) to ensure consistent request/response handling.

## 🔹 Global Request & Response Standards

### Authorization
All endpoints except `/auth/register` and `/auth/login` require a JWT Token in the HTTP Request Header:
```http
Authorization: Bearer <your_access_token>
```

### Response Envelope
The backend uses a standard response structure for successful business logic and handled errors.

- **Status Code**: Usually `200 OK` for business responses.
- **Envelope Structure**:
  - `code: 0` → Success. Data is in the `data` field.
  - `code: -1` → Business error. Description is in the `message` field.

```json
// Success Example
{ "code": 0, "message": "ok", "data": { ... } }

// Business Error Example
{ "code": -1, "message": "Reason for failure", "data": null }
```

> [!IMPORTANT]
> **FastAPI Standard Exceptions**: For errors like `401 Unauthorized` or `404 Not Found` handled by FastAPI filters, the API may return standard HTTP status codes (non-200) and a body like `{"detail": "..."}`. Frontend Axios interceptors should handle both business `code` and HTTP status codes.

---

## 🔹 1. Authentication (Auth)

### 1.1 Register User
*   **Method**: `POST`
*   **Path**: `/auth/register`
*   **Description**: Create a new user account linked to a specific Knowledge Base.
*   **Request Body**:
    ```json
    {
      "username": "user1",
      "password": "my_secure_password",
      "kb_id": "uuid-of-kb"
    }
    ```
*   **Response `data` (code: 0)**: Returns user profile including `id`, `username`, `kb_id`, `kb_name`, and `role`.

### 1.2 User Login
*   **Method**: `POST`
*   **Path**: `/auth/login`
*   **Description**: Authenticate user and return access token.
*   **Request Body**:
    ```json
    {
      "username": "user1",
      "password": "my_secure_password"
    }
    ```
*   **Response `data` (code: 0)**:
    ```json
    {
      "access_token": "JWT_TOKEN_STRING",
      "token_type": "bearer",
      "is_super_admin": false,
      "kb_id": "uuid-of-user-kb",
      "role": "user",
      "username": "user1"
    }
    ```
    > **Note**: Frontend should persist `access_token` for authorization and `is_super_admin` / `role` for UI permission control.

---

## 🔹 2. Knowledge Base Management (KB)

### 2.1 List All Knowledge Bases
*   **Method**: `GET`
*   **Path**: `/kb`
*   **Response `data` (code: 0)**: Array of KB objects (id, name, display_name, description, created_at).

### 2.2 Create Knowledge Base (Super-Admin Only)
*   **Method**: `POST`
*   **Path**: `/kb`
*   **Request Body**:
    ```json
    {
      "name": "tech_kb_slug", // Alphanumeric slug
      "display_name": "Technical Documentation",
      "description": "Optional text"
    }
    ```

### 2.3 Get KB Details
*   **Method**: `GET`
*   **Path**: `/kb/{kb_id}`
*   **Response `data` (code: 0)**: KB details including `document_count` and `total_points` (vector chunks).

### 2.4 Delete Knowledge Base (Super-Admin Only)
*   **Method**: `DELETE`
*   **Path**: `/kb/{kb_id}`
*   **Description**: Completely remove a KB, all its document records, and its vector collection.
*   **Response `data` (code: 0)**: `{"kb_id": "uuid", "documents_removed": 10}`

---

## 🔹 3. Document Ingestion

### 3.1 Upload and Ingest Document
*   **Method**: `POST`
*   **Path**: `/ingest/{kb_id}`
*   **Content-Type**: `multipart/form-data`
*   **FormData Parameters**:
    *   `file`: `(File)` **Required**. PDF or Markdown.
    *   `title`: `(String)` Optional. Defaults to filename.
    *   `url`: `(String)` Optional.
    *   `doc_type`: `(String)` Optional (e.g., "tech_spec", "requirement").
    *   `service`: `(String)` Optional.
    *   `department`: `(String)` Optional.
*   **Response `data` (code: 0)**: Contains `doc_id`, `chunk_count`, and ingestion `status`.

### 3.2 List Documents (Current User)
*   **Method**: `GET`
*   **Path**: `/ingest/documents`
*   **Description**: Returns all documents uploaded by the authenticated user across all Knowledge Bases.

### 3.3 List Documents in KB
*   **Method**: `GET`
*   **Path**: `/ingest/documents/kb/{kb_id}`
*   **Description**:
    *   **Regular User**: Returns only documents uploaded by the user in this KB.
    *   **Admin/Super-Admin**: Returns ALL documents in this KB.

### 3.4 Delete Document
*   **Method**: `DELETE`
*   **Path**: `/ingest/{doc_id}`
*   **Description**: Permanently remove a document and its associated vector chunks.
*   **Response `data` (code: 0)**: `{"doc_id": "uuid"}`

### 3.5 Inspect Document Chunks
*   **Method**: `GET`
*   **Path**: `/ingest/{doc_id}/chunks`
*   **Query Params**: `offset` (default 0), `limit` (default 20)
*   **Description**: Retrieve paginated text chunks for a document to verify ingestion quality.
*   **Response `data` (code: 0)**: List of chunk objects.

---

## 🔹 4. Chat & Retrieval

### 4.1 Chat Endpoint
*   **Method**: `POST`
*   **Path**: `/chat`
*   **Request Body**:
    ```json
    {
      "chatInput": "What is RAG?",
      "sessionId": "optional-uuid"
    }
    ```
*   **Response `data` (code: 0)**:
    ```json
    {
      "answer": "RAG stands for...",
      "sources": [{"page_content": "...", "metadata": {...}}],
      "session_id": "uuid",
      "kb_name": "current_kb_slug"
    }
    ```
    > **Note**: This is a direct response (non-streaming). Frontend should display the answer and source citations.

---

## 🔹 5. System Health

### 5.1 Health Check
*   **Method**: `GET`
*   **Path**: `/health`
*   **Description**: Check system status and connectivity to Qdrant and LLM providers.
*   **Response `data` (code: 0)**:
    ```json
    {
      "status": "ok",
      "checks": {
        "qdrant": "ok",
        "llm_api_key": "configured"
      }
    }
    ```
