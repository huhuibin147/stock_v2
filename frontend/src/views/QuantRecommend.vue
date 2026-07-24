<template>
  <div class="quant-page">
    <div class="page-header">
      <h2>📈 量化推荐</h2>
      <span class="desc">纯算法策略，仅供参考</span>
    </div>

    <div class="tabs">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        :class="['tab', { active: activeTab === tab.key }]"
        @click="activeTab = tab.key"
      >
        {{ tab.label }}
      </button>
    </div>

    <div class="strategy-desc" v-if="currentStrategy">
      {{ currentStrategy.description }}
    </div>

    <div class="signals-list" v-if="currentSignals.length">
      <div v-for="signal in currentSignals" :key="signal.code" class="signal-card">
        <div class="signal-header">
          <div class="signal-stock">
            <a :href="`https://xueqiu.com/S/${marketPrefix(signal.code)}${signal.code}`" target="_blank" class="stock-link">
              <span class="stock-name">{{ signal.name }}</span>
              <span class="stock-code">{{ signal.code }}</span>
            </a>
          </div>
          <div class="signal-score">
            <span class="score-badge" :class="scoreClass(signal.score)">{{ signal.score }}</span>
          </div>
        </div>
        <div class="signal-reason">{{ signal.reason }}</div>
        <div class="signal-indicators">
          <span v-for="(value, key) in signal.indicators" :key="key" class="indicator">
            {{ formatIndicator(key, value) }}
          </span>
        </div>
        <div class="signal-actions">
          <router-link :to="`/stock/${signal.code}`" class="action-link">详情</router-link>
          <a :href="`https://xueqiu.com/S/${marketPrefix(signal.code)}${signal.code}`" target="_blank" class="action-link">雪球</a>
        </div>
      </div>
    </div>

    <div v-else class="empty">
      <p v-if="loading">加载中...</p>
      <p v-else>暂无推荐信号</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { get } from "../api/request";

interface Signal {
  code: string;
  name: string;
  reason: string;
  score: number;
  indicators: Record<string, any>;
}

interface Strategy {
  name: string;
  display_name: string;
  description: string;
}

const strategies = ref<Strategy[]>([]);
const allSignals = ref<Record<string, Signal[]>>({});
const loading = ref(false);
const activeTab = ref("bottom_break");

const tabs = computed(() =>
  strategies.value.map((s) => ({
    key: s.name,
    label: s.display_name,
  }))
);

const currentStrategy = computed(() =>
  strategies.value.find((s) => s.name === activeTab.value)
);

const currentSignals = computed(() =>
  allSignals.value[activeTab.value] || []
);

function marketPrefix(code: string): string {
  if (code.startsWith("6")) return "SH";
  return "SZ";
}

function scoreClass(score: number): string {
  if (score >= 80) return "score-high";
  if (score >= 60) return "score-medium";
  return "score-low";
}

function formatIndicator(key: string, value: any): string {
  if (value === null || value === undefined) return "";
  const labels: Record<string, string> = {
    close: "收盘",
    volume_ratio: "量比",
    price_vs_avg: "偏离",
    pe: "PE",
    pb: "PB",
    roe: "ROE",
    net_margin: "净利率",
    eps: "EPS",
    yang_days: "连阳",
    total_pct: "涨幅",
    high_10d: "10日高",
    amplitude: "振幅",
    break_pct: "突破",
    shrink_days: "缩量天",
    vol_increasing: "量增",
    avg_volume_5: "5日均量",
  };
  const label = labels[key] || key;

  if (key === "vol_increasing") return value ? "量能递增" : "";
  if (key.includes("ratio")) return `${label}:${value}倍`;
  if (key.includes("pct") || key === "roe" || key === "net_margin") return `${label}:${value}%`;
  if (key === "close" || key === "price") return `${label}:${value}`;
  if (key === "pe" || key === "pb") return `${label}:${value}`;
  if (key === "eps") return `${label}:${value}`;
  if (key === "avg_volume_5") return `${label}:${(value / 10000).toFixed(0)}万手`;
  return `${label}:${value}`;
}

