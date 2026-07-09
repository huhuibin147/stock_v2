# 数据模型设计

## 存储策略

**不存原始全文，只存分析后的结构化数据。**

```
原始资讯(内存) → 分析处理 → 入库存储
  title  ──────→ 保留
  content ─────→ 丢弃，替换为AI摘要
  实体提取  ───→ entities (JSON TEXT)
  情感分析  ───→ sentiment 字段
```

每条资讯存储约 2~3KB，而非原始全文的 10~50KB。

---

## SQLite建表语句

### 1. stocks（股票 - 公司档案，核心表）

```sql
CREATE TABLE IF NOT EXISTS stocks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    code            TEXT NOT NULL UNIQUE,          -- 股票代码
    name            TEXT NOT NULL,                 -- 股票名称
    market          TEXT NOT NULL,                 -- SH/SZ/BJ
    industry        TEXT,                          -- 所属行业
    sector          TEXT,                          -- 所属板块
    concepts        TEXT,                          -- JSON数组: ["芯片","国产替代"]
    core_business   TEXT,                          -- 核心业务描述
    chain_id        INTEGER REFERENCES industry_chains(id),
    list_date       TEXT,                          -- YYYY-MM-DD
    is_active       INTEGER DEFAULT 1,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);

CREATE INDEX idx_stocks_industry ON stocks(industry);
CREATE INDEX idx_stocks_chain ON stocks(chain_id);
```

**数据来源**: AKShare（免费）。`stock_zh_a_spot_em` 获取股票列表，`stock_individual_info_em` 获取公司信息。

### 2. industry_chains（产业链 - 五层架构）

```sql
CREATE TABLE IF NOT EXISTS industry_chains (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,                 -- 节点名称
    layer           INTEGER NOT NULL,              -- 层级 1~5
    parent_id       INTEGER REFERENCES industry_chains(id),
    description     TEXT,
    upstream_ids    TEXT,                          -- JSON数组: [1,3]
    downstream_ids  TEXT,                          -- JSON数组: [5,7]
    created_at      TEXT DEFAULT (datetime('now'))
);
```

**层级定义:**
| 层级 | 名称 | 示例子行业 |
|------|------|-----------|
| 1 | 能源电力 | 电力设备、新能源、储能 |
| 2 | 芯片硬件 | 半导体、PCB、封测、设备 |
| 3 | 基础设施 | 数据中心、云计算、光模块 |
| 4 | AI基础 | 算力芯片、大模型、数据服务 |
| 5 | AI应用 | 智能驾驶、机器人、SaaS |

**数据来源**: 手动维护核心产业链JSON文件，MVP覆盖热门赛道100+公司。

### 3. news（资讯 - 仅存重要资讯）

```sql
CREATE TABLE IF NOT EXISTS news (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source          TEXT NOT NULL,                 -- eastmoney / cninfo / xueqiu
    source_id       TEXT,                          -- 来源原始ID
    title           TEXT NOT NULL,
    summary         TEXT NOT NULL,                 -- AI生成摘要
    key_points      TEXT,                          -- JSON数组: ["要点1","要点2"]
    url             TEXT,                          -- 原始链接
    published_at    TEXT,                          -- ISO8601
    collected_at    TEXT DEFAULT (datetime('now')),
    category        TEXT,                          -- news / announcement / social / policy
    importance_score REAL,                         -- 0~1
    sentiment       INTEGER,                       -- -1利空, 0中性, 1利好
    sentiment_score REAL,                          -- 0~1
    entities        TEXT,                          -- JSON: [{"type":"stock","code":"688981"}]
    tags            TEXT,                          -- JSON数组
    retention       TEXT DEFAULT 'normal',         -- normal(90天) / long_term(1年)
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(source, source_id)                      -- 去重约束
);

CREATE INDEX idx_news_published ON news(published_at);
CREATE INDEX idx_news_importance ON news(importance_score);
CREATE INDEX idx_news_retention ON news(retention);
```

### 4. news_fts（全文检索索引）

```sql
CREATE VIRTUAL TABLE IF NOT EXISTS news_fts USING fts5(
    title, summary,
    content='news',
    content_rowid='id'
);

-- 同步触发器
CREATE TRIGGER news_ai AFTER INSERT ON news BEGIN
    INSERT INTO news_fts(rowid, title, summary) VALUES (new.id, new.title, new.summary);
END;
CREATE TRIGGER news_ad AFTER DELETE ON news BEGIN
    INSERT INTO news_fts(news_fts, rowid, title, summary) VALUES('delete', old.id, old.title, old.summary);
END;
CREATE TRIGGER news_au AFTER UPDATE ON news BEGIN
    INSERT INTO news_fts(news_fts, rowid, title, summary) VALUES('delete', old.id, old.title, old.summary);
    INSERT INTO news_fts(rowid, title, summary) VALUES (new.id, new.title, new.summary);
END;
```

### 5. news_stocks（资讯-股票关联）

```sql
CREATE TABLE IF NOT EXISTS news_stocks (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    news_id       INTEGER NOT NULL REFERENCES news(id) ON DELETE CASCADE,
    stock_code    TEXT NOT NULL,
    relevance     REAL DEFAULT 1.0,
    mention_type  TEXT,                          -- direct / indirect / industry / concept
    created_at    TEXT DEFAULT (datetime('now')),
    UNIQUE(news_id, stock_code)
);

CREATE INDEX idx_news_stocks_code ON news_stocks(stock_code);
```

### 6. concepts（概念板块）

```sql
CREATE TABLE IF NOT EXISTS concepts (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    name          TEXT NOT NULL UNIQUE,
    category      TEXT,
    description   TEXT,
    stock_count   INTEGER DEFAULT 0,
    hot_score     REAL DEFAULT 0,
    created_at    TEXT DEFAULT (datetime('now')),
    updated_at    TEXT DEFAULT (datetime('now'))
);
```

**数据来源**: AKShare `stock_board_concept_name_em` + `stock_board_concept_cons_em`。

---

## JSON字段说明

SQLite中JSON存储为TEXT，用内置 `json()` 函数查询：

```sql
-- 查询包含某股票的资讯
SELECT * FROM news WHERE json_each.value = '688981',
       json_each(news.entities);
```

---

## 数据清理

```sql
-- 定期清理过期资讯（APScheduler触发）
DELETE FROM news WHERE retention = 'normal'
    AND created_at < datetime('now', '-90 days');
DELETE FROM news WHERE retention = 'long_term'
    AND created_at < datetime('now', '-1 year');
```
