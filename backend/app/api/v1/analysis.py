from fastapi import APIRouter, Query

from app.core.response import ok
from app.core.database import get_db

router = APIRouter(prefix="/api/v1/analysis", tags=["analysis"])


@router.get("/overview")
async def overview():
    """首页概览：统计信息 + 热门股票 + 热门概念 + 最新资讯"""
    db = await get_db()
    try:
        stats = await _get_stats(db)
        hot_stocks = await _get_hot_stocks(db)
        hot_concepts = await _get_hot_concepts(db)
        recent_news = await _get_recent_news(db)
        layers = await _get_layer_summary(db)

        return ok({
            "stats": stats,
            "hot_stocks": hot_stocks,
            "hot_concepts": hot_concepts,
            "recent_news": recent_news,
            "layers": layers,
        })
    finally:
        await db.close()


async def _get_stats(db) -> dict:
    cursor = await db.execute("SELECT COUNT(*) FROM stocks WHERE is_active = 1")
    stock_count = (await cursor.fetchone())[0]

    cursor = await db.execute("SELECT COUNT(*) FROM news")
    news_count = (await cursor.fetchone())[0]

    cursor = await db.execute("SELECT COUNT(*) FROM concepts")
    concept_count = (await cursor.fetchone())[0]

    cursor = await db.execute("SELECT COUNT(*) FROM industry_chains")
    chain_count = (await cursor.fetchone())[0]

    # 供应链统计
    cursor = await db.execute("SELECT COUNT(*) FROM supply_chain_research")
    supply_chain_count = (await cursor.fetchone())[0]

    cursor = await db.execute("SELECT COUNT(*) FROM supply_chain_relations")
    supply_chain_relations = (await cursor.fetchone())[0]

    return {
        "stocks": stock_count,
        "news": news_count,
        "concepts": concept_count,
        "chains": chain_count,
        "supply_chain": supply_chain_count,
        "supply_chain_relations": supply_chain_relations,
    }


async def _get_hot_stocks(db, limit: int = 12) -> list[dict]:
    """按成交额排序的热门股票"""
    cursor = await db.execute(
        """SELECT s.code, s.name, s.market, s.industry, s.turnover_amount
           FROM stocks s
           WHERE s.is_active = 1 AND s.turnover_amount > 0
           ORDER BY s.turnover_amount DESC
           LIMIT ?""",
        (limit,),
    )
    rows = await cursor.fetchall()
    return [
        {"code": r[0], "name": r[1], "market": r[2], "industry": r[3], "turnover_amount": r[4]}
        for r in rows
    ]


async def _get_hot_concepts(db, limit: int = 30) -> list[dict]:
    """热门概念板块"""
    cursor = await db.execute(
        """SELECT name, stock_count, hot_score
           FROM concepts
           ORDER BY stock_count DESC, hot_score DESC
           LIMIT ?""",
        (limit,),
    )
    rows = await cursor.fetchall()
    return [{"name": r[0], "stock_count": r[1], "hot_score": r[2]} for r in rows]


async def _get_recent_news(db, limit: int = 10) -> list[dict]:
    """最新重要资讯"""
    cursor = await db.execute(
        """SELECT id, title, summary, sentiment, published_at, source
           FROM news
           ORDER BY importance_score DESC NULLS LAST, published_at DESC
           LIMIT ?""",
        (limit,),
    )
    rows = await cursor.fetchall()
    return [
        {"id": r[0], "title": r[1], "summary": r[2], "sentiment": r[3], "published_at": r[4], "source": r[5]}
        for r in rows
    ]


async def _get_layer_summary(db) -> list[dict]:
    """各产业链层级概要"""
    cursor = await db.execute(
        """SELECT layer, COUNT(*) as chain_count
           FROM industry_chains
           GROUP BY layer
           ORDER BY layer"""
    )
    rows = await cursor.fetchall()

    layer_names = {1: "能源电力", 2: "芯片硬件", 3: "基础设施", 4: "AI基础", 5: "AI应用"}
    result = []
    for r in rows:
        # 每层关联的股票数
        cursor2 = await db.execute(
            """SELECT COUNT(*) FROM stocks s
               JOIN industry_chains ic ON s.chain_id = ic.id
               WHERE ic.layer = ?""",
            (r[0],),
        )
        stock_count = (await cursor2.fetchone())[0]

        result.append({
            "layer": r[0],
            "name": layer_names.get(r[0], f"Layer {r[0]}"),
            "chain_count": r[1],
            "stock_count": stock_count,
        })

    return result
