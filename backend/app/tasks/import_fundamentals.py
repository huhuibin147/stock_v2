import asyncio
import json
import subprocess
import time
from datetime import datetime, timedelta

import structlog

from app.core.database import get_db

logger = structlog.get_logger()


def _get_target_date() -> str:
    """获取目标交易日期：15:00前取前一个交易日，15:00后取当天"""
    now = datetime.now()
    if now.hour < 15:
        # 15点前，往前找最近的工作日
        target = now - timedelta(days=1)
        # 周日→周五，周六→周五
        while target.weekday() >= 5:
            target -= timedelta(days=1)
    else:
        target = now
    return target.strftime("%Y%m%d")


def _curl_get(url: str, params: dict, timeout: int = 15) -> dict | None:
    """用 curl 调用 API（绕过 Python requests 的 TLS 指纹检测）"""
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


async def _fetch_kline(code: str, days: int = 5) -> list[dict]:
    """获取单只股票最近N个交易日的K线数据（使用 curl 绕过 TLS 检测）"""
    start = (datetime.now() - timedelta(days=days * 2)).strftime("%Y%m%d")
    end = datetime.now().strftime("%Y%m%d")

    # 判断市场：0=深圳，1=上海
    market = 1 if code.startswith("6") else 0

    data = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: _curl_get(
            "https://push2his.eastmoney.com/api/qt/stock/kline/get",
            {
                "secid": f"{market}.{code}",
                "ut": "fa5fd1943c7b386f172d6893dbbd4dc",
                "fields1": "f1,f2,f3,f4,f5,f6",
                "fields2": "f51,f52,f53,f54,f55,f56,f57,f58,f59,f60,f61",
                "klt": "101",
                "fqt": "1",
                "beg": start,
                "end": end,
            },
        ),
    )

    if not data or data.get("rc") != 0:
        return []

    klines = data.get("data", {}).get("klines", [])
    rows = []
    for line in klines:
        # 格式: 日期,开盘,收盘,最高,最低,成交量,成交额,振幅,涨跌幅,涨跌额,换手率
        parts = line.split(",")
        if len(parts) < 11:
            continue
        rows.append({
            "trade_date": parts[0],
            "open": _safe_float(parts[1]),
            "close": _safe_float(parts[2]),
            "high": _safe_float(parts[3]),
            "low": _safe_float(parts[4]),
            "volume": _safe_float(parts[5]),
            "turnover": _safe_float(parts[6]),
            "amplitude": _safe_float(parts[7]),
            "pct_change": _safe_float(parts[8]),
            "change_amount": _safe_float(parts[9]),
            "turnover_rate": _safe_float(parts[10]),
        })
    return rows


async def _fetch_spot_em() -> list[dict] | None:
    """获取全市场实时行情（使用 curl 绕过 TLS 检测）。若 bulk 接口被限流，返回 None。"""
    all_rows = []
    page = 1
    max_pages = 20  # 安全限制，防止无限循环
    while page <= max_pages:
        data = await asyncio.get_event_loop().run_in_executor(
            None,
            lambda p=page: _curl_get(
                "https://82.push2.eastmoney.com/api/qt/clist/get",
                {
                    "pn": str(p),
                    "pz": "5000",
                    "po": "1",
                    "np": "1",
                    "fltt": "2",
                    "invt": "2",
                    "fid": "f6",
                    "fs": "m:0 t:6,m:0 t:80,m:1 t:2,m:1 t:23,m:0 t:81 s:2048",
                    "fields": "f2,f3,f6,f12,f14,f9,f23,f20",
                    "ut": "fa5fd1943c7b386f172d6893dbbd4dc",
                },
            ),
        )
        if not data or data.get("rc") != 0:
            break
        diff = data.get("data", {}).get("diff", [])
        if not diff:
            break
        all_rows.extend(diff)
        total = data.get("data", {}).get("total", 0)
        if len(all_rows) >= total:
            break
        page += 1
        time.sleep(1)  # 页间延迟，避免限流
    return all_rows if all_rows else None


