# AI模块设计

## 模块职责

基于LLM提供高级智能分析能力：资讯摘要、智能问答、趋势研判。

## 技术方案

- LLM: Claude API (claude-sonnet-4-6)
- RAG: Elasticsearch检索 + 上下文拼接
- 流式输出: SSE (Server-Sent Events)

## 功能设计

### 1. 资讯摘要

将长篇资讯压缩为结构化摘要。

```python
SUMMARIZE_PROMPT = """你是一个专业的财经资讯分析师。请对以下资讯进行分析：

{content}

请输出JSON格式：
{{
  "summary": "50字以内的核心摘要",
  "key_points": ["要点1", "要点2", "要点3"],
  "sentiment": "利好/利空/中性",
  "impact_level": "high/medium/low",
  "related_stocks": ["涉及的股票代码"],
  "related_concepts": ["涉及的概念板块"]
}}"""
```

### 2. 智能问答

基于RAG的财经问答系统。

```python
async def ask(question: str, context: dict | None = None) -> AsyncIterator[str]:
    # 1. 检索相关资讯
    related_news = await search_news(question, limit=10)

    # 2. 构建上下文
    context_text = build_context(related_news, context)

    # 3. 流式调用LLM
    prompt = QA_PROMPT.format(
        question=question,
        context=context_text
    )

    async for chunk in stream_claude(prompt):
        yield chunk
```

**RAG检索策略:**
- 关键词搜索: Elasticsearch全文检索
- 语义搜索: 向量相似度（后续扩展）
- 时间衰减: 近期资讯权重更高
- 相关度排序: 情感强度 + 时效性 + 匹配度

### 3. 趋势研判

多维度综合分析某股票/行业的近期趋势。

```python
TREND_PROMPT = """基于以下近期资讯，分析{target}的趋势：

近期资讯（按时间倒序）：
{news_list}

请分析：
1. 整体趋势判断（偏多/偏空/震荡）
2. 判断置信度（0~1）
3. 主要利多因素
4. 主要利空因素
5. 关键风险提示
6. 需要关注的后续事件

请以JSON格式输出。"""
```

## Prompt管理

```python
# prompts.py
class PromptManager:
    """Prompt模板集中管理"""

    TEMPLATES = {
        "summarize": SUMMARIZE_PROMPT,
        "qa": QA_PROMPT,
        "trend": TREND_PROMPT,
        "event_extract": EVENT_EXTRACT_PROMPT,
        "sentiment_complex": SENTIMENT_COMPLEX_PROMPT,
    }

    @classmethod
    def render(cls, template_name: str, **kwargs) -> str:
        return cls.TEMPLATES[template_name].format(**kwargs)
```

## 成本控制

| 场景 | 模型选择 | 预估Token | 频率 |
|------|----------|-----------|------|
| 资讯摘要 | Claude Haiku | ~500 | 每条资讯 |
| 简单情感 | 规则+模型 | 0 | 实时 |
| 智能问答 | Claude Sonnet | ~2000 | 用户请求 |
| 趋势分析 | Claude Sonnet | ~3000 | 用户请求 |
| 复杂事件提取 | Claude Haiku | ~800 | 低置信度时 |

**优化策略:**
- 缓存已摘要的资讯，不重复生成
- 简单任务用小模型，复杂任务用大模型
- 批量处理非实时场景
- 设置每日Token上限

## 接口实现

### POST /api/v1/ai/summarize
```python
@router.post("/ai/summarize")
async def summarize_news(req: SummarizeRequest):
    news = await get_news(req.news_id)
    if news.summary:
        return {"summary": news.summary}  # 返回缓存

    result = await llm_service.summarize(news.content)
    await save_summary(news.id, result)
    return result
```

### POST /api/v1/ai/ask (SSE)
```python
@router.post("/ai/ask")
async def ask_question(req: AskRequest):
    return StreamingResponse(
        qa_service.ask_stream(req.question, req.context),
        media_type="text/event-stream"
    )
```

## 监控指标

- LLM调用延迟（P50/P95/P99）
- Token消耗（按功能分）
- 缓存命中率
- 用户满意度（点赞/点踩）
