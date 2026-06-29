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
