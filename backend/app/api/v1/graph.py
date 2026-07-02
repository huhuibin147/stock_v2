from fastapi import APIRouter, Query

from app.core.response import ok
from app.services import chain_service

router = APIRouter(prefix="/api/v1/graph", tags=["graph"])


@router.get("/industry-chain")
async def industry_chain(
    layer: int | None = Query(None, ge=1, le=5),
    stock_code: str | None = Query(None),
):
    data = await chain_service.get_industry_chain(layer=layer, stock_code=stock_code)
    return ok(data)


@router.get("/chain/{chain_id}/stocks")
async def chain_stocks(chain_id: int):
    """获取产业链下的公司列表"""
    data = await chain_service.get_chain_stocks(chain_id)
    return ok(data)
