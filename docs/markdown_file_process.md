说一下我对 `_custom_split_markdown()` 函数的理解: 

> 理解误区: 文档内容有普通文字, 标题, code block, image, quote, table, 不同的内容有不同的处理方式, 其中 code block, image, quote, table block 需要完整语义, 也就是说他们不允许被切分成多个小 chunk
> 
> 这里有个理解是不正确的, 只有 image 会会单独生成一个 Document chunk, 其他的 block 并不是一定“单独成一个 chunk”, 它们只是保证不会在段落切分阶段被拆碎。恢复占位符之后，它们会按 content block 进入 current_texts，和普通文字一起打包, 如果打包后的整块长度 > target_size，就会进入 _halve_text()，然后被二分切开, 也就是说：它们是“原子 block”, 但不一定是“独立 chunk”

形成 chunk 的条件:

- 遇到标题，收口前文
- 遇到图片，收口前文，图片单独成块
- 正文累计太长(超过配置里的 chunk size)，自动收口
- 文档结束，把尾巴收口

再补一个很容易忽略的点：

quote / table / code block 本身不会主动触发 chunk。它们在分类里都属于 content，所以默认只是被当成一个普通内容块塞进当前 chunk

处理流程, 输入一篇 Markdown 长文 `text`

```
1. 先把 `code block / blockquote / table` 保护起来，替换成占位符，避免它们内部的空行干扰段落切分。
2. 然后按双换行把全文切成“段落级 block 列表”。
3. 再逐个 block 分类成 `header / image / content`。
4. 如果是 `content`：
   - 先恢复其中的占位符
   - 如果太长就继续二分
   - 然后放进当前 chunk 累积器 `current_texts`
5. 如果是 `header`：
   - 先把前面积累的 `current_texts` flush 成 chunk
   - 再更新当前章节路径 `current_headers`
   - 后面的 chunk 会继承这个 header 上下文
6. 如果是 `image`：
   - 先 flush 当前文本 chunk
   - 再把 image 单独生成为一个 image 类型的 `Document`
7. 每次 flush 时：
   - 会把 `title + header path` 拼成 breadcrumb 加到 chunk 开头
   - 会保留一部分尾部 block 作为 overlap，给下一个 chunk 续上上下文
8. 全部 block 处理完后，最后再 flush 一次
```

- `image` 不是前置占位保护，而是后置分类识别
- `quote/table/code block` 是原子 block，不等于一定独立 chunk
- `header` 不只是 flush 边界，还是章节上下文更新器
- `flush` 后会保留 overlap


