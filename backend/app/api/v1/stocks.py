from fastapi import APIRouter, Query

from app.core.response import ok, fail, paginated
from app.services import stock_service

router = APIRouter(prefix="/api/v1/stocks", tags=["stocks"])


@router.get("/search")
async def search(q: str = Query(..., min_length=1), limit: int = Query(10, ge=1, le=50)):
    results = await stock_service.search_stocks(q, limit)
    return ok(results)


@router.get("/{code}/profile")
async def profile(code: str):
    data = await stock_service.get_stock_profile(code)
    if not data:
        return fail(40401, f"股票 {code} 不存在")
    return ok(data)


@router.get("/{code}/news")
async def news(
    code: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(10, ge=1, le=100),
    sentiment: int | None = Query(None),
):
    data = await stock_service.get_stock_news(code, page, page_size, sentiment)
    return ok(data)


@router.get("/{code}/events")
async def events(code: str, limit: int = Query(20, ge=1, le=100)):
    data = await stock_service.get_stock_events(code, limit)
    return ok(data)
