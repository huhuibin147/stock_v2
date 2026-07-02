"""产业链重新映射 - 基于AI产业链五层架构（简化版）"""

import structlog
from app.core.database import get_db

logger = structlog.get_logger()

# 基于 aichainmap.com 的五层架构分类
# 使用更精确的匹配规则

# 核心业务关键词到产业链的映射（更精确）
BUSINESS_CHAIN_MAP = {
    # Layer 1: 能源与电力
    "电力设备": {
        "keywords": ["电力设备", "电气设备", "电网设备", "输变电设备", "配电设备", "特高压设备", "智能电网设备"],
        "layer": 1
    },
    "新能源": {
        "keywords": ["光伏", "风电", "太阳能", "风力发电", "新能源发电", "清洁能源发电"],
        "layer": 1
    },
    "储能": {
        "keywords": ["储能系统", "储能电池", "储能设备", "抽水蓄能", "液流电池"],
        "layer": 1
    },
    "核电": {
        "keywords": ["核电", "核能", "核电站"],
        "layer": 1
    },
    "水电": {
        "keywords": ["水电", "水力发电", "水电站"],
        "layer": 1
    },
    "火电": {
        "keywords": ["火电", "燃煤发电", "燃气发电", "热电联产"],
        "layer": 1
    },

    # Layer 2: 芯片系统
    "GPU/AI芯片": {
        "keywords": ["GPU芯片", "AI芯片", "算力芯片", "智能芯片", "NPU芯片", "TPU芯片", "AI加速器芯片"],
        "layer": 2
    },
    "CPU": {
        "keywords": ["CPU芯片", "中央处理器", "x86处理器", "ARM处理器"],
        "layer": 2
    },
    "存储芯片": {
        "keywords": ["存储芯片", "内存芯片", "DRAM芯片", "NAND芯片", "HBM芯片"],
        "layer": 2
    },
    "芯片设计": {
        "keywords": ["芯片设计", "IC设计", "集成电路设计", "EDA工具", "IP核授权"],
        "layer": 2
    },
    "芯片制造": {
        "keywords": ["晶圆代工", "芯片制造", "半导体制造", "Foundry服务"],
        "layer": 2
    },
    "封装测试": {
        "keywords": ["芯片封装", "封装测试", "半导体封测", "IC封装"],
        "layer": 2
    },
    "半导体设备": {
        "keywords": ["半导体设备", "光刻机设备", "刻蚀设备", "薄膜设备", "清洗设备", "CVD设备", "PVD设备"],
        "layer": 2
    },
    "半导体材料": {
        "keywords": ["硅片材料", "光刻胶材料", "CMP材料", "靶材", "电子气体", "半导体材料"],
        "layer": 2
    },
    "PCB/被动元件": {
        "keywords": ["PCB板", "印制电路板", "被动元件", "电容器", "电阻器", "电感器"],
        "layer": 2
    },
    "连接器/线缆": {
        "keywords": ["连接器", "线缆组件", "电缆", "射频线缆", "光纤线缆"],
        "layer": 2
    },

    # Layer 3: AI基础设施
    "光模块": {
        "keywords": ["光模块", "光器件", "光收发器", "光通信模块", "CPO模块", "光互连", "光引擎", "收发模块", "光收发模块", "光通信器件"],
        "layer": 3
    },
    "云计算": {
        "keywords": ["云计算服务", "云服务平台", "IaaS服务", "PaaS服务", "SaaS服务", "云服务"],
        "layer": 3
    },
    "数据中心": {
        "keywords": ["数据中心", "IDC服务", "算力中心", "智算中心", "数据机房"],
        "layer": 3
    },
    "网络设备": {
        "keywords": ["交换机设备", "路由器设备", "网络设备", "网络通信设备"],
        "layer": 3
    },
    "通信设备": {
        "keywords": ["通信设备制造", "通信系统集成", "通信终端设备", "基站设备制造", "天线设备制造", "射频设备制造", "通信设备研发"],
        "layer": 3
    },
    "液冷/散热": {
        "keywords": ["液冷系统", "散热系统", "温控系统", "热管理系统", "冷却设备"],
        "layer": 3
    },
    "服务器": {
        "keywords": ["服务器设备", "AI服务器", "计算服务器", "存储服务器"],
        "layer": 3
    },
    "存储设备": {
        "keywords": ["存储设备", "磁盘阵列", "NAS设备", "SAN设备", "存储系统"],
        "layer": 3
    },

    # Layer 4: AI基础模型
    "大模型": {
        "keywords": ["大语言模型", "基础大模型", "通用大模型", "预训练大模型"],
        "layer": 4
    },
    "多模态模型": {
        "keywords": ["多模态大模型", "视觉大模型", "图像大模型", "视频大模型"],
        "layer": 4
    },
    "AI框架": {
        "keywords": ["深度学习框架", "AI开发框架", "AI训练框架"],
        "layer": 4
    },
    "AI工具链": {
        "keywords": ["MLOps平台", "AI开发工具", "AI训练平台", "AI推理平台"],
        "layer": 4
    },
    "数据服务": {
        "keywords": ["数据标注服务", "数据清洗服务", "数据服务", "训练数据服务", "数据管理平台"],
        "layer": 4
    },

    # Layer 5: AI应用
    "AI SaaS": {
        "keywords": ["AI SaaS服务", "企业AI服务", "AI办公服务", "AI协作服务"],
        "layer": 5
    },
    "智能驾驶": {
        "keywords": ["智能驾驶系统", "自动驾驶系统", "车联网系统", "ADAS系统", "无人驾驶技术"],
        "layer": 5
    },
    "机器人": {
        "keywords": ["人形机器人", "工业机器人", "服务机器人", "协作机器人", "机器人系统"],
        "layer": 5
    },
    "AI+医疗": {
        "keywords": ["AI医疗系统", "医疗AI系统", "AI制药技术", "AI诊断系统"],
        "layer": 5
    },
    "AI+金融": {
        "keywords": ["AI金融系统", "金融AI系统", "智能投顾系统", "AI风控系统"],
        "layer": 5
    },
    "AI+教育": {
        "keywords": ["AI教育系统", "教育AI系统", "智能教育平台"],
        "layer": 5
    },
    "AI+安全": {
        "keywords": ["AI安全系统", "安全AI系统", "智能安防系统"],
        "layer": 5
    },
    "AI+游戏": {
        "keywords": ["AI游戏引擎", "游戏AI系统", "AIGC游戏"],
        "layer": 5
    },
    "AI+营销": {
        "keywords": ["AI营销系统", "数字营销平台", "AI广告系统"],
        "layer": 5
    },
    "AI Agent": {
        "keywords": ["AI Agent系统", "智能体系统", "AI助手系统"],
        "layer": 5
    },
    "具身智能": {
        "keywords": ["具身智能系统", "具身AI系统"],
        "layer": 5
    }
}

