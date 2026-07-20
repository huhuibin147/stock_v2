#!/usr/bin/env python3
"""执行清理"""
import asyncio
import sys
sys.path.insert(0, '/opt/stock_v2/backend')

from app.core.database import get_db, DB_PATH

async def cleanup():
    print(f'数据库路径: {DB_PATH}')
    db = await get_db()
    try:
        cursor = await db.execute("SELECT COUNT(*) FROM news WHERE retention = 'normal' AND created_at < datetime('now', '-14 days')")
        count = (await cursor.fetchone())[0]
        print(f'符合条件的资讯: {count} 条')

        cursor = await db.execute("DELETE FROM news_stocks WHERE news_id NOT IN (SELECT id FROM news)")
        orphan1 = cursor.rowcount

        cursor = await db.execute("DELETE FROM news WHERE retention = 'normal' AND created_at < datetime('now', '-14 days')")
        deleted = cursor.rowcount

        cursor = await db.execute("DELETE FROM news_stocks WHERE news_id NOT IN (SELECT id FROM news)")
        orphan2 = cursor.rowcount

        await db.commit()
        print(f'已删除: {deleted} 条资讯, {orphan1 + orphan2} 条关联')

        cursor = await db.execute("SELECT COUNT(*) FROM news")
        remaining = (await cursor.fetchone())[0]
        print(f'剩余资讯: {remaining} 条')
    finally:
        await db.close()

asyncio.run(cleanup())
