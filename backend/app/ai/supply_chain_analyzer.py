"""供应链AI分析器 - 联网搜索版本（使用OpenAI API）"""

import json
import structlog

from app.core.config import settings
from app.collectors.supply_chain import SupplyChainCollector, SupplyChainParser

logger = structlog.get_logger()

_client = None


def _get_client():
    global _client
    if _client is None:
        if not settings.openai_api_key:
            return None
        from openai import AsyncOpenAI
        _client = AsyncOpenAI(
            api_key=settings.openai_api_key,
            base_url=settings.openai_base_url,
        )
    return _client


SUPPLY_CHAIN_PROMPT_WITH_SEARCH = """你是一个专业的供应链分析师。请基于以下搜索结果，详细分析目标公司的供应链关系。

目标公司：TARGET_NAME（TARGET_TYPE_CN）

搜索结果：
SEARCH_RESULTS

请从搜索结果中提取并整理供应链关系：

1. 上游供应商：为目标公司提供原材料、零部件、设备或服务的公司
2. 下游客户：目标公司的产品或服务的客户公司
3. 合作伙伴：与目标公司有战略合作关系的公司

要求：
- 仔细阅读每条搜索结果，提取所有提到的供应链关系
- company_name 必须使用A股上市公司的标准股票名称（如"雅克科技"而非"雅克科技公司"），非上市公司用全称
- 对每条关系，尽可能详细地描述：
  * 具体提供什么产品或服务（型号、规格、技术参数等）
  * 合作规模、占比、金额等信息
  * 合作开始时间、持续时间
  * 合作的深度和重要程度
- 每条关系必须标注 source_url（搜索结果中的链接URL）
- news_title 和 news_date 从搜索结果中提取

请以JSON格式返回结果：
{
  "summary": "详细的供应链分析摘要（200-300字）",
  "sources": [
    {"title": "搜索结果标题", "url": "链接地址", "source": "来源平台"}
  ],
  "relations": [
    {
      "company_name": "A股标准股票名称",
      "company_code": "股票代码（如果是A股上市公司，否则为空）",
      "relation_type": "supplier/customer/partner",
      "relation_desc": "详细的关系描述（50-100字）",
      "product_service": "具体提供的产品或服务",
      "cooperation_detail": "合作详情（规模、占比、重要程度等）",
      "business_volume": "业务量/金额（如有）",
      "start_time": "合作开始时间（如有）",
      "confidence": 0.8,
      "source": "信息来源说明",
      "source_url": "来源链接URL",
      "news_title": "相关新闻标题",
      "news_date": "新闻日期"
    }
  ]
}

重要：
- company_name 必须是A股标准名称，便于后续匹配股票代码
- 每条关系必须有 source_url，这是信息出处
- confidence: 搜索结果明确提到的设为0.8-0.9，根据行业常识补充的设为0.5-0.7
- 只返回JSON，不要其他内容"""


SUPPLY_CHAIN_PROMPT_KNOWLEDGE = """你是一个专业的供应链分析师。请分析{target_name}（{target_type_cn}）的供应链关系。

请根据你的知识，识别以下类型的供应链关系：
1. 上游供应商：为{target_name}提供原材料、零部件、设备或服务的公司
2. 下游客户：{target_name}的产品或服务的客户公司
3. 合作伙伴：与{target_name}有战略合作关系的公司

请以JSON格式返回结果，包含以下字段：
- summary: 供应链分析摘要（100-200字）
- relations: 关系数组，每个关系包含 company_name, company_code, relation_type, relation_desc, product_service, confidence, source

注意：
- confidence: 根据确定程度设为0.5-0.8
- company_code: A股上市公司填写股票代码，非上市公司或不确定的留空
- 只返回JSON，不要其他内容"""


