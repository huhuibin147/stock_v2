<template>
  <div class="admin-stocks">
    <div class="toolbar">
      <h2>股票管理</h2>
      <div class="toolbar-right">
        <input v-model="searchQ" type="search" placeholder="搜索代码或名称" @input="onSearch" />
        <button class="btn" @click="load(1)">刷新</button>
      </div>
    </div>

    <div class="table-wrap">
      <table v-if="items.length">
        <thead>
          <tr>
            <th>代码</th><th>名称</th><th>市场</th><th>行业</th><th>概念</th><th>核心业务</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="s in items" :key="s.code">
            <td class="code-cell">
              <router-link :to="`/stock/${s.code}`">{{ s.code }}</router-link>
            </td>
            <td>{{ s.name }}</td>
            <td>{{ s.market }}</td>
            <td>{{ s.industry || '-' }}</td>
            <td class="concepts-cell">
              <span v-for="c in s.concepts.slice(0, 3)" :key="c" class="tag-mini">{{ c }}</span>
              <span v-if="s.concepts.length > 3" class="tag-more">+{{ s.concepts.length - 3 }}</span>
            </td>
            <td class="biz-cell">{{ s.core_business || '-' }}</td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty">暂无数据</div>
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
import { getAdminStocks } from "../../api/admin";
import type { AdminStock } from "../../api/admin";

const items = ref<AdminStock[]>([]);
const page = ref(1);
const pageSize = 20;
const total = ref(0);
const searchQ = ref("");
let timer: ReturnType<typeof setTimeout> | null = null;

async function load(p: number) {
  page.value = p;
  const res = await getAdminStocks(p, pageSize, searchQ.value);
  if (res.code === 0) {
    items.value = res.data.items;
    total.value = res.data.total;
  }
}

function onSearch() {
  if (timer) clearTimeout(timer);
  timer = setTimeout(() => load(1), 300);
}

onMounted(() => load(1));
</script>

<style scoped>
.toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.toolbar-right { display: flex; gap: 8px; align-items: center; }
.toolbar-right input { width: 220px; }

.table-wrap {
  background: var(--bg);
  border: 1px solid var(--border-light);
  border-radius: var(--radius);
  overflow-x: auto;
}
table { width: 100%; border-collapse: collapse; font-size: 13px; }
th {
  background: var(--bg-secondary);
  padding: 8px 12px;
  text-align: left;
  font-weight: 600;
  border-bottom: 1px solid var(--border-light);
  white-space: nowrap;
}
td { padding: 8px 12px; border-bottom: 1px solid var(--border-light); }
tr:last-child td { border-bottom: none; }
.code-cell { font-family: monospace; }
.concepts-cell { max-width: 200px; }
.biz-cell { max-width: 250px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.tag-mini {
  display: inline-block;
  padding: 1px 6px;
  background: var(--primary-light);
  color: var(--primary);
  border-radius: 3px;
  font-size: 11px;
  margin-right: 4px;
}
.tag-more { font-size: 11px; color: var(--text-muted); }

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
</style>
