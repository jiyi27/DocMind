## 1. 重要的写在前面 (Token 就是金钱)

- 图片的多模态处理由 IMAGE_PROCESSOR 控制, 支持 "multimodal" | "ocr" | "none", 定义在 backend/docmind/core/
  config.py:196 和使用处 backend/docmind/ingestion/nodes.py
- 代码 block 的处理由 ENABLE_CODE_SUMMARIZATION 控制, 定义在 backend/docmind/core/config.py
- ingest 流程里代码和图片是两个独立节点: split_text -> summarize_code -> summarize_image -> embed_and_store, 见
  backend/docmind/ingestion/graph.py

对于代码 block, 这个开关控制的是"是否做 LLM 总结", 不是"是否忽略代码块"

- 当 ENABLE_CODE_SUMMARIZATION=false 时, summarize_code_node 直接返回原 chunks, 不做代码总结, 见 backend/docmind/
  ingestion/nodes.py
- 这意味着代码块仍然会被 ingest, 不会被忽略, 只是保持原文进入后续 embedding/store
- 当 ENABLE_CODE_SUMMARIZATION=true 时, 会用普通文本 LLM 对代码块做摘要, 不是图片那种 multimodal, 调用的是
  get_llm() + code_summarization_prompt, 见 backend/docmind/ingestion/nodes.py:469 和 backend/docmind/ingestion/
  prompts.py

还有几个实现细节你应该知道

- 只有"带语言标记的 fenced code block"才会被总结, 比如 ```python, 见 backend/docmind/ingestion/nodes.py
- 很短的代码块不会总结, 长度小于 200 直接跳过, 见 backend/docmind/ingestion/nodes.py
- 如果总结成功, 向量库里存的是摘要文本, 同时原始代码放在 metadata["original_content"], 检索时会还原成原代码给上层
  使用, 见 backend/docmind/ingestion/nodes.py 和 backend/docmind/retrieval/resolvers.py

## 1. 系统是否能够启动

这是最底层的一层行为, DocMind 在启动时不会"尽量跑起来", 而是采用 fail-fast 策略

- 控制项
  `QDRANT_URL`, `LLM_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL`, `CHUNK_SIZE`, `CHUNK_OVERLAP`, `ENABLE_CODE_SUMMARIZATION`, `TOP_K`, `MAX_MESSAGES`, `MAX_FULL_DOCS`, `MAX_FULL_DOC_CHARS`, `LOG_DIR`, `LOG_LEVEL`, `JWT_SECRET_KEY`, `JWT_EXPIRE_MINUTES`, 以及按条件启用的 `IMAGE_VISION_*`, `CONFLUENCE_*`
- 行为
  只要有必填项缺失或格式非法, 服务在启动阶段就会直接退出, 而不是带着半残配置继续运行, 
- 额外规则
  - 当 `IMAGE_PROCESSOR=multimodal` 时, `IMAGE_VISION_API_KEY`, `IMAGE_VISION_MODEL`, `IMAGE_VISION_BASE_URL` 变成必填
  - `CONFLUENCE_BASE_URL` 和 `CONFLUENCE_PAT` 必须同时为空, 或同时有值, 只配一个会直接导致启动失败

这意味着: 如果你想排查"为什么后端起不来", 优先不要看业务逻辑, 而是先看配置完整性

## 2. 文档 ingest 时会怎么切块

所有文档在入库前都会经过 chunking, 这决定了向量库里存的是多大的文本单元

- 控制项
  `CHUNK_SIZE`, `CHUNK_OVERLAP`
- 行为
  - `CHUNK_SIZE` 控制目标分块大小
  - `CHUNK_OVERLAP` 控制相邻块之间重复保留多少上下文
  - Markdown / PDF 在进入统一切分流程后, 系统会尽量保护结构化内容, 不会简单粗暴地按固定长度切断

当前代码对以下结构有明确保护倾向

- 标题层级
- fenced code block
- blockquote
- table

所以这两个参数控制的是"块有多大, 上下文重叠多少", 不是"是否识别代码块, 图片, 标题"

## 3. ingest 时代码块是否会被总结

这是代码类文档最关键的 ingest 行为之一

- 控制项
  `ENABLE_CODE_SUMMARIZATION`
- 行为
  - 当它为 `false` 时, 代码块不会做 LLM 总结, 原始文本直接参与后续 embedding 和存储
  - 当它为 `true` 时, 系统会扫描 chunk 中符合条件的 fenced code block, 用普通文本 LLM 生成摘要, 再用摘要替换原代码参与向量检索

这里要特别注意两个边界

- 这不是"是否忽略代码块"的开关
  关闭后代码块仍然会被 ingest, 只是不做总结, 
- 这也不是"多模态代码理解"的开关
  当前实现里代码块总结走的是常规文本 LLM, 不走 vision / multimodal 模型

当前总结逻辑还有三个重要约束

- 只有带语言标记的 fenced code block 才会被识别, 例如 ````python`
- 很短的代码块会跳过总结
- 如果总结失败, 会回退到保留原始代码, 不会因为单个代码块失败而直接把该 chunk 清空

