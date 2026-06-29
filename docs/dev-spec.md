# 开发规范

## 总则

1. **文档先行**: 开发前先完成设计文档
2. **文档同步**: 代码变更同步更新文档
3. **单一真相**: 文档是设计的唯一真相来源

---

## Python 后端

### 代码风格
- PEP 8 + type hints
- Pydantic 做数据校验
- 字符串用双引号 `"`

### 命名
```
模块名:     snake_case (collector_eastmoney.py)
类名:       PascalCase (EastMoneyCollector)
函数名:     snake_case (fetch_news_list)
常量:       UPPER_SNAKE_CASE (MAX_RETRY_COUNT)
```

### 项目结构
```
app/
├── api/v1/
│   ├── stocks.py        # 个股搜索、全景、资讯、事件
│   ├── news.py          # 全市场热点
│   ├── analysis.py      # 概览、概念排行
│   ├── ai.py            # 摘要、研判
│   └── graph.py         # 产业链图谱
├── core/
│   ├── config.py        # pydantic-settings 配置
│   ├── database.py      # SQLAlchemy async session
│   └── logging.py       # structlog
├── models/              # SQLAlchemy ORM
│   ├── stock.py
│   ├── news.py
│   ├── event.py
│   └── chain.py
├── schemas/             # Pydantic 请求/响应
│   ├── stock.py
│   ├── news.py
│   └── common.py
├── services/            # 业务逻辑
│   ├── stock_service.py
│   ├── news_service.py
│   ├── chain_service.py
│   └── graph_service.py
├── collectors/          # 采集器
│   ├── base.py          # 基类（去重+重要度过滤）
│   ├── eastmoney.py
│   └── cninfo.py
├── analyzers/           # NLP分析
│   ├── entity_extractor.py
│   ├── sentiment.py
│   └── event_detector.py
├── ai/                  # LLM调用
│   ├── summarizer.py
│   ├── judge.py
│   └── prompts.py
├── scheduler.py           # APScheduler定时任务
└── main.py
```

### API规范
- RESTful，版本前缀 `/api/v1/`
- 分页: `page`(从1), `page_size`(默认20, 最大100)
- 响应: `{"code": 0, "message": "success", "data": {...}}`

### 数据库规范
- 表名复数: `news`, `stocks`, `events`
- 主键: `id INTEGER PRIMARY KEY AUTOINCREMENT`
- 时间: `TEXT` 存ISO8601，`created_at`, `updated_at`
- JSON字段用于半结构化数据（SQLite存储为TEXT，用json()函数查询）

### 测试
- `tests/test_<module>.py`
- pytest + pytest-asyncio
- 采集器用 respx mock
- 核心逻辑覆盖率 > 80%

---

## TypeScript 前端（Vue 3 轻量方案）

### 技术选型
- **Vue 3** + Composition API（比React轻，生态成熟）
- **Vite** 构建（快）
- **原生CSS** + CSS Variables（不用Ant Design/Tailwind，按需写样式）
- **ECharts** 图表（按需引入，不用全量打包）
- **axios** HTTP请求

包体目标：< 100KB gzipped（Vue ~30KB + ECharts按需 ~50KB）

### 代码风格
- ESLint + Prettier
- `<script setup>` 语法
- 命名: 组件 PascalCase，函数 camelCase，CSS kebab-case

### 页面结构
```
src/
├── views/
│   ├── Home.vue           # 首页：搜索框 + 市场概览
│   ├── StockProfile.vue   # 核心：个股全景
│   └── Graph.vue          # 产业链图谱（Phase 3）
├── components/
│   ├── StockCard.vue      # 股票信息卡片
│   ├── NewsList.vue       # 资讯列表
│   ├── EventTimeline.vue  # 事件时间线
│   └── SentimentBadge.vue # 情感标签
├── composables/           # 组合函数（替代store）
│   ├── useStock.ts
│   └── useNews.ts
├── api/
│   ├── request.ts         # axios 封装
│   └── stock.ts           # 个股API
├── types/
│   └── index.ts
├── styles/
│   └── global.css         # 全局样式 + CSS变量
├── App.vue
└── main.ts
```

---

## Git规范

### Commit
```
<type>(<scope>): <subject>

feat(collector): 新增东方财富采集器
fix(analyzer): 修复实体识别空指针
docs(api): 更新个股全景接口文档
```

### 分支
```
main ← 生产
├── develop ← 开发
│   ├── feature/xxx
│   └── fix/xxx
```

---

## 环境变量

```bash
DATABASE_URL=sqlite+aiosqlite:///./data/stock_v2.db
ANTHROPIC_API_KEY=sk-xxx
# AKShare 免费，无需token
```

使用 `pydantic-settings` 管理，敏感信息只通过环境变量注入。
