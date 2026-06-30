<template>
  <div v-if="loading" class="loading">加载中...</div>
  <div v-else-if="!news" class="not-found">
    <p>未找到资讯信息</p>
    <router-link to="/">返回首页</router-link>
  </div>
  <div v-else class="detail">
    <!-- 标题区 -->
    <div class="card header-card">
      <div class="header-meta">
        <span :class="['badge', sentimentClass(news.sentiment)]">{{ sentimentText(news.sentiment) }}</span>
        <span v-if="news.source" class="source">{{ news.source }}</span>
        <span v-if="news.published_at" class="time">{{ formatTime(news.published_at) }}</span>
        <span v-if="news.category" class="category">{{ news.category }}</span>
      </div>
      <h1 class="title">{{ news.title }}</h1>
      <div v-if="news.url" class="original-link">
        <a :href="news.url" target="_blank" rel="noopener">查看原文 ↗</a>
      </div>
    </div>

    <!-- 涉及股票 -->
    <div v-if="news.stocks.length" class="card">
      <h3>涉及股票</h3>
      <div class="stocks-row">
        <router-link
          v-for="s in news.stocks"
          :key="s.code"
          :to="`/stock/${s.code}`"
          class="stock-tag"
        >
          <span class="stock-name">{{ s.name }}</span>
          <span class="stock-code">{{ s.code }}</span>
        </router-link>
      </div>
    </div>

    <!-- AI 摘要 -->
    <div v-if="news.summary" class="card">
      <h3>AI 摘要</h3>
      <p class="summary-text">{{ news.summary }}</p>
    </div>

    <!-- 原文 -->
    <div v-if="news.content" class="card">
      <h3>原文</h3>
      <p class="content-text">{{ news.content }}</p>
    </div>

    <!-- 要点 -->
    <div v-if="news.key_points && news.key_points.length" class="card">
      <h3>要点</h3>
      <ul class="key-points">
        <li v-for="(point, i) in news.key_points" :key="i">{{ point }}</li>
      </ul>
    </div>

    <!-- 分析结果 -->
    <div class="card analysis-card" v-if="hasAnalysis">
      <h3>分析结果</h3>

      <!-- 情感 -->
      <div class="analysis-section">
        <span class="label">情感</span>
        <span :class="['badge', sentimentClass(news.sentiment)]">{{ sentimentText(news.sentiment) }}</span>
        <span v-if="news.sentiment_score != null" class="score">评分: {{ news.sentiment_score.toFixed(2) }}</span>
      </div>

      <!-- 实体 -->
      <div v-if="news.entities && news.entities.length" class="analysis-section">
        <span class="label">实体</span>
        <div class="tag-list">
          <router-link
            v-for="(e, i) in news.entities"
            :key="i"
            :to="e.code ? `/stock/${e.code}` : '#'"
            class="tag"
          >{{ e.name || e.code }}</router-link>
        </div>
      </div>

      <!-- 事件 -->
      <div v-if="news.events && news.events.length" class="analysis-section">
        <span class="label">事件</span>
        <div class="tag-list">
          <span v-for="(ev, i) in news.events" :key="i" class="tag">
            {{ ev.type }}{{ ev.subtype ? ' · ' + ev.subtype : '' }}
          </span>
        </div>
      </div>

      <!-- 标签 -->
      <div v-if="news.tags && news.tags.length" class="analysis-section">
        <span class="label">标签</span>
        <div class="tag-list">
          <span v-for="(tag, i) in news.tags" :key="i" class="tag">{{ tag }}</span>
        </div>
      </div>
    </div>

    <!-- 返回 -->
    <div class="back-row">
      <router-link to="/" class="back-link">← 返回首页</router-link>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { useRoute } from "vue-router";
import { getNewsDetail } from "../api/stock";
import type { NewsDetail } from "../types";

const route = useRoute();
const news = ref<NewsDetail | null>(null);
const loading = ref(true);

async function loadDetail(id: number) {
  loading.value = true;
  const res = await getNewsDetail(id);
  news.value = res.code === 0 ? res.data : null;
  loading.value = false;
}

const hasAnalysis = computed(() => {
  if (!news.value) return false;
  return (
    news.value.sentiment != null ||
    (news.value.entities && news.value.entities.length > 0) ||
    (news.value.events && news.value.events.length > 0) ||
    (news.value.tags && news.value.tags.length > 0)
  );
});

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

function formatTime(t?: string | null) {
  if (!t) return "";
  return t.replace("T", " ").substring(0, 16);
}

onMounted(() => loadDetail(Number(route.params.id)));
watch(() => route.params.id, (id) => { if (id) loadDetail(Number(id)); });
</script>

<style scoped>
.detail {
  max-width: 800px;
  margin: 0 auto;
  display: flex;
  flex-direction: column;
  gap: 16px;
}
.loading, .not-found {
  text-align: center;
  padding: 60px 0;
  color: var(--text-secondary);
}

/* 标题区 */
.header-card {
  padding-bottom: 16px;
}
.header-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 12px;
  font-size: 13px;
}
.source {
  color: var(--text-secondary);
  font-weight: 500;
}
.time {
  color: var(--text-muted);
}
.category {
  color: var(--blue);
  font-size: 12px;
  padding: 1px 6px;
  background: var(--blue-light);
  border-radius: 4px;
}
.title {
  font-size: 22px;
  font-weight: 700;
  line-height: 1.5;
  margin-bottom: 8px;
}
.original-link {
  font-size: 13px;
}
.original-link a {
  color: var(--text-secondary);
}
.original-link a:hover {
  color: var(--primary);
}

/* 涉及股票 */
.stocks-row {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}
.stock-tag {
  display: flex;
  align-items: center;
  gap: 6px;
  padding: 6px 14px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-light);
  border-radius: var(--radius-sm);
  text-decoration: none;
  transition: all 0.2s;
}
.stock-tag:hover {
  border-color: var(--primary);
  background: var(--primary-light);
  text-decoration: none;
}
.stock-name {
  font-size: 14px;
  font-weight: 500;
  color: var(--text);
}
.stock-code {
  font-size: 12px;
  color: var(--text-muted);
}

/* 摘要 */
.summary-text {
  font-size: 15px;
  line-height: 1.8;
  color: var(--text);
}

/* 原文 */
.content-text {
  font-size: 14px;
  line-height: 1.8;
  color: var(--text-secondary);
  white-space: pre-wrap;
}

/* 要点 */
.key-points {
  padding-left: 20px;
}
.key-points li {
  font-size: 14px;
  line-height: 1.8;
  color: var(--text);
  margin-bottom: 4px;
}

/* 分析区 */
.analysis-card h3 {
  margin-bottom: 16px;
}
.analysis-section {
  display: flex;
  align-items: flex-start;
  gap: 12px;
  padding: 10px 0;
  border-bottom: 1px solid var(--border-light);
}
.analysis-section:last-child {
  border-bottom: none;
}
.analysis-section .label {
  flex-shrink: 0;
  width: 48px;
  font-size: 13px;
  color: var(--text-muted);
  padding-top: 2px;
}
.score {
  font-size: 13px;
  color: var(--text-secondary);
}
.tag-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

/* 卡片通用 */
.card h3 {
  font-size: 16px;
  margin-bottom: 12px;
}

/* 返回 */
.back-row {
  padding: 8px 0 24px;
}
.back-link {
  font-size: 14px;
  color: var(--text-secondary);
}
.back-link:hover {
  color: var(--primary);
}
</style>
