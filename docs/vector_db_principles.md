## 1. 向量数据库是什么

向量数据库 = 用"相似度"找数据的数据库

## 2. 向量数据库存的是什么

以 Qdrant 为例, 每条数据叫 **point**, 结构如下

```
Point
 ├─ id
 ├─ vector
 └─ payload
```

具体示例

```json
{
  "id": "abc123", 
  "vector": [0.12, -0.33, 0.991, "..."], 
  "payload": {
    "summary": "这段代码实现 FastAPI hello endpoint", 
    "code": "def hello(): return 'hi'", 
    "file": "api.md", 
    "type": "code"
  }
}
```

- `vector` → 用来做相似度检索
- `payload` → 用来存你自己的数据和元信息

> payload 的结构完全是你在插入数据时自定义的, 向量数据库 (比如 Qdrant) 并不规定 payload 里面必须有什么字段, 它只是把 payload 当作一个 JSON 文档存起来

## 3. 存储过程

### 第一步: 生成 embedding

用 embedding 模型对文本编码

```
summary = "FastAPI hello endpoint 示例"
vector = embed(summary)
# → [0.13, -0.22, 0.91, ...]
```

### 第二步: 写入向量数据库

```json
{
  "id": "uuid", 
  "vector": [0.13, -0.22, 0.91, "..."], 
  "payload": {
    "summary": "...", 
    "code": "...", 
    "file": "example.md"
  }
}
```

数据库里就多了一条记录

### 本项目的实际写入流程

在 `backend/docmind/ingestion/nodes.py` 中, `embed_and_store_node` 负责最终写入

```python
def embed_and_store_node(state: IngestionState) -> dict:
    """Embed chunks and store them in the knowledge base's Qdrant collection."""
    chunks = state["chunks"]
    kb_name = state["kb_name"]

    store = get_vector_store_for_kb(kb_name)
    store.add_documents(chunks)
```

`store.add_documents(chunks)` 由 LangChain 的 `QdrantVectorStore` 封装, 它会自动: 
1. 对每个 chunk 的 `page_content` 调用 embedding 模型生成向量
2. 将 `page_content` + `metadata` 序列化为 payload 写入 Qdrant

#### 实际写入 Qdrant 的 payload 结构

文本经过 `split_text_node` 分块后, 最终写入 Qdrant 时, 每条 point 的 payload 是这样的

```json
{
  "page_content": "这是当前 Chunk 的文本内容段落...", 
  "metadata": {
    "doc_id": "uuid-xxxx", 
    "user_id": "user-xxxx", 
    "kb_name": "你建的知识库名称", 
    "source": "/path/to/upload/example.md", 
    "file_name": "example.md"

    // Markdown 文档: 自定义分块器会额外增加上下文 header
    "header_1": "一级标题名字", 
    "header_2": "二级标题名字"

    // PDF 文档: PyPDFLoader 会自动加入
    "page": 1

    // 代码块经过 summarize_code_node 处理后会额外加入
    "chunk_type": "code_mixed", 
    "original_content": "原始代码文本..."

    // 用户/API 调用时传递的其他自定义 metadata
    "title": "...", 
    "url": "..."
  }
}
```

> **注意**: `page_content` 是 LangChain 约定俗成的标准字段, 向量模型 embedding 的其实也就是这个字段里的文本, 对于代码块, `summarize_code_node` 会先用 LLM 生成摘要替换原始代码, 再写入 `page_content`, 原始代码保存在 `metadata["original_content"]` 中

#### 集合 (Collection) 管理

`backend/docmind/vectorstore/qdrant_store.py` 中, 每个知识库对应一个独立的 Qdrant collection, 命名规则为 `docmind_{kb_name}`

```python
def kb_collection_name(kb_name: str) -> str:
    return f"docmind_{kb_name}"
```

Collection 不存在时会自动创建, 向量维度通过动态探测 embedding 模型确定, 距离度量固定使用 **Cosine Similarity**

```python
_DISTANCE = Distance.COSINE

def _probe_vector_size(embeddings: Embeddings) -> int:
    vector = embeddings.embed_query("probe")
    return len(vector)
```

## 4. 查询时发生什么

用户提问

```
如何写 FastAPI hello API
```

### 第一步: query embedding

```python
query_vector = embed(query)
# → [0.11, -0.19, 0.88, ...]
```

### 第二步: 向量相似度搜索

数据库计算

```
similarity(query_vector, stored_vector)
```

**常见算法: **

1. **Cosine Similarity**(最常见, 本项目使用)

   ```
   similarity = cos(A, B)
   ```

   结果范围 `-1 ~ 1`, 越接近 **1** 越相似

2. **Dot Product**(内积)

3. **Euclidean Distance**(欧氏距离)

### 第三步: 检索 Top K

假设数据库有 10000 条数据

```
query_vector
      ↓
计算与 10000 个 vector 的相似度
      ↓
排序
      ↓
取 top k(本项目由 settings.retrieval.top_k 配置)
```

### 第四步: 返回结果

Qdrant 返回

```json
[
  {
    "score": 0.92, 
    "payload": {
      "page_content": "...", 
      "metadata": { "..." : "..." }
    }
  }, 
  {
    "score": 0.88, 
    "payload": { "...": "..." }
  }
]
```

## 5. 本项目 RAG 流程: 检索结果如何组装 context

在 `backend/docmind/retrieval/nodes.py` 的 `retrieve_node` 中

```python
store = get_vector_store_for_kb(kb_name)
docs = store.similarity_search(query, k=settings.retrieval.top_k)

context_parts: list[str] = []
sources: list[str] = []

for i, doc in enumerate(docs, 1):
    meta = doc.metadata or {}

    # 代码块优先使用原始代码 (而非 LLM 摘要) 作为 context
    if meta.get("chunk_type") == "code_mixed" and "original_content" in meta:
        context_content = meta["original_content"]
    else:
        context_content = doc.page_content

    # 1. 组装给大模型阅读的 context
    context_parts.append(f"[{i}] {context_content}")

    # 2. 从元数据中提取出处, 组装给前端展示的来源链接
    url = meta.get("url", "")
    title = meta.get("title") or meta.get("file_name") or meta.get("source", "")

    if url and title:
        sources.append(f"[{i}] [{title}]({url})")
    elif url:
        sources.append(f"[{i}] [{url}]({url})")
    elif title:
        sources.append(f"[{i}] {title}")
    else:
        sources.append(f"[{i}] unknown source")
```

整体 RAG pipeline

```
User Query
     ↓
Embedding(embed_query)
     ↓
Vector Search(similarity_search, top_k)
     ↓
Top K Results(LangChain Document 列表)
     ↓
拼接成 context("\n\n".join(context_parts))
     ↓
注入 rag_prompt(context + sources + messages)
     ↓
LLM 生成回答
```

## 6. 向量数据库为什么这么快

如果数据库有 1000 万条 vector, 逐个算相似度太慢, 向量数据库使用 **ANN(Approximate Nearest Neighbor)** 算法

**HNSW(Hierarchical Navigable Small World)**

Qdrant 使用的就是这个算法, 时间复杂度

```
O(log n)
```

牺牲极小的精度换取极大的速度提升
