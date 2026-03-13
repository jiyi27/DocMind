# DocMind API 接口契约规范 (Frontend Reference)

这份文档详细定义了 DocMind 后端提供的核心 API 接口。它主要供前端开发人员（或接手编码的 AI）在编写 Vue/Axios 集成代码时提供请求与响应的参考约束。

## 🔹 全局请求与响应规范

### 认证方式 (Authorization)
除 `/auth/register` 和 `/auth/login` 外，所有接口都需要在 HTTP Request Header 中携带 JWT Token：
```http
Authorization: Bearer <your_access_token>
```

### 全局响应结构 (Response Envelope)
DocMind 后端的绝大多数接口（包括成功和被统一拦截的业务异常）都会返回 **HTTP Status 200**，并通过 JSON 内部的 `code` 区分成功与否：

*   **成功响应**: `{"code": 0, "message": "ok", "data": {...}}`
*   **失败响应**: `{"code": -1, "message": "error description", "data": null}`

**注意：** 部分直接抛出 `HTTPException` 的错误（如 401 Unauthorized, 404 Not Found 等），可能会直接返回对应的 HTTP 状态码及 `{"detail": "..."}` 结构。前端封装 Axios Interceptor 时需要同时兼容检查 HTTP Status Code 和 `response.data.code`。

---

## 🔹 1. 认证模块 (Auth)

### 1.1 用户注册
*   **Method**: `POST`
*   **Path**: `/auth/register`
*   **Content-Type**: `application/json`
*   **Request Body**:
    ```json
    {
      "username": "user1",
      "password": "my_secure_password",
      "kb_id": "uuid-of-a-knowledge-base"
    }
    ```
*   **Response `data` (code: 0)**:
    ```json
    {
      "id": "uuid",
      "username": "user1",
      "kb_id": "uuid-of-a-knowledge-base",
      "kb_name": "tech_kb_slug",
      "role": "user",
      "created_at": "2023-10-27T10:00:00"
    }
    ```

### 1.2 用户登录
*   **Method**: `POST`
*   **Path**: `/auth/login`
*   **Content-Type**: `application/json`
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
      "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
      "token_type": "bearer"
    }
    ```
    *说明：登录成功后，前端需将 `access_token` 保存，并在后续请求中通过 Header 携带。*

---

## 🔹 2. 知识库管理模块 (Knowledge Base)

### 2.1 获取知识库列表
*   **Method**: `GET`
*   **Path**: `/kb`
*   **Response `data` (code: 0)**:
    ```json
    [
      {
        "id": "uuid",
        "name": "tech_kb_slug",
        "display_name": "Technical Documentation",
        "description": "...",
        "created_at": "timestamp"
      }
    ]
    ```

### 2.2 创建知识库 (Super-Admin Only)
*   **Method**: `POST`
*   **Path**: `/kb`
*   **Content-Type**: `application/json`
*   **Request Body**:
    ```json
    {
      "name": "tech_kb_slug",           // 必须为字母和数字 (支持横杠/下划线)
      "display_name": "Technical Documentation",
      "description": "Optional description."
    }
    ```
*   **Response `data` (code: 0)**: 返回新创建的知识库对象。

### 2.3 获取单个知识库详情
*   **Method**: `GET`
*   **Path**: `/kb/{kb_id}`
*   **Response `data` (code: 0)**:
    ```json
    {
      "id": "uuid",
      "name": "tech_kb_slug",
      "display_name": "Technical Documentation",
      "description": "...",
      "created_at": "timestamp",
      "document_count": 10,
      "total_points": 250 // 知识库内 Vector Chunks 总数
    }
    ```

### 2.4 删除知识库 (Super-Admin Only)
*   **Method**: `DELETE`
*   **Path**: `/kb/{kb_id}`
*   **Response `data` (code: 0)**: `{"kb_id": "uuid", "documents_removed": 10}`

---

## 🔹 3. 文档注入模块 (Ingestion)

### 3.1 上传并注入文档
*   **Method**: `POST`
*   **Path**: `/ingest`
*   **Content-Type**: `multipart/form-data`
*   **Request Payload (Form Data)**:
    *   `file`: `(File)` *必填, PDF 或 Markdown 文件*
    *   `title`: `(String)` *选填, 默认取文件名*
    *   `url`: `(String)` *选填*
    *   `doc_type`: `(String)` *选填, 例如: "all"*
    *   `service`: `(String)` *选填, 逗号分隔的字符, 例如: "all"*
    *   `department`: `(String)` *选填, 逗号分隔的字符, 例如: "all"*
*   **Response `data` (code: 0)**:
    ```json
    {
      "doc_id": "uuid",
      "status": "success",
      "chunk_count": 45,
      "file_name": "example.pdf",
      "kb_name": "tech_kb_slug"
    }
    ```

### 3.2 获取当前用户的文档列表
*   **Method**: `GET`
*   **Path**: `/ingest/documents`
*   **Response `data` (code: 0)**:
    ```json
    [
      {
        "id": "uuid",
        "file_name": "example.pdf",
        "title": "Example Title",
        "doc_type": "all",
        "chunk_count": 45,
        "created_at": "timestamp"
      }
    ]
    ```

### 3.3 删除文档及向量数据
*   **Method**: `DELETE`
*   **Path**: `/ingest/{doc_id}`
*   **Response `data` (code: 0)**: `{"doc_id": "uuid"}`

### 3.4 检查文档 Chunk 列表
*   **Method**: `GET`
*   **Path**: `/ingest/{doc_id}/chunks?offset=0&limit=20`
*   **Response `data` (code: 0)**: 返回 Qdrant Points 的分页信息 (含文本和 Metadata, 不含 Vector)。

---

## 🔹 4. 检索与对话模块 (Chat)

### 4.1 发起对话
*   **Method**: `POST`
*   **Path**: `/chat`
*   **Content-Type**: `application/json`
*   **Request Body**:
    ```json
    {
      "chatInput": "什么是 RAG？",
      "sessionId": "random-uuid-for-thread" // 用于多轮对话的上下文窗口
    }
    ```
*   **Response `data` (code: 0)**:
    ```json
    {
      "answer": "RAG 是一种...",
      "sources": [{"page_content": "...", "metadata": {"source": "example.pdf"}}],
      "session_id": "random-uuid-for-thread",
      "kb_name": "tech_kb_slug"
    }
    ```
    *说明：Chat 接口使用了 `rag_graph.invoke`，目前为一次性返回 (非流式 SSE)，前端无需处理 Fetch 流，只需要像普通 API 那样 await 挂起并渲染 `answer` 及 `sources`。*
