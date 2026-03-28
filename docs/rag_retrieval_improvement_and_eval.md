# DocMind RAG 检索改进与 Retrieval Eval 方法论

2026-03-26

本文档整理两部分内容

- 针对当前 `DocMind` 系统的 RAG 检索改进建议
- Retrieval Eval 的定义, 指标, 以及在本系统中的最小落地方案

重点不是抽象讨论, 而是结合当前仓库的实际实现, 给出可执行的工程建议

## 1. 背景与目标

在一个典型的 RAG 系统中, 召回质量通常由以下几层共同决定

- 文档如何切块
- chunk 是否保留足够语义和上下文
- 向量检索是否能覆盖 query 的真实表达
- 是否有 keyword / BM25 等补充召回信号
- 是否有 query rewrite, rerank, parent expansion 等二阶段策略

对于 `DocMind`, 当前最需要提升的不是生成阶段, 而是 retrieval 阶段的召回完整性和排序稳定性

换句话说, 如果第一阶段没有把正确内容找回来, 后面的回答模型再强也无从补救

## 2. 当前系统现状

结合当前代码, `DocMind` 的 retrieval 主链路大致如下

1. ingestion 时对文档做结构化切块
2. chunk 直接写入 Qdrant
3. retrieval 时使用用户原始 query 调用 `similarity_search_with_score`
4. 将召回到的 chunk 直接拼装成生成上下文

当前实现有几个已经做得不错的点

- Markdown / PDF 统一走结构化切块路径
- 切块时会保留标题层级, 并把标题 breadcrumb 拼到 chunk 前面
- 代码块, 表格, blockquote 会被特殊保护, 避免被粗暴切断
- 支持 `full_doc` 模式, 说明系统已经意识到"小 chunk 命中但上下文不足"的问题

但当前 retrieval 仍然有几个明显限制

- 只有单路 dense vector retrieval
- 没有 hybrid retrieval
- 没有 query rewrite 或 multi-query
- 没有 rerank
- 没有 parent retrieval / neighbor expansion
- 没有 retrieval eval 闭环, 很难判断改动是否真的提升了召回

因此, 当前系统已经具备一个不错的 chunking 基础, 但 retrieval 策略仍然偏基础版

## 3. 关于 chunk size 的结论

对于当前系统, 不建议把优化重点理解为"找到一个神奇的 chunk size"

更准确的结论是

- `chunk 的语义完整性` 通常比固定长度更重要
- `chunk size` 仍然重要, 但它更像调参区间, 而不是唯一答案
- 召回提升通常来自 `chunking + retrieval strategy + eval` 的组合, 而不是只改一个 size

对当前系统来说, 一个好的 chunk 应至少满足这些条件

- 脱离相邻 chunk 后, 人仍能大致理解这段在说什么
- 不丢失关键主语, 条件, 时间, 配置项, 错误码
- 不把多个无关主题硬塞进同一个 chunk
- 尽量带上标题路径, 文档标题等上下文

当前系统已经做了标题 breadcrumb, 这是正确方向, 但还可以继续加强 document-level context

## 4. 针对 DocMind 的改进建议

下面的优先级顺序, 是按"投入产出比"和对当前架构的适配度来排的

### 4.1 第一优先级: 增加 hybrid retrieval

当前系统是单路向量检索, 这对纯语义问题有效, 但对下面这些 query 容易漏召回

- API 名称
- 类名 / 函数名
- 配置项名
- 错误码
- 版本号
- 表格字段
- 专有术语

这些内容在 BM25 / keyword 检索里往往更稳

建议改为

- dense retrieval 召回一批候选
- keyword / BM25 再召回一批候选
- 做 rank fusion 或统一合并去重

这样可以同时覆盖语义相似和精确词匹配两类 query

### 4.2 第二优先级: 增强 chunk 的 document-level context

当前 chunk 已经带有标题 breadcrumb, 但仍然主要是正文 + 标题路径

建议继续增强为更明确的 contextual chunk, 例如在 embedding 前补入

- 文档标题
- 章节路径
- 来源 URL
- 文档类型
- 该 chunk 在全文中的主题说明

目标不是让 metadata 代替正文, 而是让 chunk 更像一个"可独立理解的检索单元"

### 4.3 第三优先级: 不再靠直觉调 chunk size, 改用实验比较

当前系统里存在两组默认值

- `backend/.env.example`: `CHUNK_SIZE=500`, `CHUNK_OVERLAP=50`
- `backend/.env`: `CHUNK_SIZE=400`, `CHUNK_OVERLAP=200`

这说明系统当前对最优参数还没有稳定结论

同时, 当前 chunk 预算主要按字符数而不是 token 数工作, 这会带来两个问题

- 不同语言下字符数与 token 数不稳定
- overlap 很容易被设得过大

建议

