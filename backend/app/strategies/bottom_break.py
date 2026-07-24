"""底部放量突破策略

条件：
1. 当前价格处于近20日低位（低于20日均价的95%）
2. 当日成交量 > 5日均量的2倍
3. 当日收阳线（收盘 > 开盘）
"""

from app.strategies.base import BaseStrategy, Signal
from app.core.database import get_db


class BottomBreakStrategy(BaseStrategy):
    name = "bottom_break"
    display_name = "底部放量突破"
    description = "低位启动信号：近20日低位 + 放量收阳"

    async def scan(self, limit: int = 20) -> list[Signal]:
        db = await get_db()
        try:
            # 查询有足够K线数据的股票
            cursor = await db.execute("""
                SELECT DISTINCT k.code
                FROM stock_kline k
                WHERE k.trade_date >= date('now', '-30 days')
                GROUP BY k.code
                HAVING COUNT(*) >= 15
            """)
            codes = [row[0] for row in await cursor.fetchall()]

            signals = []
            for code in codes:
                signal = await self._check_stock(db, code)
                if signal:
                    signals.append(signal)

            # 按分数排序，返回top N
            signals.sort(key=lambda x: x.score, reverse=True)
            return signals[:limit]
        finally:
            await db.close()

    async def _check_stock(self, db, code: str) -> Signal | None:
        """检查单只股票是否符合条件"""
        # 获取近20日K线
        cursor = await db.execute("""
            SELECT trade_date, open, close, high, low, volume
            FROM stock_kline
            WHERE code = ?
            ORDER BY trade_date DESC
            LIMIT 20
        """, (code,))
        rows = await cursor.fetchall()

        if len(rows) < 15:
            return None

        # 解析数据
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

        # 最新一根K线
        latest = klines[0]
        if not latest["volume"] or latest["volume"] <= 0:
            return None

        # 条件1：当日收阳线
        if latest["close"] <= latest["open"]:
            return None

        # 条件2：计算20日均价
        closes = [k["close"] for k in klines if k["close"]]
        if len(closes) < 10:
            return None
        avg_20 = sum(closes) / len(closes)

        # 当前价格低于20日均价的95%
        if latest["close"] > avg_20 * 0.95:
            return None

        # 条件3：计算5日均量
        volumes = [k["volume"] for k in klines[:5] if k["volume"]]
        if len(volumes) < 3:
            return None
        avg_vol_5 = sum(volumes) / len(volumes)

        # 当日成交量 > 5日均量的2倍
        if latest["volume"] < avg_vol_5 * 2:
            return None

        # 计算信号分数
        vol_ratio = latest["volume"] / avg_vol_5 if avg_vol_5 > 0 else 0
        price_ratio = latest["close"] / avg_20 if avg_20 > 0 else 0

        # 分数：量比越高、价格越低，分数越高
        score = min(100, (vol_ratio - 2) * 20 + (1 - price_ratio) * 100)

        # 获取股票名称
        cursor = await db.execute("SELECT name FROM stocks WHERE code = ?", (code,))
        row = await cursor.fetchone()
        name = row[0] if row else code

        return Signal(
            code=code,
            name=name,
            reason=f"底部放量，量比{vol_ratio:.1f}倍，价格低于均价{(1-price_ratio)*100:.0f}%",
            score=round(score, 1),
            indicators={
                "close": latest["close"],
                "volume_ratio": round(vol_ratio, 2),
                "price_vs_avg": round(price_ratio, 3),
                "avg_volume_5": int(avg_vol_5),
            },
        )
