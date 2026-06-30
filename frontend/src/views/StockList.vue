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
            <th>代码</th>
            <th>名称</th>
            <th>行业</th>
            <th class="num">PE(TTM)</th>
            <th class="num">PB</th>
            <th class="num">总市值</th>
            <th>核心业务</th>
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
            <td>{{ s.industry || '-' }}</td>
            <td class="num">{{ s.pe_ttm != null ? s.pe_ttm.toFixed(1) : '-' }}</td>
            <td class="num">{{ s.pb != null ? s.pb.toFixed(2) : '-' }}</td>
            <td class="num">{{ formatCap(s.market_cap) }}</td>
            <td class="biz-cell">{{ s.core_business || '-' }}</td>
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
import { ref, onMounted } from "vue";
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
}

const items = ref<StockItem[]>([]);
const page = ref(1);
const pageSize = 30;
const total = ref(0);
const searchQ = ref("");
let timer: ReturnType<typeof setTimeout> | null = null;

async function load(p: number) {
  page.value = p;
  const params = new URLSearchParams({ page: String(p), page_size: String(pageSize) });
  if (searchQ.value) params.set("q", searchQ.value);
  const res = await get<{ items: StockItem[]; total: number }>(`/api/v1/stocks?${params}`);
  if (res.code === 0) {
    items.value = res.data.items;
    total.value = res.data.total;
  }
}

function onSearch() {
  if (timer) clearTimeout(timer);
  timer = setTimeout(() => load(1), 300);
}

function formatCap(val?: number | null) {
  if (val == null) return "-";
  if (val >= 1e12) return (val / 1e12).toFixed(1) + "万亿";
  if (val >= 1e8) return (val / 1e8).toFixed(0) + "亿";
  return val.toLocaleString();
}

onMounted(() => load(1));
</script>

<style scoped>
.stock-list-page {
  max-width: 1100px;
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
td { padding: 10px 12px; border-bottom: 1px solid var(--border-light); }
td.num { text-align: right; font-variant-numeric: tabular-nums; }
.stock-row { cursor: pointer; transition: background 0.15s; text-decoration: none; color: inherit; display: table-row; }
.stock-row:hover { background: var(--bg-secondary); }
.stock-row td { border-bottom: 1px solid var(--border-light); }
.code-cell { font-family: "SF Mono", monospace; font-size: 12px; color: var(--primary); font-weight: 600; white-space: nowrap; }
.name-cell { font-weight: 500; white-space: nowrap; }
.biz-cell { max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--text-secondary); font-size: 12px; }

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
