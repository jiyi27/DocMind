"""Prompts used during the ingestion phase."""

from langchain_core.prompts import PromptTemplate

code_summarization_prompt = PromptTemplate.from_template(
    """你是一个资深的研发架构师和技术文档整理专家。
你的任务是为下方的一段代码块编写一段高度浓缩、富含语义关键字的【自然语言摘要】，以便于未来的 RAG 向量检索系统能够通过用户的自然语言提问精准命中这段代码。

【上下文信息】
所在文档章节：{headers}
代码语言：{language}

【代码块】
```
{code}
```

【输出要求】
请直接输出摘要文本，不要包含任何多余的寒暄、解释性前缀（如“这段代码是...”）或 Markdown 格式。
你的摘要必须包含以下维度的信息，使其成为高密度的检索特征：
1. 核心意图：用一两句话说明这段代码的目标和业务逻辑（它用来解决什么问题？）。
2. 技术特征：列出代码中使用的核心框架、类名、关键方法名、重要变量名或配置项键值（用自然语言串联起来，这是命中的关键）。
3. 关联场景：如果适用，说明在什么场景下用户会搜索或需要使用这段代码。

【摘要示例参考】
用于初始化 Qdrant 向量数据库连接的 Python 配置代码。核心逻辑包括使用 QdrantClient 建立连接，并通过 _ensure_collection 方法检查和自动创建 docmind 集合。涉及的关键变量和类有 settings.qdrant.url、QdrantVectorStore 和 Embeddings。适用于系统部署、知识库初始化或排查向量库连接失败等场景。"""
)
