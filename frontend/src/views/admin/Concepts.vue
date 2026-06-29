<template>
  <div class="admin-concepts">
    <div class="toolbar">
      <h2>概念管理</h2>
      <button class="btn" @click="load(1)">刷新</button>
    </div>

    <div class="table-wrap">
      <table v-if="items.length">
        <thead>
          <tr><th>ID</th><th>名称</th><th>分类</th><th>关联股票数</th></tr>
        </thead>
        <tbody>
          <tr v-for="c in items" :key="c.id">
            <td>{{ c.id }}</td>
            <td>{{ c.name }}</td>
            <td>{{ c.category || '-' }}</td>
            <td>{{ c.stock_count }}</td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty">暂无概念数据</div>
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
import { getAdminConcepts } from "../../api/admin";
import type { AdminConcept } from "../../api/admin";

const items = ref<AdminConcept[]>([]);
const page = ref(1);
const pageSize = 50;
const total = ref(0);

async function load(p: number) {
  page.value = p;
  const res = await getAdminConcepts(p, pageSize);
  if (res.code === 0) {
    items.value = res.data.items;
    total.value = res.data.total;
  }
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
}
td { padding: 8px 12px; border-bottom: 1px solid var(--border-light); }
tr:last-child td { border-bottom: none; }

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
