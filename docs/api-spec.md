# API接口规范

## 基础约定

- 基础路径: `/api/v1`
- 认证: Bearer Token (JWT)
- Content-Type: `application/json`
- 时间格式: ISO 8601 (`2026-06-29T10:00:00+08:00`)

## 通用响应

```json
// 成功
{ "code": 0, "message": "success", "data": { ... } }

// 分页
{
  "code": 0,
  "message": "success",
  "data": {
    "items": [...],
    "total": 100,
    "page": 1,
    "page_size": 20
  }
}

// 错误
{ "code": 40001, "message": "错误描述", "data": null }
```

---

## 个股接口（核心页面）

### GET /stocks/:code/profile
个股全景（核心接口，一次返回公司全貌）

**Response:**
```json
{
  "code": 0,
  "data": {
    "stock": {
      "code": "688981",
      "name": "中芯国际",
      "market": "SH",
      "industry": "半导体",
      "concepts": ["芯片", "国产替代", "先进制程"],
      "description": "公司核心业务描述..."
    },
    "chain_position": {
      "layer": 2,
      "layer_name": "芯片硬件层",
      "sub_industry": "晶圆代工",
      "upstream": [{"code": "688012", "name": "中微公司", "relation": "设备供应商"}],
      "downstream": [{"code": "002049", "name": "紫光国微", "relation": "芯片设计客户"}]
    },
    "recent_news": [
      {
        "id": 123,
        "title": "中芯国际Q2营收超预期...",
        "summary": "AI生成的一句话摘要",
        "sentiment": 1,
        "published_at": "2026-06-28T10:00:00+08:00"
      }
    ],
    "recent_events": [
      {
        "event_type": "performance",
        "title": "2026年半年度业绩预增",
        "impact": 1,
        "event_date": "2026-06-25"
      }
    ],
    "sentiment_summary": {
      "recent_7d": { "positive": 5, "neutral": 3, "negative": 1 },
      "trend": "偏多"
    }
  }
}
```

### GET /stocks/list
股票列表（搜索和筛选）

### GET /stocks/:code/news
个股关联资讯（分页，默认按重要度+时间排序，只返回重要资讯）

**参数:**
| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| page | int | 否 | 页码，默认1 |
| page_size | int | 否 | 每页条数，默认10（个股页不需要太多） |
| sentiment | int | 否 | 情感筛选：-1/0/1 |

### GET /stocks/:code/events
个股关联事件时间线

---

## 资讯接口（辅助）

### GET /news/hot
今日全市场热点（按重要度排序，默认返回前20条）

### GET /news/:id
资讯详情

---

## 全局分析接口

### GET /analysis/overview
全市场概览（今日热点板块、重大事件、情感分布）

### GET /analysis/concepts
概念热度排行

---

## AI接口

### POST /ai/summarize
资讯摘要生成

```json
// Request
{ "news_id": 123 }
// 或
{ "content": "长文本内容..." }

// Response
{
  "code": 0,
  "data": {
    "summary": "摘要文本...",
    "key_points": ["要点1", "要点2"],
    "sentiment": "利好",
    "related_stocks": ["000001", "600519"]
  }
}
```

### POST /ai/ask
智能问答（流式响应）

```json
// Request
{
  "question": "最近半导体行业有什么利好消息？",
  "context": { "stock_code": "002049" }  // 可选上下文
}

// Response (SSE stream)
data: {"type": "text", "content": "根据最近的资讯分析..."}
data: {"type": "sources", "items": [...]}
data: {"type": "done"}
```

### POST /ai/analyze
综合趋势分析

```json
// Request
{ "target": "半导体行业", "period": "1w" }

// Response
{
  "code": 0,
  "data": {
    "trend": "偏多",
    "confidence": 0.75,
    "analysis": "详细分析文本...",
    "key_factors": [...],
    "risk_warnings": [...]
  }
}
```

---

## 图谱接口

### GET /graph/industry-chain
产业链图谱数据

**参数:**
| 参数 | 类型 | 说明 |
|------|------|------|
| layer | int | 层级 1~5，不传返回全部 |
| stock_code | string | 以某股票为中心展开 |

### GET /graph/concept-network
概念关联网络

### GET /graph/stock-relations/:code
个股关联图谱

---

## WebSocket接口

### WS /ws/realtime
实时资讯推送

```json
// 订阅
{ "action": "subscribe", "channel": "news" }
{ "action": "subscribe", "channel": "stock:000001" }

// 推送
{
  "type": "news",
  "data": {
    "id": 123,
    "title": "...",
    "sentiment": 1,
    "stock_codes": ["000001"]
  }
}
```
