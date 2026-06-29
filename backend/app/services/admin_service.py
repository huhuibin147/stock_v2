import json
import structlog

from app.core.database import get_db

logger = structlog.get_logger()


async def log_action(action: str, detail: str = "", status: str = "success"):
    """记录操作日志"""
    db = await get_db()
    try:
        await db.execute(
            "INSERT INTO admin_logs (action, detail, status) VALUES (?, ?, ?)",
            (action, detail, status),
        )
        await db.commit()
    finally:
        await db.close()


async def get_logs(limit: int = 50) -> list[dict]:
    """获取最近操作日志"""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT id, action, detail, status, created_at FROM admin_logs ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        rows = await cursor.fetchall()
        return [
            {"id": r[0], "action": r[1], "detail": r[2], "status": r[3], "created_at": r[4]}
            for r in rows
        ]
    finally:
        await db.close()


async def get_system_status() -> dict:
    """获取系统状态"""
    db = await get_db()
    try:
        stats = {}
        for table in ["stocks", "news", "events", "concepts", "industry_chains", "news_stocks"]:
            cursor = await db.execute(f"SELECT COUNT(*) FROM {table}")
            stats[table] = (await cursor.fetchone())[0]

        # DB文件大小
        import os
        from app.core.config import settings
        db_path = settings.database_url.replace("sqlite+aiosqlite:///", "")
        db_size = os.path.getsize(db_path) if os.path.exists(db_path) else 0

        return {
            "tables": stats,
            "db_size": db_size,
            "db_size_human": _format_size(db_size),
        }
    finally:
        await db.close()


async def get_stocks_page(page: int = 1, page_size: int = 20, q: str = "") -> dict:
    """管理视图：股票列表分页"""
    db = await get_db()
    try:
        offset = (page - 1) * page_size
        where = ""
        params: list = []

        if q:
            where = "WHERE code LIKE ? OR name LIKE ?"
            params = [f"%{q}%", f"%{q}%"]

        cursor = await db.execute(f"SELECT COUNT(*) FROM stocks {where}", params)
        total = (await cursor.fetchone())[0]

        cursor = await db.execute(
            f"""SELECT code, name, market, industry, concepts, core_business, chain_id, is_active
                FROM stocks {where}
                ORDER BY code
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
                "code": r[0], "name": r[1], "market": r[2], "industry": r[3],
                "concepts": concepts or [], "core_business": r[5],
                "chain_id": r[6], "is_active": r[7],
            })

        return {"items": items, "total": total, "page": page, "page_size": page_size}
    finally:
        await db.close()


async def get_news_page(page: int = 1, page_size: int = 20) -> dict:
    """管理视图：资讯列表分页"""
    db = await get_db()
    try:
        offset = (page - 1) * page_size

        cursor = await db.execute("SELECT COUNT(*) FROM news")
        total = (await cursor.fetchone())[0]

        cursor = await db.execute(
            """SELECT id, source, source_id, title, summary, sentiment,
                      importance_score, published_at, category, entities, events
               FROM news
               ORDER BY id DESC
               LIMIT ? OFFSET ?""",
            (page_size, offset),
        )
        rows = await cursor.fetchall()

        items = []
        for r in rows:
            entities = r[9]
            events = r[10]
            for field_val, field_name in [(entities, "entities"), (events, "events")]:
                if isinstance(field_val, str):
                    try:
                        locals()[field_name] = json.loads(field_val)
                    except (json.JSONDecodeError, TypeError):
                        pass
            items.append({
                "id": r[0], "source": r[1], "source_id": r[2], "title": r[3],
                "summary": r[4], "sentiment": r[5], "importance_score": r[6],
                "published_at": r[7], "category": r[8],
            })

        return {"items": items, "total": total, "page": page, "page_size": page_size}
    finally:
        await db.close()


async def get_concepts_page(page: int = 1, page_size: int = 50) -> dict:
    """管理视图：概念列表分页"""
    db = await get_db()
    try:
        offset = (page - 1) * page_size

        cursor = await db.execute("SELECT COUNT(*) FROM concepts")
        total = (await cursor.fetchone())[0]

        cursor = await db.execute(
            """SELECT id, name, category, stock_count, hot_score
               FROM concepts
               ORDER BY stock_count DESC
               LIMIT ? OFFSET ?""",
            (page_size, offset),
        )
        rows = await cursor.fetchall()

        items = [
            {"id": r[0], "name": r[1], "category": r[2], "stock_count": r[3], "hot_score": r[4]}
            for r in rows
        ]

        return {"items": items, "total": total, "page": page, "page_size": page_size}
    finally:
        await db.close()


def _format_size(size: int) -> str:
    for unit in ["B", "KB", "MB", "GB"]:
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"