## 4. ingest 时图片会不会被处理

图片和代码块是两套独立机制, 不共享一个总开关

- 控制项
  `IMAGE_PROCESSOR`
- 可选值
  `multimodal`, `ocr`, `none`

行为可以直接理解为三档

- `IMAGE_PROCESSOR=none`
  系统跳过图片处理, 图片 chunk 不会额外调用图像能力, 
- `IMAGE_PROCESSOR=ocr`
  系统抓取图片后, 使用 OCR 提取文本, 适合"图片里主要是字"的场景, 
- `IMAGE_PROCESSOR=multimodal`
  系统抓取图片后, 调用视觉模型生成图像摘要, 适合图表, 截图, 流程图, 表格等不只是纯文本提取的场景

这几个模式的差异, 不只是"效果不同", 而是"底层处理方式完全不同"

- `ocr` 更像文字抽取
- `multimodal` 更像图像理解加检索摘要
- `none` 就是不处理

## 5. 图片多模态能力由谁提供

当图片处理模式切到 `multimodal` 时, 系统不会复用主对话 LLM, 而是使用单独的一组视觉模型配置

- 控制项
  `IMAGE_PROCESSOR`, `IMAGE_VISION_API_KEY`, `IMAGE_VISION_MODEL`, `IMAGE_VISION_BASE_URL`
- 行为
  - 只有 `IMAGE_PROCESSOR=multimodal` 时, `IMAGE_VISION_*` 才会生效并且变成必填
  - 这组配置专门用于 ingest 阶段的图片总结, 不直接控制普通聊天或代码总结

这背后的设计含义是

- 主文本模型和视觉模型可以分开选型
- 你可以让聊天走一个模型, 让图片理解走另一个模型
- 视觉配置缺失时, 不允许"假装开启了多模态但实际上跑不起来"

## 6. 检索时会取回多少结果

这是问答质量和成本之间最直接的全局平衡杆

- 控制项
  `TOP_K`
- 行为
  向量检索默认只取最相近的前 `K` 个候选结果, 再进入后续上下文组装

这不是一个纯性能参数, 它会直接影响回答风格

- 太小: 容易漏召回, 答案上下文不足
- 太大: 容易把噪声带进 prompt, 回答发散

如果你观察到"经常答不到点上", `TOP_K` 是第一批要看的参数之一

## 7. 对话历史会保留多少轮

系统不是无限带上历史消息, 而是对历史做截断

- 控制项
  `MAX_MESSAGES`
- 行为
  每次聊天时, 只会把最近的若干条历史消息送入生成链路, 更早的消息虽然仍然保存在数据库里, 但不会继续参与当前轮推理

这会影响两个方面

- 上下文连续性
- prompt 体积和生成成本

如果用户反馈"长对话里模型开始忘前文", 先看这个值, 而不是先怀疑数据库没存成功

## 8. 全文检索模式能带多少篇整文进入上下文

DocMind 不是只有 chunk 检索, 还支持按整篇文档参与上下文

- 控制项
  `MAX_FULL_DOCS`, `MAX_FULL_DOC_CHARS`
- 行为
  - `MAX_FULL_DOCS` 限制单次检索最多允许多少篇整文进入上下文
  - `MAX_FULL_DOC_CHARS` 限制每篇整文最多能带多少字符

这两个参数在行为上保护的是"大文档把上下文挤爆"的问题

具体来说

- 命中了全文模式文档后, 不会无限装载整篇内容
- 达到全文数量上限后, 系统会停止继续往后扫描更低排名结果
- 单篇文档过长时会被截断

所以它们控制的不是"能否全文检索", 而是"全文检索的上下文预算上限"

## 9. 聊天和 ingest 用的是不是同一个模型

是部分共享, 部分隔离

- 控制项
  `LLM_API_KEY`, `LLM_MODEL`, `LLM_BASE_URL`
- 行为
  这组配置是系统的主文本模型配置, 主要用于: 
  - 代码块总结
  - RAG 问答生成
  - 流式回答生成
  - 会话标题生成等普通文本生成任务

但图片多模态总结不一定走它, 而是可能走单独的 `IMAGE_VISION_*`

因此可以这样理解

- 文本智能的"总开关"是 `LLM_*`
- 图片视觉理解的"专用通道"是 `IMAGE_VISION_*`

