import json
import structlog

from app.core.database import get_db

logger = structlog.get_logger()


async def import_stocks():
    """从AKShare导入A股股票列表"""
    try:
        import akshare as ak
    except ImportError:
        logger.error("akshare_not_installed")
        return

    logger.info("import_stocks_start")

    try:
        # 获取A股实时行情（含代码、名称、行业等）
        df = ak.stock_zh_a_spot_em()
        if df is None or df.empty:
            logger.warning("akshare_returned_empty")
            return

        db = await get_db()
        try:
            count = 0
            for _, row in df.iterrows():
                code = str(row.get("代码", "")).strip()
                name = str(row.get("名称", "")).strip()
                if not code or not name:
                    continue

                # 判断市场
                if code.startswith("6"):
                    market = "SH"
                elif code.startswith(("0", "3")):
                    market = "SZ"
                elif code.startswith(("4", "8")):
                    market = "BJ"
                else:
                    market = "OTHER"

                industry = str(row.get("所属行业", "")).strip() if "所属行业" in df.columns else ""

                await db.execute(
                    """INSERT OR REPLACE INTO stocks (code, name, market, industry, is_active)
                       VALUES (?, ?, ?, ?, 1)""",
                    (code, name, market, industry or None),
                )
                count += 1

            await db.commit()
            logger.info("import_stocks_done", count=count)
        finally:
            await db.close()

    except Exception as e:
        logger.error("import_stocks_failed", error=str(e))


async def import_concepts():
    """从AKShare导入概念板块"""
    try:
        import akshare as ak
    except ImportError:
        logger.error("akshare_not_installed")
        return

    logger.info("import_concepts_start")

    try:
        df = ak.stock_board_concept_name_em()
        if df is None or df.empty:
            logger.warning("akshare_concepts_empty")
            return

        db = await get_db()
        try:
            count = 0
            for _, row in df.iterrows():
                name = str(row.get("板块名称", "")).strip()
                if not name:
                    continue

                await db.execute(
                    "INSERT OR IGNORE INTO concepts (name, category) VALUES (?, ?)",
                    (name, "concept"),
                )
                count += 1

            await db.commit()
            logger.info("import_concepts_done", count=count)
        finally:
            await db.close()

    except Exception as e:
        logger.error("import_concepts_failed", error=str(e))


async def import_concept_stocks():
    """从AKShare导入概念板块成分股，更新stocks.concepts字段"""
    try:
        import akshare as ak
    except ImportError:
        logger.error("akshare_not_installed")
        return

    logger.info("import_concept_stocks_start")

    db = await get_db()
    try:
        # 获取所有概念
        cursor = await db.execute("SELECT id, name FROM concepts")
        concepts = await cursor.fetchall()

        total = 0
        for concept_id, concept_name in concepts:
            try:
                df = ak.stock_board_concept_cons_em(symbol=concept_name)
                if df is None or df.empty:
                    continue

                for _, row in df.iterrows():
                    code = str(row.get("代码", "")).strip()
                    if not code:
                        continue

                    # 更新stocks.concepts
                    cursor2 = await db.execute("SELECT concepts FROM stocks WHERE code = ?", (code,))
                    stock_row = await cursor2.fetchone()
                    if stock_row:
                        existing = []
                        if stock_row[0]:
                            try:
                                existing = json.loads(stock_row[0])
                            except (json.JSONDecodeError, TypeError):
                                existing = []
                        if concept_name not in existing:
                            existing.append(concept_name)
                            await db.execute(
                                "UPDATE stocks SET concepts = ?, updated_at = datetime('now') WHERE code = ?",
                                (json.dumps(existing, ensure_ascii=False), code),
                            )
                            total += 1

            except Exception as e:
                logger.warning("import_concept_failed", concept=concept_name, error=str(e))
                continue

        await db.commit()
        logger.info("import_concept_stocks_done", updated=total)

    except Exception as e:
        logger.error("import_concept_stocks_failed", error=str(e))
    finally:
        await db.close()
