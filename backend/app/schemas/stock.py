from pydantic import BaseModel


class StockInfo(BaseModel):
    code: str
    name: str
    market: str
    industry: str | None = None
    concepts: list[str] = []
    core_business: str | None = None


class ChainPosition(BaseModel):
    layer: int | None = None
    layer_name: str | None = None
    position: str | None = None
    upstream: list[dict] = []
    downstream: list[dict] = []


class SentimentSummary(BaseModel):
    positive: int = 0
    neutral: int = 0
    negative: int = 0
    trend: str = "中性"


class StockProfile(BaseModel):
    stock: StockInfo
    chain: ChainPosition
    recent_news: list[dict] = []
    sentiment_7d: SentimentSummary
