from dataclasses import dataclass

import structlog

logger = structlog.get_logger()

# 利好关键词
POSITIVE_KEYWORDS = {
    "预增", "增长", "超预期", "利好", "涨停", "大涨", "突破", "新高", "增持", "回购",
    "中标", "合同", "订单", "分红", "送转", "扭亏", "扩产", "投产", "获批", "专利",
    "合作", "战略", "升级", "创新", "龙头", "景气", "需求旺盛", "供不应求",
}

# 利空关键词
NEGATIVE_KEYWORDS = {
    "预减", "下降", "亏损", "利空", "跌停", "大跌", "暴跌", "减持", "违规", "处罚",
    "退市", "风险", "诉讼", "仲裁", "立案", "调查", "下调", "评级下调", "取消",
    "终止", "暂停", "延期", "爆雷", "跑路", "造假", "ST", "暂停上市",
}


@dataclass
class SentimentResult:
    label: int  # -1利空, 0中性, 1利好
    score: float  # 置信度 0~1
    keywords: list[str]  # 触发关键词
    method: str = "rule"


def analyze_sentiment(text: str) -> SentimentResult:
    """规则层情感分析：关键词匹配"""
    hit_positive = [kw for kw in POSITIVE_KEYWORDS if kw in text]
    hit_negative = [kw for kw in NEGATIVE_KEYWORDS if kw in text]

    pos_score = len(hit_positive)
    neg_score = len(hit_negative)

    if pos_score == 0 and neg_score == 0:
        return SentimentResult(label=0, score=0.3, keywords=[], method="rule")

    if pos_score > neg_score:
        confidence = min(0.5 + pos_score * 0.15, 1.0)
        return SentimentResult(label=1, score=confidence, keywords=hit_positive, method="rule")

    if neg_score > pos_score:
        confidence = min(0.5 + neg_score * 0.15, 1.0)
        return SentimentResult(label=-1, score=confidence, keywords=hit_negative, method="rule")

    # 正负相等，看强度
    return SentimentResult(label=0, score=0.5, keywords=hit_positive + hit_negative, method="rule")
