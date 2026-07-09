# API接口规范

## 基础约定

- 基础路径: `/api/v1`
- Content-Type: `application/json`
- 时间格式: ISO 8601

## 响应格式

```json
// 成功
{ "code": 0, "message": "success", "data": { ... } }

// 分页
{ "code": 0, "message": "success", "data": { "items": [...], "total": 100, "page": 1, "page_size": 20 } }

// 错误
{ "code": 40001, "message": "参数错误", "data": null }
```

---

## 个股接口（核心）

### GET /stocks/search
股票搜索

| 参数 | 类型 | 说明 |
|------|------|------|
| q | string | 搜索关键词（代码或名称） |
| limit | int | 返回数量，默认10 |

### GET /stocks/:code/profile
**核心接口** — 个股全景，一次返回公司全貌

```json
{
  "code": 0,
  "data": {
    "stock": {
      "code": "688981", "name": "中芯国际", "market": "SH",
      "industry": "半导体", "concepts": ["芯片", "国产替代"],
      "core_business": "晶圆代工，国内先进制程龙头"
    },
    "chain": {
      "layer": 2, "layer_name": "芯片硬件层",
      "position": "晶圆代工",
      "upstream": [{"code": "688012", "name": "中微公司", "relation": "设备供应商"}],
      "downstream": [{"code": "002049", "name": "紫光国微", "relation": "芯片设计客户"}]
    },
    "recent_news": [
      {"id": 1, "title": "Q2营收超预期", "summary": "...", "sentiment": 1, "published_at": "..."}
    ],
    "sentiment_7d": {"positive": 5, "neutral": 3, "negative": 1, "trend": "偏多"}
  }
}
```

### GET /stocks/:code/news
个股资讯（分页，默认返回最重要的）

| 参数 | 类型 | 说明 |
|------|------|------|
| page | int | 页码，默认1 |
| page_size | int | 每页条数，默认10 |
| sentiment | int | 情感筛选：-1/0/1 |

---

## 全市场接口

### GET /news/hot
今日热点（按重要度排序，默认前20条）

### GET /news/:id
资讯详情

### GET /analysis/overview
全市场概览（热点板块、情感分布）

### GET /analysis/concepts
概念热度排行

---

## AI接口

### POST /ai/summarize
资讯摘要（入库时调用，或补充生成）

```json
// Request
{ "news_id": 123 }

// Response
{ "code": 0, "data": { "summary": "...", "key_points": ["..."], "sentiment": "利好" } }
```

### POST /ai/analyze
趋势研判（Phase 3）

```json
// Request
{ "stock_code": "688981", "period": "1w" }

// Response
{ "code": 0, "data": { "trend": "偏多", "confidence": 0.75, "analysis": "...", "key_factors": [...] } }
```

---

## 图谱接口

### GET /graph/industry-chain
产业链图谱

| 参数 | 类型 | 说明 |
|------|------|------|
| layer | int | 层级 1~5，不传返回全部 |
| stock_code | string | 以某股票为中心展开 |

### GET /graph/stock-relations/:code
个股关联图谱（上下游+同概念+同行业）
