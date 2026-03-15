## 测试标题

这涉及到目前 RAG 技术中最前沿和最痛点的部分：数据治理与语义级切片（Semantic Chunking）


在 RAG 中，如果检索到的切片（Chunk）是断章取义的、一半代码一半文本的，或者把一个完整的表格劈成了两半，那么不管后面的 LLM 有多强大，生成的答案都会很糟糕(这被称为 Garbage In, Garbage Out)


关于“把文档代码都翻译成文字”


- 不建议完全替换： 如果用户问了一个编程问题，他期望看到的往往是原始代码，而不是代码的文字描述。如果预处理时把代码丢了，RAG 就失去了回答代码问题的能力
- 优化方案（Multi-Vector 策略）： 更好的做法是保留原始代码，然后让 LLM 为这段代码生成一段“摘要/解释”。我们把“摘要”向量化存入数据库，但把它和“原始代码”绑定。检索时，基于摘要的语义进行匹配，匹配中后，把完整的原始代码丢给 RAG 的生成模型


```python
def build_rag_graph():
    """Build and compile a stateless RAG chat graph.


    Flow
    ——
    retrieve → generate → END


    History is injected into the initial state by the caller; the graph
    itself holds no session state between invocations.
    “”"
    graph = StateGraph(RAGState)


    graph.add_node("retrieve", retrieve_node)
    graph.add_node("generate", generate_node)


    graph.set_entry_point(“retrieve”)
    graph.add_edge("retrieve", “generate”)
    graph.add_edge("generate", END)


    return graph.compile()




# Module-level singleton — safe to reuse across requests (stateless)
rag_graph = build_rag_graph()
```


## 测试标题


> 这涉及到目前 RAG 技术中最前沿和最痛点的部分：数据治理与语义级切片（Semantic Chunking）
>
> 在 RAG 中，如果检索到的切片（Chunk）是断章取义的、一半代码一半文本的，或者把一个完整的表格劈成了两半，那么不管后面的 LLM 有多强大，生成的答案都会很糟糕(这被称为 Garbage In, Garbage Out)
