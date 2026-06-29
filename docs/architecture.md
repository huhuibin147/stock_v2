# 系统架构设计

## 设计原则

**MVP用最小组件跑通全链路，有真实需求后再升级。**

```
升级路径（不是一步到位，是按需升级）：

SQLite        → PostgreSQL    （数据量>10万或需要并发写入时）
内存缓存       → Redis         （多进程部署时）
SQLite FTS5   → Elasticsearch （需要复杂搜索/聚合时）
APScheduler   → Celery        （任务量大或需要分布式时）
单机运行       → Docker Compose（需要部署到服务器时）
```

## MVP架构

```
┌──────────────────────────────────┐
│       前端：Vue 3 + Vite          │
├──────────────────────────────────┤
│       FastAPI 单进程              │
│  ┌────────┬────────┬──────┬───┐  │
│  │  API   │ 采集器  │ 分析器│AI │  │
│  └────────┴────────┴──────┴───┘  │
│  ┌─────────────────────────────┐ │
│  │ APScheduler（定时采集调度）   │ │
│  └─────────────────────────────┘ │
├──────────────────────────────────┤
│           SQLite 单文件           │
│    (数据存储 + FTS5全文检索)       │
└──────────────────────────────────┘
```

**零外部依赖**：不需要安装PostgreSQL、Redis、ES，不需要Docker。`pip install` 后直接跑。

## 模块划分

### API层 (`app/api/v1/`)
- `stocks.py` — 个股搜索、全景、资讯、事件
- `news.py` — 全市场热点
- `analysis.py` — 概览、概念排行
- `ai.py` — 摘要、趋势研判
- `graph.py` — 产业链图谱

### 采集层 (`app/collectors/`)
- `base.py` — 采集器基类（去重+重要度过滤）
- `eastmoney.py` — 东方财富新闻+快讯
- `cninfo.py` — 巨潮资讯公告
- `akshare.py` — AKShare基础数据（股票列表、概念板块）

### 分析层 (`app/analyzers/`)
- `entity_extractor.py` — 实体识别（股票代码/名称词典匹配）
- `sentiment.py` — 情感分析（规则层关键词）
- `event_detector.py` — 事件检测（模板匹配）

### AI层 (`app/ai/`)
- `summarizer.py` — 资讯摘要生成（Claude API）
- `judge.py` — 趋势研判（Phase 3）
- `prompts.py` — Prompt模板管理

### 图谱层 (`app/services/`)
- `chain_service.py` — 产业链数据查询
- `graph_service.py` — 图谱构建

### 调度层 (`app/scheduler.py`)
- APScheduler 进程内调度
- 采集任务定时触发
- 数据清理定时触发

## 数据流

```
APScheduler 定时触发
    ↓
采集器(httpx抓取→内存去重→重要度过滤)
    ↓
分析器(实体识别→情感分析→事件检测)
    ↓
AI摘要(Claude API，批量生成摘要)
    ↓
写入SQLite(title+summary+entities+events+sentiment)
    ↓
用户请求 → FastAPI → 前端展示
```

## 去重方案（替代Redis布隆过滤器）

```python
# 方案：SQLite唯一索引 + 内存集合
class Deduplicator:
    def __init__(self):
        self._seen: set[str] = set()  # 启动时从DB加载已有source_id

    def is_duplicate(self, source: str, source_id: str) -> bool:
        key = f"{source}:{source_id}"
        if key in self._seen:
            return True
        self._seen.add(key)
        return False

# DB层：news表 source+source_id 建 UNIQUE索引，双重保障
```

## 缓存方案（替代Redis）

```python
# 方案：cachetools TTL缓存
from cachetools import TTLCache

stock_cache = TTLCache(maxsize=1000, ttl=3600)      # 股票信息缓存1小时
profile_cache = TTLCache(maxsize=500, ttl=300)       # 个股全景缓存5分钟
```

## 全文检索方案（替代Elasticsearch）

```sql
-- SQLite FTS5 全文检索
CREATE VIRTUAL TABLE news_fts USING fts5(
    title, summary,
    content='news',
    content_rowid='id',
    tokenize='unicode61'  -- 配合jieba分词预处理
);
```

查询时先用jieba分词，再用FTS5检索。

## 股票基础数据来源

| 数据 | 来源 | 更新频率 |
|------|------|----------|
| 股票列表 | AKShare `stock_zh_a_spot_em` | 每日 |
| 公司信息 | AKShare `stock_individual_info_em` | 季度 |
| 概念板块 | AKShare `stock_board_concept_name_em` | 每周 |
| 产业链关系 | 预定义JSON文件（手动维护） | 月度 |
| 行情数据 | AKShare `stock_zh_a_hist` | 每日收盘 |

## 技术选型

| 组件 | MVP | 升级后 |
|------|-----|--------|
| Web框架 | FastAPI | FastAPI |
| ORM | SQLModel (Pydantic+SQLAlchemy) | SQLAlchemy 2.0 |
| 数据库 | **SQLite** (单文件) | PostgreSQL |
| 缓存 | **cachetools** (进程内) | Redis |
| 全文检索 | **SQLite FTS5** | Elasticsearch |
| 任务调度 | **APScheduler** (进程内) | Celery+Redis |
| 前端 | Vue 3 + TS + Vite | Vue 3 + TS + Vite |
| CSS | 原生CSS + CSS Variables | TailwindCSS（如需） |
| 图表 | ECharts | ECharts |
| AI | Claude API | Claude API |
| NLP | jieba | jieba |
| 部署 | **直接运行** | Docker Compose |

## 启动方式

```bash
# 开发：一条命令启动全部
python -m app.main

# 这条命令同时启动：
# - FastAPI web服务 (端口8000)
# - APScheduler 定时采集任务
# - SQLite自动创建（首次运行）
```

## 升级触发条件

| 升级项 | 触发条件 |
|--------|----------|
| SQLite → PostgreSQL | 数据量>50万条 或 需要多服务并发写入 |
| 内存缓存 → Redis | 部署到多实例/多进程 |
| FTS5 → ES | 需要复杂聚合分析、语义搜索 |
| APScheduler → Celery | 采集任务量大、需要分布式重试 |
| 直接运行 → Docker | 部署到服务器 |
