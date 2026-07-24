"""强势连阳策略

条件：
1. 连续收阳 >= 3天
2. 量能温和放大
3. 涨幅适中（非暴涨）
"""

from app.strategies.base import BaseStrategy, Signal
from app.core.database import get_db


class StrongYangStrategy(BaseStrategy):
    name = "strong_yang"
    display_name = "强势连阳"
    description = "趋势跟踪：连续收阳+量能温和放大"

    async def scan(self, limit: int = 20) -> list[Signal]:
        db = await get_db()
        try:
            cursor = await db.execute("""
                SELECT DISTINCT k.code
                FROM stock_kline k
                WHERE k.trade_date >= date('now', '-10 days')
                GROUP BY k.code
                HAVING COUNT(*) >= 5
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
            SELECT trade_date, open, close, volume, pct_change
            FROM stock_kline
            WHERE code = ?
            ORDER BY trade_date DESC
            LIMIT 6
        """, (code,))
        rows = await cursor.fetchall()

        if len(rows) < 4:
            return None

        klines = [
            {
                "date": r[0],
                "open": r[1],
                "close": r[2],
                "volume": r[3],
                "pct_change": r[4],
            }
            for r in rows
        ]

        # 计算连续收阳天数
        yang_days = 0
        total_pct = 0
        for k in klines:
            if k["close"] and k["open"] and k["close"] > k["open"]:
                yang_days += 1
                total_pct += k["pct_change"] or 0
            else:
                break

        # 条件1：连阳 >= 3天
        if yang_days < 3:
            return None

        # 条件2：涨幅适中（单日不超过9%，累计不超过20%）
        if total_pct > 20:
            return None

        # 条件3：量能温和放大
        volumes = [k["volume"] for k in klines[:yang_days] if k["volume"]]
        if len(volumes) < 2:
            return None

        # 检查量能是否递增
        vol_increasing = all(
            volumes[i] >= volumes[i + 1] * 0.8
            for i in range(len(volumes) - 1)
        )

        # 计算分数
        score = yang_days * 15 + (5 if vol_increasing else 0)
        score = min(100, score)

        # 获取股票名称
        cursor = await db.execute("SELECT name FROM stocks WHERE code = ?", (code,))
        row = await cursor.fetchone()
        name = row[0] if row else code

        latest = klines[0]

        return Signal(
            code=code,
            name=name,
            reason=f"连阳{yang_days}天，累计涨幅{total_pct:.1f}%",
            score=round(score, 1),
            indicators={
                "yang_days": yang_days,
                "total_pct": round(total_pct, 2),
                "close": latest["close"],
                "vol_increasing": vol_increasing,
            },
        )
