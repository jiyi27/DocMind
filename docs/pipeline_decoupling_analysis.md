# DocMind Pipeline 解耦分析与重构方案

> 分析日期: 2026-03-19

## 1. 现状梳理

### 1.1 切片流水线（Ingestion）

当前流程：

```
load_document → split_text → summarize_code → embed_and_store
```

关键文件:
- `ingestion/nodes.py` — 所有节点逻辑
- `ingestion/loaders.py` — 文档加载
- `ingestion/graph.py` — LangGraph 编排

**图片的现状**：`_handle_image()` 是一个纯 `pass` 的 TODO，图片块被分类器识别后直接丢弃。

### 1.2 检索流水线（Retrieval）

当前流程：

```
retrieve_node → generate_node
```

`retrieve_node` 内部做了三件事，**全部耦合在同一个函数里**：

1. **向量搜索** — `store.similarity_search_with_score()`
2. **内容解析** — 根据 `chunk_type` / `retrieval_mode` 判断要用哪份内容（full_doc 读文件、`code_mixed` 应回退 `original_content`、image 未来要用链接）
3. **格式化** — 拼 `context_parts` 字符串、拼 `sources` 列表

这三件事混在一起，导致后续扩展（如加入图片多模态）必须在同一个函数里加 `if/elif`，越堆越难维护。

---

## 2. 解耦问题诊断

### 2.1 Ingestion 侧

| 维度              | 现状                             | 问题                                                                   |
| ----------------- | -------------------------------- | ---------------------------------------------------------------------- |
| 块类型扩展        | `classify()` + `HANDLERS` dict   | **良好**，加图片只需实现 `_handle_image`                               |
| 图片存储策略      | TODO pass                        | 缺失：摘要写入 `page_content`、图片链接写入 metadata                   |
| `chunk_type` 枚举 | 只有 `text` / `code_mixed`       | 需要增加 `image` 类型                                                  |
| 节点职责          | `summarize_code_node` 只处理代码 | 未来图片摘要需要一个等价的节点，或泛化为 `summarize_rich_content_node` |

**结论**：Ingestion 侧框架本身是解耦的（HANDLERS dispatch），主要缺的是图片处理的具体实现。

### 2.2 Retrieval 侧

`retrieve_node` 是主要的解耦问题所在，但这里还有一个需要先点明的**现存不一致**：

- Ingestion 侧在代码摘要成功后写入的是：
  - `metadata["chunk_type"] = "code_mixed"`
  - `metadata["original_content"] = original_text`
- Retrieval 侧当前判断的却是：
  - `meta.get("chunk_type") == "code"`
  - `meta["original_code"]`

这意味着“检索时恢复原始代码”这条路径当前大概率并没有真正生效。后续重构时，建议把这个问题视为**顺手修复的现存 bug**，而不是完全无行为变化的纯重构。

`retrieve_node` 当前的职责问题仍然成立：

```python
# 当前 retrieve_node 内部（nodes.py:67-131）
for doc, _score in results:
    meta = doc.metadata or {}
    retrieval_mode = meta.get("retrieval_mode", ...)

    if retrieval_mode == "full_doc":
        # 读文件逻辑
        ...
        context_content = full_text
    else:
        # chunk 逻辑
        if meta.get("chunk_type") == "code_mixed" and "original_content" in meta:
            context_content = meta["original_content"]
        else:
            context_content = doc.page_content

    # 拼格式
    context_parts.append(f"[{i}] {context_content}")
    sources.append(...)
```

**问题**：当加入 `image` 类型时，需要在这个 for 循环里再加一个分支：
- 提取图片链接
- 把图片单独传给多模态 LLM（不能和文本一起塞进 `context` 字符串）
- `context` 是纯字符串，无法携带结构化的图片信息

这意味着 `generate_node` 也要同步改造（现在它只接收一个 `context: str`）。

**根本问题**：`context` 是一个**扁平字符串**，丢失了块的结构信息（类型、元数据）。一旦把所有内容压平成字符串，下游就没有能力区分哪些是文本、哪些是图片、哪些是代码了。

