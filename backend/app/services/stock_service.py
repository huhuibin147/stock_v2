import json
import structlog

from app.core.database import get_db

logger = structlog.get_logger()


async def list_stocks(page: int = 1, page_size: int = 20, industry: str = "", q: str = "") -> dict:
    """分页查询股票列表"""
    db = await get_db()
    try:
        where = ["s.is_active = 1"]
        params = []
        if industry:
            where.append("s.industry = ?")
            params.append(industry)
        if q:
            where.append("(s.code LIKE ? OR s.name LIKE ?)")
            params.extend([f"%{q}%", f"%{q}%"])

        where_sql = " AND ".join(where)

        # 总数
        cursor = await db.execute(f"SELECT COUNT(*) FROM stocks s WHERE {where_sql}", params)
        total = (await cursor.fetchone())[0]

        # 分页数据
        offset = (page - 1) * page_size
        cursor = await db.execute(
            f"""SELECT s.code, s.name, s.market, s.industry, s.concepts, s.core_business,
                       s.pe_ttm, s.pb, s.market_cap
                FROM stocks s
                WHERE {where_sql}
                ORDER BY s.market_cap DESC NULLS LAST, s.code
                LIMIT ? OFFSET ?""",
            params + [page_size, offset],
        )
        rows = await cursor.fetchall()
        items = []
        for r in rows:
            concepts = r[4]
            if isinstance(concepts, str):
                try:
                    concepts = json.loads(concepts)
                except (json.JSONDecodeError, TypeError):
                    concepts = []
            items.append({
                "code": r[0],
                "name": r[1],
                "market": r[2],
                "industry": r[3],
                "concepts": concepts or [],
                "core_business": r[5],
                "pe_ttm": r[6],
                "pb": r[7],
                "market_cap": r[8],
            })

        return {"items": items, "total": total, "page": page, "page_size": page_size}
    finally:
        await db.close()


async def search_stocks(query: str, limit: int = 10) -> list[dict]:
    """搜索股票（代码或名称模糊匹配）"""
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT code, name, market, industry, concepts, core_business
               FROM stocks
               WHERE is_active = 1
                 AND (code LIKE ? OR name LIKE ?)
               ORDER BY
                 CASE WHEN code = ? THEN 0 WHEN name = ? THEN 1 ELSE 2 END,
                 code
               LIMIT ?""",
            (f"%{query}%", f"%{query}%", query, query, limit),
        )
        rows = await cursor.fetchall()
        return [_row_to_stock(r) for r in rows]
    finally:
        await db.close()


async def get_stock_by_code(code: str) -> dict | None:
    """获取股票基本信息"""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT code, name, market, industry, concepts, core_business, chain_id, pe_ttm, pb, market_cap, dividend_yield FROM stocks WHERE code = ?",
            (code,),
        )
        row = await cursor.fetchone()
        if not row:
            return None
        return _row_to_stock(row)
    finally:
        await db.close()


async def get_stock_profile(code: str) -> dict | None:
    """获取个股全景数据"""
    stock = await get_stock_by_code(code)
    if not stock:
        return None

    db = await get_db()
    try:
        # 产业链信息
        chain = await _get_chain_info(db, stock.get("chain_id"))

        # 公司详细信息
        company = await _get_company_profile(db, code)

        # 最近重要资讯
        recent_news = await _get_recent_news(db, code, limit=5)

        # 最近事件
        recent_events = await _get_recent_events(db, code, limit=5)

        # 近7天情感分布
        sentiment_7d = await _get_sentiment_summary(db, code, days=7)

        return {
            "stock": stock,
            "chain": chain,
            "company": company,
            "recent_news": recent_news,
            "recent_events": recent_events,
            "sentiment_7d": sentiment_7d,
        }
    finally:
        await db.close()


async def get_stock_news(code: str, page: int = 1, page_size: int = 10, sentiment: int | None = None) -> dict:
    """获取个股资讯列表"""
    db = await get_db()
    try:
        offset = (page - 1) * page_size
        where = "WHERE ns.stock_code = ?"
        params: list = [code]

        if sentiment is not None:
            where += " AND n.sentiment = ?"
            params.append(sentiment)

        # 总数
        cursor = await db.execute(
            f"SELECT COUNT(*) FROM news_stocks ns JOIN news n ON ns.news_id = n.id {where}", params
        )
        total = (await cursor.fetchone())[0]

        # 列表
        cursor = await db.execute(
            f"""SELECT n.id, n.title, n.summary, n.sentiment, n.published_at, n.source, n.url
                FROM news_stocks ns JOIN news n ON ns.news_id = n.id
                {where}
                ORDER BY n.importance_score DESC NULLS LAST, n.published_at DESC
                LIMIT ? OFFSET ?""",
            params + [page_size, offset],
        )
        rows = await cursor.fetchall()

        items = [
            {
                "id": r[0],
                "title": r[1],
                "summary": r[2],
                "sentiment": r[3],
                "published_at": r[4],
                "source": r[5],
                "url": r[6],
            }
            for r in rows
        ]

        return {"items": items, "total": total, "page": page, "page_size": page_size}
    finally:
        await db.close()


async def get_stock_events(code: str, limit: int = 20) -> list[dict]:
    """获取个股事件时间线"""
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT event_type, event_subtype, title, description, impact, impact_level, event_date
               FROM events
               WHERE stock_codes LIKE ?
               ORDER BY event_date DESC
               LIMIT ?""",
            (f'%"{code}"%', limit),
        )
        rows = await cursor.fetchall()
        return [
            {
                "event_type": r[0],
                "event_subtype": r[1],
                "title": r[2],
                "description": r[3],
                "impact": r[4],
                "impact_level": r[5],
                "event_date": r[6],
            }
            for r in rows
        ]
    finally:
        await db.close()


