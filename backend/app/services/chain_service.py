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
            # 返回全部或某层级
            where = "WHERE c.layer = ?" if layer else ""
            params = (layer,) if layer else ()
            cursor = await db.execute(
                f"""SELECT c.id, c.name, c.layer, c.upstream_ids, c.downstream_ids, COUNT(s.code)
                    FROM industry_chains c
                    LEFT JOIN stocks s ON s.chain_id = c.id AND s.is_active = 1
                    {where}
                    GROUP BY c.id
                    ORDER BY c.layer, c.name""",
                params,
            )
            rows = await cursor.fetchall()

            for r in rows:
                nodes.append({"id": f"chain_{r[0]}", "type": "industry", "name": r[1], "layer": r[2], "stock_count": r[5]})
                for up_id in json.loads(r[3]) if r[3] else []:
                    edges.append({"source": f"chain_{up_id}", "target": f"chain_{r[0]}", "type": "upstream"})
                for down_id in json.loads(r[4]) if r[4] else []:
                    edges.append({"source": f"chain_{r[0]}", "target": f"chain_{down_id}", "type": "downstream"})

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