补充一点：当前系统不只有 LangGraph 的 `retrieve_node -> generate_node` 路径，流式聊天还走了一套单独的 `retrieve() -> stream_generate()` 路径。因此后续如果把上下文升级为结构化对象，改造面不止 `generate_node`，还会波及流式接口。

---

## 3. 重构方案

核心思路：**把 `context` 从字符串升级为结构化的 `ContextItem` 列表，让生成层根据类型自行决定如何消费。**

### 3.1 新增 `ContextItem` 数据结构

```python
# retrieval/context.py（新增文件）

from dataclasses import dataclass
from typing import Literal

@dataclass
class ContextItem:
    index: int                              # 用于引用 [1], [2]
    chunk_type: Literal["text", "code", "image", "full_doc"]
    content: str                            # 文本内容 / 代码 / 图片摘要
    image_url: str | None = None            # 仅 image 类型有效
    title: str = ""
    url: str = ""
    source_label: str = ""                  # 最终用于 sources 列表
```

### 3.2 拆解 `retrieve_node` 为两个职责

**拆前**（现在）：
```
retrieve_node = 搜索 + 内容解析 + 格式化
```

**拆后**：
```
retrieve_node  = 搜索 + 内容解析  →  返回 list[ContextItem]
build_context  = 格式化          →  由 generate_node 或独立函数完成
```

```python
# retrieval/nodes.py（重构后）

def retrieve_node(state: RAGState) -> dict:
    """只负责搜索和解析，返回结构化 ContextItem 列表。"""
    results = store.similarity_search_with_score(query, k=top_k)
    items = []
    for i, (doc, _score) in enumerate(results, 1):
        item = _resolve_chunk(i, doc)  # 根据 chunk_type 分派
        if item:
            items.append(item)
    return {"context_items": items}


def _resolve_chunk(index: int, doc: Document) -> ContextItem | None:
    """把一个 Qdrant 检索结果转换为 ContextItem。

    可扩展：新增 chunk_type 只需在这里加分支。
    """
    meta = doc.metadata or {}
    chunk_type = meta.get("chunk_type", "text")
    retrieval_mode = meta.get("retrieval_mode", "chunk")

    if retrieval_mode == "full_doc":
        content = _load_full_text(meta.get("file_path", ""))
        return ContextItem(index=index, chunk_type="full_doc", content=content, ...)

    if chunk_type == "code_mixed":
        content = meta.get("original_content", doc.page_content)
        return ContextItem(index=index, chunk_type="code", content=content, ...)

    if chunk_type == "image":
        return ContextItem(
            index=index,
            chunk_type="image",
            content=doc.page_content,          # 图片摘要（向量化内容）
            image_url=meta.get("image_url"),   # 实际图片链接
            ...
        )

    return ContextItem(index=index, chunk_type="text", content=doc.page_content, ...)
```

### 3.3 `generate_node` / `stream_generate` 根据 ContextItem 类型组装输入

```python
def generate_node(state: RAGState) -> dict:
    items: list[ContextItem] = state["context_items"]
    text_context = _build_text_context(items)
    image_items = [it for it in items if it.chunk_type == "image" and it.image_url]

    # Step 1：先继续派生兼容的 context/sources，不改变现有 prompt 接口
    # Step 2：再把 generate_node 和 stream_generate 一起升级为多模态消息
    ...
```

这里建议明确分阶段：

- **Step 1**：`ContextItem` 只是 retrieval 层的中间结构，最终仍派生出兼容的 `context: str` 和 `sources: list[str]`，保持现有 prompt 和 streaming 接口不变。
- **Step 2**：再统一升级 `generate_node` 与 `stream_generate`，让它们都支持图片 URL 进入 message content。

原因是当前 prompt 模板本身只消费 `{context}` 和 `{messages}`，并没有真正消费结构化 sources；如果一步到位改成多模态，实际牵涉的接口面会比文档初版写得更大。

### 3.4 RAGState 变更

