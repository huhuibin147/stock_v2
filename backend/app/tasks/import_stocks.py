import json
import structlog

from app.core.database import get_db

logger = structlog.get_logger()


async def import_stocks():
    """从AKShare导入A股股票列表（使用新浪源，不依赖东方财富）"""
    try:
        import akshare as ak
    except ImportError:
        logger.error("akshare_not_installed")
        return

    logger.info("import_stocks_start")

    try:
        # 基础列表：code + name（新浪源，5500+条）
        df = ak.stock_info_a_code_name()
        if df is None or df.empty:
            logger.warning("akshare_returned_empty")
            return

        # 上交所补充信息（上市日期等）
        sh_extra = {}
        try:
            df_sh = ak.stock_info_sh_name_code()
            for _, r in df_sh.iterrows():
                code = str(r.get("证券代码", "")).strip()
                sh_extra[code] = {
                    "full_name": str(r.get("证券全称", "")).strip(),
                    "list_date": str(r.get("上市日期", "")).strip(),
                }
        except Exception as e:
            logger.warning("sh_info_failed", error=str(e))

        # 深交所补充信息
        sz_extra = {}
        try:
            df_sz = ak.stock_info_sz_name_code()
            for _, r in df_sz.iterrows():
                code = str(r.get("A股代码", "")).strip()
                sz_extra[code] = {
                    "list_date": str(r.get("A股上市日期", "")).strip(),
                }
        except Exception as e:
            logger.warning("sz_info_failed", error=str(e))

        db = await get_db()
        try:
            count = 0
            for _, row in df.iterrows():
                code = str(row.get("code", "")).strip()
                name = str(row.get("name", "")).strip()
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

                # 补充信息
                extra = sh_extra.get(code) or sz_extra.get(code) or {}
                list_date = extra.get("list_date", "")

                await db.execute(
                    """INSERT OR REPLACE INTO stocks (code, name, market, list_date, is_active)
                       VALUES (?, ?, ?, ?, 1)""",
                    (code, name, market, list_date or None),
                )
                count += 1

            await db.commit()
            logger.info("import_stocks_done", count=count)
        finally:
            await db.close()

    except Exception as e:
        logger.error("import_stocks_failed", error=str(e))


# ── 以下接口依赖东方财富，当前环境不可用 ──
# 如需启用，在可访问东方财富的网络环境下运行


async def import_concepts():
    """从AKShare导入概念板块（依赖东方财富，当前不可用）"""
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
    """从AKShare导入概念成分股（依赖东方财富，当前不可用）"""
    try:
        import akshare as ak
    except ImportError:
        logger.error("akshare_not_installed")
        return

    logger.info("import_concept_stocks_start")

    db = await get_db()
    try:
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
