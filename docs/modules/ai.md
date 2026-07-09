# AI模块设计

## 模块职责

基于LLM为每条入库资讯生成摘要，并在Phase 3提供趋势研判能力。

## MVP功能：资讯摘要

采集→分析后的资讯，在入库前调用Claude API生成摘要和结构化要点。

### 调用时机
```
采集器 → 分析器(实体+情感) → AI摘要 → 入库
                                      ↑
                               每条重要资讯必经
```

### Prompt模板

```python
SUMMARIZE_PROMPT = """你是一个专业的A股资讯分析师。请对以下资讯进行分析：

标题：{title}
来源：{source}
{content_section}

请输出JSON格式：
{{
  "summary": "50字以内的核心摘要",
  "key_points": ["要点1", "要点2"],
  "sentiment": "利好/利空/中性",
  "impact_level": "high/medium/low",
  "related_stocks": ["涉及的股票代码"],
  "related_concepts": ["涉及的概念"]
}}"""
```

### 实现

```python
class NewsSummarizer:
    async def summarize(self, raw_news: RawNews, entities: list) -> SummaryResult:
        # 构建prompt（content仅用于生成摘要，不入库）
        content_section = f"内容：{raw_news.content[:2000]}" if raw_news.content else ""
        prompt = SUMMARIZE_PROMPT.format(
            title=raw_news.title,
            source=raw_news.source,
            content_section=content_section,
        )

        # 调用Claude API
        result = await self.llm.chat(prompt, response_format="json")

        return SummaryResult(
            summary=result["summary"],
            key_points=result["key_points"],
            sentiment=result["sentiment"],
            impact_level=result["impact_level"],
        )
```

## Phase 3功能：趋势研判

基于个股近期资讯，综合分析趋势。

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

请以JSON格式输出。"""
```

## 成本控制

| 场景 | 模型 | Token | 频率 |
|------|------|-------|------|
| 资讯摘要 | Claude Haiku | ~500 | 每条入库资讯 |
| 趋势研判 | Claude Sonnet | ~3000 | 用户请求时 |

**优化策略:**
- 摘要生成后缓存到DB，不重复调用
- 批量处理（采集后统一调用，不逐条实时调用）
- 每日Token上限告警

## 监控

- LLM调用延迟（P50/P95）
- 每日Token消耗
- 摘要生成成功率
