# DocMind 前端 (Vue) 分步实现流程方案

为了避免一次性生成太多代码导致 AI 上下文超载或逻辑混乱，建议将前端开发拆分为多个离散的阶段（Phases）。利用 Vue 组件化的优势，你可以将以下每个阶段作为一个单独的 Prompt 发送给其他 AI，逐步完成整个项目。

在开始任何步骤之前，请确保 AI 已经阅读了后端的 [README.md](file:///Users/david/codes/agent/DocMind/README.md) 和 [frontend/docs/api_contract.md](file:///Users/david/codes/agent/DocMind/frontend/docs/api_contract.md)。

---

## 🟢 阶段一：项目初始化与基础设施搭建 (Phase 1: Initialization & Infrastructure)

**目标**：搭建基础工程结构、路由骨架、状态管理和全局 HTTP 请求拦截。

1.  **项目创建**：使用 `npm create vite@latest frontend -- --template vue` 初始化 Vue3 + Vite 项目。
2.  **依赖安装**：安装核心依赖：`vue-router`, `pinia`, `axios`，以及选定的 UI 组件库（推荐 Element-Plus 或 Tailwind CSS）。
3.  **目录规范**：按照以下结构创建基础空目录：
    *   `src/api/` (API 请求定义)
    *   `src/components/` (业务组件)
        *   `auth/`, `kb/`, `ingestion/`, [chat/](file:///Users/david/codes/agent/DocMind/backend/docmind/api/routers/chat.py#17-40), `layout/`
    *   `src/views/` (页面级视图)
    *   `src/stores/` (Pinia 状态)
    *   `src/router/` (Vue Router 配置)
4.  **路由骨架 (`src/router/index.js`)**：定义 `/login`, `/register`, `/` (Dashboard主控台), `/kb/:id` 四个核心路由。
5.  **网络层封装 (`src/api/http.js`)**：
    *   配置 Axios 实例，BaseURL 指向 `http://localhost:8000` (或依环境变量定)。
    *   实现 Request Interceptor：从 localStorage 或 Pinia 读取 JWT Token，注入 `Authorization: Bearer <token>` Header。
    *   实现 Response Interceptor：统一处理 HTTP 200 下的业务错误（解析 `{code: -1, message}`），统一拦截 HTTP 401 自动跳转回 `/login`。

---

## 🟡 阶段二：Auth 认证模块与全局路由守卫 (Phase 2: Authentication & Guards)

**目标**：跑通登录注册流程，完成用户状态的持久化。

1.  **状态管理 (`src/stores/auth.js`)**：创建 Pinia Store，管理 `token` 和 `userInfo`。实现 [login](file:///Users/david/codes/agent/DocMind/backend/docmind/api/routers/auth.py#69-101) 和 `logout` actions，并确保持久化（localStorage）。
2.  **API 定义 (`src/api/auth.js`)**：基于 `http.js`，导出 [login(username, password)](file:///Users/david/codes/agent/DocMind/backend/docmind/api/routers/auth.py#69-101) 和 [register(...)](file:///Users/david/codes/agent/DocMind/backend/docmind/api/routers/auth.py#24-63) 请求函数。
3.  **开发视图与组件**：
    *   开发 `src/views/LoginView.vue` 和 `src/views/RegisterView.vue`。
    *   实现表单验证逻辑（用户名密码规则等）。
4.  **路由守卫 (`src/router/index.js`)**：添加全局前置守卫 `router.beforeEach`。如果目标路由不是 `/login` 或 `/register` 且 Store 中无有效 Token，则重定向至 `/login`。

---

## 🟠 阶段三：控制台布局与知识库管理模块 (Phase 3: Layout & KB Management)

**目标**：开发登录成功后的主界面，展示所有知识库列表，并根据权限显示管理操作。

1.  **全局布局组件 (`src/components/layout/`)**：
    *   开发 `AppHeader.vue` (显示当前登录用户名、登出按钮)。
    *   开发 `BaseLayout.vue`，作为带导航栏的基础布局容器。
2.  **Auth Store (`src/stores/auth.js`)** 需保存以下字段：
    *   `token`：JWT access token，持久化至 localStorage。
    *   `isSuperAdmin`：来自登录响应的 `is_super_admin` 布尔值，持久化至 localStorage，用于 UI 权限控制。
3.  **API 定义 (`src/api/kb.js`)**：实现 `getKbs()`, `createKb(data)`, `deleteKb(id)` 接口函数。
4.  **状态管理 (`src/stores/kb.js`)**：管理用户的知识库列表及当前选中的知识库。
5.  **开发主页面 (`src/views/DashboardView.vue` 对应路由 `/`)**：
    *   进入页面时请求当前用户的知识库列表并渲染为卡片 (`KbCard.vue`)。
    *   **仅当 Auth Store 中 `isSuperAdmin === true` 时**，显示"创建知识库"按钮，点击唤出表单或弹窗。
    *   **仅当 `isSuperAdmin === true` 时**，每张 `KbCard.vue` 上显示"删除"操作入口。
    *   点击任意知识库卡片，路由跳转至 `/kb/:id`。

---

## 🔵 阶段四：知识库详情页与文档注入 (Phase 4: Document Ingestion View)

**目标**：实现特定知识库的工作区，支持拖拽/点击上传文档。

1.  **详情页基础结构 (`src/views/KbDetailView.vue` 对应路由 `/kb/:id`)**：
    *   获取 URL 中的 [id](file:///Users/david/codes/agent/DocMind/backend/docmind/api/schemas.py#39-46)。
    *   左侧区域放置**文档管理**，右侧区域放置**RAG对话**（右侧此时可留一个 Placeholder 空白占位）。
2.  **API 定义 (`src/api/ingest.js`)**：实现 `uploadDocument() /ingest` (需注意支持 `FormData` 格式) 和 `getDocuments() /ingest/documents` 接口函数。
3.  **开发文档组件 (`src/components/ingestion/`)**：
    *   `UploadZone.vue`: 支持文件选择，提交时附带必要的 metadata 表单（title, doc_type 等）。上传时显示 Loading 状态。
    *   `DocumentList.vue`: 获取并渲染此知识库下的已有历史文档列表，显示 Chunk count 和基础信息。

---

## 🟣 阶段五：检索对话模块 (Phase 5: Chat Retrieval)

**目标**：在知识库详情页整合多轮对话系统。

1.  **API 定义 (`src/api/chat.js`)**：实现 `sendMessage(data) /chat` 函数。由于目前后端是非流式返回，前端按普通 Promise 处理即可。
2.  **开发对话组件 (`src/components/chat/`)**：
    *   `ChatWindow.vue`: 对话区域的主容器，管理对话历史状态（`sessionId`）及消息列表。
    *   `ChatMessageList.vue`: 渲染 User 与 AI 对话气泡。
    *   `ChatMessageItem.vue`: 支持 Markdown 解析（推荐引入 `marked` 库或类似包渲染 RAG 的 `answer` 字段）。并在下方附带显示引用的 `sources`（参考来源）。
    *   `ChatInputBox.vue`: 底部悬浮或固定的输入框，回车发送请求并控制按钮 Loading 状态。
3.  **整合进详情页**：将 Chat 模块嵌入阶段四创建的 `KbDetailView.vue` 右侧工作区中。

---

**最终联调 (Phase 6)**：所有模块拼接完成后，进行跨组件的状态核对、UI 响应式优化及边界情况（Error Toast 展示等）的处理。
