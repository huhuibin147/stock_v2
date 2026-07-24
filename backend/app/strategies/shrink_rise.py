"""缩量回调放量策略

条件：
1. 近3-5日连续缩量下跌
2. 今日放量收阳
3. 量比 > 1.5
"""

from app.strategies.base import BaseStrategy, Signal
from app.core.database import get_db


class ShrinkRiseStrategy(BaseStrategy):
    name = "shrink_rise"
    display_name = "缩量回调放量"
    description = "洗盘结束信号：连续缩量下跌后放量收阳"

    async def scan(self, limit: int = 20) -> list[Signal]:
        db = await get_db()
        try:
            cursor = await db.execute("""
                SELECT DISTINCT k.code
                FROM stock_kline k
                WHERE k.trade_date >= date('now', '-15 days')
                GROUP BY k.code
                HAVING COUNT(*) >= 8
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
            SELECT trade_date, open, close, volume
            FROM stock_kline
            WHERE code = ?
            ORDER BY trade_date DESC
            LIMIT 8
        """, (code,))
        rows = await cursor.fetchall()

        if len(rows) < 5:
            return None

        klines = [
            {"date": r[0], "open": r[1], "close": r[2], "volume": r[3]}
            for r in rows
        ]

        # 最新一根K线（今日）
        latest = klines[0]
        if not latest["volume"] or latest["volume"] <= 0:
            return None

        # 条件1：今日收阳线
        if latest["close"] <= latest["open"]:
            return None

        # 条件2：前3-5日连续缩量下跌
        shrink_days = 0
        for i in range(1, min(6, len(klines))):
            k = klines[i]
            prev = klines[i + 1] if i + 1 < len(klines) else None
            if not prev:
                break
            # 判断是否下跌且缩量
            if k["close"] < prev["close"] and k["volume"] < prev["volume"]:
                shrink_days += 1
            else:
                break

        if shrink_days < 2:
            return None

        # 条件3：今日放量（相比前一日）
        prev_vol = klines[1]["volume"] if klines[1]["volume"] else 0
        if prev_vol <= 0:
            return None

        vol_ratio = latest["volume"] / prev_vol
        if vol_ratio < 1.5:
            return None

        # 计算分数
        score = min(100, shrink_days * 15 + (vol_ratio - 1.5) * 20)

        # 获取股票名称
        cursor = await db.execute("SELECT name FROM stocks WHERE code = ?", (code,))
        row = await cursor.fetchone()
        name = row[0] if row else code

        return Signal(
            code=code,
            name=name,
            reason=f"缩量{shrink_days}天后放量，量比{vol_ratio:.1f}倍",
            score=round(score, 1),
            indicators={
                "close": latest["close"],
                "shrink_days": shrink_days,
                "volume_ratio": round(vol_ratio, 2),
            },
        )
