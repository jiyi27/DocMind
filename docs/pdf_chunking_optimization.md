# PDF 切片优化：从裸文本到结构化 Markdown

本文档记录了对 PDF 文档切片效果的一次完整优化过程，包括问题发现、原因分析、决策权衡和最终结果。

## 1. 问题发现

在对比 PDF 和 Markdown 文件的切片预览结果时，发现两者存在明显的质量差距：

- Markdown 文件的 chunk 语义完整，标题层级清晰，代码块、表格均被正确保护
- PDF 文件的 chunk 内容混乱，段落被随机截断，标题和正文混杂在一起，没有任何结构信息

最直观的表现是：同一份文档，Markdown 版本的切片结果可以直接用于检索，PDF 版本几乎无法区分"这是哪个章节的内容"。

## 2. 原因分析

### 2.1 PDF 格式的本质

PDF 的底层格式是页面布局指令，本质上存储的是"在坐标 (x, y) 处渲染字符 C"这样的信息，而不是文档的逻辑结构。标题和正文在视觉上靠字体大小和粗细区分，但这些视觉属性不会自动转化为语义信息。

此外需要区分两类 PDF：

- **文字型 PDF**：文档内部有真正的文字层（Unicode 字符 + 坐标），可以被程序读取和提取
- **图片型 PDF（扫描件）**：每页实际上是一张光栅图片（JPEG/PNG）嵌入进来，内部没有文字层，程序只能看到图片数据，无法提取任何字符

本次优化针对的是文字型 PDF。图片型 PDF 需要 OCR，不在此次范围内。

### 2.2 原有解析库的问题

原来使用的是 `PyPDFLoader`（基于 `pypdf`），它的工作方式是按坐标顺序拼接字符，输出纯文本。

这个过程只拿字符坐标，不读字体属性，所以：

- 标题层级完全丢失，和正文没有区别
- 多栏排版、页眉、页脚、图注容易混入正文
- 页面切断发生在句子中间，与语义边界无关

进入切片阶段时，`_split_pdf` 拿到的是一段没有任何标记的裸文本，只能按 `\n\n` 机械切分，无法感知语义边界。

### 2.3 切片路径不对等

原有流程中，Markdown 文件走 `_custom_split_markdown`，PDF 文件走 `_split_pdf`。两条路径的能力差距很大：

| 能力              | `_custom_split_markdown` | `_split_pdf` |
| ----------------- | ------------------------ | ------------ |
| 标题感知 / 面包屑 | 有                       | 无           |
| 代码块保护        | 有                       | 无           |
| 表格保护          | 有                       | 无           |
| 引用块保护        | 有                       | 无           |
| 递归切分过大块    | 有                       | 有           |

`_custom_split_markdown` 是专门为结构化文本设计的。PDF 提取出来的裸文本不具备这些结构，即使换用它来处理 PDF，效果也不会好——除非先把 PDF 转成带结构的 Markdown。

## 3. 决策点

### 方案对比

| 方案                                | 效果                               | 代价         |
| ----------------------------------- | ---------------------------------- | ------------ |
| 继续用 `pypdf`，优化 `_split_pdf`   | 有限，信息已在解析阶段丢失         | 低           |
| 换用 `pdfminer`，提取更多文本信息   | 有限，仍是裸文本                   | 中           |
| 引入 `unstructured` 做结构化解析    | 较好，但依赖重，部署复杂           | 高           |
| 用 `pymupdf4llm` 将 PDF 转 Markdown | 好，直接复用已有 Markdown 切片逻辑 | 低           |
| Multimodal LLM 解析页面             | 极佳，适合图片型 PDF               | 极高，成本大 |

### 决策依据

核心判断是：**问题出在解析层，不在切片层**。`_custom_split_markdown` 本身已经足够完善，真正缺少的是结构化的输入。

