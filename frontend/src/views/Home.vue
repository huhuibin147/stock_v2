<template>
  <div class="home">
    <!-- Hero Section -->
    <section class="hero">
      <div class="hero-content">
        <h1 class="hero-title">A股产业链全景分析</h1>
        <p class="hero-subtitle">五层架构 · 资讯驱动 · AI研判</p>
        <div class="hero-links">
          <router-link to="/admin" class="hero-link">⚙ 进入管理后台</router-link>
        </div>
        <div class="hero-search">
          <input
            v-model="query"
            type="search"
            placeholder="输入股票代码或名称，如 600519 或 贵州茅台"
            @input="onSearch"
            @keydown.enter="goFirst"
          />
          <div v-if="results.length" class="search-dropdown">
            <router-link
              v-for="s in results"
              :key="s.code"
              :to="`/stock/${s.code}`"
              class="search-item"
            >
              <span class="s-code">{{ s.code }}</span>
              <span class="s-name">{{ s.name }}</span>
              <span class="s-market">{{ s.market }}</span>
              <span v-if="s.industry" class="s-industry">{{ s.industry }}</span>
            </router-link>
          </div>
        </div>
      </div>
      <!-- Stats Bar -->
      <div class="stats-bar" v-if="overview">
        <div class="stat-chip">
          <span class="stat-num">{{ overview.stats.stocks.toLocaleString() }}</span>
          <span class="stat-label">公司</span>
        </div>
        <div class="stat-chip">
          <span class="stat-num">{{ overview.stats.news.toLocaleString() }}</span>
          <span class="stat-label">资讯</span>
        </div>
        <div class="stat-chip">
          <span class="stat-num">{{ overview.stats.concepts.toLocaleString() }}</span>
          <span class="stat-label">概念</span>
        </div>
        <div class="stat-chip">
          <span class="stat-num">{{ overview.stats.events.toLocaleString() }}</span>
          <span class="stat-label">事件</span>
        </div>
        <div class="stat-chip">
          <span class="stat-num">{{ overview.stats.chains.toLocaleString() }}</span>
          <span class="stat-label">产业链</span>
        </div>
      </div>
    </section>

    <div class="content" v-if="overview">
      <!-- 五层产业链 -->
      <section class="section">
        <div class="section-header">
          <h2 class="section-title">五层产业链</h2>
        </div>
        <div class="layers-grid">
          <div
            v-for="layer in overview.layers"
            :key="layer.layer"
            class="layer-card"
            :class="`layer-${layer.layer}`"
          >
            <div class="layer-num">Layer {{ layer.layer }}</div>
            <div class="layer-name">{{ layer.name }}</div>
            <div class="layer-stats">
              <span>{{ layer.chain_count }} 个子行业</span>
              <span>{{ layer.stock_count }} 家公司</span>
            </div>
          </div>
        </div>
      </section>

      <!-- 两栏：热门公司 + 最新事件 -->
      <section class="section two-col">
        <div class="col">
          <h2 class="section-title">
            热门公司
            <span class="count">按关联资讯数</span>
          </h2>
          <div class="card stock-list">
            <div v-if="!overview.hot_stocks.length" class="empty">暂无数据，请先导入股票</div>
            <router-link
              v-for="(s, i) in overview.hot_stocks"
              :key="s.code"
              :to="`/stock/${s.code}`"
              class="stock-row"
            >
              <span class="rank" :class="{ top3: i < 3 }">{{ String(i + 1).padStart(2, '0') }}</span>
              <span class="stock-name">{{ s.name }}</span>
              <span class="stock-code-tag">{{ s.code }}.{{ s.market }}</span>
              <span v-if="s.industry" class="stock-ind">{{ s.industry }}</span>
              <span class="news-badge" v-if="s.news_count">{{ s.news_count }}</span>
            </router-link>
          </div>
        </div>
        <div class="col">
          <h2 class="section-title">
            最新事件
            <span class="count">按时间</span>
          </h2>
          <div class="card event-list">
            <div v-if="!overview.recent_events.length" class="empty">暂无事件</div>
            <div
              v-for="(ev, i) in overview.recent_events"
              :key="i"
              class="event-row"
            >
              <span class="event-date">{{ ev.event_date || '-' }}</span>
              <span :class="['badge', impactClass(ev.impact)]">{{ ev.event_type }}</span>
              <span class="event-title">{{ ev.title }}</span>
            </div>
          </div>
        </div>
      </section>

      <!-- 高频概念 -->
      <section class="section">
        <h2 class="section-title">
          高频概念
          <span class="count">按关联公司数</span>
        </h2>
        <div class="concept-cloud">
          <router-link
            v-for="c in overview.hot_concepts"
            :key="c.name"
            :to="`/?q=${c.name}`"
            class="tag concept-tag"
          >
            {{ c.name }}
            <span class="tag-count" v-if="c.stock_count">{{ c.stock_count }}</span>
          </router-link>
          <div v-if="!overview.hot_concepts.length" class="empty">暂无概念数据</div>
        </div>
      </section>

      <!-- 最新资讯 -->
      <section class="section">
        <h2 class="section-title">
          最新资讯
          <span class="count">按重要度</span>
        </h2>
        <div class="news-feed">
          <div v-if="!overview.recent_news.length" class="empty">暂无资讯</div>
          <div
            v-for="item in overview.recent_news"
            :key="item.id"
            class="news-card card"
          >
            <div class="news-meta">
              <span :class="['badge', sentimentClass(item.sentiment)]">{{ sentimentText(item.sentiment) }}</span>
              <span class="news-source">{{ item.source }}</span>
              <span class="news-time">{{ formatTime(item.published_at) }}</span>
            </div>
            <div class="news-title">{{ item.title }}</div>
            <div v-if="item.summary" class="news-summary">{{ item.summary }}</div>
          </div>
        </div>
      </section>
    </div>

    <!-- Loading -->
    <div v-if="!overview && !error" class="loading">
      <div class="loading-spinner"></div>
      <span>加载中...</span>
    </div>
    <div v-if="error" class="error-msg">{{ error }}</div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { searchStocks, getOverview } from "../api/stock";
