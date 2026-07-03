"""导入同花顺概念板块和成分股数据"""

import asyncio
import time
from datetime import datetime

import structlog
import requests
from bs4 import BeautifulSoup

from app.core.database import get_db

logger = structlog.get_logger()


def fetch_ths_concept_list() -> list[dict]:
    """获取同花顺概念板块列表"""
    try:
        import akshare as ak
        df = ak.stock_board_concept_name_ths()
        if df is None or df.empty:
            return []

        concepts = []
        for _, row in df.iterrows():
            name = str(row.get("name", "")).strip()
            code = str(row.get("code", "")).strip()
            if name and code:
                concepts.append({"name": name, "code": code})

        return concepts
    except Exception as e:
        logger.error("fetch_ths_concept_list_failed", error=str(e))
        return []


def fetch_ths_concept_stocks(concept_code: str) -> list[str]:
    """获取同花顺概念板块的成分股代码列表"""
    url = f'https://q.10jqka.com.cn/gn/detail/code/{concept_code}/'
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
        'Referer': 'https://q.10jqka.com.cn/',
    }

    try:
        response = requests.get(url, headers=headers, timeout=15)
        if response.status_code != 200:
            return []

        soup = BeautifulSoup(response.text, 'html.parser')
        stock_table = soup.find('table', class_='m-table')
        if not stock_table:
            return []

        stock_codes = []
        rows = stock_table.find_all('tr')
        for row in rows:
            cols = row.find_all('td')
            if len(cols) >= 2:
                code = cols[1].text.strip()
                if code and code.isdigit() and len(code) == 6:
                    stock_codes.append(code)

        return stock_codes
    except Exception as e:
        logger.error("fetch_ths_concept_stocks_failed", concept_code=concept_code, error=str(e))
        return []


async def import_ths_concepts():
    """导入同花顺概念板块列表"""
    logger.info("import_ths_concepts_start")

    concepts = fetch_ths_concept_list()
    if not concepts:
        logger.warning("import_ths_concepts_empty")
        return

    db = await get_db()
    try:
        count = 0
        for c in concepts:
            await db.execute(
                "INSERT OR REPLACE INTO concepts (name, category) VALUES (?, ?)",
                (c["name"], "ths_concept"),
            )
            count += 1

        await db.commit()
        logger.info("import_ths_concepts_done", count=count)
    finally:
        await db.close()


async def import_ths_concept_stocks():
    """导入同花顺概念成分股关联"""
    logger.info("import_ths_concept_stocks_start")

    db = await get_db()
    try:
        # 创建关联表（如果不存在）
        await db.execute(
            "CREATE TABLE IF NOT EXISTS stock_concepts ("
            "stock_code TEXT NOT NULL, "
            "concept_name TEXT NOT NULL, "
            "created_at TEXT DEFAULT (datetime('now')), "
            "PRIMARY KEY (stock_code, concept_name))"
        )
        await db.commit()

        # 先获取所有概念的代码映射
        logger.info("fetching_ths_concept_list")
        concept_list = fetch_ths_concept_list()
        concept_map = {c["name"]: c["code"] for c in concept_list}
        logger.info("ths_concept_list_fetched", count=len(concept_map))

        # 获取所有同花顺概念
        cursor = await db.execute("SELECT name FROM concepts WHERE category = 'ths_concept'")
        concepts = await cursor.fetchall()

        total = 0
        for (concept_name,) in concepts:
            try:
                # 从映射中获取概念代码
                concept_code = concept_map.get(concept_name)
                if not concept_code:
                    continue

                # 获取成分股
                stock_codes = fetch_ths_concept_stocks(concept_code)
                if not stock_codes:
                    continue

                # 保存关联
                for code in stock_codes:
                    await db.execute(
                        "INSERT OR IGNORE INTO stock_concepts (stock_code, concept_name) VALUES (?, ?)",
                        (code, concept_name),
                    )
                    total += 1

                await db.commit()
                logger.debug("import_ths_concept_stocks_done", concept=concept_name, count=len(stock_codes))

                # 限流
                time.sleep(1)

            except Exception as e:
                logger.warning("import_ths_concept_stocks_failed", concept=concept_name, error=str(e))
                continue

        logger.info("import_ths_concept_stocks_all_done", total=total)

    finally:
        await db.close()


async def get_stock_concepts(stock_code: str) -> list[str]:
    """获取股票的概念列表"""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT concept_name FROM stock_concepts WHERE stock_code = ?",
            (stock_code,)
        )
        rows = await cursor.fetchall()
        return [r[0] for r in rows]
    finally:
        await db.close()


async def get_concept_stocks(concept_name: str) -> list[str]:
    """获取概念的股票代码列表"""
    db = await get_db()
    try:
        cursor = await db.execute(
            "SELECT stock_code FROM stock_concepts WHERE concept_name = ?",
            (concept_name,)
        )
        rows = await cursor.fetchall()
        return [r[0] for r in rows]
    finally:
        await db.close()


async def run_import():
    """执行完整的概念导入流程"""
    logger.info("import_ths_concepts_full_start")
    await import_ths_concepts()
    await import_ths_concept_stocks()
    logger.info("import_ths_concepts_full_done")