## 10. Confluence 集成是否真正启用

Confluence 不是前端点个开关就能生效, 它首先受后端能力是否启用控制

- 控制项
  `CONFLUENCE_BASE_URL`, `CONFLUENCE_PAT`
- 行为
  - 两者都为空时, Confluence 集成在后端整体禁用
  - 两者都有值时, 后端认为 Confluence 能力可用, 并在启动时创建 Confluence 同步 worker
  - 只填一个时, 服务启动失败

这个行为有两个层次

- 能力层
  后端是否具备调用 Confluence 的基础凭证和 worker
- 业务层
  某个知识库是否开启同步, 根页面是谁, 同步周期是多少

也就是说, `.env` 控制的是"系统有没有 Confluence 能力", 不是"每个 KB 一定开始同步"

## 11. 某个知识库能不能开启 Confluence 同步

这是在"后端具备 Confluence 能力"基础上的第二层控制

- 环境变量控制项
  `CONFLUENCE_BASE_URL`, `CONFLUENCE_PAT`
- 非环境变量控制项
  知识库自己的 `confluence.sync_enabled`, `root_page_id`, `sync_interval_minutes`, `retrieval_mode`

行为上要这样区分

- 如果后端没配 `CONFLUENCE_*`
  即使前端想给某个 KB 打开同步, 也会被后端拒绝, 
- 如果后端已配 `CONFLUENCE_*`
  某个 KB 仍然可以选择不开同步, 或者只配置 Confluence 信息但暂时不启用周期同步

所以 `.env` 决定"有没有这个能力", KB 配置决定"具体哪个知识库要不要用这个能力"

## 12. 谁拥有超级管理员权限

后台的某些能力不是登录后人人都能用, 比如创建或删除知识库

- 控制项
  `SUPER_ADMIN_USERNAMES`
- 行为
  只有用户名在这个列表里的用户, 才能通过 `require_super_admin` 保护的接口

这类行为不是认证本身, 而是认证后的授权

换句话说

- `JWT_*` 解决"你是谁"
- `SUPER_ADMIN_USERNAMES` 解决"你能做什么高权限操作"

如果这里留空, 效果就是关闭超级管理员能力

## 13. 登录后的 token 能活多久

这是认证体验和安全性之间的平衡项

- 控制项
  `JWT_SECRET_KEY`, `JWT_ALGORITHM`, `JWT_EXPIRE_MINUTES`
- 行为
  - `JWT_SECRET_KEY` 控制签名密钥
  - `JWT_ALGORITHM` 控制签名算法
  - `JWT_EXPIRE_MINUTES` 控制 token 的有效期

系统行为上最重要的是最后一个

- 值更小: 更安全, 但用户更容易遇到过期后重新登录
- 值更大: 会话更稳定, 但 token 泄露后的风险窗口也更长

如果用户频繁反馈"刚登录没多久就掉线", 先看这里

## 14. 前端能不能跨域访问后端

这决定了浏览器环境下的 API 调用是否会被 CORS 拦住

- 控制项
  `CORS_ORIGINS`
- 行为
  该值会直接传给 FastAPI 的 `CORSMiddleware` 作为允许来源列表

常见表现如下

- `*`
  所有来源都允许, 开发环境省事, 但生产环境通常不建议, 
- 指定域名列表
  只有列出的前端地址可以直接访问后端

如果前端页面能打开, 但接口在浏览器里报跨域错误, 先看这个, 而不是先查业务代码

## 15. 日志会不会落盘, 以及落到哪里

排障时最容易忽略的一层是日志行为

- 控制项
  `LOG_DIR`, `LOG_LEVEL`
- 行为
  - `LOG_DIR` 决定日志目录位置
  - `LOG_LEVEL` 决定最低写入级别

它们不改变业务逻辑, 但直接决定你能不能看见足够的运行线索

在实际排查里

- `debug` 适合联调和问题分析
- `info` 适合常规运行
- `error` 适合极简日志, 但会牺牲很多过程信息

## 16. 向量库连接的是哪一个服务

系统的检索和入库都依赖 Qdrant, 可是 `.env` 中真正控制的不是"知识库名字", 而是 Qdrant 服务入口

- 控制项
  `QDRANT_URL`
- 行为
  后端会连接这个地址对应的 Qdrant 实例, 具体 collection 不是由环境变量静态决定, 而是按知识库动态创建

这意味着

- 换 `QDRANT_URL`, 本质上是在切换向量库服务
- 不是在切换单个 collection 名字

如果你碰到"同样的 KB 名称在不同环境里查到不同数据", 很可能不是代码差异, 而是 `QDRANT_URL` 指向了不同实例
