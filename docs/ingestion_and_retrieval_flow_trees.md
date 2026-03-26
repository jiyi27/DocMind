## 1. 总体视角: 先看处理链路

这套系统理解起来最清晰的方式, 不是先按 `chunk_type` 看, 而是先看 LangGraph 的处理链路

```text
ingestion graph
load_document
  -> split_text
  -> summarize_code
  -> summarize_image
  -> embed_and_store
```

可以先把它理解成一条固定流水线

- `load_document`: 把原始文件读进来, 补齐文档级元数据
- `split_text`: 先把文档拆成可检索的 chunk 骨架
- `summarize_code`: 只处理其中带代码块的 chunk
- `summarize_image`: 只处理其中的 image chunk
- `embed_and_store`: 把最终 chunk 写入向量库

这意味着一个重要事实

- 不是所有内容都在每个 node 里被处理
- 不同实体会在这条链路上的不同阶段被识别和改写
- 有些内容在 `split_text` 之后还会继续变形, 有些不会

所以后面这份文档, 不按 node 逐个展开, 而是按"实体在整条链路里如何流动"来讲

## 2. ingestion 阶段, 文档先变成什么

无论是 PDF 还是 Markdown, 在真正切 chunk 之前, 系统都会先得到一个或多个 `Document`

这些 `Document` 先带上文档级元数据, 例如

- `doc_id`
- `user_id`
- `kb_name`
- `title`
- `url`
- `source`
- `file_name`
- `retrieval_mode`

这些字段的作用很简单

- 后面切出多少个 chunk 都还能知道自己属于哪篇文档
- retrieval 命中后可以回源, 也可以生成来源标签

从这个阶段开始, 后面的所有 chunk 都是在这些文档级信息之上演化出来的

## 3. 文本内容这条主线: 文档是怎么被切开的

### 先说结论

当前 chunking 不是"纯字符硬切", 也不是"简单按换行逐行切"

它更接近下面这个过程

```text
text splitting
原始 Markdown / PDF 转出的 Markdown
├── 先保护特殊结构
│ ├── fenced code block
│ ├── blockquote
│ └── table
├── 再按空行分成 paragraph-level blocks
├── 对每个 block 识别类型
│ ├── header
│ ├── image
│ └── content
├── 普通 content block 按 target_size 装箱
├── 如果某个 block 本身已经超长
│ └── 递归二分
└── 生成最终 text-like chunks
```

### 它优先按什么切

第一层是按空行切, 也就是按 `\n\n` 把文档拆成 paragraph-level block

所以它不是一上来就按单个换行 `\n` 切, 更不是直接按固定字符数切

### 超长段落怎么切

如果某个普通文本 block 本身就超过 `chunk_size`, 系统会递归切它

规则是

- 优先在中点附近找换行 `\n`
- 如果中点附近找不到合适换行, 才按字符位置硬切
- 切出来的两半如果仍然超长, 继续递归

所以它的优先级可以概括为

```text
超长 block 的兜底切分
├── 优先找中点附近的换行
└── 否则直接硬切
```

### overlap 是怎么做的

`chunk_overlap` 也不是纯字符滑窗

它会在 flush 一个 chunk 之后, 把尾部若干个"完整 block"保留下来作为下一块的开头, 前提是这些 block 的总长度不超过 overlap budget

所以 overlap 也是 block 级继承, 不是任意位置截取

## 4. header / 普通文本 在链路里怎么流动

这类内容最接近"标准 chunk"

```text
text entity lifecycle
load_document
├── 原始文档被读成 Document
└── 文档级 metadata 被挂上去

split_text
├── header 被识别出来, 用来维护当前章节路径
├── 普通段落被打包进当前 chunk
├── flush chunk 时会把标题路径拼进正文前缀
└── 产出普通 text chunk

summarize_code
└── 如果这个 chunk 里没有可摘要代码块, 基本保持不变

summarize_image
└── 如果这个 chunk 不是 image chunk, 不处理

embed_and_store
└── 以最终 page_content 做 embedding 并写入 Qdrant
```