# 特殊公司映射（手动修正）
SPECIAL_COMPANY_MAP = {
    "300394": {"chain": "光模块", "layer": 3, "reason": "光器件和CPO"},
    "002281": {"chain": "光模块", "layer": 3, "reason": "光通信器件"},
    "300308": {"chain": "光模块", "layer": 3, "reason": "光通信收发模块"},
    "300502": {"chain": "光模块", "layer": 3, "reason": "光模块研发生产"},
    "300548": {"chain": "光模块", "layer": 3, "reason": "光通信器件"},
    "300557": {"chain": "光模块", "layer": 3, "reason": "光纤传感器"},
    "300620": {"chain": "光模块", "layer": 3, "reason": "光纤器件"},
    "300747": {"chain": "光模块", "layer": 3, "reason": "光纤激光器"},
    "301205": {"chain": "光模块", "layer": 3, "reason": "光通信收发模块"},
}


def match_chain_by_business(name: str, industry: str, core_business: str) -> tuple[str, int] | None:
    """根据核心业务匹配产业链分类"""
    if not core_business:
        return None

    # 只使用核心业务描述进行匹配，不使用行业分类
    text = f"{name} {core_business}".lower()

    # 特殊公司映射检查
    for code, mapping in SPECIAL_COMPANY_MAP.items():
        if code in text:
            return mapping["chain"], mapping["layer"]

    # 按关键词长度排序，优先匹配更具体的关键词
    matches = []

    for chain_name, config in BUSINESS_CHAIN_MAP.items():
        keywords = config["keywords"]

        # 检查关键词匹配
        for keyword in keywords:
            if keyword.lower() in text:
                # 计算匹配分数（关键词长度越长，分数越高）
                score = len(keyword)
                layer = config.get("layer", 0)
                matches.append((chain_name, score, layer))

    if not matches:
        return None

    # 选择分数最高的匹配
    matches.sort(key=lambda x: x[1], reverse=True)
    best_match = matches[0]

    return best_match[0], best_match[2]


