<template>
  <div v-if="loading" class="loading">加载中...</div>
  <div v-else-if="!profile" class="not-found">
    <p>未找到股票信息</p>
    <router-link to="/">返回首页</router-link>
  </div>
  <div v-else class="profile">
    <!-- 公司信息卡片 -->
    <div class="card stock-card">
      <div class="stock-header">
        <h1>{{ profile.stock.name }} <span class="code">{{ profile.stock.code }}.{{ profile.stock.market }}</span></h1>
      </div>
      <div v-if="profile.stock.core_business" class="core-business">
        {{ profile.stock.core_business }}
      </div>
      <div class="meta-row">
        <span v-if="profile.stock.industry" class="meta-tag">{{ profile.stock.industry }}</span>
        <span v-for="c in profile.stock.concepts" :key="c" class="meta-tag concept">{{ c }}</span>
      </div>
    </div>

    <!-- 产业链位置 -->
    <div v-if="profile.chain.layer" class="card chain-card">
      <h3>产业链位置</h3>
      <div class="chain-info">
        <span class="layer">Layer {{ profile.chain.layer }} · {{ profile.chain.layer_name }}</span>
        <span class="position">{{ profile.chain.position }}</span>
      </div>
      <div v-if="profile.chain.upstream.length" class="chain-relations">
        <span class="label">上游：</span>
        <router-link v-for="s in profile.chain.upstream" :key="s.code" :to="`/stock/${s.code}`" class="rel-link">
          {{ s.name }}
        </router-link>
      </div>
      <div v-if="profile.chain.downstream.length" class="chain-relations">
        <span class="label">下游：</span>
        <router-link v-for="s in profile.chain.downstream" :key="s.code" :to="`/stock/${s.code}`" class="rel-link">
          {{ s.name }}
        </router-link>
      </div>
    </div>

    <!-- 情感概览 -->
    <div class="card sentiment-card">
      <h3>近7日情感</h3>
      <div class="sentiment-row">
        <span class="trend" :class="trendClass">{{ profile.sentiment_7d.trend }}</span>
        <span class="badge badge-positive">利好 {{ profile.sentiment_7d.positive }}</span>
        <span class="badge badge-neutral">中性 {{ profile.sentiment_7d.neutral }}</span>
        <span class="badge badge-negative">利空 {{ profile.sentiment_7d.negative }}</span>
      </div>
    </div>

    <!-- 最新动态 -->
    <div class="card">
      <h3>最新动态</h3>
      <div v-if="!profile.recent_news.length" class="empty">暂无资讯</div>
      <div v-for="item in profile.recent_news" :key="item.id" class="news-item">
        <div class="news-header">
          <span :class="['badge', sentimentClass(item.sentiment)]">{{ sentimentText(item.sentiment) }}</span>
          <span class="news-time">{{ formatTime(item.published_at) }}</span>
        </div>
        <div class="news-title">{{ item.title }}</div>
        <div v-if="item.summary" class="news-summary">{{ item.summary }}</div>
      </div>
    </div>

    <!-- 事件时间线 -->
    <div v-if="profile.recent_events.length" class="card">
      <h3>重要事件</h3>
      <div v-for="(ev, i) in profile.recent_events" :key="i" class="event-item">
        <span :class="['badge', ev.impact === 1 ? 'badge-positive' : ev.impact === -1 ? 'badge-negative' : 'badge-neutral']">
          {{ ev.event_type }}
        </span>
        <span class="event-title">{{ ev.title }}</span>
        <span class="event-date">{{ ev.event_date }}</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from "vue";
import { useRoute } from "vue-router";
import { getStockProfile } from "../api/stock";
import type { StockProfile } from "../types";

const route = useRoute();
const profile = ref<StockProfile | null>(null);
const loading = ref(true);

async function loadProfile(code: string) {
  loading.value = true;
  const res = await getStockProfile(code);
  profile.value = res.code === 0 ? res.data : null;
  loading.value = false;
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

function formatTime(t?: string) {
  if (!t) return "";
  return t.replace("T", " ").substring(0, 16);
}

const trendClass = computed(() => {
  const t = profile.value?.sentiment_7d.trend;
  if (t === "偏多") return "trend-positive";
  if (t === "偏空") return "trend-negative";
  return "";
});

onMounted(() => loadProfile(route.params.code as string));
watch(() => route.params.code, (c) => { if (c) loadProfile(c as string); });
</script>

<style scoped>
.profile {
  max-width: 800px;
  margin: 0 auto;
}
.loading, .not-found {
  text-align: center;
  padding: 60px 0;
  color: var(--text-secondary);
}
.stock-header h1 {
  font-size: 24px;
  margin-bottom: 8px;
}
.code {
  font-size: 14px;
  color: var(--text-secondary);
  font-weight: 400;
}
.core-business {
  font-size: 15px;
  color: var(--text-secondary);
  margin-bottom: 12px;
  padding-bottom: 12px;
  border-bottom: 1px solid var(--border);
}
.meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.meta-tag {
  font-size: 12px;
  padding: 2px 8px;
  background: var(--bg-secondary);
  border-radius: 4px;
  color: var(--text-secondary);
}
.meta-tag.concept {
  background: #fde8e8;
  color: var(--primary);
}

.chain-card h3,
.sentiment-card h3,
.card h3 {
  font-size: 16px;
  margin-bottom: 12px;
}
.chain-info {
  display: flex;
  gap: 12px;
  margin-bottom: 8px;
}
.layer {
  font-weight: 600;
  color: var(--primary);
}
.chain-relations {
  font-size: 14px;
  margin-top: 4px;
}
.chain-relations .label {
  color: var(--text-secondary);
}
.rel-link {
  margin-right: 12px;
}

.sentiment-row {
  display: flex;
  align-items: center;
  gap: 12px;
}
.trend {
  font-size: 18px;
  font-weight: 700;
}
.trend-positive { color: var(--primary); }
.trend-negative { color: var(--success); }

.news-item {
  padding: 12px 0;
  border-bottom: 1px solid var(--border);
}
.news-item:last-child { border-bottom: none; }
.news-header {
  display: flex;
  align-items: center;
  gap: 8px;
  margin-bottom: 4px;
}
.news-time {
  font-size: 12px;
  color: var(--text-secondary);
}
.news-title {
  font-size: 14px;
  font-weight: 500;
  margin-bottom: 4px;
}
.news-summary {
  font-size: 13px;
  color: var(--text-secondary);
}

.event-item {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 0;
  border-bottom: 1px solid var(--border);
}
.event-item:last-child { border-bottom: none; }
.event-title {
  flex: 1;
  font-size: 14px;
}
.event-date {
  font-size: 12px;
  color: var(--text-secondary);
}
.empty {
  color: var(--text-secondary);
  font-size: 14px;
}
</style>