- 中长期: 改为 token-aware 的切块预算
- 短期: 先做三档实验, 不再拍脑袋定值

建议的试验区间

- 小块: 约 `250-350 tokens`
- 中块: 约 `450-650 tokens`
- 大块: 约 `700-900 tokens`

如果短期内仍按字符做预算, overlap 建议优先回到 chunk 的 `10%-20%` 区间, 避免过高重叠造成重复召回和上下文浪费

### 4.4 第四优先级: 做 small-to-large retrieval

当前系统检索到哪个 chunk, 就把哪个 chunk 用于生成

这个策略的问题是

- 小 chunk 更容易命中
- 但命中后上下文可能不够完整

建议改为

- 用小 chunk 建索引
- 检索命中后, 根据 `doc_id` 和标题层级补回父块或邻近 chunk
- 给生成模型的是一个更完整的局部上下文窗口

这类 parent retrieval / neighbor expansion, 通常比一开始把 chunk 切很大更稳

### 4.5 第五优先级: 增加 query rewrite / multi-query

当前 retrieval 直接使用用户原始 query 去检索

这会吃亏于

- 口语表达
- 模糊描述
- 描述过长
- 问法与文档原文措辞不一致

建议增加一个轻量预处理层

- query normalization
- query rewrite
- multi-query expansion

目标是把用户问题转成更适合检索的表达, 提高第一阶段召回覆盖率

### 4.6 第六优先级: 二阶段 rerank

当第一阶段召回候选足够多时, rerank 可以显著提高前排结果质量

典型流程是

- first-stage retrieval 先取 top 30 / 50 / 100
- second-stage rerank 再筛到 top 5 / 10 / 20

但对于当前系统, rerank 不应该排在最前面

原因是

- 如果第一阶段本来就漏召回, rerank 也救不回来
- 先补 hybrid retrieval 和 query rewrite, 往往收益更高

## 5. 为什么要做 Retrieval Eval

如果没有 retrieval eval, 那么每次改 chunking 或 retrieval 策略时, 团队只能凭主观感觉判断

例如

- "感觉这次好像更准了"
- "似乎回答更完整了"
- "这个 size 看起来更合理"

这类判断不够稳定, 也不利于做工程决策

Retrieval Eval 的作用就是

- 把"召回效果"从主观感受变成可对比的数据
- 让不同 chunking / retrieval 配置可以做 A/B 比较
- 单独评估 retrieval, 避免把问题混进生成阶段

一句话概括

`Retrieval Eval 不是评估回答写得好不好, 而是评估系统有没有把该找的内容找回来`

## 6. Retrieval Eval 集是什么

所谓 retrieval eval 集, 本质上是一套专门测试检索质量的样本集合

每条样本至少应包含

- `query`: 用户可能会怎么问
- `kb_name`: 该在哪个知识库里测
- `gold_doc_ids` 或 `gold_chunk_ids`: 理论上应该召回到的目标内容

一个最小样例如下

```json
{
  "query": "Confluence 同步失败怎么排查? ", 
  "kb_name": "product_docs", 
  "gold_doc_ids": ["doc_123"]
}
```

这条样本表示

- 当用户这样问时
- 在 `product_docs` 这个 KB 里
- 系统至少应该把 `doc_123` 这篇文档召回出来

## 7. 对 DocMind 来说, 最推荐的起步方式

### 7.1 先做 document-level eval, 不要一上来做 chunk-level eval

对于当前系统, 最适合先做的是 document-level eval

原因

- 现有系统天然有 `doc_id`
- 文档级命中比 chunk 级标注简单得多
- 足以先比较 chunking 与 retrieval 方案

换句话说, 第一阶段先回答这个问题

`正确文档有没有出现在 top K 结果里`

而不是一开始就要求

`正确 chunk 是否精确命中`

### 7.2 样本数量不需要一开始就很多

建议先人工整理 `30-50` 条样本即可

来源优先选这些

- 用户真实常问的问题
- 你们自己知道经常漏召回的问题
- 关键业务场景
- 容易混淆的 query

建议覆盖不同类型

- 精确关键词型
- 模糊语义型
- 长句描述型
- 错误码 / 配置项 / 版本号型
- 表格字段型

### 7.3 最适合当前系统的样本主题

结合 `DocMind` 当前功能, 优先覆盖这些主题

- Confluence 同步相关
- knowledge base 创建与配置
- embedding 配置
- ingestion 行为
- `chunk` 与 `full_doc` 的差异
- 常见报错排查

## 8. 推荐指标

对于当前系统, 最小可用指标集合如下

### 8.1 Recall@K

定义

- 看正确目标是否出现在 top K 召回结果中

例如

- `Recall@1`: 正确文档是否排在第一条
- `Recall@3`: 正确文档是否出现在前三条
- `Recall@5`: 正确文档是否出现在前五条

