# Stock V2 - A股资讯分析系统

## 项目概述

基于资讯驱动的A股智能分析系统，参考 aichainmap.com 的图谱架构，实现资讯采集、智能分析、AI辅助决策的全链路闭环。

## 技术栈

- **前端**: React 18 + TypeScript + Ant Design + ECharts/D3.js
- **后端**: Python 3.11+ (FastAPI)
- **数据库**: PostgreSQL + Redis + Elasticsearch
- **AI/LLM**: Claude API / OpenAI API (资讯摘要、情感分析、实体提取)
- **采集框架**: Scrapy / httpx + asyncio
- **部署**: Docker Compose

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
│   └── modules/            # 模块设计文档
├── backend/                # 后端服务
│   ├── app/
│   │   ├── api/            # API路由
│   │   ├── core/           # 核心配置
│   │   ├── models/         # 数据模型
│   │   ├── services/       # 业务逻辑
│   │   ├── collectors/     # 数据采集器
│   │   ├── analyzers/      # 分析引擎
│   │   └── ai/             # AI模块
│   ├── tests/
│   └── requirements.txt
├── frontend/               # 前端应用
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   └── stores/
│   └── package.json
└── docker-compose.yml
```

## 核心设计原则

### 产品定位：公司为核心，资讯为辅助
用户的核心场景是**看一家公司**：
1. 这家公司是干什么的（核心业务、产业链位置、上下游关系）
2. 最近有什么重要动态（最新几条重要资讯和事件）
3. 整体怎么看（AI综合研判）

系统围绕**个股页面**构建，资讯不是主角，是为理解公司服务的。

### 存储最小化：只存重要的，只存整合后的
- 资讯量极大（日均数千条），但有价值的不到20%
- 采集时全量抓取用于去重和判断，但**内存中过滤**，不落盘
- 只有通过重要度过滤的资讯才入库（预估日均500~800条）
- **不存原始全文**，只存 title + AI摘要 + 结构化分析结果（实体/事件/情感）
- 每条存储约2~3KB，而非原始的10~50KB
- 过期数据定期清理（normal: 90天, long_term: 1年）

## 核心模块

### 1. 采集模块 (Collectors)
- 财经新闻采集（东方财富、同花顺、新浪财经等）
- 公告采集（巨潮资讯）
- 社交媒体采集（雪球、微博财经）
- 行情数据采集（Tushare / AKShare）

### 2. 分析模块 (Analyzers)
- 实体识别（股票、行业、人物、政策）
- 情感分析（正面/负面/中性）
- 事件分类（利好/利空/中性事件）
- 关联分析（产业链上下游影响）

### 3. AI模块
- 资讯摘要生成
- 智能问答
- 趋势分析
- 风险提示

### 4. 图谱模块
- 产业链图谱（参考aichainmap五层架构）
- 概念关联图谱
- 个股关联网络

## 开发约定

- 所有代码必须有对应的文档说明
- 新模块开发前先写设计文档（docs/modules/xxx.md）
- API开发前先定义接口文档（docs/api-spec.md）
- 数据模型变更需更新 data-model.md
- 遵循 docs/dev-spec.md 中的编码规范

## AI开发流程

1. **先读文档**: 开始任何开发前，先阅读相关设计文档
2. **更新文档**: 设计变更时同步更新文档
3. **文档驱动**: 以文档作为开发的唯一真相来源
4. **测试先行**: 关键逻辑先写测试再实现
