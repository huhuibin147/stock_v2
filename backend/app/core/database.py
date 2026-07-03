import json
from pathlib import Path

import aiosqlite
import structlog

from app.core.config import settings

logger = structlog.get_logger()

DB_PATH = settings.database_url.replace("sqlite+aiosqlite:///", "")

# 建表SQL
TABLES_SQL = """
CREATE TABLE IF NOT EXISTS industry_chains (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    layer           INTEGER NOT NULL,
    parent_id       INTEGER REFERENCES industry_chains(id),
    description     TEXT,
    upstream_ids    TEXT,
    downstream_ids  TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS stocks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    code            TEXT NOT NULL UNIQUE,
    name            TEXT NOT NULL,
    market          TEXT NOT NULL,
    industry        TEXT,
    sector          TEXT,
    concepts        TEXT,
    core_business   TEXT,
    chain_id        INTEGER REFERENCES industry_chains(id),
    list_date       TEXT,
    is_active       INTEGER DEFAULT 1,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_stocks_industry ON stocks(industry);
CREATE INDEX IF NOT EXISTS idx_stocks_chain ON stocks(chain_id);

CREATE TABLE IF NOT EXISTS news (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    source          TEXT NOT NULL,
    source_id       TEXT,
    title           TEXT NOT NULL,
    content         TEXT DEFAULT '',
    summary         TEXT NOT NULL DEFAULT '',
    key_points      TEXT,
    url             TEXT,
    published_at    TEXT,
    collected_at    TEXT DEFAULT (datetime('now')),
    category        TEXT,
    importance_score REAL,
    sentiment       INTEGER,
    sentiment_score REAL,
    entities        TEXT,
    events          TEXT,
    tags            TEXT,
    retention       TEXT DEFAULT 'normal',
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(source, source_id)
);
CREATE INDEX IF NOT EXISTS idx_news_published ON news(published_at);
CREATE INDEX IF NOT EXISTS idx_news_importance ON news(importance_score);
CREATE INDEX IF NOT EXISTS idx_news_retention ON news(retention);

CREATE TABLE IF NOT EXISTS news_stocks (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    news_id       INTEGER NOT NULL REFERENCES news(id) ON DELETE CASCADE,
    stock_code    TEXT NOT NULL,
    relevance     REAL DEFAULT 1.0,
    mention_type  TEXT,
    created_at    TEXT DEFAULT (datetime('now')),
    UNIQUE(news_id, stock_code)
);
CREATE INDEX IF NOT EXISTS idx_news_stocks_code ON news_stocks(stock_code);

CREATE TABLE IF NOT EXISTS events (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    event_type    TEXT NOT NULL,
    event_subtype TEXT,
    title         TEXT NOT NULL,
    description   TEXT,
    news_id       INTEGER REFERENCES news(id),
    stock_codes   TEXT,
    impact        INTEGER,
    impact_level  TEXT,
    event_date    TEXT,
    extra         TEXT,
    created_at    TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_events_date ON events(event_date);

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

CREATE TABLE IF NOT EXISTS stock_profiles (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    code            TEXT NOT NULL UNIQUE,
    company_name    TEXT,
    english_name    TEXT,
    legal_rep       TEXT,
    reg_capital     TEXT,
    found_date      TEXT,
    list_date       TEXT,
    website         TEXT,
    email           TEXT,
    phone           TEXT,
    reg_address     TEXT,
    office_address  TEXT,
    business_scope  TEXT,
    introduction    TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS stock_financials (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    code            TEXT NOT NULL,
    report_date     TEXT NOT NULL,
    net_profit      REAL,
    net_profit_yoy  REAL,
    revenue         REAL,
    revenue_yoy     REAL,
    eps             REAL,
    bps             REAL,
    roe             REAL,
    net_margin      REAL,
    equity_ratio    REAL,
    ocf_ps          REAL,
    created_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(code, report_date)
);
CREATE INDEX IF NOT EXISTS idx_financials_code ON stock_financials(code);

CREATE TABLE IF NOT EXISTS stock_kline (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    code            TEXT NOT NULL,
    trade_date      TEXT NOT NULL,
    open            REAL,
    close           REAL,
    high            REAL,
    low             REAL,
    volume          REAL,
    turnover        REAL,
    amplitude       REAL,
    pct_change      REAL,
    change_amount   REAL,
    turnover_rate   REAL,
    created_at      TEXT DEFAULT (datetime('now')),
    UNIQUE(code, trade_date)
);
CREATE INDEX IF NOT EXISTS idx_kline_code ON stock_kline(code);
CREATE INDEX IF NOT EXISTS idx_kline_date ON stock_kline(trade_date);

CREATE TABLE IF NOT EXISTS admin_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    action      TEXT NOT NULL,
    detail      TEXT,
    status      TEXT DEFAULT 'success',
    created_at  TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS supply_chain_research (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    target_type     TEXT NOT NULL,
    target_name     TEXT NOT NULL,
    target_code     TEXT,
    status          TEXT DEFAULT 'pending',
    result_summary  TEXT,
    search_sources  TEXT,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);

CREATE TABLE IF NOT EXISTS supply_chain_relations (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    research_id     INTEGER NOT NULL REFERENCES supply_chain_research(id) ON DELETE CASCADE,
    company_name    TEXT NOT NULL,
    company_code    TEXT,
    relation_type   TEXT NOT NULL,
    relation_desc   TEXT,
    product_service TEXT,
    cooperation_detail TEXT,
    business_volume TEXT,
    start_time      TEXT,
    confidence      REAL,
    source          TEXT,
    source_url      TEXT,
    news_title      TEXT,
    news_date       TEXT,
    created_at      TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_supply_chain_research_id ON supply_chain_relations(research_id);

CREATE TABLE IF NOT EXISTS supply_chain_notes (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    research_id     INTEGER NOT NULL REFERENCES supply_chain_research(id) ON DELETE CASCADE,
    content         TEXT NOT NULL,
    created_at      TEXT DEFAULT (datetime('now')),
    updated_at      TEXT DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_supply_chain_notes_research_id ON supply_chain_notes(research_id);
"""

