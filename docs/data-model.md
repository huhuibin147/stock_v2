# 数据模型设计

## 存储策略：只存整合后的结果

**核心原则：不存原始全文，只存分析后的结构化数据。**

```
原始资讯(内存) → 分析处理 → 入库存储
  title  ──────→ 保留
  content ─────→ 丢弃，替换为AI摘要
  实体提取  ───→ entities JSONB
  情感分析  ───→ sentiment 字段
  事件提取  ───→ events JSONB
```

每条资讯存储约 2~3KB（摘要+结构化），而非原始全文的 10~50KB。

## 核心实体

### 1. News（资讯 - 仅存储重要资讯的整合结果）

```sql
CREATE TABLE news (
    id              BIGSERIAL PRIMARY KEY,
    source          VARCHAR(32) NOT NULL,       -- 来源：eastmoney, ths, sina, cninfo, xueqiu
    source_id       VARCHAR(128),               -- 来源原始ID
    title           VARCHAR(512) NOT NULL,
    -- content 字段移除：不存原始全文
    summary         TEXT NOT NULL,              -- AI生成摘要（替代content，核心存储）
    key_points      TEXT[],                      -- AI提取的关键要点
    url             VARCHAR(1024),              -- 原始链接（需要回溯时访问原文）
    published_at    TIMESTAMPTZ,                -- 发布时间
    collected_at    TIMESTAMPTZ DEFAULT NOW(),   -- 采集时间
    category        VARCHAR(64),                -- 分类：news, announcement, social, policy
    importance_score FLOAT,                     -- 重要度分数（采集时计算）
    sentiment       SMALLINT,                   -- 情感：-1利空, 0中性, 1利好
    sentiment_score FLOAT,                      -- 情感分数 0~1
    entities        JSONB,                      -- 提取的实体列表
    events          JSONB,                      -- 提取的事件列表
    tags            TEXT[],                      -- 标签
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_news_source ON news(source);
CREATE INDEX idx_news_published ON news(published_at DESC);
CREATE INDEX idx_news_sentiment ON news(sentiment);
CREATE INDEX idx_news_entities ON news USING GIN(entities);
CREATE INDEX idx_news_tags ON news USING GIN(tags);
CREATE INDEX idx_news_importance ON news(importance_score DESC);
```

### 数据生命周期

```sql
-- 自动清理90天前的资讯（定期任务）
-- 重要公告可标记为 long_term 保留更久
ALTER TABLE news ADD COLUMN retention VARCHAR(16) DEFAULT 'normal';  -- normal/long_term

-- 清理策略
-- normal: 90天后自动归档/删除
-- long_term: 重要公告、重大事件，保留1年
```

### 2. Stock（股票 - 公司核心档案）

```sql
CREATE TABLE stocks (
    id              SERIAL PRIMARY KEY,
    code            VARCHAR(10) NOT NULL UNIQUE,  -- 股票代码 000001
    name            VARCHAR(64) NOT NULL,          -- 股票名称
    market          VARCHAR(10) NOT NULL,          -- SH/SZ/BJ
    industry        VARCHAR(64),                   -- 所属行业
    sector          VARCHAR(64),                   -- 所属板块
    concepts        TEXT[],                        -- 所属概念列表
    core_business   TEXT,                          -- 核心业务描述（用户看到的第一句话）
    chain_layer     SMALLINT,                      -- 产业链层级 1~5
    chain_position  VARCHAR(64),                   -- 产业链位置：晶圆代工、封测、设备...
    upstream_codes   TEXT[],                       -- 上游关联股票代码
    downstream_codes TEXT[],                       -- 下游关联股票代码
    list_date       DATE,                          -- 上市日期
    is_active       BOOLEAN DEFAULT TRUE,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_stocks_code ON stocks(code);
CREATE INDEX idx_stocks_industry ON stocks(industry);
CREATE INDEX idx_stocks_concepts ON stocks USING GIN(concepts);
```

### 3. NewsStock（资讯-股票关联）

```sql
CREATE TABLE news_stocks (
    id            BIGSERIAL PRIMARY KEY,
    news_id       BIGINT NOT NULL REFERENCES news(id),
    stock_code    VARCHAR(10) NOT NULL,
    relevance     FLOAT DEFAULT 1.0,           -- 相关度 0~1
    mention_type  VARCHAR(32),                  -- 提及方式：direct, indirect, industry, concept
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(news_id, stock_code)
);

CREATE INDEX idx_news_stocks_news ON news_stocks(news_id);
CREATE INDEX idx_news_stocks_code ON news_stocks(stock_code);
```

