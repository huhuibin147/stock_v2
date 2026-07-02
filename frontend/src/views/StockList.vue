<template>
  <div class="stock-list-page">
    <div class="page-header">
      <h2>公司列表</h2>
      <div class="header-actions">
        <input v-model="searchQ" type="search" placeholder="搜索代码或名称" @input="onSearch" />
      </div>
    </div>

    <div class="table-wrap">
      <table v-if="items.length">
        <thead>
          <tr>
            <th class="sortable" @click="toggleSort('code')">
              代码 <span class="arrow" v-if="sortField === 'code'">{{ sortOrder === 'asc' ? '↑' : '↓' }}</span>
            </th>
            <th class="sortable" @click="toggleSort('name')">
              名称 <span class="arrow" v-if="sortField === 'name'">{{ sortOrder === 'asc' ? '↑' : '↓' }}</span>
            </th>
            <th class="num sortable" @click="toggleSort('last_price')">
              最新价 <span class="arrow" v-if="sortField === 'last_price'">{{ sortOrder === 'asc' ? '↑' : '↓' }}</span>
            </th>
            <th class="num sortable" @click="toggleSort('pct_change')">
              涨跌% <span class="arrow" v-if="sortField === 'pct_change'">{{ sortOrder === 'asc' ? '↑' : '↓' }}</span>
            </th>
            <th class="num sortable" @click="toggleSort('turnover_amount')">
              成交额 <span class="arrow" v-if="sortField === 'turnover_amount'">{{ sortOrder === 'asc' ? '↑' : '↓' }}</span>
            </th>
            <th class="num sortable" @click="toggleSort('market_cap')">
              总市值 <span class="arrow" v-if="sortField === 'market_cap'">{{ sortOrder === 'asc' ? '↑' : '↓' }}</span>
            </th>
            <th>行业</th>
          </tr>
        </thead>
        <tbody>
          <router-link
            v-for="s in items"
            :key="s.code"
            :to="`/stock/${s.code}`"
            tag="tr"
            class="stock-row"
          >
            <td class="code-cell">{{ s.code }}.{{ s.market }}</td>
            <td class="name-cell">{{ s.name }}</td>
            <td class="num">{{ s.last_price != null ? s.last_price.toFixed(2) : '-' }}</td>
            <td class="num" :class="pctClass(s.pct_change)">{{ s.pct_change != null ? (s.pct_change > 0 ? '+' : '') + s.pct_change.toFixed(2) + '%' : '-' }}</td>
            <td class="num">{{ formatAmount(s.turnover_amount) }}</td>
            <td class="num">{{ formatCap(s.market_cap) }}</td>
            <td class="industry-cell">{{ s.industry || '-' }}</td>
          </router-link>
        </tbody>
      </table>
      <div v-else class="empty">暂无数据</div>
    </div>

    <div class="pagination" v-if="total > pageSize">
      <button class="btn" :disabled="page <= 1" @click="load(page - 1)">上一页</button>
      <span>第 {{ page }} / {{ Math.ceil(total / pageSize) }} 页 (共 {{ total }} 家)</span>
      <button class="btn" :disabled="page >= Math.ceil(total / pageSize)" @click="load(page + 1)">下一页</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted, nextTick } from "vue";
import { onBeforeRouteLeave } from "vue-router";
import { get } from "../api/request";

interface StockItem {
  code: string;
  name: string;
  market: string;
  industry: string | null;
  concepts: string[];
  core_business: string | null;
  pe_ttm: number | null;
  pb: number | null;
  market_cap: number | null;
  turnover_amount: number | null;
  last_price: number | null;
  pct_change: number | null;
  volume: number | null;
}

const items = ref<StockItem[]>([]);
const page = ref(1);
const pageSize = 100;
const total = ref(0);
const searchQ = ref("");
const sortField = ref("turnover_amount");
const sortOrder = ref("desc");
let searchTimer: ReturnType<typeof setTimeout> | null = null;
let autoRefreshTimer: ReturnType<typeof setInterval> | null = null;

async function load(p: number) {
  page.value = p;
  const params = new URLSearchParams({
    page: String(p),
    page_size: String(pageSize),
    sort: sortField.value,
    order: sortOrder.value,
  });
  if (searchQ.value) params.set("q", searchQ.value);
  const res = await get<{ items: StockItem[]; total: number }>(`/api/v1/stocks?${params}`);
  if (res.code === 0) {
    items.value = res.data.items;
    total.value = res.data.total;
  }
}