```python
class RAGState(TypedDict, total=False):
    query:         Required[str]
    kb_name:       Required[str]
    context_items: list[ContextItem]    # 新增，替代原来的 context: str
    sources:       list[str]            # 保留（可从 context_items 派生）
    messages:      list[AnyMessage]
    answer:        str
```

> `context: str` 应保留为向后兼容的导出字段，在 `retrieve_node` 末尾根据 `context_items` 派生。这样 `rag_graph`、同步聊天和 `stream_generate` 都可以先不改调用协议。

---

## 4. Ingestion 侧图片方案

### 4.1 流程

```
load_document
  └─ PDF: pymupdf4llm → Markdown（含 ![alt](image_path) 引用）
  └─ MD:  原样

split_text
  └─ _handle_image(block)
       ├─ 解析 image_ref / alt_text
       ├─ 创建轻量占位 Document
       └─ metadata 写入 image_ref / alt_text / chunk_type

summarize_image
  ├─ 解析真实 URL（本地路径可先上传对象存储）
  ├─ 调用多模态 LLM 生成摘要 → page_content
  └─ 回填 metadata.image_url

embed_and_store
  └─ 向量化 page_content = 图片摘要
     metadata.image_url = 原图链接
```

这里特意不建议把“上传图片 + 调模型摘要”放进 `_handle_image()` 本身。原因是 `_handle_image()` 现在属于 splitter 内部的轻量 block handler；如果在 split 阶段做 IO/LLM 调用，会让 `split_text_node` 从“纯切分”变成“切分 + 外部副作用”，失败恢复和职责边界都会变差。

### 4.2 新增节点（建议）

推荐显式新增 `summarize_image_node`，而不是先把重逻辑塞进 `_handle_image`：

```
load_document → split_text → summarize_code → summarize_image → embed_and_store
```

这样职责更清晰：

- `split_text`：识别并产出图片块
- `summarize_image`：做上传、URL 解析、图片摘要
- `embed_and_store`：统一入向量库

若后续 rich content 类型继续增多，再考虑把 `summarize_code_node` / `summarize_image_node` 收敛成 `summarize_rich_content_node`。

### 4.3 `_handle_image` 实现骨架

```python
def _handle_image(block: str) -> None:
    match = _IMAGE_RE.match(block)
    alt_text = match.group(1)
    image_ref = match.group(2)

    flush_chunk()

    docs.append(
        Document(
            page_content=alt_text or "[image]",
            metadata={
                **base_metadata,
                **current_headers,
                "chunk_type": "image",
                "image_ref": image_ref,
                "alt_text": alt_text,
            },
        )
    )
```

注意：

- `_IMAGE_RE` 需要从当前的“仅判断是否匹配”改成带捕获组的版本。
- 这里的 `page_content` 先放占位文本或 alt 文本即可，不在 split 阶段调用模型。
- 如果图片来源是相对路径，后续 `summarize_image_node` 需要结合源文档路径去解析真实文件位置。

### 4.4 对 loader / config 的影响

初版文档说这些层“基本不用动”，这个判断需要收窄。

- `loaders.py` 本身不一定要改，但图片相对路径解析会依赖源文件路径语义。
- `core/config`、`.env`、`.env.example` 很可能需要新增图片对象存储或多模态模型相关配置。
- 如果图片要上传到对象存储，启动校验路径也要同步补齐，避免运行时才发现缺配置。

所以更准确的说法应是：**数据库 schema 大概率不用动，但 config 与启动校验大概率会受影响。**

---

## 5. 流水线全景（重构后）

