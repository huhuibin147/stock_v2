"""导入概念板块和成分股数据"""

import asyncio
import json
import subprocess
import time
from datetime import datetime

import structlog

from app.core.database import get_db

logger = structlog.get_logger()


def _curl_get(url: str, params: dict, timeout: int = 15) -> dict | None:
    """用 curl 调用 API"""
    from urllib.parse import quote
    qs = "&".join(f"{k}={quote(str(v), safe='')}" for k, v in params.items())
    full_url = f"{url}?{qs}"
    try:
        result = subprocess.run(
            ["curl", "-s", full_url,
             "-H", "User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
             "-H", "Referer: https://quote.eastmoney.com/",
             "--connect-timeout", str(timeout)],
            capture_output=True, text=True, timeout=timeout + 5,
        )
        if result.returncode == 0 and result.stdout:
            return json.loads(result.stdout)
    except Exception:
        pass
    return None


async def fetch_concept_list() -> list[dict]:
    """获取概念板块列表"""
    all_concepts = []
    page = 1
    max_pages = 10

    while page <= max_pages:
        data = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda p=page: _curl_get(
                "https://82.push2.eastmoney.com/api/qt/clist/get",
                {
                    "pn": str(p),
                    "pz": "100",
                    "po": "1",
                    "np": "1",
                    "fltt": "2",
                    "invt": "2",
                    "fid": "f3",
                    "fs": "m:90 t:3 f:!50",
                    "fields": "f12,f14,f3,f8,f104,f105",
                    "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                },
            ),
        )

        if not data or data.get("rc") != 0:
            break

        diff = data.get("data", {}).get("diff", [])
        if not diff:
            break

        for item in diff:
            code = str(item.get("f12", ""))
            name = str(item.get("f14", ""))
            if code and name:
                all_concepts.append({
                    "code": code,
                    "name": name,
                    "stock_count": item.get("f104", 0),
                })

        total = data.get("data", {}).get("total", 0)
        if len(all_concepts) >= total:
            break

        page += 1
        await asyncio.sleep(0.5)

    return all_concepts


async def fetch_concept_stocks(concept_code: str) -> list[str]:
    """获取概念板块的成分股代码列表"""
    all_codes = []
    page = 1
    max_pages = 20

    while page <= max_pages:
        data = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda p=page: _curl_get(
                "https://82.push2.eastmoney.com/api/qt/clist/get",
                {
                    "pn": str(p),
                    "pz": "1000",
                    "po": "1",
                    "np": "1",
                    "fltt": "2",
                    "invt": "2",
                    "fid": "f3",
                    "fs": f"b:{concept_code} f:!50",
                    "fields": "f12",
                    "ut": "bd1d9ddb04089700cf9c27f6f7426281",
                },
            ),
        )

        if not data or data.get("rc") != 0:
            break

        diff = data.get("data", {}).get("diff", [])
        if not diff:
            break

        for item in diff:
            code = str(item.get("f12", ""))
            if code:
                all_codes.append(code)

        total = data.get("data", {}).get("total", 0)
        if len(all_codes) >= total:
            break

        page += 1
        await asyncio.sleep(0.3)

    return all_codes


async def import_concepts():
    """导入概念板块列表"""
    logger.info("import_concepts_start")

    concepts = await fetch_concept_list()
    if not concepts:
        logger.warning("import_concepts_empty")
        return

    db = await get_db()
    try:
        count = 0
        for c in concepts:
            await db.execute(
                "INSERT OR REPLACE INTO concepts (name, category, stock_count) VALUES (?, ?, ?)",
                (c["name"], "concept", c["stock_count"]),
            )
            count += 1

        await db.commit()
        logger.info("import_concepts_done", count=count)
    finally:
        await db.close()


async def import_concept_stocks():
    """导入概念成分股关联"""
    logger.info("import_concept_stocks_start")

    db = await get_db()
    try:
        # 创建关联表（如果不存在）
        await db.execute("""
            CREATE TABLE IF NOT EXISTS stock_concepts (
                stock_code TEXT NOT NULL,
                concept_name TEXT NOT NULL,
                created_at TEXT DEFAULT datetime('now'),
                PRIMARY KEY (stock_code, concept_name)
            )
        """)
        await db.commit()

        # 先获取所有概念的代码映射
        logger.info("fetching_concept_list")
        concept_list = await fetch_concept_list()
        concept_map = {c["name"]: c["code"] for c in concept_list}
        logger.info("concept_list_fetched", count=len(concept_map))

        # 获取所有概念
        cursor = await db.execute("SELECT name FROM concepts")
        concepts = await cursor.fetchall()

        total = 0
        for (concept_name,) in concepts:
            try:
                # 从映射中获取概念代码
                concept_code = concept_map.get(concept_name)
                if not concept_code:
                    continue

                # 获取成分股
                stock_codes = await fetch_concept_stocks(concept_code)
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
                logger.debug("import_concept_stocks_done", concept=concept_name, count=len(stock_codes))

                # 限流
                await asyncio.sleep(0.5)

            except Exception as e:
                logger.warning("import_concept_stocks_failed", concept=concept_name, error=str(e))
                continue

        logger.info("import_concept_stocks_all_done", total=total)

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
    logger.info("import_concepts_full_start")
    await import_concepts()
    await import_concept_stocks()
    logger.info("import_concepts_full_done")