这里有一个容易忽略的点

- header 自己通常不会单独成为一个只含标题的 chunk
- header 更像是在 `split_text` 里维护"当前章节上下文"
- 真正 flush 出 chunk 时, 标题路径会作为 breadcrumb 被拼到 chunk 正文前面

所以一个普通文本 chunk 往往既包含正文, 也包含标题路径信息, 这样 retrieval 命中后上下文更完整

## 5. code block 在整条链路里怎么被处理

代码块不是在 retrieval 时才特殊处理, 而是在 ingestion 时就已经开始分两步走了

```text
code block lifecycle
load_document
└── 代码仍然只是文档正文的一部分

split_text
├── fenced code block 先被占位保护
├── 避免内部空行把代码块拆坏
├── 代码块所在段落跟周围文本一起形成 chunk
└── restore 后, 代码重新回到 chunk.page_content

summarize_code
├── 只扫描声明了 language 的 fenced code block
├── 短代码块跳过
├── 较长代码块调用 LLM 生成摘要
├── 用摘要替换 chunk.page_content 里的原始代码
└── 把原始代码保存到 metadata.original_content

summarize_image
└── code chunk 不处理

embed_and_store
└── 用"带代码摘要的 page_content"做 embedding
```

这套处理的含义是

- 切 chunk 时, 代码块被当作原子结构保护起来, 不会因为内部空行而被拆散
- 入库前, 长代码块可能会被摘要化, 让向量检索更容易命中"这段代码是干什么的"
- 但原始代码不会丢, 会保存在 `metadata.original_content`

所以 retrieval 命中代码块时, 实际存在两份语义

- 检索用的是摘要化后的文本
- 给模型看时优先恢复原始代码

## 6. image 在整条链路里怎么被处理

image 是最容易引起误解的一类, 因为它和普通文本的处理时机不同

```text
image lifecycle
load_document
└── 图片仍然只是 Markdown 里的 image 语法

split_text
├── 识别独立 image block
├── 先 flush 当前文本 chunk
├── 为图片单独创建一个 image chunk
└── 这个 image chunk 的初始 page_content 只是 alt text 或 [image]

summarize_code
└── image chunk 不处理

summarize_image
├── 根据 image_url 拉取图片
├── 走 multimodal 或 OCR
├── 得到图片摘要 / 识别文本
└── 直接覆盖 image chunk.page_content

embed_and_store
└── 用覆盖后的图片文本做 embedding
```

### 为什么会出现一个 image chunk 很长

根因就在这里

- image chunk 是在 `split_text` 阶段先被创建出来的
- 当时它还只有占位内容
- 后面 `summarize_image` 再把 OCR / 多模态结果整段写回 `page_content`
- 写回之后不会再重新进入 `split_text`

所以如果图片识别结果有 1000 多字符, 它确实可能完整地留在一个 image chunk 里

这不是 `CHUNK_SIZE` 完全失效, 而是 image 内容的真实文本是在切分之后才生成的

换句话说

```text
普通文本
先生成文本
-> 再切 chunk

图片文本
先生成 image chunk 骨架
-> 后生成 OCR / 摘要文本
-> 不再二次切分
```

## 7. table / blockquote 这类结构为什么不容易被切坏

这两类结构的策略和 code block 类似, 但没有后续摘要步骤

```text
atomic structures
split_text
├── blockquote 先整体保护
│ └── 还原时会去掉 Markdown 的 > 前缀噪音
├── table 先整体保护
│ └── 还原时会转成更适合检索的 prose 形式
└── 这样它们不会因为空行切分而碎掉
```

所以它们的关键不是"后面怎么特殊处理", 而是"在 chunking 之前先避免结构被破坏"

## 8. full_doc 模式在 ingestion 里是什么表现

`full_doc` 最容易被误解成"根本不切 chunk", 但当前实现不是这样

在 ingestion 阶段