async def analyze_supply_chain(target_type: str, target_name: str, target_code: str = None) -> dict:
    """分析供应链关系"""
    client = _get_client()

    # 1. 先进行联网搜索
    search_results = await _search_supply_chain_info(target_name, target_code)

    # 2. 如果有搜索结果且有API Key，使用AI分析
    if search_results and client:
        logger.info("using_ai_with_search", target=target_name, results=len(search_results))
        return await _analyze_with_ai(client, target_type, target_name, search_results)

    # 3. 如果有API Key但无搜索结果，使用AI基于知识分析
    if client:
        logger.info("using_ai_knowledge", target=target_name)
        return await _analyze_with_ai_knowledge(client, target_type, target_name)

    # 4. 如果有搜索结果但无API Key，基于规则提取
    if search_results:
        logger.info("using_rules_with_search", target=target_name, results=len(search_results))
        return _generate_from_search_results(target_type, target_name, target_code, search_results)

    # 5. 都没有，使用内置模拟数据
    logger.info("using_mock_data", target=target_name)
    return _get_mock_data(target_type, target_name, target_code)


async def _analyze_with_ai(client, target_type: str, target_name: str, search_results: list[dict]) -> dict:
    """使用AI基于搜索结果进行分析"""
    target_type_cn = "公司" if target_type == "company" else "行业"
    search_text = _format_search_results(search_results)

    # 添加数据来源统计
    sources = set(r.get("source", "") for r in search_results)
    source_info = f"\n数据来源：{', '.join(sources)}，共{len(search_results)}条信息"

    # 使用 replace 而不是 format，避免 JSON 中的花括号问题
    prompt = SUPPLY_CHAIN_PROMPT_WITH_SEARCH
    prompt = prompt.replace("TARGET_NAME", target_name)
    prompt = prompt.replace("TARGET_TYPE_CN", target_type_cn)
    prompt = prompt.replace("SEARCH_RESULTS", search_text + source_info)

    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            max_tokens=4000,  # 增加token限制
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        text = response.choices[0].message.content
        result = _parse_json_response(text)
        return await _validate_and_enhance(result, target_name)
    except Exception as e:
        logger.error("ai_analysis_failed", error=str(e), target=target_name)
        return _generate_from_search_results(target_type, target_name, None, search_results)


async def _analyze_with_ai_knowledge(client, target_type: str, target_name: str) -> dict:
    """使用AI基于知识进行分析（无搜索结果时）"""
    target_type_cn = "公司" if target_type == "company" else "行业"

    prompt = SUPPLY_CHAIN_PROMPT_KNOWLEDGE.format(
        target_name=target_name,
        target_type_cn=target_type_cn,
    )

    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            max_tokens=3000,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        text = response.choices[0].message.content
        result = _parse_json_response(text)
        return await _validate_and_enhance(result, target_name)
    except Exception as e:
        logger.error("ai_knowledge_analysis_failed", error=str(e), target=target_name)
        return _get_mock_data(target_type, target_name, None)


def _parse_json_response(text: str) -> dict:
    """解析AI返回的JSON"""
    # 提取JSON部分
    if "```json" in text:
        text = text.split("```json")[1].split("```")[0]
    elif "```" in text:
        text = text.split("```")[1].split("```")[0]

    return json.loads(text.strip())


async def _search_supply_chain_info(company_name: str, company_code: str = None) -> list[dict]:
    """搜索供应链信息"""
    collector = SupplyChainCollector()
    try:
        results = await collector.search_supply_chain(company_name, company_code)
        logger.info("supply_chain_search", company=company_name, results=len(results))
        return results
    except Exception as e:
        logger.error("supply_chain_search_failed", company=company_name, error=str(e))
        return []
    finally:
        await collector.close()


def _format_search_results(results: list[dict]) -> str:
    """格式化搜索结果为文本"""
    formatted = []
    for i, result in enumerate(results[:10], 1):  # 最多使用10条结果
        title = result.get("title", "")
        abstract = result.get("abstract", "")
        source = result.get("source", "")
        formatted.append(f"[{i}] {title}\n来源: {source}\n内容: {abstract}\n")

    return "\n".join(formatted)