import type { StockInfo, OverviewData } from "../types";

const query = ref("");
const results = ref<StockInfo[]>([]);
const overview = ref<OverviewData | null>(null);
const error = ref("");
let timer: ReturnType<typeof setTimeout> | null = null;

function onSearch() {
  if (timer) clearTimeout(timer);
  if (!query.value.trim()) {
    results.value = [];
    return;
  }
  timer = setTimeout(async () => {
    const res = await searchStocks(query.value.trim());
    if (res.code === 0) results.value = res.data;
  }, 300);
}

function goFirst() {
  if (results.value.length > 0) {
    window.location.href = `/stock/${results.value[0].code}`;
  }
}

function sentimentClass(s?: number) {
  if (s === 1) return "badge-positive";
  if (s === -1) return "badge-negative";
  return "badge-neutral";
}
function sentimentText(s?: number) {
  if (s === 1) return "利好";
  if (s === -1) return "利空";
  return "中性";
}
function impactClass(impact?: number) {
  if (impact === 1) return "badge-positive";
  if (impact === -1) return "badge-negative";
  return "badge-neutral";
}
function formatTime(t?: string) {
  if (!t) return "";
  return t.replace("T", " ").substring(0, 16);
}

onMounted(async () => {
  const res = await getOverview();
  if (res.code === 0) {
    overview.value = res.data;
  } else {
    error.value = res.message;
  }
});
</script>

