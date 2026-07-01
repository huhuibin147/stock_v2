"""实时行情数据更新服务 - 访问时触发"""

import time
from datetime import datetime

import structlog

from app.core.database import get_db

logger = structlog.get_logger()

# 缓存: {stock_code: last_update_timestamp}
_update_cache: dict[str, float] = {}
# 收盘后已更新的股票集合
_after_close_updated: set[str] = set()


def _is_trading_time() -> bool:
    """判断当前是否为交易时间"""
    now = datetime.now()
    weekday = now.weekday()
    if weekday >= 5:  # 周末
        return False

    hour = now.hour
    minute = now.minute
    current = hour * 100 + minute

    # 9:15-11:30, 13:00-15:00
    if (915 <= current <= 1130) or (1300 <= current <= 1500):
        return True
    return False


def _is_after_close() -> bool:
    """判断是否已收盘（15:00之后）"""
    now = datetime.now()
    if now.weekday() >= 5:
        return False
    return now.hour >= 15


def should_refresh(stock_code: str) -> bool:
    """判断是否需要刷新该股票的数据"""
    now = time.time()

    # 交易时间内: 每次访问都更新（限制最少30秒间隔，避免频繁刷新）
    if _is_trading_time():
        last_update = _update_cache.get(stock_code, 0)
        if now - last_update < 30:
            return False
        return True

    # 收盘后: 只更新一次
    if _is_after_close():
        if stock_code in _after_close_updated:
            return False
        return True

    # 非交易时间（盘前/周末）: 不更新
    return False


def mark_updated(stock_code: str):
    """标记股票已更新"""
    _update_cache[stock_code] = time.time()
    if _is_after_close():
        _after_close_updated.add(stock_code)


async def refresh_stock_data(code: str, market: str) -> dict | None:
    """实时爬取单只股票的最新数据并更新数据库"""
    if not should_refresh(code):
        return None

    try:
        from app.tasks.import_fundamentals import _fetch_spot_em, _safe_float

        # 直接调用异步函数获取全市场数据
        all_data = await _fetch_spot_em()
        if not all_data:
            return None

        # 查找目标股票
        target = None
        for item in all_data:
            item_code = str(item.get("f12", ""))
            if item_code == code:
                # 转换字段名
                target = {
                    "last_price": item.get("f2"),
                    "pct_change": item.get("f3"),
                    "turnover_amount": item.get("f6"),
                    "code": item.get("f12"),
                    "name": item.get("f14"),
                    "pe_ttm": item.get("f9"),
                    "pb": item.get("f23"),
                    "market_cap": item.get("f20"),
                }
                break

        if not target:
            return None

        # 更新数据库
        db = await get_db()
        try:
            await db.execute(
                """
                UPDATE stocks
                SET last_price = ?,
                    pct_change = ?,
                    volume = ?,
                    turnover_amount = ?,
                    market_cap = ?,
                    pe_ttm = ?,
                    pb = ?,
                    updated_at = datetime('now')
                WHERE code = ?
                """,
                (
                    _safe_float(target.get("last_price")),
                    _safe_float(target.get("pct_change")),
                    _safe_float(target.get("volume")),
                    _safe_float(target.get("turnover_amount")),
                    _safe_float(target.get("market_cap")),
                    _safe_float(target.get("pe_ttm")),
                    _safe_float(target.get("pb")),
                    code,
                ),
            )
            await db.commit()

            mark_updated(code)

            logger.info(f"实时更新 {code} 成功: 价格={target.get('last_price')}, 涨跌={target.get('pct_change')}%")
            return target
        finally:
            await db.close()

    except Exception as e:
        logger.error(f"实时更新 {code} 失败: {e}")
        return None
