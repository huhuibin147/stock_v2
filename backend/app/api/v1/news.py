from fastapi import APIRouter, Query

from app.core.response import ok, fail
from app.services import news_service

router = APIRouter(prefix="/api/v1/news", tags=["news"])


@router.get("")
async def list_news(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    source: str = Query(""),
    sentiment: int | None = Query(None),
):
    data = await news_service.list_news(page, page_size, source, sentiment)
    return ok(data)


@router.get("/hot")
async def hot(limit: int = Query(20, ge=1, le=100)):
    data = await news_service.get_hot_news(limit)
    return ok(data)


@router.get("/{news_id}")
async def detail(news_id: int):
    data = await news_service.get_news_detail(news_id)
    if not data:
        return fail(40401, "资讯不存在")
    return ok(data)
