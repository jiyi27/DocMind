# FAQ

## Chunking Behavior

### Q: `CHUNK_OVERLAP` 会被算进 `CHUNK_SIZE` 吗

不会, 两者是独立的机制

每次 `flush_chunk()` 密封一个 chunk 后, 会从该 chunk 的末尾块开始**倒序**收集内容, 直到累计字符数超过 `CHUNK_OVERLAP` 预算为止, 这些尾部块会作为**下一个 chunk 的起始内容**重新注入

实际效果: 每个新 chunk 开头携带上一个 chunk 末尾约 `CHUNK_OVERLAP` 字符的内容, 然后继续追加新块, 直到总长超过 `CHUNK_SIZE` 再触发下一次 flush, 因此一个 chunk 的实际字符数可能超过 `CHUNK_SIZE`(overlap 带入的内容 + 新内容不会被截断)

### Q: Overlap 的选取是字符盲切, 还是优先保留完整段落

是**块级选取**, 不是字符盲切

`_collect_overlap_blocks` 的操作对象是**已经按 `\n\n` 分好的段落块列表**, 每次以整块为单位放入 overlap, 放不下就停, 不会在块内部截断, 所以 overlap 保留的内容一定是**完整的段落**, 不会出现半句话

唯一的边界情况: 如果当前 chunk 的最后一个块本身超过 `CHUNK_OVERLAP` 字符, 该块无法放入预算, 则下一个 chunk 的 overlap 为空

### Q: Code block, blockquote, table, image 超过 `CHUNK_SIZE` 会被切开吗

| Block 类型                      | 保护机制                                                    | 超过 CHUNK_SIZE 的行为                  |
| ------------------------------- | ----------------------------------------------------------- | --------------------------------------- |
| **Code block**(\`\`\`...\`\`\`) | 切割前替换为 `__CODE_BLOCK_N__` 占位符                      | **整体保留, 不切割**, 单独占一个 chunk  |
| **Blockquote**(`>` 开头)        | 切割前替换为 `__BLOCKQUOTE_N__` 占位符                      | **整体保留, 不切割**, 单独占一个 chunk  |
| **Table**(pipe 语法)            | 切割前替换为 `__TABLE_N__` 占位符 (转为 `key: value` prose) | **整体保留, 不切割**, 单独占一个 chunk  |
| **Image**(`![alt](url)`)        | 单独 emit 一个 Document, 不参与 pack 逻辑                   | **独立成一个 chunk**, 不受大小控制      |
| **普通段落 (prose)**            | 直接参与大小判断                                            | **超过则被 `_halve_text` 递归二分切割** |

### Q: 普通段落超过 `CHUNK_SIZE` 是怎么切的

走 `_halve_text` 递归二分

1. 找文本中点前后 ±100 字符范围内**最近的换行符**作为切割点
2. 找不到换行符则直接在中点硬切
3. 对每个子片段递归重复, 直到所有片段都 ≤ `CHUNK_SIZE`

---

## 文档大小限制

### Q: 系统对上传文档有没有大小限制, 什么情况下会触发

**限制只在 `full_doc` 检索模式下生效**, `chunk` 模式没有大小限制, 文档会被正常切片入库

`full_doc` 模式下, 控制参数是 `MAX_FULL_DOC_CHARS`, 有三处地方会用到它:

**手动上传**

上传时在入队前先解析文档并统计字符数, 超过限制直接返回 HTTP 422, 文件不会进入 ingestion pipeline

**Confluence 同步**

新建或更新页面时, 拉取并转换为 Markdown 后检查长度:
- 新建: 超过限制 → 同步记录标记为 `failed`, 跳过该页面, 不影响其他页面继续同步
- 更新: 超过限制 → 同步记录标记为 `failed`, **保留旧版文档不做替换**

**检索时**

即使文档已经入库, 检索时读取原始文件注入上下文时, 仍会在 `MAX_FULL_DOC_CHARS` 处截断, 防止单篇文档把整个上下文窗口挤满