async function loadData() {
  loading.value = true;
  try {
    const [stratRes, signalRes] = await Promise.all([
      get<Strategy[]>("/api/v1/quant/strategies"),
      get<Record<string, Signal[]>>("/api/v1/quant/recommend?limit=20"),
    ]);
    if (stratRes.code === 0) strategies.value = stratRes.data;
    if (signalRes.code === 0) allSignals.value = signalRes.data;
  } catch (e) {
    console.error("Failed to load quant data:", e);
  }
  loading.value = false;
}

onMounted(loadData);
</script>

<style scoped>
.quant-page {
  max-width: 900px;
  margin: 0 auto;
  padding: 20px 16px;
}

.page-header {
  display: flex;
  align-items: baseline;
  gap: 12px;
  margin-bottom: 20px;
}

.page-header h2 {
  font-size: 20px;
  margin: 0;
}

.desc {
  font-size: 13px;
  color: var(--text-muted);
}

.tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 12px;
  border-bottom: 1px solid var(--border-light);
  padding-bottom: 12px;
  overflow-x: auto;
}

.tab {
  padding: 8px 14px;
  border: 1px solid var(--border);
  border-radius: 20px;
  background: #fff;
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
  color: var(--text-secondary);
  white-space: nowrap;
}

.tab:hover {
  border-color: var(--primary);
  color: var(--primary);
}

.tab.active {
  background: var(--primary);
  border-color: var(--primary);
  color: #fff;
}

.strategy-desc {
  font-size: 13px;
  color: var(--text-muted);
  margin-bottom: 16px;
  padding: 10px 12px;
  background: var(--bg-secondary);
  border-radius: 6px;
}

.signals-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.signal-card {
  background: #fff;
  border: 1px solid var(--border-light);
  border-radius: 8px;
  padding: 16px;
  transition: box-shadow 0.2s;
}

.signal-card:hover {
  box-shadow: 0 2px 8px rgba(0, 0, 0, 0.06);
}

.signal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 8px;
}

.signal-stock {
  display: flex;
  align-items: center;
  gap: 8px;
}

.stock-link {
  display: flex;
  align-items: center;
  gap: 8px;
  text-decoration: none;
  color: inherit;
}

.stock-link:hover .stock-name {
  color: var(--primary);
}

.stock-name {
  font-size: 16px;
  font-weight: 600;
  transition: color 0.2s;
}

.stock-code {
  font-size: 13px;
  color: var(--text-muted);
  font-family: monospace;
}

.score-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 40px;
  height: 40px;
  border-radius: 50%;
  font-size: 14px;
  font-weight: 700;
}

.score-high {
  background: #e8f5e9;
  color: #2e7d32;
}

.score-medium {
  background: #fff3e0;
  color: #e65100;
}

.score-low {
  background: #f5f5f5;
  color: #757575;
}

.signal-reason {
  font-size: 14px;
  color: var(--text);
  margin-bottom: 10px;
  line-height: 1.5;
}

.signal-indicators {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 10px;
}

.indicator {
  font-size: 12px;
  padding: 3px 8px;
  background: var(--bg-secondary);
  border-radius: 4px;
  color: var(--text-secondary);
}

.signal-actions {
  display: flex;
  gap: 12px;
}

.action-link {
  font-size: 13px;
  color: var(--primary);
  text-decoration: none;
}

.action-link:hover {
  text-decoration: underline;
}

.empty {
  text-align: center;
  padding: 60px 0;
  color: var(--text-muted);
}

@media (max-width: 640px) {
  .tabs {
    gap: 6px;
  }

  .tab {
    padding: 6px 10px;
    font-size: 12px;
  }

  .signal-header {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }
}
</style>