def _safe_float(val):
    if val is None or val is False or str(val) in ("-", "", "False", "--", "None"):
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


async def import_turnover():
    """采集全市场实时行情（成交额+最新价+涨跌幅+成交量），更新到 stocks 表"""
    try:
        import akshare as ak
    except ImportError:
        logger.error("akshare_not_installed")
        return

    logger.info("import_turnover_start")

    try:
        loop = asyncio.get_event_loop()
        df = await loop.run_in_executor(None, ak.stock_zh_a_spot)

        if df is None or df.empty:
            logger.warning("turnover_empty")
            return

        db = await get_db()
        try:
            updated = 0
            for _, row in df.iterrows():
                raw_code = str(row.get("代码", "")).strip()
                code = raw_code[-6:] if len(raw_code) >= 6 else raw_code
                if not code or not code.isdigit():
                    continue

                amount = _safe_float(row.get("成交额"))
                price = _safe_float(row.get("最新价"))
                pct = _safe_float(row.get("涨跌幅"))
                vol = _safe_float(row.get("成交量"))

                await db.execute(
                    """UPDATE stocks SET
                       turnover_amount = COALESCE(?, turnover_amount),
                       last_price = ?, pct_change = ?, volume = ?,
                       updated_at = datetime('now')
                       WHERE code = ?""",
                    (amount, price, pct, vol, code),
                )
                updated += 1

            await db.commit()
            logger.info("import_turnover_done", updated=updated, total=len(df))
        finally:
            await db.close()

    except Exception as e:
        logger.error("import_turnover_failed", error=str(e))


async def _import_turnover_from_kline(limit: int = 500):
    """从K线接口获取热门股票成交额（批量接口被限流时的降级方案）"""
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT code FROM stocks
               WHERE is_active = 1
               ORDER BY market_cap DESC NULLS LAST
               LIMIT ?""",
            (limit,),
        )
        codes = [r[0] for r in await cursor.fetchall()]
    finally:
        await db.close()

    if not codes:
        return

    updated = 0
    consecutive_failures = 0
    for i, code in enumerate(codes):
        rows = await _fetch_kline(code, days=2)
        if rows:
            latest = rows[-1]
            turnover = latest.get("turnover")
            # 合理性校验：单日成交额不可能超过1万亿（1e12）
            if turnover and 0 < turnover < 1e12:
                db = await get_db()
                try:
                    await db.execute(
                        "UPDATE stocks SET turnover_amount = ?, updated_at = datetime('now') WHERE code = ?",
                        (turnover, code),
                    )
                    await db.commit()
                    updated += 1
                finally:
                    await db.close()
                consecutive_failures = 0
            else:
                consecutive_failures += 1
        else:
            consecutive_failures += 1

        # 连续失败超过5次，可能被限流，暂停30秒
        if consecutive_failures >= 5:
            logger.warning("kline_rate_limited", msg="连续失败，暂停30秒")
            time.sleep(30)
            consecutive_failures = 0

        # 每3只休息1秒
        if (i + 1) % 3 == 0:
            time.sleep(1)

    logger.info("import_turnover_from_kline_done", updated=updated, total=len(codes))


async def get_hot_stock_codes(min_amount: float = 1e9, top_n: int = 500) -> set[str]:
    """获取热门股票代码集合（成交额前500，且≥10亿）"""
    db = await get_db()
    try:
        cursor = await db.execute(
            """SELECT code FROM stocks
               WHERE turnover_amount >= ?
               ORDER BY turnover_amount DESC
               LIMIT ?""",
            (min_amount, top_n),
        )
        rows = await cursor.fetchall()
        return {r[0] for r in rows}
    finally:
        await db.close()


async def import_valuation():
    """批量更新全市场估值数据（PE/PB/市值）到 stocks 表"""
    logger.info("import_valuation_start")

    try:
        rows = await _fetch_spot_em()
        if not rows:
            logger.warning("valuation_empty")
            return

        db = await get_db()
        try:
            updated = 0
            for row in rows:
                code = str(row.get("f12", "")).strip()
                if not code:
                    continue

                pe = _safe_float(row.get("f9"))    # f9 = 市盈率-动态
                pb = _safe_float(row.get("f23"))   # f23 = 市净率
                cap = _safe_float(row.get("f20"))  # f20 = 总市值

                if pe is None and pb is None and cap is None:
                    continue

                await db.execute(
                    """UPDATE stocks SET pe_ttm = ?, pb = ?, market_cap = ?, updated_at = datetime('now')
                       WHERE code = ?""",
                    (pe, pb, cap, code),
                )
                updated += 1

            await db.commit()
            logger.info("import_valuation_done", updated=updated, total=len(rows))
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


async def import_kline_single(code: str, days: int = 5):
    """采集单只股票的最新K线数据，覆盖更新"""
    rows = await _fetch_kline(code, days)
    if not rows:
        return

    db = await get_db()
    try:
        for r in rows:
            await db.execute(
                """INSERT OR REPLACE INTO stock_kline
                   (code, trade_date, open, close, high, low, volume, turnover,
                    amplitude, pct_change, change_amount, turnover_rate)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (code, r["trade_date"], r["open"], r["close"], r["high"], r["low"],
                 r["volume"], r["turnover"], r["amplitude"], r["pct_change"],
                 r["change_amount"], r["turnover_rate"]),
            )
        await db.commit()
    finally:
        await db.close()