这组指标最适合作为第一阶段的核心指标

### 8.2 Precision@K

定义

- 前 K 条结果里, 有多少是真正相关的

如果一个方案 Recall 很高, 但前排夹杂大量噪声, Precision 会下降

### 8.3 MRR

定义

- Reciprocal Rank, 更关注第一个正确结果排得有多靠前

它适合比较排序质量, 特别适合多次调 retrieval 排序逻辑时使用

### 8.4 nDCG

定义

- 当一条 query 对应多个相关结果时, 用于衡量排序整体质量

这对"一个问题可能需要多篇文档共同支撑"的场景更有意义

## 9. 当前系统的最小落地方案

对 `DocMind`, 最小版本完全不需要大改主链路

建议做法

1. 在 `backend/testdata/` 下放一份 `retrieval_eval.jsonl`
2. 每行一个样本, 至少包含 `query`, `kb_name`, `gold_doc_ids`
3. 在 `backend/` 下写一个临时脚本 `tmp_retrieval_eval.py`
4. 脚本直接调用现有 retrieval 逻辑
5. 输出 Recall@1 / Recall@3 / Recall@5
6. 同时打印漏召回样本, 便于人工排查

建议的样本格式如下

```json
{"query":"Confluence 同步失败怎么排查? ", "kb_name":"product_docs", "gold_doc_ids":["doc_123"]}
{"query":"如何配置 embedding 模型", "kb_name":"product_docs", "gold_doc_ids":["doc_456"]}
```

脚本逻辑大致分为这几步

1. 读入样本文件
2. 对每条样本调用 retrieval 接口
3. 取 top K 返回结果
4. 判断是否命中 gold 文档
5. 累计统计 Recall@1 / Recall@3 / Recall@5
6. 输出 miss case 列表

## 10. 实施时的一个实际注意点

当前 `/search` 和 `retrieve_with_items()` 已经能返回检索结果, 但做 eval 时最好明确保留文档标识信息

也就是说, 用于 eval 的返回结果中最好能稳定拿到

- `doc_id`
- `title`
- `url`
- score

如果当前 `ContextItem` 没有直接暴露足够的文档身份字段, 可以在 eval 路径里单独补充, 不一定要影响正式对外接口

## 11. 建议的实验顺序

为了让 eval 真正服务于工程决策, 建议按下面顺序推进

### 阶段一: 建立 baseline

- 固定当前 retrieval 逻辑
- 建 30-50 条 document-level 样本
- 跑出 baseline 的 Recall@1 / 3 / 5

### 阶段二: 先比较 chunking 参数

- 比较小块 / 中块 / 大块
- 比较不同 overlap
- 看 Recall@K 的变化

### 阶段三: 引入 hybrid retrieval

- 对比 dense only 与 dense + keyword
- 观察错误码, 配置项, API 名这类 query 的变化

### 阶段四: 引入 query rewrite

- 比较原 query 与 rewrite 后 query
- 观察模糊问法和长句问法的变化

### 阶段五: 引入 rerank 或 parent expansion

- 这一步主要比较排序前排质量和上下文完整性

## 12. 一些常见误区

### 12.1 误区: 只要找到最佳 chunk size, 召回率就会自然变好

不准确

chunk size 只是影响因素之一

很多情况下, 真正限制召回率的是

- query 表达和文档表达不一致
- 缺少 keyword 信号
- chunk 缺少上下文身份
- 检索后没有二阶段处理

### 12.2 误区: 只看最终回答好不好就够了

不够

最终回答质量混合了多层因素

- retrieval
- prompt
- model 推理
- 引用拼接

如果 retrieval 本身有问题, 只看最终回答很难定位问题出在哪一层

### 12.3 误区: 一开始就要做很复杂的评测框架

没必要

对当前系统来说, 最小版本只做这些就够用了

- 30-50 条人工样本
- document-level gold labels
- Recall@1 / 3 / 5

这已经足够支持第一轮 chunking 和 retrieval 策略调整

## 13. 最终建议

针对当前 `DocMind`, 推荐的总体路线是

1. 先建最小 retrieval eval 集, 建立 baseline
2. 优先做 hybrid retrieval
3. 增强 chunk 的 document-level context
4. 用实验而不是直觉重新确定 chunk size / overlap
5. 加 query rewrite
6. 再考虑 rerank 和 parent retrieval

这一顺序的核心原因是

- 先让系统有可测量的召回指标
- 再做高收益的第一阶段召回增强
- 最后再做精排和上下文扩展

如果没有 eval, 后续所有优化都会变成"感觉更好了"

如果有 eval, 才能真正回答这些问题

- 哪个 chunking 配置更好
- hybrid retrieval 是否值得
- query rewrite 是否有效
- rerank 是否真的提升了前排质量

这也是把 RAG 检索从"经验调参"走向"可验证工程优化"的关键一步