# 概念到产业链的映射
CONCEPT_CHAIN_MAP = {
    # Layer 1: 能源与电力
    "电力设备": ["特高压", "智能电网", "电力设备", "电网设备", "输变电设备"],
    "新能源": ["光伏", "风电", "太阳能", "新能源", "清洁能源", "绿色电力"],
    "储能": ["储能", "锂电池", "钠电池", "液流电池", "储能系统"],
    "核电": ["核电", "核能"],
    "水电": ["水电", "水力发电"],
    "火电": ["火电", "燃煤发电", "燃气发电"],

    # Layer 2: 芯片系统
    "GPU/AI芯片": ["GPU", "AI芯片", "算力芯片", "智能芯片", "NPU", "TPU"],
    "CPU": ["CPU", "处理器"],
    "存储芯片": ["存储芯片", "内存", "DRAM", "NAND", "HBM"],
    "芯片设计": ["芯片设计", "IC设计", "集成电路设计", "EDA"],
    "芯片制造": ["晶圆", "代工", "芯片制造", "半导体制造"],
    "封装测试": ["封测", "封装测试", "芯片封装"],
    "半导体设备": ["半导体设备", "光刻机", "刻蚀", "薄膜", "清洗"],
    "半导体材料": ["硅片", "光刻胶", "CMP", "靶材", "电子气体"],
    "PCB/被动元件": ["PCB", "印制电路", "被动元件", "电容", "电阻", "电感"],
    "连接器/线缆": ["连接器", "线缆", "电缆", "射频"],

    # Layer 3: AI基础设施
    "光模块": ["光模块", "光器件", "光通信模块", "光收发模块", "光互连", "光引擎"],
    "云计算": ["云计算", "云服务", "云平台", "IaaS", "PaaS", "SaaS"],
    "数据中心": ["数据中心", "IDC", "算力中心", "智算中心"],
    "网络设备": ["交换机", "路由器", "网络设备", "通信设备"],
    "液冷/散热": ["液冷", "散热", "温控", "热管理"],
    "服务器": ["服务器", "AI服务器"],
    "存储设备": ["存储设备", "磁盘阵列", "NAS", "SAN"],

    # Layer 4: AI基础模型
    "大模型": ["大模型", "LLM", "语言模型", "基础模型", "通用大模型"],
    "多模态模型": ["多模态", "视觉模型", "图像模型", "视频模型"],
    "AI框架": ["深度学习框架", "AI框架", "PyTorch", "TensorFlow"],
    "AI工具链": ["MLOps", "模型训练", "模型推理", "AI开发工具"],
    "数据服务": ["数据标注", "数据清洗", "数据服务", "训练数据"],

    # Layer 5: AI应用
    "AI SaaS": ["AI SaaS", "企业AI", "AI办公", "AI协作"],
    "智能驾驶": ["智能驾驶", "自动驾驶", "车联网", "ADAS", "无人驾驶"],
    "机器人": ["机器人", "人形机器人", "工业机器人", "服务机器人"],
    "AI+医疗": ["AI医疗", "医疗AI", "AI制药", "AI诊断"],
    "AI+金融": ["AI金融", "金融AI", "智能投顾", "AI风控"],
    "AI+教育": ["AI教育", "教育AI", "智能教育"],
    "AI+安全": ["AI安全", "安全AI", "智能安防"],
    "AI+游戏": ["AI游戏", "游戏AI", "AIGC游戏"],
    "AI+营销": ["AI营销", "数字营销", "AI广告"],
    "AI Agent": ["AI Agent", "智能体", "AI助手"],
    "具身智能": ["具身智能", "具身AI"],
}