function toggleSort(field: string) {
  if (sortField.value === field) {
    sortOrder.value = sortOrder.value === "desc" ? "asc" : "desc";
  } else {
    sortField.value = field;
    sortOrder.value = "desc";
  }
  load(1);
}

function onSearch() {
  if (searchTimer) clearTimeout(searchTimer);
  searchTimer = setTimeout(() => load(1), 300);
}

function isTradingTime(): boolean {
  const now = new Date();
  const day = now.getDay();
  if (day === 0 || day === 6) return false; // 周末

  const hour = now.getHours();
  const minute = now.getMinutes();
  const time = hour * 100 + minute;

  // 9:00-11:59, 13:00-14:59
  return (time >= 900 && time <= 1159) || (time >= 1300 && time <= 1459);
}

function startAutoRefresh() {
  // 盘中每1分钟自动刷新
  if (isTradingTime()) {
    autoRefreshTimer = setInterval(() => {
      if (isTradingTime()) {
        load(page.value);
      } else {
        // 非交易时间停止刷新
        if (autoRefreshTimer) {
          clearInterval(autoRefreshTimer);
          autoRefreshTimer = null;
        }
      }
    }, 60000); // 1分钟 = 60000毫秒
  }
}

function formatCap(val?: number | null) {
  if (val == null) return "-";
  if (val >= 1e12) return (val / 1e12).toFixed(1) + "万亿";
  if (val >= 1e8) return (val / 1e8).toFixed(0) + "亿";
  return val.toLocaleString();
}

function formatAmount(val?: number | null) {
  if (val == null) return "-";
  if (val >= 1e8) return (val / 1e8).toFixed(1) + "亿";
  if (val >= 1e4) return (val / 1e4).toFixed(0) + "万";
  return val.toLocaleString();
}

function pctClass(val?: number | null) {
  if (val == null) return "";
  if (val > 0) return "pct-up";
  if (val < 0) return "pct-down";
  return "";
}

// 保存滚动位置
let savedScrollTop = 0;

onBeforeRouteLeave((_to, _from, next) => {
  // 保存当前滚动位置
  savedScrollTop = window.scrollY;
  next();
});

onMounted(() => {
  load(1).then(() => {
    // 恢复滚动位置
    nextTick(() => {
      if (savedScrollTop > 0) {
        window.scrollTo(0, savedScrollTop);
      }
    });
  });
  startAutoRefresh();
});

onUnmounted(() => {
  if (searchTimer) {
    clearTimeout(searchTimer);
    searchTimer = null;
  }
  if (autoRefreshTimer) {
    clearInterval(autoRefreshTimer);
    autoRefreshTimer = null;
  }
});
</script>

<style scoped>
.stock-list-page {
  max-width: 1200px;
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
.header-actions input {
  width: 240px;
  padding: 8px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  font-size: 13px;
}
.header-actions input:focus { border-color: var(--primary); outline: none; }

.table-wrap {
  background: var(--bg);
  border: 1px solid var(--border-light);
  border-radius: var(--radius);
  overflow-x: auto;
}
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th {
  background: var(--bg-secondary);
  padding: 10px 12px;
  text-align: left;
  font-weight: 600;
  border-bottom: 1px solid var(--border-light);
  white-space: nowrap;
}
th.num { text-align: right; }
th.sortable { cursor: pointer; user-select: none; }
th.sortable:hover { color: var(--primary); }
th .arrow { font-size: 11px; color: var(--primary); }

td { padding: 10px 12px; border-bottom: 1px solid var(--border-light); }
td.num { text-align: right; font-variant-numeric: tabular-nums; }
.stock-row { cursor: pointer; transition: background 0.15s; text-decoration: none; color: inherit; display: table-row; }
.stock-row:hover { background: var(--bg-secondary); }
.stock-row td { border-bottom: 1px solid var(--border-light); }
.code-cell { font-family: "SF Mono", monospace; font-size: 12px; color: var(--primary); font-weight: 600; white-space: nowrap; }
.name-cell { font-weight: 500; white-space: nowrap; }
.biz-cell { max-width: 200px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--text-secondary); font-size: 12px; }
.industry-cell { max-width: 120px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--text-secondary); font-size: 12px; }

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
.pct-up { color: var(--primary); }
.pct-down { color: var(--success); }

@media (max-width: 768px) {
  .biz-cell { display: none; }
}
</style>
