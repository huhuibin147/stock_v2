"""单股数据刷新服务 - 访问股票详情时触发，只采集当前股票"""

import asyncio
import json
import subprocess
import time
from datetime import datetime, timedelta

import structlog

from app.core.database import get_db

logger = structlog.get_logger()

# 防重复触发: {stock_code: last_refresh_timestamp}
_refresh_lock: dict[str, float] = {}
# 最小刷新间隔（秒）
MIN_REFRESH_INTERVAL = 60


def _curl_get(url: str, params: dict, timeout: int = 10) -> dict | None:
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


def _safe_float(val):
    if val is None or val is False or str(val) in ("-", "", "False", "--", "None"):
        return None
    try:
        return float(val)
    except (ValueError, TypeError):
        return None


def should_refresh(code: str) -> bool:
    """判断是否需要刷新该股票的数据"""
    now = time.time()
    last_refresh = _refresh_lock.get(code, 0)
    if now - last_refresh < MIN_REFRESH_INTERVAL:
        return False
    return True


def mark_refreshing(code: str):
    """标记股票正在刷新"""
    _refresh_lock[code] = time.time()


async def fetch_single_stock_quote(code: str) -> dict | None:
    """获取单只股票的实时行情数据"""
    # 判断市场：0=深圳，1=上海
    market = 1 if code.startswith("6") else 0

    data = await asyncio.get_event_loop().run_in_executor(
        None,
        lambda: _curl_get(
            "https://push2.eastmoney.com/api/qt/stock/get",
            {
                "secid": f"{market}.{code}",
                "ut": "fa5fd1943c7b386f172d6893dbbd4dc",
                "fields": "f43,f44,f45,f46,f47,f48,f50,f51,f52,f55,f57,f58,f60,f116,f117,f162,f167,f168,f169,f170,f171,f177",
                "invt": "2",
                "fltt": "2",
            },
        ),
    )

    if not data or data.get("rc") != 0:
        return None

    d = data.get("data", {})
    if not d:
        return None

    return {
        "name": d.get("f58"),                           # 股票名称（含XD/XR/DR等标记）
        "last_price": _safe_float(d.get("f43")),       # 最新价
        "pct_change": _safe_float(d.get("f170")),       # 涨跌幅
        "turnover_amount": _safe_float(d.get("f47")),   # 成交额
        "volume": _safe_float(d.get("f48")),            # 成交量
        "pe_ttm": _safe_float(d.get("f167")),           # 市盈率-动态
        "pb": _safe_float(d.get("f168")),               # 市净率
        "market_cap": _safe_float(d.get("f116")),       # 总市值
    }


async def fetch_single_stock_kline(code: str, days: int = 7) -> list[dict]:
    """获取单只股票最近N个交易日的K线数据"""
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
        # 格式: 日期,开盘,收盘,最高,低,成交量,成交额,振幅,涨跌幅,涨跌额,换手率
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


async def update_stock_quote(code: str, quote: dict):
    """更新股票行情数据到数据库"""
    db = await get_db()
    try:
        # 更新股票名称（处理除权除息标记 XD/XR/DR）和行情数据
        await db.execute(
            """UPDATE stocks
               SET name = ?,
                   last_price = ?,
                   pct_change = ?,
                   turnover_amount = ?,
                   volume = ?,
                   pe_ttm = ?,
                   pb = ?,
                   market_cap = ?,
                   updated_at = datetime('now')
               WHERE code = ?""",
            (
                quote.get("name"),
                quote.get("last_price"),
                quote.get("pct_change"),
                quote.get("turnover_amount"),
                quote.get("volume"),
                quote.get("pe_ttm"),
                quote.get("pb"),
                quote.get("market_cap"),
                code,
            ),
        )
        await db.commit()
    finally:
        await db.close()


async def update_stock_kline(code: str, klines: list[dict]):
    """更新K线数据到数据库"""
    if not klines:
        return

    db = await get_db()
    try:
        for r in klines:
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


async def refresh_single_stock(code: str) -> bool:
    """刷新单只股票的行情和K线数据（带防重复）"""
    if not should_refresh(code):
        logger.debug("stock_refresh_skip", code=code, reason="recently_refreshed")
        return False

    mark_refreshing(code)

    try:
        # 并发获取行情和K线
        quote_task = fetch_single_stock_quote(code)
        kline_task = fetch_single_stock_kline(code, days=7)

        quote, klines = await asyncio.gather(quote_task, kline_task)

        # 更新数据库
        if quote:
            await update_stock_quote(code, quote)
            logger.info("stock_quote_updated", code=code, price=quote.get("last_price"))

        if klines:
            await update_stock_kline(code, klines)
            logger.info("stock_kline_updated", code=code, count=len(klines))

        return True

    except Exception as e:
        logger.error("stock_refresh_failed", code=code, error=str(e))
        return False
