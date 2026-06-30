import structlog

from app.core.database import get_db

logger = structlog.get_logger()

# industry → chain_name 关键词映射
INDUSTRY_CHAIN_MAP = [
    # Layer 1: 能源电力
    ("电力设备", ["电力", "电气", "电网", "输变电", "配电"]),
    ("新能源", ["新能源", "光伏", "风电", "太阳能", "氢能", "风力发电"]),
    ("储能", ["储能", "电池", "锂电"]),
    ("特高压", ["特高压", "高压"]),
    # Layer 2: 芯片硬件
    ("半导体设备", ["半导体"]),
    ("晶圆代工", ["晶圆", "芯片制造"]),
    ("封测", ["封测", "封装"]),
    ("芯片设计", ["集成电路", "IC设计", "芯片设计"]),
    ("PCB", ["PCB", "印制电路", "电路板"]),
    ("被动元件", ["电容", "电阻", "电感", "被动元件", "电子元件"]),
    # Layer 3: 基础设施
    ("数据中心", ["数据中心", "IDC", "服务器", "算力"]),
    ("云计算", ["云计算", "云服务", "云平台"]),
    ("通信设备", ["通信", "5G", "光纤", "基站", "光通信"]),
    ("光模块", ["光模块", "光器件"]),
    # Layer 4: AI基础
    ("算力芯片", ["GPU", "AI芯片", "算力芯片", "智能芯片"]),
    ("大模型", ["大模型", "人工智能", "AI"]),
    ("数据服务", ["数据服务", "数据标注", "数据平台"]),
    # Layer 5: AI应用
    ("智能驾驶", ["智能驾驶", "自动驾驶", "车联网", "汽车电子"]),
    ("机器人", ["机器人", "工业自动化", "自动化设备"]),
    ("AI SaaS", ["软件", "SaaS", "企业服务"]),
    ("金融科技", ["金融科技", "金融IT", "银行IT", "证券IT"]),
]

# core_business 关键词补充（优先级高于 industry）
BUSINESS_KEYWORDS = {
    "储能": ["储能", "锂电池", "电池"],
    "新能源": ["光伏", "风电", "太阳能", "新能源"],
    "半导体设备": ["半导体设备", "光刻", "刻蚀"],
    "晶圆代工": ["晶圆代工", "芯片制造"],
    "芯片设计": ["芯片设计", "集成电路设计", "IC设计"],
    "PCB": ["PCB", "印制电路板"],
    "被动元件": ["电容", "电阻", "电感"],
    "数据中心": ["数据中心", "IDC", "服务器"],
    "云计算": ["云计算", "云服务"],
    "通信设备": ["通信设备", "5G", "光纤", "光通信"],
    "算力芯片": ["GPU", "AI芯片", "算力"],
    "大模型": ["大模型", "人工智能", "AI"],
    "智能驾驶": ["自动驾驶", "智能驾驶", "车联网"],
    "机器人": ["机器人", "工业机器人"],
    "金融科技": ["金融科技", "金融IT"],
    "电力设备": ["电力设备", "输变电", "变压器"],
    "特高压": ["特高压"],
}


async def map_stocks_to_chains():
    """将股票映射到产业链节点"""
    logger.info("map_chains_start")

    db = await get_db()
    try:
        # 获取 chain name → id 映射
        cursor = await db.execute("SELECT id, name FROM industry_chains")
        chain_map = {}
        for r in await cursor.fetchall():
            chain_map[r[1]] = r[0]

        # 获取所有活跃股票
        cursor = await db.execute(
            "SELECT code, name, industry, core_business FROM stocks WHERE is_active = 1"
        )
        stocks = await cursor.fetchall()

        mapped = 0
        unmapped = 0

        for code, name, industry, business in stocks:
            chain_id = None
            chain_name = None

            # 1. 先用 core_business 关键词匹配（更精确）
            if business:
                for c_name, keywords in BUSINESS_KEYWORDS.items():
                    if any(kw in business for kw in keywords):
                        chain_name = c_name
                        break

            # 2. 再用 industry 匹配
            if not chain_name and industry:
                for c_name, keywords in INDUSTRY_CHAIN_MAP:
                    if any(kw in industry for kw in keywords):
                        chain_name = c_name
                        break

            # 3. 用股票名称兜底（包含行业关键词）
            if not chain_name:
                for c_name, keywords in INDUSTRY_CHAIN_MAP:
                    if any(kw in name for kw in keywords):
                        chain_name = c_name
                        break

            if chain_name and chain_name in chain_map:
                chain_id = chain_map[chain_name]
                await db.execute(
                    "UPDATE stocks SET chain_id = ?, updated_at = datetime('now') WHERE code = ?",
                    (chain_id, code),
                )
                mapped += 1
            else:
                unmapped += 1

        await db.commit()
        logger.info("map_chains_done", mapped=mapped, unmapped=unmapped, total=len(stocks))
    finally:
        await db.close()
