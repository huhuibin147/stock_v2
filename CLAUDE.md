# Stock V2 - AI开发指南

## 项目概述

以公司为核心视角的A股资讯分析系统。用户打开一家公司，看到核心定位、产业链位置、最新重要动态和AI研判。

## 技术栈

- **前端**: Vue 3 + TypeScript + Vite + ECharts（轻量，无UI框架）
- **后端**: Python 3.11+ (FastAPI)
- **数据库**: SQLite（单文件，零依赖）
- **AI/LLM**: Claude API（资讯摘要、趋势研判）
- **采集**: httpx + asyncio
- **部署**: 直接运行 `python -m app.main`

## 项目结构

```
stock_v2/
├── CLAUDE.md               # AI开发指南（本文件）
├── README.md               # 项目文档
├── docs/                   # 设计文档
│   ├── architecture.md     # 系统架构设计
│   ├── data-model.md       # 数据模型设计
│   ├── api-spec.md         # API接口规范
│   ├── dev-spec.md         # 开发规范
│   ├── mvp-scope.md        # MVP分期计划
│   └── modules/            # 模块设计文档
├── backend/
│   ├── app/
│   │   ├── api/v1/         # API路由
│   │   ├── core/           # 配置、数据库、日志
│   │   ├── models/         # ORM模型
│   │   ├── schemas/        # Pydantic模型
│   │   ├── services/       # 业务逻辑
│   │   ├── collectors/     # 采集器
│   │   ├── analyzers/      # 分析引擎
│   │   └── ai/             # AI模块（摘要+研判）
│   ├── tests/
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── components/     # 通用组件
│   │   ├── views/          # 页面（StockProfile为核心）
│   │   ├── services/       # API调用
│   │   └── stores/         # 状态管理
│   └── package.json
└── data/                   # SQLite数据库文件（自动创建，git忽略）
```

## 核心设计原则

### 产品定位：公司为核心，资讯为辅助
用户场景：**我想快速了解一家公司。**
1. 这家公司干什么（核心业务、产业链位置、上下游）
2. 最近有什么重要动态（最新几条重要资讯）
3. 整体怎么看（AI综合研判）

资讯不是主角，是为理解公司服务的。

### 存储最小化：只存重要的，只存整合后的
- 采集全量抓取用于去重，但**内存中过滤**，不落盘
- 只有通过重要度过滤的资讯才入库（日均5000→500~800条）
- **不存原始全文**，只存 title + AI摘要 + 结构化分析结果
- 过期数据定期清理（normal: 14天, long_term: 1年）

## 模块概览

| 模块 | 职责 | 设计文档 |
|------|------|----------|
| 采集 | 多源采集、重要度过滤、去重 | docs/modules/collector.md |
| 分析 | 实体识别、情感分析 | docs/modules/analyzer.md |
| AI | 资讯摘要、趋势研判 | docs/modules/ai.md |
| 图谱 | 产业链图谱、个股关联 | docs/modules/graph.md |

## 开发约定

- 新模块开发前先写设计文档（docs/modules/xxx.md）
- API开发前先定义接口文档（docs/api-spec.md）
- 数据模型变更需更新 data-model.md
- 遵循 docs/dev-spec.md 中的编码规范

## AI开发流程

1. **先读文档**: 开始任何开发前，先阅读相关设计文档
2. **更新文档**: 设计变更时同步更新文档
3. **文档驱动**: 以文档作为开发的唯一真相来源
4. **测试先行**: 关键逻辑先写测试再实现
