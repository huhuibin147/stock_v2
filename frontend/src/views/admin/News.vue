<template>
  <div class="admin-news">
    <div class="toolbar">
      <h2>资讯管理</h2>
      <button class="btn" @click="load(1)">刷新</button>
    </div>

    <div class="table-wrap">
      <table v-if="items.length">
        <thead>
          <tr>
            <th>ID</th><th>来源</th><th>标题</th><th>情感</th><th>重要度</th><th>时间</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="n in items" :key="n.id">
            <td>{{ n.id }}</td>
            <td>{{ n.source }}</td>
            <td class="title-cell" :title="n.title">{{ n.title }}</td>
            <td>
              <span :class="['badge', sentimentClass(n.sentiment)]">{{ sentimentText(n.sentiment) }}</span>
            </td>
            <td>{{ n.importance_score?.toFixed(2) || '-' }}</td>
            <td class="time-cell">{{ n.published_at?.replace('T', ' ').substring(0, 16) || '-' }}</td>
          </tr>
        </tbody>
      </table>
      <div v-else class="empty">暂无资讯数据</div>
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
import { getAdminNews } from "../../api/admin";
import type { AdminNews } from "../../api/admin";

const items = ref<AdminNews[]>([]);
const page = ref(1);
const pageSize = 20;
const total = ref(0);

async function load(p: number) {
  page.value = p;
  const res = await getAdminNews(p, pageSize);
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
  white-space: nowrap;
}
td { padding: 8px 12px; border-bottom: 1px solid var(--border-light); }
tr:last-child td { border-bottom: none; }
.title-cell { max-width: 350px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
.time-cell { font-family: monospace; font-size: 12px; color: var(--text-muted); white-space: nowrap; }

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