`pymupdf4llm` 基于 PyMuPDF，在读取文字坐标的同时也读取字体大小、粗细等属性，据此推断标题层级，将整个文档输出为 Markdown，包含 `#` / `##` / `###` 等标题、表格、代码块。

这样，PDF 在进入切片阶段之前就具备了 `_custom_split_markdown` 所需要的结构信息。

选择这个方案的额外原因：**改动最小，收益最大**。不需要新写切片逻辑，只需要换一个解析器，PDF 就能和 Markdown 走完全相同的切片路径。

## 4. 实现变更

### 4.1 `loaders.py`

将 `load_pdf` 中的 `PyPDFLoader` 替换为 `pymupdf4llm.to_markdown()`：

- 原来：调用 `PyPDFLoader`，返回多个 Document（每页一个），内容为裸文本
- 现在：调用 `pymupdf4llm.to_markdown()`，返回单个 Document，内容为结构化 Markdown

返回单个 Document 而不是逐页切分，是因为 `pymupdf4llm` 在文档层面做结构推断，逐页截断反而会破坏跨页的标题和段落连续性。

**图片型 PDF 的处理**

提取完成后，代码检查结果的有效字符数（去除空格和换行后）是否低于 50。

这个数字的含义是：一份正常的文字型 PDF，哪怕只有一页简单内容，提取出来的文本也会有几百到几千个字符。图片型 PDF 内部没有文字层，`pymupdf4llm` 遍历整个文件也找不到任何字形数据，返回的字符串几乎为空，或只有少量空行、格式符。

低于 50 意味着这份 PDF 没有可用的文字层，继续走下去只会产生空 chunk，不如提前报错，给用户明确的提示：

```
无法提取文本：该 PDF 可能是扫描件或图片型文档，暂不支持。
请转换为可复制文字的 PDF 后重新上传。
```

这个错误会沿现有链路自然冒泡，最终由 worker 的异常捕获写入 `documents.error_message`，前端展示给用户，无需改动任何其他地方。

### 4.2 `nodes.py`

`split_text_node` 中移除了 Markdown / PDF 的分支判断，所有文件统一走 `_custom_split_markdown`。

原来的 `_split_pdf` 函数保留在代码中，仅供预览脚本的 `--legacy-pdf` 参数使用。

### 4.3 `pyproject.toml`

新增依赖：`pymupdf4llm`。原有的 `pypdf` 依赖保留（其他组件仍可能依赖它）。

## 5. 完整处理流程

```
上传 PDF
  │
  ▼
pymupdf4llm.to_markdown()
  │
  ├─ 有效字符 < 50 → DocumentError（图片型 PDF，提示用户）
  │    └─ worker 捕获 → documents.status = 'failed'
  │                    documents.error_message = 用户可读提示
  │
  └─ 有效字符 ≥ 50 → 结构化 Markdown Document
       │
       ▼
  _custom_split_markdown
  （标题感知、面包屑、代码块/表格/引用块保护）
       │
       ▼
  embed_and_store → Qdrant
```

## 6. 预览脚本的配套调整

对 `scripts/preview_chunking.py` 做了以下调整：

- 默认不再输出 chunk 的元数据，只显示内容本身
- 新增 `--show-metadata` 参数，需要时可以显式开启
- 新增 `--legacy-pdf` 参数，使用旧的 `PyPDFLoader` + `_split_pdf` 路径，便于与新方案直接对比

```bash
# 新方案
uv run python scripts/preview_chunking.py /path/to/file.pdf --strict-mode false --chunk-size 800

# 旧方案对比
uv run python scripts/preview_chunking.py /path/to/file.pdf --strict-mode false --chunk-size 800 --legacy-pdf
```

## 7. 局限与后续

当前方案仅支持文字型 PDF。图片型 PDF（扫描件）的支持需要引入 OCR，可以考虑在检测到无文字层时走 OCR 路径（如 `pytesseract` 或多模态模型），目前作为后续工作。
