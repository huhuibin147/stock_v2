#!/usr/bin/env python3
"""检查清理效果"""
import asyncio
import sys
sys.path.insert(0, '/opt/stock_v2/backend')

from app.core.database import get_db, DB_PATH

async def check():
    print(f'数据库路径: {DB_PATH}')
    db = await get_db()
    try:
        cursor = await db.execute("SELECT COUNT(*) FROM news WHERE retention = 'normal' AND created_at < datetime('now', '-14 days')")
        count = (await cursor.fetchone())[0]
        print(f'超过14天的资讯: {count} 条')

        cursor = await db.execute("SELECT COUNT(*) FROM news")
        total = (await cursor.fetchone())[0]
        print(f'总资讯数: {total} 条')
        print(f'清理后剩余: {total - count} 条')

        cursor = await db.execute("SELECT MIN(created_at), MAX(created_at) FROM news")
        row = await cursor.fetchone()
        print(f'最早: {row[0]}')
        print(f'最新: {row[1]}')
    finally:
        await db.close()

asyncio.run(check())
