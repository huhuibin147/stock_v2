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

CREATE TABLE IF NOT EXISTS admin_logs (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    action      TEXT NOT NULL,
    detail      TEXT,
    status      TEXT DEFAULT 'success',
    created_at  TEXT DEFAULT (datetime('now'))
);
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
    """初始化数据库：建表 + FTS索引"""
    Path(DB_PATH).parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.executescript(TABLES_SQL)
        await db.executescript(FTS_SQL)
        await db.commit()
    logger.info("database_initialized", path=DB_PATH)


async def get_db() -> aiosqlite.Connection:
    """获取数据库连接（用于依赖注入）"""
    db = await aiosqlite.connect(DB_PATH)
    db.row_factory = aiosqlite.Row
    await db.execute("PRAGMA journal_mode=WAL")
    return db