- 文档仍然会经过 `split_text`
- 仍然会生成 chunk 并写入 Qdrant
- 只是文档文件本身会保留在磁盘, `metadata.file_path` 也会保留下来

所以 `full_doc` 的真实含义更接近

- ingestion 还是靠 chunk 建索引
- retrieval 命中后, 再把整篇文档重新读出来作为上下文

## 9. retrieval 阶段: 命中后不是直接把 chunk 原样喂给模型

检索阶段的核心不是"再切一次", 而是"解释命中的记录"

```text
retrieval lifecycle
用户 query
├── 向量化
├── Qdrant 返回相似 chunk
├── 系统逐条检查 metadata
│ ├── 先看 retrieval_mode
│ └── 再看 chunk_type
├── 根据类型把命中结果变成 ContextItem
└── 把 ContextItem 拼成最终 context
```

所以向量库里命中的对象只是"候选记录"

系统还要再决定

- 这是普通 text chunk 吗
- 这是 code chunk 吗
- 这是 image chunk 吗
- 这是 `full_doc` 模式下应该整篇回源的结果吗

## 10. 不同实体在 retrieval 时如何还原

```text
resolver decision
├── 先看 retrieval_mode
│ └── 如果是 full_doc -> 整篇文档解析
└── 否则看 chunk_type
    ├── text -> 直接使用 page_content
    ├── code_block -> 优先用 metadata.original_content
    ├── image -> 使用 page_content 中的图片摘要 / OCR 文本
    └── 其他 -> 按 text 处理
```

### 普通 text

- 直接把命中的 `page_content` 作为上下文内容

### code block

- 向量检索时命中的是摘要化后的文本
- 进入上下文时优先恢复 `metadata.original_content`

### image

- 进入上下文时使用 ingestion 阶段已经写回的 OCR / 图片摘要文本
- 如果 metadata 里有 `image_url`, 也会保留下来用于来源展示

### full_doc

- 即使命中的是某个 chunk, 最终也不是只拿这一小段
- 系统会根据 `file_path` 回源重新读取整篇文档
- 再按 `doc_id` 去重
- 再受 `MAX_FULL_DOCS` 和 `MAX_FULL_DOC_CHARS` 限制

所以 `full_doc` 不是"向量库里存整篇正文", 而是

```text
full_doc retrieval
chunk 命中
-> 识别这是 full_doc 文档
-> 回源读取整篇
-> 整篇进入上下文
```

## 11. ContextItem 是 retrieval 和 generation 之间的统一中间层

命中结果不会直接拼字符串, 而是先被转换成统一结构

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

这个结构的作用是

- 让 text / code / image / full_doc 都能先收敛到统一格式
- 再统一编号
- 再统一拼成最后的 context

## 12. 最终给模型看的 context 是什么样

最后阶段, 系统会把所有 `ContextItem` 展平成一段带编号的纯文本

```text
final context
[1] 第一段内容

[2] 第二段内容

[3] 第三段内容
```

模型真正看到的是这段已经编号好的扁平文本, 而不是原始 chunk 对象

所以从模型视角看, 前面复杂的链路最终都被收敛成两件事

- 一段上下文文本
- 一组可引用的来源标签

## 13. 关于 CHUNK_SIZE, 最后再补一个容易误判的点

如果你看到实际 chunk 表现和 `.env` 里的 `CHUNK_SIZE` 不一致, 先不要直接判断"配置没生效"

要先区分三件事

- 后端默认值是否已经在进程启动时读取
- 实际上传请求有没有显式传 `chunk_size`
- 命中的是不是 image chunk 这种"文本生成晚于切分"的特殊实体

当前实现里

- 后端默认值来自环境变量
- 但请求参数可以覆盖默认值
- 前端上传表单也可能主动提交 `chunk_size`
- image chunk 的 OCR / 多模态文本是在切分后才写回, 不会自动二次切分

所以"看到一个超长 chunk"并不能单独证明 `CHUNK_SIZE` 没生效