<style scoped>
/* Hero */
.hero {
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 50%, #0f3460 100%);
  color: #fff;
  padding: 48px 24px 32px;
  text-align: center;
}
.hero-content { max-width: 640px; margin: 0 auto; }
.hero-title { font-size: 32px; font-weight: 800; margin-bottom: 8px; letter-spacing: 1px; }
.hero-subtitle { font-size: 14px; color: rgba(255,255,255,0.6); margin-bottom: 12px; }
.hero-links { margin-bottom: 20px; }
.hero-link {
  color: rgba(255,255,255,0.5);
  font-size: 13px;
  text-decoration: none;
  transition: color 0.2s;
}
.hero-link:hover { color: #fff; text-decoration: underline; }
.hero-search { position: relative; max-width: 520px; margin: 0 auto; }
.hero-search input {
  padding: 14px 18px;
  font-size: 15px;
  border-radius: 8px;
  border: none;
  width: 100%;
  box-shadow: 0 4px 20px rgba(0,0,0,0.3);
}
.search-dropdown {
  position: absolute;
  top: 100%;
  left: 0;
  right: 0;
  background: #fff;
  border-radius: 8px;
  margin-top: 4px;
  box-shadow: 0 8px 30px rgba(0,0,0,0.15);
  overflow: hidden;
  z-index: 10;
}
.search-item {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  color: var(--text);
  text-decoration: none;
  border-bottom: 1px solid var(--border-light);
  transition: background 0.15s;
}
.search-item:last-child { border-bottom: none; }
.search-item:hover { background: var(--bg-secondary); text-decoration: none; }
.s-code { font-family: "SF Mono", "Fira Code", monospace; color: var(--primary); font-weight: 600; font-size: 13px; min-width: 60px; }
.s-name { font-weight: 500; }
.s-market { font-size: 11px; color: var(--text-muted); }
.s-industry { font-size: 11px; color: var(--text-muted); margin-left: auto; }

/* Stats Bar */
.stats-bar {
  display: flex;
  justify-content: center;
  gap: 24px;
  margin-top: 28px;
  flex-wrap: wrap;
}
.stat-chip {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 70px;
}
.stat-num { font-size: 22px; font-weight: 800; color: #fff; font-variant-numeric: tabular-nums; }
.stat-label { font-size: 11px; color: rgba(255,255,255,0.5); margin-top: 2px; }

/* Content */
.content {
  max-width: 1100px;
  margin: 0 auto;
  padding: 24px;
}

/* Section */
.section { margin-bottom: 32px; }
.section-header { display: flex; align-items: center; justify-content: space-between; }

/* Layers */
.layers-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 12px;
}
.layer-card {
  background: #fff;
  border: 1px solid var(--border-light);
  border-radius: var(--radius);
  padding: 16px;
  text-align: center;
  transition: all 0.2s;
  cursor: default;
  border-top: 3px solid transparent;
}
.layer-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}
.layer-1 { border-top-color: #27ae60; }
.layer-2 { border-top-color: #3498db; }
.layer-3 { border-top-color: #f39c12; }
.layer-4 { border-top-color: #e74c3c; }
.layer-5 { border-top-color: #9b59b6; }
.layer-num { font-size: 11px; color: var(--text-muted); text-transform: uppercase; letter-spacing: 1px; }
.layer-name { font-size: 16px; font-weight: 700; margin: 6px 0; }
.layer-stats {
  display: flex;
  flex-direction: column;
  font-size: 12px;
  color: var(--text-secondary);
  gap: 2px;
}

/* Two Column */
.two-col { display: grid; grid-template-columns: 1fr 1fr; gap: 20px; }
.col { min-width: 0; }

/* Stock List */
.stock-list { padding: 0; overflow: hidden; }
.stock-row {
  display: flex;
  align-items: center;
  gap: 10px;
  padding: 10px 16px;
  border-bottom: 1px solid var(--border-light);
  color: var(--text);
  text-decoration: none;
  transition: background 0.15s;
}
.stock-row:last-child { border-bottom: none; }
.stock-row:hover { background: var(--bg-secondary); text-decoration: none; }
.rank {
  font-family: "SF Mono", monospace;
  font-size: 13px;
  color: var(--text-muted);
  min-width: 22px;
}
.rank.top3 { color: var(--primary); font-weight: 700; }
.stock-name { font-weight: 500; font-size: 14px; }
.stock-code-tag { font-family: "SF Mono", monospace; font-size: 11px; color: var(--text-muted); }
.stock-ind { font-size: 11px; color: var(--text-muted); margin-left: auto; }
.news-badge {
  background: var(--primary-light);
  color: var(--primary);
  font-size: 11px;
  font-weight: 600;
  padding: 1px 6px;
  border-radius: 10px;
  min-width: 20px;
  text-align: center;
}

/* Event List */
.event-list { padding: 0; overflow: hidden; }
.event-row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border-bottom: 1px solid var(--border-light);
  font-size: 13px;
}
.event-row:last-child { border-bottom: none; }
.event-date { font-family: "SF Mono", monospace; font-size: 12px; color: var(--text-muted); min-width: 80px; }
.event-title { flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

/* Concepts */
.concept-cloud {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.concept-tag {
  position: relative;
}
.tag-count {
  font-size: 10px;
  color: var(--text-muted);
  margin-left: 4px;
}

/* News Feed */
.news-feed {
  display: grid;
  gap: 12px;
}
.news-card { padding: 16px; }
.news-meta {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 6px;
}
.news-source { font-size: 12px; color: var(--text-muted); }
.news-time { font-size: 12px; color: var(--text-muted); margin-left: auto; }
.news-title { font-size: 15px; font-weight: 500; margin-bottom: 4px; line-height: 1.5; }
.news-summary { font-size: 13px; color: var(--text-secondary); line-height: 1.5; }

/* Loading */
.loading {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 12px;
  padding: 80px 0;
  color: var(--text-muted);
}
.loading-spinner {
  width: 24px;
  height: 24px;
  border: 3px solid var(--border);
  border-top-color: var(--primary);
  border-radius: 50%;
  animation: spin 0.8s linear infinite;
}
@keyframes spin { to { transform: rotate(360deg); } }
.error-msg { text-align: center; padding: 40px; color: var(--primary); }

/* Responsive */
@media (max-width: 768px) {
  .layers-grid { grid-template-columns: repeat(2, 1fr); }
  .two-col { grid-template-columns: 1fr; }
  .hero-title { font-size: 24px; }
  .stats-bar { gap: 16px; }
  .stat-num { font-size: 18px; }
}
</style>