### 4. Event（事件）

```sql
CREATE TABLE events (
    id            BIGSERIAL PRIMARY KEY,
    event_type    VARCHAR(64) NOT NULL,         -- 事件类型
    event_subtype VARCHAR(64),                  -- 事件子类型
    title         VARCHAR(512) NOT NULL,
    description   TEXT,
    news_id       BIGINT REFERENCES news(id),   -- 关联资讯
    stock_codes   TEXT[],                        -- 涉及股票
    impact        SMALLINT,                     -- 影响：-1负面, 0中性, 1正面
    impact_level  VARCHAR(16),                  -- 影响程度：high, medium, low
    event_date    DATE,                          -- 事件日期
    extra         JSONB,                        -- 扩展信息
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

CREATE INDEX idx_events_type ON events(event_type);
CREATE INDEX idx_events_stocks ON events USING GIN(stock_codes);
CREATE INDEX idx_events_date ON events(event_date DESC);
```

### 5. Concept（概念）

```sql
CREATE TABLE concepts (
    id            SERIAL PRIMARY KEY,
    name          VARCHAR(128) NOT NULL UNIQUE,
    category      VARCHAR(64),                  -- 概念分类
    description   TEXT,
    stock_count   INT DEFAULT 0,               -- 关联股票数
    hot_score     FLOAT DEFAULT 0,             -- 热度分
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    updated_at    TIMESTAMPTZ DEFAULT NOW()
);
```

### 6. IndustryChain（产业链）

```sql
CREATE TABLE industry_chains (
    id            SERIAL PRIMARY KEY,
    name          VARCHAR(128) NOT NULL,
    layer         SMALLINT NOT NULL,            -- 层级 1~5
    parent_id     INT REFERENCES industry_chains(id),
    description   TEXT,
    stock_codes   TEXT[],                        -- 关联股票
    upstream      INT[],                        -- 上游节点ID
    downstream    INT[],                        -- 下游节点ID
    created_at    TIMESTAMPTZ DEFAULT NOW()
);

-- 层级定义（参考aichainmap五层架构）
-- 1: 能源与电力（电力设备、新能源）
-- 2: 芯片与硬件（半导体、PCB、被动元件）
-- 3: 基础设施（数据中心、云计算、通信）
-- 4: AI基础（算力、大模型、数据服务）
-- 5: AI应用（智能驾驶、机器人、SaaS、金融AI）
```

### 7. HotConcept（热点概念追踪）

```sql
CREATE TABLE hot_concepts (
    id            BIGSERIAL PRIMARY KEY,
    concept_id    INT REFERENCES concepts(id),
    date          DATE NOT NULL,
    news_count    INT DEFAULT 0,               -- 当日资讯数
    sentiment_avg FLOAT,                        -- 平均情感分
    stock_count   INT DEFAULT 0,               -- 关联股票数
    hot_score     FLOAT,                        -- 热度分
    created_at    TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(concept_id, date)
);
```

## 事件类型枚举

| 类型 | 子类型 | 说明 |
|------|--------|------|
| performance | pre_increase, pre_decrease, loss | 业绩预告/快报 |
| merger | acquisition, restructuring | 并购重组 |
| equity | buyback, incentive, top_up, top_down | 股权变动 |
| policy | subsidy, regulation, industry_plan | 政策影响 |
| product | launch, patent, contract | 产品/技术 |
| risk | violation, lawsuit, rating_down | 风险事件 |
| market | limit_up, limit_down, volume_surge | 市场异动 |

## ES索引映射

```json
{
  "news": {
    "mappings": {
      "properties": {
        "title": { "type": "text", "analyzer": "ik_max_word" },
        "summary": { "type": "text", "analyzer": "ik_smart" },
        "key_points": { "type": "text", "analyzer": "ik_smart" },
        "source": { "type": "keyword" },
        "category": { "type": "keyword" },
        "sentiment": { "type": "integer" },
        "importance_score": { "type": "float" },
        "published_at": { "type": "date" },
        "entities": {
          "type": "nested",
          "properties": {
            "name": { "type": "keyword" },
            "type": { "type": "keyword" },
            "code": { "type": "keyword" }
          }
        }
      }
    }
  }
}
```
