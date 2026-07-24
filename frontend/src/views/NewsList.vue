<template>
  <div class="news-list-page">
    <div class="page-header">
      <h2>资讯列表</h2>
      <div class="header-actions">
        <button class="refresh-btn" @click="load(page)" :disabled="loading">
          {{ loading ? '加载中...' : '刷新' }}
        </button>
        <button class="filter-toggle" @click="showFilter = !showFilter">
          {{ showFilter ? '收起' : '筛选' }}
        </button>
      </div>
    </div>

    <div class="filters" :class="{ open: showFilter }">
      <div class="filter-row">
        <select v-model="sortBy" @change="load(1)" class="select">
          <option value="time_desc">时间倒序</option>
          <option value="time_asc">时间正序</option>
          <option value="importance">重要度</option>
        </select>
        <select v-model="filterSource" @change="load(1)" class="select">
          <option value="">全部来源</option>
          <option value="eastmoney">东方财富</option>
          <option value="ths">同花顺</option>
          <option value="sina">新浪财经</option>
          <option value="cninfo">巨潮公告</option>
        </select>
      </div>
      <div class="filter-row">
        <select v-model="filterSentiment" @change="load(1)" class="select">
          <option value="">全部情感</option>
          <option value="1">利好</option>
          <option value="0">中性</option>
          <option value="-1">利空</option>
        </select>
        <select v-model="filterCategory" @change="load(1)" class="select">
          <option value="">全部类型</option>
          <option value="news">新闻</option>
          <option value="announcement">公告</option>
        </select>
        <input
          v-model="filterStock"
          type="search"
          placeholder="股票代码"
          class="stock-input"
          @input="onStockSearch"
        />
      </div>
    </div>

    <div class="news-table">
      <div v-if="!items.length" class="empty">暂无资讯</div>
      <router-link
        v-for="n in items"
        :key="n.id"
        :to="`/news/${n.id}`"
        class="news-row"
        target="_blank"
      >
        <span :class="['badge', sentimentClass(n.sentiment)]">{{ sentimentText(n.sentiment) }}</span>
        <span class="news-title-wrap">
          <span class="news-title">{{ n.title }}</span>
          <span class="stock-tags" v-if="n.stocks && n.stocks.length">
            <router-link
              v-for="s in n.stocks"
              :key="s.code"
              :to="`/stock/${s.code}`"
              class="stock-tag"
              @click.stop
            >{{ s.name }}</router-link>
          </span>
        </span>
        <span class="news-right">
          <span class="source-tag">{{ sourceLabel(n.source) }}</span>
          <span class="news-time">{{ formatTime(n.published_at) }}</span>
        </span>
      </router-link>
    </div>

    <div class="pagination" v-if="total > pageSize">
      <button class="btn" :disabled="page <= 1" @click="goPage(page - 1)">上一页</button>
      <span class="page-info">
        {{ page }}/{{ Math.ceil(total / pageSize) }} ({{ total }}条)
        <span class="page-jump">
          跳至<input v-model.number="jumpPage" type="number" min="1" :max="Math.ceil(total / pageSize)" class="page-input" @keyup.enter="goPage(jumpPage)" />页
          <button class="btn btn-sm" @click="goPage(jumpPage)">GO</button>
        </span>
      </span>
      <button class="btn" :disabled="page >= Math.ceil(total / pageSize)" @click="goPage(page + 1)">下一页</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from "vue";
import { get } from "../api/request";

interface StockInfo {
  code: string;
  name: string;
}

interface NewsItem {
  id: number;
  title: string;
  summary: string;
  sentiment: number | null;
  published_at: string | null;
  source: string;
  category: string;
  stocks?: StockInfo[];
}

const items = ref<NewsItem[]>([]);
const page = ref(1);
const pageSize = 30;
const total = ref(0);
const loading = ref(false);
const showFilter = ref(false);
const sortBy = ref("time_desc");
const filterSource = ref("");
const filterSentiment = ref("");
const filterCategory = ref("");
const filterStock = ref("");
const jumpPage = ref(1);
let stockTimer: ReturnType<typeof setTimeout> | null = null;
let autoRefreshTimer: ReturnType<typeof setInterval> | null = null;

async function load(p: number) {
  loading.value = true;
  page.value = p;
  const params = new URLSearchParams({ page: String(p), page_size: String(pageSize) });
  if (sortBy.value) params.set("sort", sortBy.value);
  if (filterSource.value) params.set("source", filterSource.value);
  if (filterSentiment.value) params.set("sentiment", filterSentiment.value);
  if (filterCategory.value) params.set("category", filterCategory.value);
  if (filterStock.value) params.set("stock_code", filterStock.value.trim());
  const res = await get<{ items: NewsItem[]; total: number }>(`/api/v1/news?${params}`);
  if (res.code === 0) {
    items.value = res.data.items;
    total.value = res.data.total;
  }
  loading.value = false;
}

function goPage(p: number) {
  const maxPage = Math.ceil(total.value / pageSize);
  const target = Math.max(1, Math.min(p, maxPage));
  jumpPage.value = target;
  load(target);
  window.scrollTo({ top: 0, behavior: 'smooth' });
}

function onStockSearch() {
  if (stockTimer) clearTimeout(stockTimer);
  stockTimer = setTimeout(() => load(1), 500);
}

