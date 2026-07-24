"""量化策略推荐API"""

from fastapi import APIRouter, Query
from app.core.response import ok
from app.strategies.manager import strategy_manager

router = APIRouter(prefix="/api/v1/quant", tags=["quant"])


@router.get("/strategies")
async def list_strategies():
    """获取策略列表"""
    strategies = strategy_manager.list_strategies()
    return ok(strategies)


@router.get("/recommend")
async def recommend(
    limit: int = Query(20, ge=1, le=50),
):
    """获取所有策略推荐"""
    results = await strategy_manager.run_all(limit)

    # 转换为可序列化的格式
    data = {}
    for name, signals in results.items():
        data[name] = [
            {
                "code": s.code,
                "name": s.name,
                "reason": s.reason,
                "score": s.score,
                "indicators": s.indicators,
            }
            for s in signals
        ]

    return ok(data)


@router.get("/recommend/{strategy}")
async def recommend_by_strategy(
    strategy: str,
    limit: int = Query(20, ge=1, le=50),
):
    """获取单策略推荐"""
    signals = await strategy_manager.run_strategy(strategy, limit)

    data = [
        {
            "code": s.code,
            "name": s.name,
            "reason": s.reason,
            "score": s.score,
            "indicators": s.indicators,
        }
        for s in signals
    ]

    return ok(data)