async def _validate_and_enhance(result: dict, target_name: str) -> dict:
    """验证并增强结果"""
    if "relations" not in result:
        result["relations"] = []

    # 尝试匹配股票代码
    for relation in result.get("relations", []):
        if not relation.get("company_code"):
            # 可以在这里添加股票代码匹配逻辑
            pass

    return result


def _generate_from_search_results(
    target_type: str,
    target_name: str,
    target_code: str,
    search_results: list[dict]
) -> dict:
    """基于搜索结果生成供应链数据（无API Key时使用）"""
    parser = SupplyChainParser()

    # 从搜索结果中提取公司（排除目标公司自身）
    companies = parser.extract_companies(search_results, target_name)

    # 生成关系
    relations = []
    for company in companies[:10]:
        # 简单规则判断关系类型
        relation_type = _guess_relation_type(company.get("contexts", []))

        relations.append({
            "company_name": company["name"],
            "company_code": None,  # 需要进一步匹配
            "relation_type": relation_type,
            "relation_desc": f"基于搜索结果发现的{relation_type}关系",
            "product_service": "",
            "confidence": min(0.5 + company.get("source_count", 0) * 0.1, 0.8),
            "source": f"搜索结果（出现{company.get('source_count', 0)}次）",
        })

    # 生成摘要
    summary = f"基于联网搜索，发现了{target_name}的{len(relations)}个潜在供应链关系。"
    if relations:
        upstream = len([r for r in relations if r["relation_type"] == "upstream"])
        downstream = len([r for r in relations if r["relation_type"] == "downstream"])
        partner = len([r for r in relations if r["relation_type"] == "partner"])
        summary += f"其中上游供应商{upstream}家，下游客户{downstream}家，合作伙伴{partner}家。"
    summary += "（注：由于未配置AI API，数据基于简单规则提取，建议配置API后重新分析）"

    return {
        "summary": summary,
        "relations": relations,
    }


def _guess_relation_type(contexts: list[str]) -> str:
    """根据上下文猜测关系类型"""
    text = " ".join(contexts)

    # 上游关键词
    upstream_keywords = ["供应", "提供", "采购", "原材料", "设备", "零部件", "服务商"]
    # 下游关键词
    downstream_keywords = ["客户", "销售", "终端", "应用", "使用"]
    # 合作关键词
    partner_keywords = ["合作", "战略", "联盟", "合资"]

    for kw in upstream_keywords:
        if kw in text:
            return "upstream"

    for kw in downstream_keywords:
        if kw in text:
            return "downstream"

    for kw in partner_keywords:
        if kw in text:
            return "partner"

    # 默认返回上游
    return "upstream"


def _get_mock_data(target_type: str, target_name: str, target_code: str = None) -> dict:
    """模拟数据（无API Key且无搜索结果时使用）"""
    if target_name in ["长鑫", "长鑫存储", "CXMT"]:
        return {
            "summary": "长鑫存储（CXMT）是中国领先的DRAM内存芯片制造商，总部位于安徽合肥。"
                       "其供应链涵盖半导体设备、材料、封测等多个环节，与多家国内外知名企业有紧密的供应链关系。",
            "relations": [
                {
                    "company_name": "北方华创",
                    "company_code": "002371",
                    "relation_type": "upstream",
                    "relation_desc": "半导体设备供应商",
                    "product_service": "刻蚀设备、薄膜沉积设备",
                    "confidence": 0.9,
                    "source": "公开财报、行业报道"
                },
                {
                    "company_name": "中微公司",
                    "company_code": "688012",
                    "relation_type": "upstream",
                    "relation_desc": "半导体设备供应商",
                    "product_service": "刻蚀设备",
                    "confidence": 0.85,
                    "source": "公开财报、行业报道"
                },
                {
                    "company_name": "沪硅产业",
                    "company_code": "688126",
                    "relation_type": "upstream",
                    "relation_desc": "硅片供应商",
                    "product_service": "硅片",
                    "confidence": 0.8,
                    "source": "行业报道"
                },
                {
                    "company_name": "通富微电",
                    "company_code": "002156",
                    "relation_type": "downstream",
                    "relation_desc": "封测服务商",
                    "product_service": "芯片封装测试",
                    "confidence": 0.7,
                    "source": "行业报道"
                },
            ],
        }

    return {
        "summary": f"{target_name}的供应链分析结果。由于未配置AI API Key且搜索结果有限，返回模拟数据。",
        "relations": [
            {
                "company_name": "示例供应商A",
                "company_code": "000001",
                "relation_type": "upstream",
                "relation_desc": "主要原材料供应商",
                "product_service": "原材料",
                "confidence": 0.5,
                "source": "模拟数据"
            },
        ],
    }


