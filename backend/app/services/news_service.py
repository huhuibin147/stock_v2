import json
import structlog

from app.core.database import get_db

logger = structlog.get_logger()


async def list_news(
    page: int = 1,
    page_size: int = 20,
    source: str = "",
    sentiment: int | None = None,
    category: str = "",
    stock_code: str = "",
    sort: str = "time_desc",
) -> dict:
    """分页查询资讯列表"""
    db = await get_db()
    try:
        where = ["1=1"]
        params = []
        join = ""

        if source:
            where.append("n.source = ?")
            params.append(source)
        if sentiment is not None:
            where.append("n.sentiment = ?")
            params.append(sentiment)
        if category:
            where.append("n.category = ?")
            params.append(category)
        if stock_code:
            join = "JOIN news_stocks ns ON n.id = ns.news_id"
            where.append("ns.stock_code = ?")
            params.append(stock_code)

        where_sql = " AND ".join(where)

        # 排序
        order_sql = "n.published_at DESC"
        if sort == "time_asc":
            order_sql = "n.published_at ASC"
        elif sort == "importance":
            order_sql = "n.importance_score DESC NULLS LAST, n.published_at DESC"

        cursor = await db.execute(f"SELECT COUNT(*) FROM news n {join} WHERE {where_sql}", params)
        total = (await cursor.fetchone())[0]

        offset = (page - 1) * page_size
        cursor = await db.execute(
            f"""SELECT DISTINCT n.id, n.title, n.summary, n.sentiment, n.published_at, n.source, n.category
                FROM news n {join}
                WHERE {where_sql}
                ORDER BY {order_sql}
                LIMIT ? OFFSET ?""",
            params + [page_size, offset],
        )
        rows = await cursor.fetchall()

        # 获取每条资讯关联的股票（代码+名称）
        items = []
        for r in rows:
            news_id = r[0]
            stock_cursor = await db.execute(
                """SELECT ns.stock_code, s.name
                   FROM news_stocks ns
                   LEFT JOIN stocks s ON ns.stock_code = s.code
                   WHERE ns.news_id = ?
                   LIMIT 5""",
                (news_id,),
            )
            stock_rows = await stock_cursor.fetchall()
            stocks = [{"code": s[0], "name": s[1]} for s in stock_rows]

            items.append({
                "id": r[0], "title": r[1], "summary": r[2],
                "sentiment": r[3], "published_at": r[4], "source": r[5], "category": r[6],
                "stocks": stocks,
            })

        return {"items": items, "total": total, "page": page, "page_size": page_size}
    finally:
        await db.close()


async def get_hot_news(limit: int = 20) -> list[dict]:
    """获取今日热点资讯"""
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT id, title, summary, sentiment, published_at, source, url
               FROM news
               WHERE collected_at >= datetime('now', '-1 day')
               ORDER BY importance_score DESC NULLS LAST, published_at DESC
               LIMIT ?""",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [
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
    finally:
        await db.close()


async def get_news_detail(news_id: int) -> dict | None:
    """获取资讯详情"""
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT id, title, content, summary, key_points, sentiment, sentiment_score,
                      published_at, source, url, entities, events, tags,
                      category, importance_score
               FROM news WHERE id = ?""",
            (news_id,),
        )
        row = await cursor.fetchone()
        if not row:
            return None

        def parse_json(val):
            if isinstance(val, str):
                try:
                    return json.loads(val)
                except (json.JSONDecodeError, TypeError):
                    return None
            return val

        # 查询关联股票
        cursor2 = await db.execute(
            """SELECT ns.stock_code, s.name
               FROM news_stocks ns
               LEFT JOIN stocks s ON s.code = ns.stock_code
               WHERE ns.news_id = ?""",
            (news_id,),
        )
        stocks = [{"code": r[0], "name": r[1]} for r in await cursor2.fetchall()]

        return {
            "id": row[0],
            "title": row[1],
            "content": row[2],
            "summary": row[3],
            "key_points": parse_json(row[4]),
            "sentiment": row[5],
            "sentiment_score": row[6],
            "published_at": row[7],
            "source": row[8],
            "url": row[9],
            "entities": parse_json(row[10]),
            "events": parse_json(row[11]),
            "tags": parse_json(row[12]),
            "category": row[13],
            "importance_score": row[14],
            "stocks": stocks,
        }
    finally:
        await db.close()


async def save_news(news_data: dict, stock_codes: list[str] | None = None) -> int:
    """保存一条资讯到数据库，返回news_id。同源同标题去重。"""
    db = await get_db()
    try:
        source = news_data.get("source")
        source_id = news_data.get("source_id")
        title = news_data.get("title", "")

        # 同源同标题去重：先检查是否已存在
        cursor = await db.execute(
            "SELECT id FROM news WHERE source = ? AND title = ?",
            (source, title),
        )
        existing = await cursor.fetchone()
        if existing:
            return existing[0]

        # source_id 去重（兜底）
        if source_id:
            cursor = await db.execute(
                "SELECT id FROM news WHERE source = ? AND source_id = ?",
                (source, source_id),
            )
            existing = await cursor.fetchone()
            if existing:
                return existing[0]

        cursor = await db.execute(
            """INSERT INTO news
               (source, source_id, title, content, summary, key_points, url, published_at,
                category, importance_score, sentiment, sentiment_score,
                entities, events, tags, retention)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                source,
                source_id,
                title,
                news_data.get("content", ""),
                news_data.get("summary", ""),
                json.dumps(news_data.get("key_points"), ensure_ascii=False) if news_data.get("key_points") else None,
                news_data.get("url"),
                news_data.get("published_at"),
                news_data.get("category"),
                news_data.get("importance_score"),
                news_data.get("sentiment"),
                news_data.get("sentiment_score"),
                json.dumps(news_data.get("entities"), ensure_ascii=False) if news_data.get("entities") else None,
                json.dumps(news_data.get("events"), ensure_ascii=False) if news_data.get("events") else None,
                json.dumps(news_data.get("tags"), ensure_ascii=False) if news_data.get("tags") else None,
                news_data.get("retention", "normal"),
            ),
        )
        await db.commit()

        news_id = cursor.lastrowid

        # 关联股票
        if stock_codes and news_id:
            for code in stock_codes:
                await db.execute(
                    "INSERT OR IGNORE INTO news_stocks (news_id, stock_code, mention_type) VALUES (?, ?, ?)",
                    (news_id, code, "direct"),
                )
            await db.commit()

        return news_id
    finally:
        await db.close()
