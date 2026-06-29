import json
from pathlib import Path

import structlog

from app.core.database import get_db

logger = structlog.get_logger()

# 预定义产业链数据（MVP核心）
CHAINS_DATA = [
    # Layer 1: 能源电力
    {"name": "电力设备", "layer": 1, "description": "发电、输电、配电设备"},
    {"name": "新能源", "layer": 1, "description": "光伏、风电、氢能"},
    {"name": "储能", "layer": 1, "description": "电池储能、抽水蓄能"},
    {"name": "特高压", "layer": 1, "description": "特高压输电"},
    # Layer 2: 芯片硬件
    {"name": "半导体设备", "layer": 2, "description": "光刻机、刻蚀机、薄膜设备"},
    {"name": "晶圆代工", "layer": 2, "description": "芯片制造"},
    {"name": "封测", "layer": 2, "description": "封装测试"},
    {"name": "芯片设计", "layer": 2, "description": "IC设计"},
    {"name": "PCB", "layer": 2, "description": "印制电路板"},
    {"name": "被动元件", "layer": 2, "description": "电容、电阻、电感"},
    # Layer 3: 基础设施
    {"name": "数据中心", "layer": 3, "description": "IDC、服务器"},
    {"name": "云计算", "layer": 3, "description": "公有云、私有云"},
    {"name": "通信设备", "layer": 3, "description": "5G基站、光纤"},
    {"name": "光模块", "layer": 3, "description": "光通信模块"},
    # Layer 4: AI基础
    {"name": "算力芯片", "layer": 4, "description": "GPU、AI加速器"},
    {"name": "大模型", "layer": 4, "description": "基础大模型"},
    {"name": "数据服务", "layer": 4, "description": "数据标注、数据平台"},
    # Layer 5: AI应用
    {"name": "智能驾驶", "layer": 5, "description": "自动驾驶、车路协同"},
    {"name": "机器人", "layer": 5, "description": "人形机器人、工业机器人"},
    {"name": "AI SaaS", "layer": 5, "description": "企业AI应用"},
    {"name": "金融科技", "layer": 5, "description": "AI+金融"},
]

# 上下游关系
UPSTREAM_DOWNSTREAM = [
    # 能源 → 芯片
    ("电力设备", "半导体设备"), ("新能源", "数据中心"),
    # 芯片内部
    ("半导体设备", "晶圆代工"), ("晶圆代工", "封测"), ("芯片设计", "晶圆代工"),
    # 芯片 → 基础设施
    ("封测", "服务器"), ("PCB", "数据中心"), ("被动元件", "通信设备"),
    # 基础设施内部
    ("数据中心", "云计算"), ("通信设备", "光模块"),
    # 基础设施 → AI
    ("云计算", "大模型"), ("光模块", "算力芯片"), ("数据中心", "算力芯片"),
    # AI基础 → AI应用
    ("大模型", "智能驾驶"), ("大模型", "机器人"), ("大模型", "AI SaaS"),
]


async def import_chains():
    """导入产业链数据"""
    logger.info("import_chains_start")
    db = await get_db()
    try:
        # 插入产业链节点
        name_to_id: dict[str, int] = {}
        for chain in CHAINS_DATA:
            cursor = await db.execute(
                "INSERT OR IGNORE INTO industry_chains (name, layer, description) VALUES (?, ?, ?)",
                (chain["name"], chain["layer"], chain.get("description", "")),
            )
            await db.commit()
            if cursor.lastrowid:
                name_to_id[chain["name"]] = cursor.lastrowid
            else:
                # 已存在，查询id
                cursor2 = await db.execute("SELECT id FROM industry_chains WHERE name = ?", (chain["name"],))
                row = await cursor2.fetchone()
                if row:
                    name_to_id[chain["name"]] = row[0]

        # 构建上下游关系
        upstream_map: dict[str, list[int]] = {name: [] for name in name_to_id}
        downstream_map: dict[str, list[int]] = {name: [] for name in name_to_id}

        for up_name, down_name in UPSTREAM_DOWNSTREAM:
            if up_name in name_to_id and down_name in name_to_id:
                downstream_map[up_name].append(name_to_id[down_name])
                upstream_map[down_name].append(name_to_id[up_name])

        # 更新上下游
        for name, chain_id in name_to_id.items():
            await db.execute(
                "UPDATE industry_chains SET upstream_ids = ?, downstream_ids = ? WHERE id = ?",
                (
                    json.dumps(upstream_map.get(name, [])),
                    json.dumps(downstream_map.get(name, [])),
                    chain_id,
                ),
            )

        await db.commit()
        logger.info("import_chains_done", count=len(name_to_id))
    finally:
        await db.close()
