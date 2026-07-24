<template>
  <div class="xueqiu-page">
    <div class="page-header">
      <h2>📊 热度排行</h2>
      <span class="update-time" v-if="updateTime">数据更新: {{ updateTime }}</span>
    </div>

    <div class="tabs">
      <button
        v-for="tab in tabs"
        :key="tab.key"
        :class="['tab', { active: activeTab === tab.key }]"
        @click="activeTab = tab.key"
      >
        {{ tab.icon }} {{ tab.label }}
      </button>
    </div>

    <div class="rank-table" v-if="currentRank.length">
      <table>
        <thead>
          <tr>
            <th class="col-rank">排名</th>
            <th class="col-code">代码</th>
            <th class="col-name">名称</th>
            <th class="col-count">{{ countLabel }}</th>
            <th class="col-price">最新价</th>
            <th class="col-action">操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in currentRank" :key="item.code" :class="rankClass(item.rank)">
            <td class="col-rank">
              <span class="rank-badge" :class="rankBadgeClass(item.rank)">{{ item.rank }}</span>
            </td>
            <td class="col-code">
              <a :href="`https://xueqiu.com/S/${marketPrefix(item.code)}${item.code}`" target="_blank" class="xueqiu-link">{{ item.code }}</a>
            </td>
            <td class="col-name">
              <a :href="`https://xueqiu.com/S/${marketPrefix(item.code)}${item.code}`" target="_blank" class="xueqiu-link">{{ item.name }}</a>
            </td>
            <td class="col-count">{{ formatCount(item.count) }}</td>
            <td class="col-price">{{ item.price != null ? item.price.toFixed(2) : '-' }}</td>
            <td class="col-action">
              <router-link :to="`/stock/${item.code}`" class="detail-link">详情</router-link>
            </td>
          </tr>
        </tbody>
      </table>
    </div>

    <div v-else class="empty">
      <p>暂无数据</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { get } from "../api/request";

interface RankItem {
  rank: number;
  code: string;
  name: string;
  count: number;
  price: number | null;
}

interface XueqiuData {
  update_time: string | null;
  tweet_rank: RankItem[];
  deal_rank: RankItem[];
  follow_rank: RankItem[];
}

const tabs = [
  { key: "tweet", label: "讨论热度", icon: "💬" },
  { key: "deal", label: "交易热度", icon: "📈" },
  { key: "follow", label: "关注热度", icon: "👁️" },
];

const activeTab = ref("tweet");
const data = ref<XueqiuData | null>(null);
const loading = ref(false);

const updateTime = computed(() => data.value?.update_time || null);

const currentRank = computed(() => {
  if (!data.value) return [];
  switch (activeTab.value) {
    case "tweet": return data.value.tweet_rank;
    case "deal": return data.value.deal_rank;
    case "follow": return data.value.follow_rank;
    default: return [];
  }
});

const countLabel = computed(() => {
  switch (activeTab.value) {
    case "tweet": return "讨论数";
    case "deal": return "交易分享";
    case "follow": return "关注人数";
    default: return "热度";
  }
});

function formatCount(count: number): string {
  if (count >= 10000) {
    return (count / 10000).toFixed(1) + "万";
  }
  return count.toLocaleString();
}

function marketPrefix(code: string): string {
  // 6开头=上海SH，0/3开头=深圳SZ
  if (code.startsWith("6")) return "SH";
  return "SZ";
}

function rankClass(rank: number): string {
  if (rank <= 3) return "rank-top";
  return "";
}

function rankBadgeClass(rank: number): string {
  if (rank === 1) return "badge-gold";
  if (rank === 2) return "badge-silver";
  if (rank === 3) return "badge-bronze";
  return "";
}

async function loadData() {
  loading.value = true;
  try {
    const res = await get<XueqiuData>("/api/v1/xueqiu/ranking");
    if (res.code === 0) {
      data.value = res.data;
    }
  } catch (e) {
    console.error("Failed to load xueqiu data:", e);
  }
  loading.value = false;
}

onMounted(loadData);
</script>

<style scoped>
.xueqiu-page {
  max-width: 900px;
  margin: 0 auto;
  padding: 20px 16px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}

.page-header h2 {
  font-size: 20px;
  margin: 0;
}

.update-time {
  font-size: 12px;
  color: var(--text-muted);
}

.tabs {
  display: flex;
  gap: 8px;
  margin-bottom: 16px;
  border-bottom: 1px solid var(--border-light);
  padding-bottom: 12px;
}

.tab {
  padding: 8px 16px;
  border: 1px solid var(--border);
  border-radius: 20px;
  background: #fff;
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
  color: var(--text-secondary);
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

.rank-table {
  background: #fff;
  border-radius: 8px;
  border: 1px solid var(--border-light);
  overflow: hidden;
}

table {
  width: 100%;
  border-collapse: collapse;
}

th {
  background: var(--bg-secondary);
  padding: 12px 16px;
  text-align: left;
  font-size: 13px;
  font-weight: 600;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-light);
}

td {
  padding: 12px 16px;
  font-size: 14px;
  border-bottom: 1px solid var(--border-light);
}

tr:last-child td {
  border-bottom: none;
}

tr:hover {
  background: var(--bg-secondary);
}

.col-rank {
  width: 60px;
  text-align: center;
}

.col-code {
  width: 80px;
  font-family: monospace;
}

.col-name {
  min-width: 100px;
}

.col-count {
  width: 100px;
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.col-price {
  width: 80px;
  text-align: right;
  font-variant-numeric: tabular-nums;
}

.col-action {
  width: 60px;
  text-align: center;
}

.rank-badge {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  font-size: 13px;
  font-weight: 600;
  background: var(--bg-secondary);
  color: var(--text-secondary);
}

.badge-gold {
  background: linear-gradient(135deg, #FFD700, #FFA500);
  color: #fff;
}

.badge-silver {
  background: linear-gradient(135deg, #C0C0C0, #A0A0A0);
  color: #fff;
}

.badge-bronze {
  background: linear-gradient(135deg, #CD7F32, #B8860B);
  color: #fff;
}

.rank-top td {
  font-weight: 500;
}

.detail-link {
  font-size: 13px;
  color: var(--primary);
  text-decoration: none;
}

.detail-link:hover {
  text-decoration: underline;
}

.xueqiu-link {
  color: inherit;
  text-decoration: none;
}

.xueqiu-link:hover {
  color: var(--primary);
  text-decoration: underline;
}

.empty {
  text-align: center;
  padding: 60px 0;
  color: var(--text-muted);
}

@media (max-width: 640px) {
  .tabs {
    flex-wrap: wrap;
  }

  .tab {
    flex: 1;
    text-align: center;
    padding: 8px 12px;
    font-size: 13px;
  }

  th, td {
    padding: 10px 12px;
    font-size: 13px;
  }

  .col-count,
  .col-price {
    font-size: 12px;
  }
}
</style>