FTS_SQL = """
CREATE VIRTUAL TABLE IF NOT EXISTS news_fts USING fts5(
    title, summary,
    content='news',
    content_rowid='id'
);

CREATE TRIGGER IF NOT EXISTS news_ai AFTER INSERT ON news BEGIN
    INSERT INTO news_fts(rowid, title, summary) VALUES (new.id, new.title, new.summary);
END;

CREATE TRIGGER IF NOT EXISTS news_ad AFTER DELETE ON news BEGIN
    INSERT INTO news_fts(news_fts, rowid, title, summary) VALUES('delete', old.id, old.title, old.summary);
END;

CREATE TRIGGER IF NOT EXISTS news_au AFTER UPDATE ON news BEGIN
    INSERT INTO news_fts(news_fts, rowid, title, summary) VALUES('delete', old.id, old.title, old.summary);
    INSERT INTO news_fts(rowid, title, summary) VALUES (new.id, new.title, new.summary);
END;
"""


async def init_db():
    """初始化数据库：建表 + FTS索引 + 增量迁移"""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(TABLES_SQL)
        await db.executescript(FTS_SQL)

        # 增量迁移（兼容已有数据库，列已存在则忽略）
        migrations = [
            "ALTER TABLE news ADD COLUMN content TEXT DEFAULT ''",
            "ALTER TABLE stocks ADD COLUMN pe_ttm REAL",
            "ALTER TABLE stocks ADD COLUMN pb REAL",
            "ALTER TABLE stocks ADD COLUMN market_cap REAL",
            "ALTER TABLE stocks ADD COLUMN dividend_yield REAL",
            "ALTER TABLE stocks ADD COLUMN turnover_amount REAL",
            "ALTER TABLE stocks ADD COLUMN last_price REAL",
            "ALTER TABLE stocks ADD COLUMN pct_change REAL",
            "ALTER TABLE stocks ADD COLUMN volume REAL",
            # 供应链挖掘新增字段
            "ALTER TABLE supply_chain_research ADD COLUMN search_sources TEXT",
            "ALTER TABLE supply_chain_relations ADD COLUMN cooperation_detail TEXT",
            "ALTER TABLE supply_chain_relations ADD COLUMN business_volume TEXT",
            "ALTER TABLE supply_chain_relations ADD COLUMN start_time TEXT",
            "ALTER TABLE supply_chain_relations ADD COLUMN source_url TEXT",
            "ALTER TABLE supply_chain_relations ADD COLUMN news_title TEXT",
            "ALTER TABLE supply_chain_relations ADD COLUMN news_date TEXT",
        ]
        for sql in migrations:
            try:
                await db.execute(sql)
            except Exception:
                pass

        await db.commit()
    logger.info("database_initialized", path=DB_PATH)


async def get_db() -> aiosqlite.Connection:
    """获取数据库连接（用于依赖注入）"""
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    return db
