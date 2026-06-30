<template>
  <div class="news-list-page">
    <div class="page-header">
      <h2>资讯列表</h2>
      <div class="header-actions">
        <select v-model="filterSource" @change="load(1)" class="select">
          <option value="">全部来源</option>
          <option value="eastmoney">东方财富</option>
          <option value="ths">同花顺</option>
          <option value="sina">新浪财经</option>
          <option value="cninfo">巨潮公告</option>
        </select>
      </div>
    </div>

    <div class="news-table">
      <div v-if="!items.length" class="empty">暂无资讯</div>
      <router-link
        v-for="n in items"
        :key="n.id"
        :to="`/news/${n.id}`"
        class="news-row"
      >
        <div class="news-main">
          <span :class="['badge', sentimentClass(n.sentiment)]">{{ sentimentText(n.sentiment) }}</span>
          <span class="news-title">{{ n.title }}</span>
        </div>
        <div class="news-meta">
          <span class="source-tag">{{ sourceLabel(n.source) }}</span>
          <span class="news-time">{{ formatTime(n.published_at) }}</span>
        </div>
      </router-link>
    </div>

    <div class="pagination" v-if="total > pageSize">
      <button class="btn" :disabled="page <= 1" @click="load(page - 1)">上一页</button>
      <span>第 {{ page }} / {{ Math.ceil(total / pageSize) }} 页 (共 {{ total }} 条)</span>
      <button class="btn" :disabled="page >= Math.ceil(total / pageSize)" @click="load(page + 1)">下一页</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { get } from "../api/request";

interface NewsItem {
  id: number;
  title: string;
  summary: string;
  sentiment: number | null;
  published_at: string | null;
  source: string;
  category: string;
}

const items = ref<NewsItem[]>([]);
const page = ref(1);
const pageSize = 30;
const total = ref(0);
const filterSource = ref("");

async function load(p: number) {
  page.value = p;
  const params = new URLSearchParams({ page: String(p), page_size: String(pageSize) });
  if (filterSource.value) params.set("source", filterSource.value);
  const res = await get<{ items: NewsItem[]; total: number }>(`/api/v1/news?${params}`);
  if (res.code === 0) {
    items.value = res.data.items;
    total.value = res.data.total;
  }
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
  const map: Record<string, string> = { eastmoney: "东方财富", ths: "同花顺", sina: "新浪", cninfo: "巨潮公告" };
  return map[s] || s;
}
function formatTime(t?: string | null) {
  if (!t) return "-";
  return t.replace("T", " ").substring(0, 16);
}

onMounted(() => load(1));
</script>

<style scoped>
.news-list-page {
  max-width: 900px;
  margin: 0 auto;
  padding: 24px;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.page-header h2 { font-size: 20px; font-weight: 700; }
.select {
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: 13px;
  background: var(--bg);
  cursor: pointer;
}

.news-table {
  background: var(--bg);
  border: 1px solid var(--border-light);
  border-radius: var(--radius);
  overflow: hidden;
}
.news-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  border-bottom: 1px solid var(--border-light);
  text-decoration: none;
  color: inherit;
  transition: background 0.15s;
  gap: 16px;
}
.news-row:last-child { border-bottom: none; }
.news-row:hover { background: var(--bg-secondary); text-decoration: none; }

.news-main {
  display: flex;
  align-items: center;
  gap: 10px;
  flex: 1;
  min-width: 0;
}
.news-title {
  font-size: 14px;
  font-weight: 500;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.news-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-shrink: 0;
}
.source-tag {
  font-size: 11px;
  padding: 2px 6px;
  background: var(--bg-secondary);
  border-radius: 4px;
  color: var(--text-muted);
}
.news-time {
  font-size: 12px;
  color: var(--text-muted);
  font-family: monospace;
  white-space: nowrap;
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 16px;
  margin-top: 16px;
  font-size: 13px;
  color: var(--text-secondary);
}
.btn {
  padding: 6px 14px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--bg);
  cursor: pointer;
  font-size: 13px;
}
.btn:hover:not(:disabled) { border-color: var(--primary); color: var(--primary); }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.empty { text-align: center; padding: 40px; color: var(--text-muted); }
</style>