async def import_kline_batch(codes: list[str] | None = None, limit: int = 500, days: int = 250):
    """批量采集K线数据（近1年）。不传 codes 则取成交额前N的热门股票"""
    logger.info("import_kline_batch_start")

    if codes is None:
        db = await get_db()
        try:
            cursor = await db.execute(
                """SELECT code FROM stocks
                   WHERE is_active = 1 AND turnover_amount > 0
                   ORDER BY turnover_amount DESC
                   LIMIT ?""",
                (limit,),
            )
            codes = [r[0] for r in await cursor.fetchall()]
        finally:
            await db.close()

    if not codes:
        logger.info("import_kline_batch_no_stocks")
        return

    # 清理超过1年的数据
    db = await get_db()
    try:
        cursor = await db.execute("DELETE FROM stock_kline WHERE trade_date < date('now', '-1 year')")
        deleted = cursor.rowcount
        if deleted:
            logger.info("kline_cleanup", deleted=deleted)
        await db.commit()
    finally:
        await db.close()

    success = 0
    failed = 0
    consecutive_failures = 0
    for i, code in enumerate(codes):
        try:
            rows = await _fetch_kline(code, days)
            if rows:
                valid_rows = [r for r in rows if r.get("turnover") and 0 < r["turnover"] < 1e12]
                if valid_rows:
                    db = await get_db()
                    try:
                        for r in valid_rows:
                            await db.execute(
                                """INSERT OR REPLACE INTO stock_kline
                                   (code, trade_date, open, close, high, low, volume, turnover,
                                    amplitude, pct_change, change_amount, turnover_rate)
                                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                                (code, r["trade_date"], r["open"], r["close"], r["high"], r["low"],
                                 r["volume"], r["turnover"], r["amplitude"], r["pct_change"],
                                 r["change_amount"], r["turnover_rate"]),
                            )
                        await db.commit()
                    finally:
                        await db.close()
            success += 1
            consecutive_failures = 0
        except Exception as e:
            failed += 1
            consecutive_failures += 1
            logger.debug("import_kline_failed", code=code, error=str(e))

        # 连续失败超过5次，可能被限流，暂停30秒
        if consecutive_failures >= 5:
            logger.warning("kline_rate_limited", msg="连续失败，暂停30秒")
            time.sleep(30)
            consecutive_failures = 0

        # 限流：每 5 只休息 1 秒
        if (i + 1) % 5 == 0:
            time.sleep(1)

    logger.info("import_kline_batch_done", success=success, failed=failed, total=len(codes))
