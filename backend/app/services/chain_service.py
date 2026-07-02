import json
import structlog

from app.core.database import get_db

logger = structlog.get_logger()

LAYER_NAMES = {1: "能源电力", 2: "芯片硬件", 3: "基础设施", 4: "AI基础", 5: "AI应用"}


async def get_industry_chain(layer: int | None = None, stock_code: str | None = None) -> dict:
    """获取产业链图谱数据"""
    db = await get_db()
    try:
        nodes = []
        edges = []

        if stock_code:
            # 以某股票为中心展开
            cursor = await db.execute(
                "SELECT code, name, chain_id FROM stocks WHERE code = ?", (stock_code,)
            )
            stock_row = await cursor.fetchone()
            if not stock_row:
                return {"nodes": [], "edges": []}

            nodes.append({"id": f"stock_{stock_row[0]}", "type": "stock", "name": stock_row[1], "center": True})

            if stock_row[2]:
                chain = await _get_chain_node(db, stock_row[2])
                if chain:
                    nodes.append(chain)
                    edges.append({"source": f"stock_{stock_row[0]}", "target": f"chain_{chain['id']}", "type": "belongs_to"})

                    # 上下游
                    for up_id in json.loads(chain.get("upstream_ids", "[]") or "[]"):
                        up_node = await _get_chain_node(db, up_id)
                        if up_node:
                            nodes.append(up_node)
                            edges.append({"source": f"chain_{up_id}", "target": f"chain_{chain['id']}", "type": "upstream"})

                    for down_id in json.loads(chain.get("downstream_ids", "[]") or "[]"):
                        down_node = await _get_chain_node(db, down_id)
                        if down_node:
                            nodes.append(down_node)
                            edges.append({"source": f"chain_{chain['id']}", "target": f"chain_{down_id}", "type": "downstream"})
        else:
            # 返回全部或某层级 - 按名称去重，保留 stock_count 最多的
            where = "WHERE c.layer = ?" if layer else ""
            params = (layer,) if layer else ()
            cursor = await db.execute(
                f"""SELECT c.id, c.name, c.layer, c.upstream_ids, c.downstream_ids, COUNT(s.code) as stock_count
                    FROM industry_chains c
                    LEFT JOIN stocks s ON s.chain_id = c.id AND s.is_active = 1
                    {where}
                    GROUP BY c.id
                    ORDER BY c.layer, c.name""",
                params,
            )
            rows = await cursor.fetchall()

            # 按名称去重，保留 stock_count 最多的
            name_map: dict[str, dict] = {}
            for r in rows:
                name = r[1]
                stock_count = r[5]
                if name not in name_map or stock_count > name_map[name]["stock_count"]:
                    name_map[name] = {
                        "id": r[0],
                        "name": name,
                        "layer": r[2],
                        "upstream_ids": r[3],
                        "downstream_ids": r[4],
                        "stock_count": stock_count,
                    }

            # 构建去重后的节点和边
            for item in name_map.values():
                nodes.append({
                    "id": f"chain_{item['id']}",
                    "type": "industry",
                    "name": item["name"],
                    "layer": item["layer"],
                    "stock_count": item["stock_count"],
                })
                for up_id in json.loads(item["upstream_ids"]) if item["upstream_ids"] else []:
                    edges.append({"source": f"chain_{up_id}", "target": f"chain_{item['id']}", "type": "upstream"})
                for down_id in json.loads(item["downstream_ids"]) if item["downstream_ids"] else []:
                    edges.append({"source": f"chain_{item['id']}", "target": f"chain_{down_id}", "type": "downstream"})

        return {"nodes": nodes, "edges": edges}
    finally:
        await db.close()


async def _get_chain_node(db, chain_id: int) -> dict | None:
    cursor = await db.execute(
        "SELECT id, name, layer, upstream_ids, downstream_ids FROM industry_chains WHERE id = ?", (chain_id,)
    )
    r = await cursor.fetchone()
    if not r:
        return None
    return {
        "id": f"chain_{r[0]}",
        "type": "industry",
        "name": r[1],
        "layer": r[2],
        "upstream_ids": r[3],
        "downstream_ids": r[4],
    }


async def get_chain_stocks(chain_id: int) -> dict:
    """获取某个产业链下的公司列表"""
    db = await get_db()
    try:
        # 获取产业链信息
        cursor = await db.execute(
            "SELECT id, name, layer FROM industry_chains WHERE id = ?", (chain_id,)
        )
        chain_row = await cursor.fetchone()
        if not chain_row:
            return {"chain": None, "stocks": []}

        # 获取该产业链下的公司
        cursor = await db.execute(
            """SELECT code, name, market, industry, core_business,
                      pe_ttm, pb, market_cap, turnover_amount, last_price, pct_change
               FROM stocks
               WHERE chain_id = ? AND is_active = 1
               ORDER BY turnover_amount DESC NULLS LAST""",
            (chain_id,),
        )
        rows = await cursor.fetchall()

        stocks = []
        for r in rows:
            stocks.append({
                "code": r[0],
                "name": r[1],
                "market": r[2],
                "industry": r[3],
                "core_business": r[4],
                "pe_ttm": r[5],
                "pb": r[6],
                "market_cap": r[7],
                "turnover_amount": r[8],
                "last_price": r[9],
                "pct_change": r[10],
            })

        return {
            "chain": {
                "id": chain_row[0],
                "name": chain_row[1],
                "layer": chain_row[2],
            },
            "stocks": stocks,
        }
    finally:
        await db.close()
