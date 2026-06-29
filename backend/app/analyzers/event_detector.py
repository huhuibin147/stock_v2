from dataclasses import dataclass

import structlog

logger = structlog.get_logger()

# 事件模板: (关键词列表, event_type, event_subtype, impact)
EVENT_TEMPLATES: list[tuple[list[str], str, str, int]] = [
    # 业绩
    (["业绩预增", "净利润增长", "盈利增长"], "performance", "pre_increase", 1),
    (["业绩预减", "净利润下降", "盈利下降"], "performance", "pre_decrease", -1),
    (["业绩亏损", "净利润亏损"], "performance", "loss", -1),
    (["扭亏为盈", "业绩扭亏"], "performance", "turnaround", 1),
    # 并购重组
    (["收购", "并购"], "merger", "acquisition", 0),
    (["重组"], "merger", "restructuring", 0),
    (["分拆", "分立"], "merger", "spin_off", 0),
    # 股权
    (["回购"], "equity", "buyback", 1),
    (["股权激励", "限制性股票"], "equity", "incentive", 1),
    (["增持"], "equity", "top_up", 1),
    (["减持"], "equity", "top_down", -1),
    # 风险
    (["违规", "违法"], "risk", "violation", -1),
    (["诉讼", "仲裁", "起诉"], "risk", "lawsuit", -1),
    (["评级下调"], "risk", "rating_down", -1),
    (["处罚", "罚款"], "risk", "penalty", -1),
    (["退市"], "risk", "delisting", -1),
    # 政策
    (["补贴", "补助"], "policy", "subsidy", 1),
    (["监管", "整顿"], "policy", "regulation", -1),
    (["产业规划", "发展规划"], "policy", "industry_plan", 1),
    # 产品
    (["中标", "签订合同", "重大合同"], "product", "contract", 1),
    (["专利"], "product", "patent", 1),
    (["发布", "上市", "量产"], "product", "launch", 1),
]


@dataclass
class DetectedEvent:
    event_type: str
    event_subtype: str
    impact: int
    keywords: list[str]


def detect_events(text: str) -> list[DetectedEvent]:
    """关键词模板匹配事件检测"""
    events = []
    seen_types: set[str] = set()

    for keywords, event_type, event_subtype, impact in EVENT_TEMPLATES:
        if event_subtype in seen_types:
            continue

        hit = [kw for kw in keywords if kw in text]
        if hit:
            seen_types.add(event_subtype)
            events.append(DetectedEvent(
                event_type=event_type,
                event_subtype=event_subtype,
                impact=impact,
                keywords=hit,
            ))

    return events
