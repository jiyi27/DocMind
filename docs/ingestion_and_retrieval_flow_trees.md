## 1. 整体主线

```text
document lifecycle
├── 文档进入 ingestion
│ ├── 读取原始内容
│ ├── 补齐文档级元数据
│ └── 按语义切成多个 chunk
├── 每个 chunk 变成"可检索单元"
│ ├── page_content = 用来做向量检索的文本
│ └── metadata = 用来描述来源, 类型, 检索方式的结构化信息
├── chunk 写入 Qdrant
│ ├── vector = page_content 的向量
│ └── payload = page_content + metadata
├── 用户发起查询
│ └── Qdrant 返回语义最接近的一批 chunk
├── 检索层逐条解析命中结果, 根据不同类型的 chunk 拿到不同数据用于构建上下文
│ ├── 普通 text chunk -> 直接使用 chunk 文本
│ ├── code chunk -> 恢复原始代码内容
│ ├── image chunk -> 使用图片摘要 / OCR 文本
│ └── full_doc 模式 -> 回源读取整篇文档
├── 所有命中结果被组装成 context_items
│ ├── 每条都带编号
│ ├── 每条都带来源信息
│ └── 每条都带实际要喂给模型的内容
└── context_items 被拼成一个扁平 context 字符串
    └── 最终随用户问题一起发给大模型
```

## 2. 文档进入系统后, 先变成什么

### 文档级数据

一篇文档在切分前, 会先带上一些属于"整篇文档"的信息, 例如

- `doc_id`
- `user_id`
- `kb_name`
- `title`
- `url`
- `source` 或 `file_name`
- `retrieval_mode`

这些字段的作用很简单: 后面无论切出多少个 chunk, 它们都知道自己来自哪篇文档

### chunk 级数据

文档被切成多个 chunk 后, 每个 chunk 都会变成一条独立的可检索记录, 你可以把它理解成

- `page_content`: 这个 chunk 自己的文本内容, 用来做向量化和相似度检索
- `metadata`: 这个 chunk 的描述信息, 用来在命中后决定"它应该怎么被还原成上下文"

## 3. Text Chunk: 最核心的一条主线

```text
text chunk lifecycle
├── 一篇文档被切成多个文本 chunk
│ └── 每个 chunk 都继承文档级元数据
├── 每个 text chunk 都有两部分
│ ├── page_content = 这个 chunk 的正文文本
│ └── metadata = 这个 chunk 的关键属性
├── 写入 Qdrant
│ ├── vector 来自 page_content
│ └── payload 保存 page_content + metadata
├── 查询时命中这个 chunk
│ └── 检索层读取它的 page_content 和 metadata
├── 系统判断它是普通 text chunk
│ └── 直接把 page_content 作为上下文内容
├── 系统为它补一个 source_label
│ └── 例如标题, URL, 编号
└── 它最终变成一个 ContextItem
    └── 参与后续 context 拼接
```

### Text Chunk 在向量库里长什么样

可以把一条 text chunk 记录抽象理解成

```text
vector store record
├── vector
│ └── 由 page_content 计算出的向量
└── payload
    ├── page_content
    │ └── chunk 的正文文本
    └── metadata
        ├── chunk_type = "text"
        ├── retrieval_mode
        ├── doc_id
        ├── user_id
        ├── kb_name
        ├── title
        ├── url
        ├── source / file_name
        └── header_1 / header_2 / ...
```

## 4. 查询时发生了什么

```text
retrieval lifecycle
├── 用户输入 query
├── 系统把 query 向量化
├── 去 Qdrant 做相似度检索
├── Qdrant 返回 topK 个最相关结果
├── 检索层逐条查看每个命中结果的 metadata
│ ├── 看 retrieval_mode
│ └── 看 chunk_type
└── 根据判断结果, 决定如何把命中结果转换成 ContextItem
```

这一步的核心不是"再检索一次", 而是"解释检索结果"

命中的原始记录只是向量库里的文档对象, 系统还要进一步判断

- 它是普通文本吗
- 它是代码块吗
- 它是图片块吗
- 它属于 `full_doc` 检索模式吗

只有判断完, 系统才知道该把哪一段内容真正交给模型

## 5. 命中后如何判断, 以及怎么取内容

```text
resolver decision
├── 先看 retrieval_mode
│ └── 如果是 "full_doc" -> 按整篇文档处理
└── 否则看 chunk_type
    ├── "text" -> 直接使用 page_content
    ├── "code_block" -> 优先使用 metadata.original_content
    ├── "image" -> 使用 page_content 中的图片摘要 / OCR 文本
    └── 其他情况 -> 按普通 text 处理
```

这一步可以理解成"命中结果的还原规则"

### 对 text chunk

- 直接取 `page_content`
- 再从 `title`, `url`, `source` 等字段生成来源标签
- 最终形成一个 `ContextItem`

### 对 code chunk

代码块在入库时, 为了更好检索而被摘要化, 
所以命中后, 系统会优先取 `metadata.original_content`, 把原始代码还原出来构建上下文给模型看而不是直接把摘要给模型

也就是说

- 检索靠摘要文本更容易命中
- 给模型看时, 尽量恢复原始代码

### 对 image chunk

图片本身不能直接做普通文本检索, 所以入库前通常已经被转成文本表达, 例如

- 图片摘要
- OCR 提取文字

因此命中后, 系统实际给模型的仍然是文本化后的 `page_content`

### 对 full_doc 模式

`full_doc` 的意思不是"向量库里直接存整篇正文来检索", 而是

- 仍然用 chunk 级别向量去命中相关文档
- 但一旦命中, 就按 `doc_id` 去重
- 然后根据 `file_path` 回源读取整篇文档
- 最后把整篇文档文本作为上下文提供给模型

所以它本质上是

- 用 chunk 找文档
- 用文档给上下文

## 6. ContextItem 是怎么来的

检索命中后, 每条结果都会先被转换成一个统一结构, 便于后续拼接

可以把它抽象理解成

```text
ContextItem
├── index
├── chunk_type
├── content
├── title
├── url
├── source_label
└── image_url(仅图片场景可能有)
```

其中最关键的是

- `content`: 真正要放进模型上下文的文本
- `source_label`: 给引用和溯源看的标签

对于普通 text chunk, `content` 基本就等于命中的 `page_content`

## 7. 多个命中结果如何拼成最终上下文

```text
context assembly
├── 收集所有 ContextItem
├── 跳过不合法或需要忽略的结果
│ ├── full_doc 重复 doc_id
│ ├── 超过 full_doc 数量上限
│ └── 缺少必要元数据
├── 对剩余结果重新编号
├── 为每条结果生成连续的 source_label
└── 拼成一个扁平字符串
    ├── [1] 第一段内容
    ├── [2] 第二段内容
    └── [3] 第三段内容
```

最终给模型的不是"结构化 JSON", 而是一段已经排好序的纯文本 context, 例如

```text
[1] 第一段命中的内容

[2] 第二段命中的内容

[3] 第三段命中的内容
```

也就是说, 模型看到的是一个按编号拼好的上下文块集合
