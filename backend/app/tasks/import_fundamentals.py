import asyncio
import time

import structlog

from app.core.database import get_db

logger = structlog.get_logger()


async def import_valuation():
    """批量更新全市场估值数据（PE/PB/市值）到 stocks 表"""
    try:
        import akshare as ak
    except ImportError:
        logger.error("akshare_not_installed")
        return

    logger.info("import_valuation_start")

    try:
        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(None, ak.stock_zh_a_spot_em)

        if df is None or df.empty:
            logger.warning("valuation_empty")
            return

        db = await get_db()
        try:
            updated = 0
            for _, row in df.iterrows():
                code = str(row.get("代码", "")).strip()
                if not code:
                    continue

                pe = row.get("市盈率-动态")
                pb = row.get("市净率")
                cap = row.get("总市值")

                # 跳过无效值
                try:
                    pe = float(pe) if pe and str(pe) != "-" else None
                except (ValueError, TypeError):
                    pe = None
                try:
                    pb = float(pb) if pb and str(pb) != "-" else None
                except (ValueError, TypeError):
                    pb = None
                try:
                    cap = float(cap) if cap and str(cap) != "-" else None
                except (ValueError, TypeError):
                    cap = None

                if pe is None and pb is None and cap is None:
                    continue

                await db.execute(
                    """UPDATE stocks SET pe_ttm = ?, pb = ?, market_cap = ?, updated_at = datetime('now')
                       WHERE code = ?""",
                    (pe, pb, cap, code),
                )
                updated += 1

            await db.commit()
            logger.info("import_valuation_done", updated=updated, total=len(df))
        finally:
            await db.close()

    except Exception as e:
        logger.error("import_valuation_failed", error=str(e))


async def import_financials(code: str):
    """采集单只股票的季度财务数据（同花顺源）"""
    try:
        import akshare as ak
    except ImportError:
        logger.error("akshare_not_installed")
        return

    try:
        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(
            None, lambda: ak.stock_financial_abstract_ths(symbol=code, indicator="按报告期")
        )

        if df is None or df.empty:
            return

        db = await get_db()
        try:
            count = 0
            # 取最近 8 个季度（数据按时间正序，取最后8条）
            for _, row in df.tail(8).iterrows():
                report_date = str(row.get("报告期", "")).strip()
                if not report_date or report_date == "False":
                    continue

                def safe_float(val):
                    if val is None or val is False or val == "False" or val == "--" or val == "":
                        return None
                    try:
                        if isinstance(val, str):
                            val = val.replace(",", "").strip()
                            # 处理百分号
                            if val.endswith("%"):
                                return float(val[:-1])
                            # 处理中文单位（亿=1e8, 万=1e4）
                            if val.endswith("亿"):
                                return float(val[:-1]) * 1e8
                            if val.endswith("万"):
                                return float(val[:-1]) * 1e4
                        return float(val)
                    except (ValueError, TypeError):
                        return None

                await db.execute(
                    """INSERT OR REPLACE INTO stock_financials
                       (code, report_date, net_profit, net_profit_yoy, revenue, revenue_yoy,
                        eps, bps, roe, net_margin, equity_ratio, ocf_ps)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        code,
                        report_date,
                        safe_float(row.get("净利润")),
                        safe_float(row.get("净利润同比增长率")),
                        safe_float(row.get("营业总收入")),
                        safe_float(row.get("营业总收入同比增长率")),
                        safe_float(row.get("基本每股收益")),
                        safe_float(row.get("每股净资产")),
                        safe_float(row.get("净资产收益率")),
                        safe_float(row.get("销售净利率")),
                        safe_float(row.get("资产负债率")),
                        safe_float(row.get("每股经营现金流")),
                    ),
                )
                count += 1

            await db.commit()
            logger.debug("import_financials_done", code=code, rows=count)
        finally:
            await db.close()

    except Exception as e:
        logger.debug("import_financials_failed", code=code, error=str(e))


async def import_financials_batch(codes: list[str] | None = None, limit: int = 100):
    """批量采集财务数据。不传 codes 则取有资讯关联的活跃股票"""
    try:
        import akshare as ak
    except ImportError:
        logger.error("akshare_not_installed")
        return

    logger.info("import_financials_batch_start")

    if codes is None:
        db = await get_db()
        try:
            # 取有公司详情但没财务数据的股票
            cursor = await db.execute(
                """SELECT sp.code FROM stock_profiles sp
                   WHERE NOT EXISTS (SELECT 1 FROM stock_financials sf WHERE sf.code = sp.code)
                   ORDER BY sp.code
                   LIMIT ?""",
                (limit,),
            )
            codes = [r[0] for r in await cursor.fetchall()]
        finally:
            await db.close()

    if not codes:
        logger.info("import_financials_batch_no_stocks")
        return

    success = 0
    failed = 0
    for i, code in enumerate(codes):
        try:
            await import_financials(code)
            success += 1
        except Exception as e:
            failed += 1
            logger.debug("import_financials_batch_item_failed", code=code, error=str(e))

        # 限流：每 5 只休息 1 秒
        if (i + 1) % 5 == 0:
            time.sleep(1)

    logger.info("import_financials_batch_done", success=success, failed=failed, total=len(codes))
