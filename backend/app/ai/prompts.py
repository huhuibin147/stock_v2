SUMMARIZE_PROMPT = """你是一个专业的A股资讯分析师。请对以下资讯进行分析：

标题：{title}
来源：{source}
{content_section}

请输出JSON格式（不要输出其他内容）：
{{
  "summary": "50字以内的核心摘要",
  "key_points": ["要点1", "要点2"],
  "sentiment": "利好/利空/中性",
  "impact_level": "high/medium/low"
}}"""