function sentimentClass(s?: number | null) {
  if (s === 1) return "badge-positive";
  if (s === -1) return "badge-negative";
  return "badge-neutral";
}
function sentimentText(s?: number | null) {
  if (s === 1) return "利好";
  if (s === -1) return "利空";
  return "中性";
}
function sourceLabel(s: string) {
  const map: Record<string, string> = {
    eastmoney: "东方财富",
    ths: "同花顺",
    sina: "新浪",
    cninfo: "巨潮公告",
  };
  return map[s] || s;
}
function formatTime(t?: string | null) {
  if (!t) return "-";
  return t.replace("T", " ").substring(0, 16);
}

function startAutoRefresh() {
  // 每1分钟自动刷新，保持当前页码
  autoRefreshTimer = setInterval(() => {
    load(page.value);
  }, 60000);
}

onMounted(() => {
  load(1);
  startAutoRefresh();
});

onUnmounted(() => {
  if (stockTimer) {
    clearTimeout(stockTimer);
    stockTimer = null;
  }
  if (autoRefreshTimer) {
    clearInterval(autoRefreshTimer);
    autoRefreshTimer = null;
  }
});
</script>

<style scoped>
.news-list-page {
  max-width: 960px;
  margin: 0 auto;
  padding: 16px;
}
.page-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 12px;
}
.page-header h2 { font-size: 18px; font-weight: 700; }
.header-actions {
  display: flex;
  gap: 8px;
}
.refresh-btn {
  padding: 6px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--bg);
  font-size: 13px;
  cursor: pointer;
}
.refresh-btn:hover:not(:disabled) { border-color: var(--primary); color: var(--primary); }
.refresh-btn:disabled { opacity: 0.5; cursor: not-allowed; }
.filter-toggle {
  display: none;
  padding: 6px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--bg);
  font-size: 13px;
  cursor: pointer;
}

.filters {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  flex-wrap: wrap;
}
.filter-row {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}
.select {
  padding: 7px 10px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: 13px;
  background: var(--bg);
  cursor: pointer;
}
.stock-input {
  padding: 7px 10px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: 13px;
  width: 120px;
}
.stock-input:focus { border-color: var(--primary); outline: none; }

.news-table {
  background: var(--bg);
  border: 1px solid var(--border-light);
  border-radius: var(--radius);
  overflow: hidden;
}
.news-row {
  display: flex;
  align-items: center;
  padding: 10px 14px;
  border-bottom: 1px solid var(--border-light);
  text-decoration: none;
  color: inherit;
  transition: background 0.15s;
  gap: 8px;
}
.news-row:last-child { border-bottom: none; }
.news-row:hover { background: var(--bg-secondary); text-decoration: none; }

.news-title-wrap {
  display: flex;
  align-items: center;
  gap: 6px;
  flex: 1;
  min-width: 0;
}
.news-title {
  font-size: 14px;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  flex-shrink: 1;
  min-width: 0;
}

.stock-tags {
  display: inline-flex;
  gap: 4px;
  flex-shrink: 0;
}
.stock-tag {
  font-size: 11px;
  padding: 1px 6px;
  border-radius: 3px;
  background: #e8f4fd;
  color: #2563eb;
  text-decoration: none;
  font-weight: 500;
  white-space: nowrap;
}
.stock-tag:hover {
  background: #2563eb;
  color: white;
}
.news-right {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-shrink: 0;
}
.source-tag {
  font-size: 11px;
  padding: 1px 6px;
  background: var(--bg-secondary);
  border-radius: 4px;
  color: var(--text-muted);
}
.news-time {
  font-size: 11px;
  color: var(--text-muted);
  font-family: monospace;
  white-space: nowrap;
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
  margin-top: 12px;
  font-size: 13px;
  color: var(--text-secondary);
}
.page-info {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}
.page-jump {
  display: inline-flex;
  align-items: center;
  gap: 4px;
}
.page-input {
  width: 50px;
  padding: 4px 6px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: 13px;
  text-align: center;
}
.page-input:focus { border-color: var(--primary); outline: none; }
.btn {
  padding: 6px 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--bg);
  cursor: pointer;
  font-size: 13px;
}
.btn-sm { padding: 4px 10px; font-size: 12px; }
.btn:hover:not(:disabled) { border-color: var(--primary); color: var(--primary); }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.empty { text-align: center; padding: 40px; color: var(--text-muted); }

@media (max-width: 640px) {
  .news-list-page { padding: 12px; }
  .page-header h2 { font-size: 16px; }
  .filter-toggle { display: block; }
  .filters {
    display: none;
    flex-direction: column;
    gap: 8px;
    margin-bottom: 12px;
  }
  .filters.open { display: flex; }
  .filter-row { flex-direction: column; gap: 6px; }
  .select { width: 100%; }
  .stock-input { width: 100%; }

  /* 移动端：改为卡片式布局 */
  .news-row {
    flex-wrap: wrap;
    padding: 12px;
    gap: 8px;
    align-items: flex-start;
  }
  .news-title-wrap {
    flex-basis: 100%;
    order: 1;
  }
  .news-title {
    font-size: 15px;
    white-space: normal;
    line-height: 1.5;
    font-weight: 500;
  }
  .stock-tags {
    flex-wrap: wrap;
    order: 2;
    gap: 6px;
  }
  .stock-tag {
    font-size: 12px;
    padding: 2px 8px;
  }
  .news-right {
    order: 3;
    width: 100%;
    justify-content: space-between;
  }

  .pagination {
    gap: 8px;
    font-size: 12px;
    flex-wrap: wrap;
  }
  .btn { padding: 8px 16px; font-size: 13px; }
}
</style>
