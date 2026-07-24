"""突破平台策略

条件：
1. 近10日振幅 < 15%（横盘整理）
2. 今日突破10日最高价
3. 放量（成交量 > 5日均量1.5倍）
"""

from app.strategies.base import BaseStrategy, Signal
from app.core.database import get_db


class PlatformBreakStrategy(BaseStrategy):
    name = "platform_break"
    display_name = "突破平台"
    description = "整理结束信号：横盘后放量突破"

    async def scan(self, limit: int = 20) -> list[Signal]:
        db = await get_db()
        try:
            cursor = await db.execute("""
                SELECT DISTINCT k.code
                FROM stock_kline k
                WHERE k.trade_date >= date('now', '-15 days')
                GROUP BY k.code
                HAVING COUNT(*) >= 10
            """)
            codes = [row[0] for row in await cursor.fetchall()]

            signals = []
            for code in codes:
                signal = await self._check_stock(db, code)
                if signal:
                    signals.append(signal)

            signals.sort(key=lambda x: x.score, reverse=True)
            return signals[:limit]
        finally:
            await db.close()

    async def _check_stock(self, db, code: str) -> Signal | None:
        cursor = await db.execute("""
            SELECT trade_date, open, close, high, low, volume
            FROM stock_kline
            WHERE code = ?
            ORDER BY trade_date DESC
            LIMIT 12
        """, (code,))
        rows = await cursor.fetchall()

        if len(rows) < 10:
            return None

        klines = [
            {
                "date": r[0],
                "open": r[1],
                "close": r[2],
                "high": r[3],
                "low": r[4],
                "volume": r[5],
            }
            for r in rows
        ]

        latest = klines[0]
        if not latest["volume"] or latest["volume"] <= 0:
            return None

        # 条件1：今日收阳
        if latest["close"] <= latest["open"]:
            return None

        # 计算近10日（不含今日）的高低点
        recent_10 = klines[1:11]
        highs = [k["high"] for k in recent_10 if k["high"]]
        lows = [k["low"] for k in recent_10 if k["low"]]

        if not highs or not lows:
            return None

        high_10 = max(highs)
        low_10 = min(lows)

        # 条件2：振幅 < 15%
        amplitude = (high_10 - low_10) / low_10 * 100 if low_10 > 0 else 999
        if amplitude > 15:
            return None

        # 条件3：今日收盘突破10日高点
        if latest["close"] <= high_10:
            return None

        # 条件4：放量
        volumes = [k["volume"] for k in klines[1:6] if k["volume"]]
        if len(volumes) < 3:
            return None
        avg_vol_5 = sum(volumes) / len(volumes)

        vol_ratio = latest["volume"] / avg_vol_5 if avg_vol_5 > 0 else 0
        if vol_ratio < 1.5:
            return None

        # 计算分数
        break_pct = (latest["close"] - high_10) / high_10 * 100
        score = min(100, (15 - amplitude) * 3 + (vol_ratio - 1.5) * 15 + break_pct * 10)

        # 获取股票名称
        cursor = await db.execute("SELECT name FROM stocks WHERE code = ?", (code,))
        row = await cursor.fetchone()
        name = row[0] if row else code

        return Signal(
            code=code,
            name=name,
            reason=f"突破{amplitude:.0f}%振幅平台，量比{vol_ratio:.1f}倍",
            score=round(score, 1),
            indicators={
                "close": latest["close"],
                "high_10d": high_10,
                "amplitude": round(amplitude, 1),
                "volume_ratio": round(vol_ratio, 2),
                "break_pct": round(break_pct, 2),
            },
        )
