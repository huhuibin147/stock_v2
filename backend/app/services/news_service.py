import json
import structlog

from app.core.database import get_db

logger = structlog.get_logger()


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
            """SELECT id, title, summary, key_points, sentiment, sentiment_score,
                      published_at, source, url, entities, events, tags
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

        return {
            "id": row[0],
            "title": row[1],
            "summary": row[2],
            "key_points": parse_json(row[3]),
            "sentiment": row[4],
            "sentiment_score": row[5],
            "published_at": row[6],
            "source": row[7],
            "url": row[8],
            "entities": parse_json(row[9]),
            "events": parse_json(row[10]),
            "tags": parse_json(row[11]),
        }
    finally:
        await db.close()


async def save_news(news_data: dict, stock_codes: list[str] | None = None) -> int:
    """保存一条资讯到数据库，返回news_id"""
    db = await get_db()
    try:
        cursor = await db.execute(
            """INSERT OR IGNORE INTO news
               (source, source_id, title, summary, key_points, url, published_at,
                category, importance_score, sentiment, sentiment_score,
                entities, events, tags, retention)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                news_data.get("source"),
                news_data.get("source_id"),
                news_data.get("title", ""),
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
        if news_id == 0:
            # INSERT OR IGNORE 冲突，返回已有记录的id
            cursor2 = await db.execute(
                "SELECT id FROM news WHERE source = ? AND source_id = ?",
                (news_data.get("source"), news_data.get("source_id")),
            )
            row = await cursor2.fetchone()
            return row[0] if row else 0

        # 关联股票
        if stock_codes:
            for code in stock_codes:
                await db.execute(
                    "INSERT OR IGNORE INTO news_stocks (news_id, stock_code, mention_type) VALUES (?, ?, ?)",
                    (news_id, code, "direct"),
                )
            await db.commit()

        return news_id
    finally:
        await db.close()