```
INGESTION
─────────────────────────────────────────────────────────────────────
load_document
    │
    ├─ text/code blocks ──→ split_text ──→ summarize_code
    │                                          │
    └─ image blocks ──────────────────→ summarize_image
                                               │
                                        embed_and_store
                                    (向量化 page_content = 摘要)
                                    (metadata.image_url = 原图链接)

RETRIEVAL
─────────────────────────────────────────────────────────────────────
向量搜索 topK
    │
    ↓ _resolve_chunk()（按 chunk_type 分派）
    │
    ├─ text      → ContextItem(type=text,    content=...)
    ├─ code      → ContextItem(type=code,    content=original_code)
    ├─ image     → ContextItem(type=image,   content=摘要, image_url=...)
    └─ full_doc  → ContextItem(type=full_doc, content=完整文件)
    │
    ↓ generate_node
    │
    ├─ 文本 context：拼接成 [1] ... [2] ...
    └─ 图片 content：追加到 HumanMessage 的 image_url 列表
    │
    ↓ LLM（多模态）
    │
    answer
```

---

## 6. 改动范围评估

| 文件                       | 改动类型 | 说明                                                                               |
| -------------------------- | -------- | ---------------------------------------------------------------------------------- |
| `retrieval/context.py`     | **新增** | `ContextItem` dataclass                                                            |
| `retrieval/state.py`       | 修改     | 新增 `context_items` 字段                                                          |
| `retrieval/nodes.py`       | 重构     | `retrieve_node` 拆出 `_resolve_chunk`；同步兼容 `retrieve()` / `stream_generate()` |
| `ingestion/nodes.py`       | 修改     | 实现 `_handle_image`；`_IMAGE_RE` 补充捕获组；新增图片摘要节点                     |
| `ingestion/graph.py`       | 修改     | 接入 `summarize_image_node`                                                        |
| `ingestion/state.py`       | 无/小    | 可能无需改动                                                                       |
| `api/routers/chat.py`      | 小到中   | 流式链路若进入多模态，需要同步改 `retrieve()` / `stream_generate()` 调用           |
| `retrieval/prompts.py`     | 小到中   | 若改为多模态消息，需重新梳理 prompt 的 context 注入方式                            |
| `core/config.py` / `.env*` | 可能新增 | 图片存储、多模态模型配置与启动校验                                                 |

**大概率不需要改动**：
- `vectorstore/qdrant_store.py`（向量存储本身不感知 chunk_type）
- `db/`（schema 大概率无需变化）

**可能需要补充评估**：
- `ingestion/loaders.py`（是否需要补充源路径语义）
- `core/`（图片相关配置、模型能力声明、启动校验）

---

## 7. 是否需要立即重构？

### 建议分两步走

**Step 1（最小化，必须做）**：
- 实现 `retrieval/context.py` + `ContextItem`
- 重构 `retrieve_node` 中的内容解析逻辑为 `_resolve_chunk()`
- 修正现有 `code_mixed` / `original_content` 与 retrieval 判断不一致的问题
- 继续从 `context_items` 派生兼容的 `context` / `sources`，`generate_node` 和 `stream_generate` 先不改协议

**Step 2（图片多模态，按需做）**：
- 实现 `_handle_image` + `summarize_image_node`
- 统一升级 `generate_node` 与 `stream_generate`，组装多模态消息
- 必要时补充 prompt、配置和启动校验

Step 1 不是完全“零行为变化”的纯重构，因为它应该顺手修掉当前代码恢复原始代码失败的现存不一致；但整体风险仍然可控，而且能为 Step 2 铺路。现有 `context: str` 应继续作为兼容层保留，这样 `stream_generate` 接口改动最小。

---

## 8. 关键设计原则

1. **检索层先产出结构体，再决定是否导出兼容字符串**：内部用 `ContextItem`，对外短期保留 `context` / `sources`。
2. **生成层的多模态升级要覆盖同步和流式两条链路**：不要只改 `generate_node`，遗漏 `stream_generate`。
3. **split 阶段只做识别与切分，不做重 IO/LLM 调用**：图片上传和摘要放后续节点。
4. **新增内容类型至少关注三处**：Ingestion 的 `HANDLERS`、retrieval 的 `_resolve_chunk`、generation/streaming 的消费方式。
5. **向量内容与实际内容分离**：`page_content` 优先存“可检索文本”，原始代码、图片链接等真实载荷放 `metadata`，由 retrieval 层恢复。
