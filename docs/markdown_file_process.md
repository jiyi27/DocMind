说一下我对 `_custom_split_markdown()` 函数的理解:

> 理解误区: 文档内容有普通文字, 标题, code block, image, quote, table, 不同的内容有不同的处理方式, 其中 code block, image, quote, table block 需要完整语义, 也就是说他们不允许被切分成多个小 chunk
>
> 这里有个理解是不正确的, fenced code block 内部其实分两类，行为完全不同：
> - **带语言标注的 code block**（如 ` ```python `）：会独立生成一个或多个 `CHUNK_TYPE_CODE_BLOCK` Document，而不是融入普通文本 chunk
> - **无语言标注的 fenced block**（如 ` ``` ` 不带语言）：去掉 markdown fences 后，内容作为普通文本融入当前 chunk，和 quote/table 一样
>
> image 和带语言标注的 code block 会单独成块；quote / table / 无语言 fenced block 是”原子 block”，只是保证不被段落切分拆碎，但不一定是独立 chunk。恢复占位符之后，它们进入 current_texts，和普通文字一起打包；如果打包后整块长度 > target_size，就进入 `_halve_text()`，然后被二分切开。

形成 chunk 的条件:

- 遇到标题，收口前文
- 遇到图片，收口前文，图片单独成块
- 遇到带语言标注的 code block，收口前文，code block 单独成块（太长时拆成多个 code chunk）
- 正文累计太长(超过配置里的 chunk size)，自动收口
- 文档结束，把尾巴收口

再补一个很容易忽略的点：

quote / table / 无语言 fenced block 本身不会主动触发 chunk。它们在分类里都属于 content，默认只是被当成一个普通内容块塞进当前 chunk。带语言标注的 code block 则不同，它会主动触发 flush，然后单独成为一个类型为 `code` 的 block。

处理流程, 输入一篇 Markdown 长文 `text`

```
1. 先把所有 fenced block / blockquote / table 保护起来，替换成占位符，避免它们内部的空行干扰段落切分。
   - 带语言标注的 fenced block（```python 等）→ __CODE_BLOCK_N__ 占位符
   - 无语言标注的 fenced block（``` 不带语言）→ __PLAIN_FENCED_BLOCK_N__ 占位符
2. 然后按双换行把全文切成”段落级 block 列表”。
3. 再逐个 block 分类成 `header / image / code / content`。
4. 如果是 `content`：
   - 先恢复其中的占位符（__PLAIN_FENCED_BLOCK__ 去掉 fences 变成普通文本，__BLOCKQUOTE__/__TABLE__ 恢复为清洁文本）
   - 如果太长就继续二分
   - 然后放进当前 chunk 累积器 `current_texts`
5. 如果是 `header`：
   - 先把前面积累的 `current_texts` flush 成 chunk
   - 再更新当前章节路径 `current_headers`
   - 后面的 chunk 会继承这个 header 上下文
6. 如果是 `image`：
   - 先 flush 当前文本 chunk
   - 再把 image 单独生成为一个 image 类型的 `Document`
7. 如果是 `code`（带语言标注的 fenced block）：
   - 先 flush 当前文本 chunk
   - 再把 code block 单独生成为一个或多个 code 类型的 `Document`
   - 如果 code 内容超过 target_size，用 `_split_code_content_by_budget()` 二分拆分，每段重新包上 ``` 围栏
8. 每次 flush 时：
   - 会把 `title + header path` 拼成 breadcrumb 加到 chunk 开头
   - 会保留一部分尾部 block 作为 overlap，给下一个 chunk 续上上下文
9. 全部 block 处理完后，最后再 flush 一次
```

- `image` 不是前置占位保护，而是后置分类识别
- `code block` 要分两类看：带语言标注的是独立 chunk，无语言标注的是普通 content
- `quote/table/无语言 fenced block` 是原子 block，不等于一定独立 chunk
- `header` 不只是 flush 边界，还是章节上下文更新器
- `flush` 后会保留 overlap


