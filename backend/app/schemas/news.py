from pydantic import BaseModel


class NewsItem(BaseModel):
    id: int
    title: str
    summary: str
    sentiment: int | None = None
    published_at: str | None = None
    source: str | None = None
    url: str | None = None
