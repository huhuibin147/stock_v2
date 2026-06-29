# 图谱模块设计

## 模块职责

构建和维护产业链、概念关联、个股关联的知识图谱，提供可视化数据接口。

## 参考架构

参考 aichainmap.com 的五层蛋糕架构，映射到A股领域：

```
Layer 5: AI应用层    智能驾驶 | 机器人 | SaaS | 金融科技 | AI教育
Layer 4: AI基础层    算力芯片 | 大模型 | 数据服务 | AI框架
Layer 3: 基础设施层  数据中心 | 云计算 | 通信设备 | 光模块
Layer 2: 芯片硬件层  半导体 | PCB | 被动元件 | 封装测试 | 设备
Layer 1: 能源电力层  电力设备 | 新能源 | 储能 | 特高压
```

## 图谱数据结构

### 节点类型
```python
class NodeType(str, Enum):
    STOCK = "stock"          # 个股
    CONCEPT = "concept"      # 概念
    INDUSTRY = "industry"    # 行业
    LAYER = "layer"          # 层级
    EVENT = "event"          # 事件
    PERSON = "person"        # 人物
```

### 边类型
```python
class EdgeType(str, Enum):
    BELONGS_TO = "belongs_to"        # 属于（股票→行业）
    HAS_CONCEPT = "has_concept"      # 有概念（股票→概念）
    UPSTREAM = "upstream"            # 上游（股票→股票）
    DOWNSTREAM = "downstream"        # 下游
    CO_CONCEPT = "co_concept"        # 同概念关联
    CO_INDUSTRY = "co_industry"      # 同行业关联
    MENTIONED_IN = "mentioned_in"    # 被提及（股票→资讯）
    AFFECTS = "affects"              # 影响（事件→股票）
```

## 图谱构建

### 产业链图谱
```python
class IndustryChainBuilder:
    """基于预定义数据构建产业链图谱"""

    async def build(self, layer: int | None = None) -> GraphData:
        chains = await self.load_chain_definitions()
        stocks = await self.load_stocks_with_industry()

        nodes = []
        edges = []

        for chain in chains:
            nodes.append({
                "id": f"chain_{chain.id}",
                "type": "industry",
                "name": chain.name,
                "layer": chain.layer,
            })

            for stock in chain.stocks:
                nodes.append({
                    "id": f"stock_{stock.code}",
                    "type": "stock",
                    "name": stock.name,
                    "code": stock.code,
                })
                edges.append({
                    "source": f"stock_{stock.code}",
                    "target": f"chain_{chain.id}",
                    "type": "belongs_to",
                })

        # 构建上下游关系
        for relation in chains.upstream_downstream:
            edges.append({
                "source": f"chain_{relation.upstream_id}",
                "target": f"chain_{relation.downstream_id}",
                "type": "upstream",
            })

        return GraphData(nodes=nodes, edges=edges)
```

### 概念关联图谱
```python
class ConceptNetworkBuilder:
    """基于共现关系构建概念关联网络"""

    async def build(self, days: int = 7) -> GraphData:
        # 1. 统计近N天概念共现频率
        co_occurrence = await self.calc_co_occurrence(days)

        # 2. 计算概念热度
        hot_concepts = await self.calc_hot_concepts(days)

        # 3. 构建节点和边
        nodes = [concept_to_node(c) for c in hot_concepts]
        edges = [co_to_edge(pair) for pair in co_occurrence
                 if pair.weight > threshold]

        return GraphData(nodes=nodes, edges=edges)
```

### 个股关联图谱
```python
class StockRelationBuilder:
    """以某股票为中心，展示关联网络"""

    async def build(self, stock_code: str, depth: int = 2) -> GraphData:
        center = await self.get_stock(stock_code)

        nodes = [{"id": stock_code, "type": "stock", "name": center.name, "center": True}]
        edges = []

        # 同行业股票
        industry_peers = await self.get_industry_peers(stock_code)
        for peer in industry_peers:
            nodes.append(stock_to_node(peer))
            edges.append({"source": stock_code, "target": peer.code, "type": "co_industry"})

        # 同概念股票
        concept_peers = await self.get_concept_peers(stock_code)
        for peer in concept_peers:
            nodes.append(stock_to_node(peer))
            edges.append({"source": stock_code, "target": peer.code, "type": "co_concept"})

        # 产业链上下游
        chain_relations = await self.get_chain_relations(stock_code)
        for rel in chain_relations:
            nodes.append(stock_to_node(rel.target))
            edges.append({
                "source": stock_code,
                "target": rel.target.code,
                "type": rel.direction  # upstream/downstream
            })

        # 关联概念节点
        concepts = await self.get_stock_concepts(stock_code)
        for concept in concepts:
            nodes.append({"id": f"concept_{concept}", "type": "concept", "name": concept})
            edges.append({"source": stock_code, "target": f"concept_{concept}", "type": "has_concept"})

        return GraphData(nodes=nodes, edges=edges)
```

## 前端可视化

### 技术选型
- **产业链图谱**: D3.js force-directed layout
- **概念网络**: D3.js + 自定义力导向参数
- **个股关联**: ECharts graph（快速实现）

### 可视化规范
```
节点样式:
  stock   → 圆形，大小按市值/热度
  concept → 菱形，大小按热度
  industry → 方形，大小按包含股票数
  layer   → 大圆角矩形

边样式:
  upstream/downstream → 实线箭头
  co_concept → 虚线
  co_industry → 实线

颜色方案（A股惯例）:
  利好/正面 → 红色系 (#FF4D4F)
  利空/负面 → 绿色系 (#52C41A)
  中性 → 蓝色系 (#1890FF)
  未知 → 灰色 (#999)
```

### 交互设计
- 节点hover: 显示详细信息tooltip
- 节点点击: 跳转详情页或展开子图
- 缩放拖拽: 支持画布操作
- 筛选: 按层级、行业、概念筛选
- 搜索: 节点名称搜索定位
