# DocMind 项目构建完成

## 项目结构

```
DocMind/
├── .env.example                 # 环境变量模板
├── docker-compose.yml           # Qdrant + Ollama 基础设施
├── pyproject.toml               # uv 包管理 + 依赖
│
├── docmind/
│   ├── core/
│   │   ├── config.py            # 集中配置（dataclass + env vars）
│   │   ├── embedding.py         # Ollama embedding 工厂
│   │   └── llm.py               # ChatOpenAI (OpenRouter) 工厂
│   │
│   ├── ingestion/               # 数据摄入 Pipeline (LangGraph)
│   │   ├── state.py             # IngestionState 定义
│   │   ├── loaders.py           # PDF/MD 文档加载
│   │   ├── nodes.py             # graph 节点: load → split → embed
│   │   └── graph.py             # 编译后的 ingestion_graph
│   │
│   ├── retrieval/               # RAG 对话 Pipeline (LangGraph)
│   │   ├── state.py             # RAGState (add_messages reducer)
│   │   ├── prompts.py           # 带引用的 prompt 模板
│   │   ├── nodes.py             # retrieve + generate 节点
│   │   └── graph.py             # 编译后的 rag_graph (含 checkpointer)
│   │
│   ├── tools/                   # 可复用工具 (扩展点)
│   │   └── search.py            # @tool search_knowledge_base
│   │
│   ├── vectorstore/
│   │   └── qdrant_store.py      # Qdrant 封装层
│   │
│   └── api/                     # FastAPI 接口
│       ├── main.py              # app 入口
│       ├── schemas.py           # Pydantic 请求/响应模型
│       ├── dependencies.py      # auth 预留插槽
│       └── routers/
│           ├── ingest.py        # POST /ingest
│           └── chat.py          # POST /chat
│
└── scripts/
    └── ingest_file.py           # CLI 批量导入
```

## n8n → LangGraph 映射

| n8n 节点 | LangGraph 实现 |
|---|---|
| On form submission | `POST /ingest` (FastAPI) |
| Default Data Loader | [loaders.py](file:///Users/david/codes/agent/DocMind/docmind/ingestion/loaders.py) |
| Recursive Text Splitter (500/50) | [nodes.py split_text_node](file:///Users/david/codes/agent/DocMind/docmind/ingestion/nodes.py) |
| Embeddings Ollama (nomic-embed-text) | [embedding.py](file:///Users/david/codes/agent/DocMind/docmind/core/embedding.py) |
| Qdrant Vector Store (insert) | [nodes.py embed_and_store_node](file:///Users/david/codes/agent/DocMind/docmind/ingestion/nodes.py) |
| Webhook + RequestField | `POST /chat` (FastAPI) |
| Qdrant Vector Store (load, top_k=3) | [retrieve_node](file:///Users/david/codes/agent/DocMind/docmind/retrieval/nodes.py) |
| Code in JavaScript (format context) | [retrieve_node](file:///Users/david/codes/agent/DocMind/docmind/retrieval/nodes.py) — 同一节点 |
| OpenRouter Chat Model | [generate_node](file:///Users/david/codes/agent/DocMind/docmind/retrieval/nodes.py) via ChatOpenAI |
| Simple Memory (Buffer) | LangGraph MemorySaver + `thread_id` |
| Respond to Webhook | FastAPI ChatResponse |

## 验证结果

```
✅ Config loaded (Qdrant URL, Embedding model, Chunk size, Top K)
✅ States & schemas imported successfully
✅ Tool registered: search_knowledge_base
✅ FastAPI app: DocMind v0.1.0
   Routes: ['/ingest', '/chat', '/health', '/docs']
```

## 扩展预留

| 扩展方向 | 插入点 | 需改动的文件 |
|---|---|---|
| 新增 Tool (web_search 等) | `docmind/tools/` 加新文件 | 无需改现有代码 |
| Agent 模式 (动态选 tool) | 修改 `retrieval/graph.py` 加 tool_node | 仅改 graph.py |
| 上下文管理 (裁剪/摘要) | `RAGState.messages` 已用 `add_messages` | 加 trim 节点即可 |
| 用户登录 | `api/dependencies.py` 实现 `get_current_user` | 路由加 `Depends()` |
| 新文件格式 (docx/html) | `ingestion/loaders.py` 加 loader 函数 | 仅改 loaders.py |

## 下一步

1. **启动基础设施**: `docker compose up -d`
2. **拉取 embedding 模型**: `docker exec ollama ollama pull nomic-embed-text:latest`
3. **创建 Qdrant collection**: 见 README
4. **配置 .env**: 复制 `.env.example` 并填入 OpenRouter API Key
5. **启动服务**: `uv run dev`