async def get_stock_financials(code: str, limit: int = 8) -> list[dict]:
    """获取股票季度财务数据"""
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT report_date, net_profit, net_profit_yoy, revenue, revenue_yoy,
                      eps, bps, roe, net_margin, equity_ratio, ocf_ps
               FROM stock_financials
               WHERE code = ?
               ORDER BY report_date DESC
               LIMIT ?""",
            (code, limit),
        )
        rows = await cursor.fetchall()
        return [
            {
                "report_date": r[0],
                "net_profit": r[1],
                "net_profit_yoy": r[2],
                "revenue": r[3],
                "revenue_yoy": r[4],
                "eps": r[5],
                "bps": r[6],
                "roe": r[7],
                "net_margin": r[8],
                "equity_ratio": r[9],
                "ocf_ps": r[10],
            }
            for r in rows
        ]
    finally:
        await db.close()


# ── 内部辅助 ──


def _row_to_stock(row) -> dict:
    concepts = row[4]
    if isinstance(concepts, str):
        try:
            concepts = json.loads(concepts)
        except (json.JSONDecodeError, TypeError):
            concepts = []
    return {
        "code": row[0],
        "name": row[1],
        "market": row[2],
        "industry": row[3],
        "concepts": concepts or [],
        "core_business": row[5] if len(row) > 5 else None,
        "chain_id": row[6] if len(row) > 6 else None,
        "pe_ttm": row[7] if len(row) > 7 else None,
        "pb": row[8] if len(row) > 8 else None,
        "market_cap": row[9] if len(row) > 9 else None,
        "dividend_yield": row[10] if len(row) > 10 else None,
    }


LAYER_NAMES = {1: "能源电力", 2: "芯片硬件", 3: "基础设施", 4: "AI基础", 5: "AI应用"}


async def _get_company_profile(db, code: str) -> dict | None:
    """获取公司详细信息"""
    cursor = await db.execute(
        """SELECT company_name, english_name, legal_rep, reg_capital,
                  found_date, list_date, website, email, phone,
                  reg_address, office_address, business_scope, introduction
           FROM stock_profiles WHERE code = ?""",
        (code,),
    )
    row = await cursor.fetchone()
    if not row:
        return None
    return {
        "company_name": row[0],
        "english_name": row[1],
        "legal_rep": row[2],
        "reg_capital": row[3],
        "found_date": row[4],
        "list_date": row[5],
        "website": row[6],
        "email": row[7],
        "phone": row[8],
        "reg_address": row[9],
        "office_address": row[10],
        "business_scope": row[11],
        "introduction": row[12],
    }


async def _get_chain_info(db, chain_id: int | None) -> dict:
    if not chain_id:
        return {"layer": None, "layer_name": None, "position": None, "upstream": [], "downstream": []}

    cursor = await db.execute("SELECT name, layer, upstream_ids, downstream_ids FROM industry_chains WHERE id = ?", (chain_id,))
    row = await cursor.fetchone()
    if not row:
        return {"layer": None, "layer_name": None, "position": None, "upstream": [], "downstream": []}

    upstream_ids = json.loads(row[2]) if row[2] else []
    downstream_ids = json.loads(row[3]) if row[3] else []

    upstream = await _get_chain_peers(db, upstream_ids)
    downstream = await _get_chain_peers(db, downstream_ids)

    return {
        "layer": row[1],
        "layer_name": LAYER_NAMES.get(row[1], ""),
        "position": row[0],
        "upstream": upstream,
        "downstream": downstream,
    }


async def _get_chain_peers(db, chain_ids: list[int]) -> list[dict]:
    if not chain_ids:
        return []
    placeholders = ",".join("?" * len(chain_ids))
    cursor = await db.execute(
        f"SELECT code, name, core_business FROM stocks WHERE chain_id IN ({placeholders}) LIMIT 5",
        chain_ids,
    )
    rows = await cursor.fetchall()
    return [{"code": r[0], "name": r[1], "relation": r[2] or ""} for r in rows]


async def _get_recent_news(db, code: str, limit: int = 5) -> list[dict]:
    cursor = await db.execute(
        """SELECT n.id, n.title, n.summary, n.sentiment, n.published_at
           FROM news_stocks ns JOIN news n ON ns.news_id = n.id
           WHERE ns.stock_code = ?
           ORDER BY n.importance_score DESC NULLS LAST, n.published_at DESC
           LIMIT ?""",
        (code, limit),
    )
    rows = await cursor.fetchall()
    return [{"id": r[0], "title": r[1], "summary": r[2], "sentiment": r[3], "published_at": r[4]} for r in rows]


async def _get_recent_events(db, code: str, limit: int = 5) -> list[dict]:
    cursor = await db.execute(
        """SELECT event_type, title, impact, event_date
           FROM events WHERE stock_codes LIKE ?
           ORDER BY event_date DESC LIMIT ?""",
        (f'%"{code}"%', limit),
    )
    rows = await cursor.fetchall()
    return [{"event_type": r[0], "title": r[1], "impact": r[2], "event_date": r[3]} for r in rows]


async def _get_sentiment_summary(db, code: str, days: int = 7) -> dict:
    cursor = await db.execute(
        """SELECT n.sentiment, COUNT(*)
           FROM news_stocks ns JOIN news n ON ns.news_id = n.id
           WHERE ns.stock_code = ?
             AND n.published_at >= datetime('now', ?)
           GROUP BY n.sentiment""",
        (code, f"-{days} days"),
    )
    rows = await cursor.fetchall()
    result = {"positive": 0, "neutral": 0, "negative": 0}
    for r in rows:
        if r[0] == 1:
            result["positive"] = r[1]
        elif r[0] == -1:
            result["negative"] = r[1]
        else:
            result["neutral"] = r[1]

    total = result["positive"] + result["neutral"] + result["negative"]
    if total == 0:
        result["trend"] = "暂无数据"
    elif result["positive"] > result["negative"] * 2:
        result["trend"] = "偏多"
    elif result["negative"] > result["positive"] * 2:
        result["trend"] = "偏空"
    else:
        result["trend"] = "震荡"

    return result
