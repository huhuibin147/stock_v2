"""低估高ROE策略

条件：
1. PE < 20
2. PB < 3
3. ROE > 15%
"""

from app.strategies.base import BaseStrategy, Signal
from app.core.database import get_db


class ValueROEStrategy(BaseStrategy):
    name = "value_roe"
    display_name = "低估高ROE"
    description = "价值投资标的：PE<20 + PB<3 + ROE>15%"

    async def scan(self, limit: int = 20) -> list[Signal]:
        db = await get_db()
        try:
            # 查询低估高ROE的股票
            cursor = await db.execute("""
                SELECT s.code, s.name, s.pe_ttm, s.pb, s.last_price,
                       f.roe, f.net_margin, f.eps
                FROM stocks s
                LEFT JOIN (
                    SELECT code, roe, net_margin, eps
                    FROM stock_financials
                    WHERE (code, report_date) IN (
                        SELECT code, MAX(report_date)
                        FROM stock_financials
                        GROUP BY code
                    )
                ) f ON s.code = f.code
                WHERE s.pe_ttm > 0 AND s.pe_ttm < 20
                  AND s.pb > 0 AND s.pb < 3
                  AND f.roe > 15
                  AND s.is_active = 1
                ORDER BY f.roe DESC
                LIMIT ?
            """, (limit,))

            rows = await cursor.fetchall()
            signals = []

            for row in rows:
                code, name, pe, pb, price, roe, net_margin, eps = row

                # 计算分数：ROE越高、PE越低，分数越高
                score = min(100, roe * 2 + (20 - pe) * 3)

                reason_parts = []
                reason_parts.append(f"PE={pe:.1f}")
                reason_parts.append(f"PB={pb:.2f}")
                reason_parts.append(f"ROE={roe:.1f}%")
                if net_margin:
                    reason_parts.append(f"净利率={net_margin:.1f}%")

                signals.append(Signal(
                    code=code,
                    name=name,
                    reason="、".join(reason_parts),
                    score=round(score, 1),
                    indicators={
                        "pe": pe,
                        "pb": pb,
                        "roe": roe,
                        "net_margin": net_margin,
                        "eps": eps,
                        "price": price,
                    },
                ))

            return signals
        finally:
            await db.close()
