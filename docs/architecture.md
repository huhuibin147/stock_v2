# 系统架构设计

## 整体架构

系统采用微服务架构，分为四个核心服务，通过消息队列和API网关协调通信。

## 服务划分

### 1. Collector Service（采集服务）
- 职责：多源数据采集、去重、标准化
- 数据源：新闻网站、公告平台、社交媒体、行情接口
- 输出：标准化的资讯数据，写入消息队列
- 调度：Celery + Redis（定时任务）

### 2. Analyzer Service（分析服务）
- 职责：NLP处理、实体识别、情感分析、事件分类
- 输入：从消息队列消费原始资讯
- 处理：分词 → 实体识别 → 情感分析 → 事件提取 → 关联计算
- 输出：结构化分析结果，写入数据库

### 3. AI Service（AI服务）
- 职责：LLM驱动的高级分析
- 能力：摘要生成、智能问答、趋势分析
- 技术：Claude API / OpenAI API + RAG（检索增强生成）
- 接口：REST API + WebSocket（流式输出）

### 4. Graph Service（图谱服务）
- 职责：图谱构建、关联计算、可视化数据提供
- 数据源：分析结果 + 预定义产业链数据
- 输出：图谱JSON数据，供前端渲染

## 数据流

```
数据源 → Collector(全量采集→内存过滤→只推送重要的) → 消息队列(Redis Stream)
                                                            ↓
                                                       Analyzer(分析→生成摘要→结构化)
                                                            ↓
                                                       PostgreSQL(只存整合结果，不存原文)
                                                            ↓
                                                       AI Service ← 用户请求
                                                            ↓
                                                       Graph Service → 前端可视化
```

## 技术选型

| 组件 | 技术 | 理由 |
|------|------|------|
| Web框架 | FastAPI | 异步高性能，自动生成API文档 |
| 数据库 | PostgreSQL | JSONB支持，适合半结构化数据 |
| 缓存 | Redis | 消息队列 + 缓存 + 会话存储 |
| 搜索 | Elasticsearch | 全文搜索，资讯检索 |
| 任务队列 | Celery + Redis | 定时采集任务调度 |
| 前端 | React 18 + TS | 组件化，类型安全 |
| UI库 | Ant Design | 企业级组件，表格/图表丰富 |
| 图表 | ECharts + D3.js | ECharts做常规图表，D3做图谱 |
| AI | Claude API | 长文本理解，中文能力强 |
| NLP | jieba + transformers | 分词 + 预训练模型 |
| 容器化 | Docker Compose | 一键部署，环境一致 |

## 部署架构

```
                    Nginx (反向代理)
                   /              \
            前端静态资源          API服务
                                 /    \
                           FastAPI   WebSocket
                              |
                    ┌─────────┼─────────┐
                 PostgreSQL  Redis   Elasticsearch
```

## 安全设计

- API认证：JWT Token
- 数据源采集：遵守robots.txt，合理频率
- 敏感信息：环境变量管理，不入代码库
- 输入校验：Pydantic模型校验