def _get_fallback_data(target_type: str, target_name: str, target_code: str = None) -> dict:
    """降级数据（搜索和API都失败时使用）"""
    return {
        "summary": f"{target_name}的供应链分析暂时无法完成，请稍后重试。",
        "relations": [],
    }


SUPPLEMENT_PROMPT = """你是一个专业的供应链分析师。请基于补充内容，为{target_name}挖掘更多的供应链关系。

已有供应链关系：
{existing_relations}

补充内容：
{supplement_content}

{supplement_note_section}

请从补充内容中提取新的供应链关系（不要重复已有关系）。

要求：
- 仔细阅读补充内容，提取所有提到的供应链关系
- 对每条关系，尽可能详细地描述
- 标注信息来源
- 只返回新的关系，不要重复已有的

请以JSON格式返回结果：
{
  "summary": "补充分析摘要（100-200字）",
  "relations": [
    {
      "company_name": "公司名称",
      "company_code": "股票代码",
      "relation_type": "supplier/customer/partner",
      "relation_desc": "详细的关系描述",
      "product_service": "具体产品或服务",
      "cooperation_detail": "合作详情",
      "business_volume": "业务量",
      "start_time": "合作时间",
      "confidence": 0.8,
      "source": "来源说明",
      "source_url": "来源链接",
      "news_title": "新闻标题",
      "news_date": "新闻日期"
    }
  ]
}

只返回JSON，不要其他内容"""


async def analyze_with_supplement(
    target_type: str,
    target_name: str,
    existing_relations: list,
    supplement_content: str,
    supplement_note: str = None,
) -> dict:
    """基于补充内容进行分析"""
    client = _get_client()

    if not client:
        logger.warning("no_api_key", msg="未配置OpenAI API Key，无法进行补充分析")
        return {"summary": "未配置AI API，无法进行补充分析", "relations": []}

    # 格式化已有关系
    existing_text = ""
    for rel in existing_relations:
        existing_text += f"- {rel.get('company_name')}: {rel.get('relation_type')} - {rel.get('relation_desc', '')}\n"
    if not existing_text:
        existing_text = "暂无"

    # 补充说明
    supplement_note_section = f"补充说明：{supplement_note}" if supplement_note else ""

    # 使用 replace 而不是 format
    prompt = SUPPLEMENT_PROMPT
    prompt = prompt.replace("{target_name}", target_name)
    prompt = prompt.replace("{existing_relations}", existing_text)
    prompt = prompt.replace("{supplement_content}", supplement_content)
    prompt = prompt.replace("{supplement_note_section}", supplement_note_section)

    try:
        response = await client.chat.completions.create(
            model=settings.openai_model,
            max_tokens=4000,
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3,
        )
        text = response.choices[0].message.content
        result = _parse_json_response(text)
        return result
    except Exception as e:
        logger.error("supplement_analysis_failed", error=str(e), target=target_name)
        return {"summary": f"补充分析失败: {str(e)}", "relations": []}