def match_chain_by_concepts(concepts: list[str]) -> tuple[str, int] | None:
    """根据概念匹配产业链分类"""
    if not concepts:
        return None

    # 合并所有概念为一个文本
    text = " ".join(concepts).lower()

    # 按关键词长度排序，优先匹配更具体的关键词
    matches = []

    for chain_name, keywords in CONCEPT_CHAIN_MAP.items():
        for keyword in keywords:
            if keyword.lower() in text:
                # 计算匹配分数（关键词长度越长，分数越高）
                score = len(keyword)

                # 获取层级
                layer = 0
                if chain_name in BUSINESS_CHAIN_MAP:
                    layer = BUSINESS_CHAIN_MAP[chain_name].get("layer", 0)

                matches.append((chain_name, score, layer))

    if not matches:
        return None

    # 选择分数最高的匹配
    matches.sort(key=lambda x: x[1], reverse=True)
    best_match = matches[0]

    return best_match[0], best_match[2]


async def remap_stock_chains():
    """重新映射股票到产业链分类"""
    db = await get_db()
    try:
        # 获取所有活跃股票
        cursor = await db.execute(
            "SELECT code, name, industry, core_business FROM stocks WHERE is_active = 1"
        )
        stocks = await cursor.fetchall()

        # 创建新的产业链分类
        all_chains = set()
        for chain_name, config in BUSINESS_CHAIN_MAP.items():
            layer = config.get("layer", 0)
            if layer:
                all_chains.add((chain_name, layer))

        for chain_name, layer in all_chains:
            await db.execute(
                "INSERT OR IGNORE INTO industry_chains (name, layer) VALUES (?, ?)",
                (chain_name, layer)
            )

        await db.commit()

        # 获取产业链ID映射
        cursor = await db.execute("SELECT id, name FROM industry_chains")
        rows = await cursor.fetchall()
        chain_id_map = {name: id for id, name in rows}

        # 获取股票的概念数据
        cursor = await db.execute("""
            SELECT sc.stock_code, GROUP_CONCAT(sc.concept_name) as concepts
            FROM stock_concepts sc
            GROUP BY sc.stock_code
        """)
        concept_data = {}
        for code, concepts_str in await cursor.fetchall():
            if concepts_str:
                concept_data[code] = concepts_str.split(",")

        # 重新映射股票
        updated = 0
        unmapped = []
        cleared = 0

        for code, name, industry, core_business in stocks:
            # 优先匹配核心业务
            match = match_chain_by_business(name, industry or "", core_business or "")

            # 如果没有匹配到，尝试匹配概念
            if not match and code in concept_data:
                match = match_chain_by_concepts(concept_data[code])

            if match:
                chain_name, layer = match
                if chain_name in chain_id_map:
                    chain_id = chain_id_map[chain_name]
                    await db.execute(
                        "UPDATE stocks SET chain_id = ? WHERE code = ?",
                        (chain_id, code)
                    )
                    updated += 1
            else:
                # 没有匹配到，清除旧的 chain_id
                await db.execute(
                    "UPDATE stocks SET chain_id = NULL WHERE code = ?",
                    (code,)
                )
                cleared += 1
                unmapped.append(f"{code} {name}")

        await db.commit()
        logger.info("remap_stock_chains_done", updated=updated, total=len(stocks), unmapped=len(unmapped), cleared=cleared)

        # 记录未映射的股票
        if unmapped:
            logger.warning("unmapped_stocks", count=len(unmapped), samples=unmapped[:10])

    finally:
        await db.close()


async def cleanup_empty_chains():
    """清理没有公司关联的产业链分类"""
    db = await get_db()
    try:
        # 删除没有公司关联的产业链
        cursor = await db.execute(
            """DELETE FROM industry_chains
               WHERE id NOT IN (SELECT DISTINCT chain_id FROM stocks WHERE chain_id IS NOT NULL)"""
        )
        deleted = cursor.rowcount
        await db.commit()
        logger.info("cleanup_empty_chains_done", deleted=deleted)
    finally:
        await db.close()


async def run_remap():
    """执行产业链重新映射"""
    logger.info("remap_chains_start")
    await remap_stock_chains()
    await cleanup_empty_chains()
    logger.info("remap_chains_done")
