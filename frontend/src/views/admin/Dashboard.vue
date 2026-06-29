<template>
  <div class="dashboard">
    <h2>系统概览</h2>

    <!-- Stats Cards -->
    <div class="stats-grid" v-if="status">
      <div class="stat-card" v-for="(count, table) in status.tables" :key="table">
        <div class="stat-value">{{ count.toLocaleString() }}</div>
        <div class="stat-label">{{ tableLabels[table] || table }}</div>
      </div>
      <div class="stat-card">
        <div class="stat-value">{{ status.db_size_human }}</div>
        <div class="stat-label">数据库大小</div>
      </div>
    </div>

    <!-- Action Cards -->
    <h2>数据采集</h2>
    <div class="actions-grid">
      <div class="action-card">
        <div class="action-title">股票数据导入</div>
        <div class="action-desc">从AKShare导入A股全量股票列表</div>
        <button class="btn" @click="doAction('stocks')" :disabled="loading.stocks">
          {{ loading.stocks ? '导入中...' : '立即导入' }}
        </button>
      </div>
      <div class="action-card">
        <div class="action-title">概念板块导入</div>
        <div class="action-desc">从AKShare导入概念板块列表</div>
        <button class="btn" @click="doAction('concepts')" :disabled="loading.concepts">
          {{ loading.concepts ? '导入中...' : '立即导入' }}
        </button>
      </div>
      <div class="action-card">
        <div class="action-title">概念成分股关联</div>
        <div class="action-desc">导入各概念板块的成分股（耗时较长）</div>
        <button class="btn" @click="doAction('concept-stocks')" :disabled="loading.conceptStocks">
          {{ loading.conceptStocks ? '导入中...' : '立即导入' }}
        </button>
      </div>
      <div class="action-card">
        <div class="action-title">东方财富资讯采集</div>
        <div class="action-desc">采集最新财经新闻，自动过滤+分析+入库</div>
        <button class="btn btn-primary" @click="doAction('eastmoney')" :disabled="loading.eastmoney">
          {{ loading.eastmoney ? '采集中...' : '立即采集' }}
        </button>
      </div>
    </div>

    <!-- Logs -->
    <h2>操作日志</h2>
    <div class="logs-table">
      <div v-if="!logs.length" class="empty">暂无日志</div>
      <table v-else>
        <thead>
          <tr><th>时间</th><th>操作</th><th>详情</th><th>状态</th></tr>
        </thead>
        <tbody>
          <tr v-for="log in logs" :key="log.id">
            <td class="log-time">{{ log.created_at }}</td>
            <td>{{ actionLabels[log.action] || log.action }}</td>
            <td class="log-detail">{{ log.detail }}</td>
            <td>
              <span :class="['badge', statusBadge(log.status)]">{{ log.status }}</span>
            </td>
          </tr>
        </tbody>
      </table>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from "vue";
import {
  getSystemStatus, getAdminLogs,
  triggerImportStocks, triggerImportConcepts, triggerImportConceptStocks, triggerCollectEastmoney,
} from "../../api/admin";
import type { SystemStatus, AdminLog } from "../../api/admin";

const status = ref<SystemStatus | null>(null);
const logs = ref<AdminLog[]>([]);
const loading = reactive({
  stocks: false,
  concepts: false,
  conceptStocks: false,
  eastmoney: false,
});

const tableLabels: Record<string, string> = {
  stocks: "股票",
  news: "资讯",
  events: "事件",
  concepts: "概念",
  industry_chains: "产业链",
  news_stocks: "资讯关联",
};

const actionLabels: Record<string, string> = {
  import_stocks: "股票导入",
  import_concepts: "概念导入",
  import_concept_stocks: "成分股关联",
  collect_eastmoney: "东方财富采集",
};

function statusBadge(s: string) {
  if (s === "success") return "badge-positive";
  if (s === "failed") return "badge-negative";
  return "badge-neutral";
}

async function load() {
  const [s, l] = await Promise.all([getSystemStatus(), getAdminLogs()]);
  if (s.code === 0) status.value = s.data;
  if (l.code === 0) logs.value = l.data;
}

async function doAction(type: string) {
  loading[type as keyof typeof loading] = true;
  try {
    let res;
    switch (type) {
      case "stocks": res = await triggerImportStocks(); break;
      case "concepts": res = await triggerImportConcepts(); break;
      case "concept-stocks": res = await triggerImportConceptStocks(); break;
      case "eastmoney": res = await triggerCollectEastmoney(); break;
    }
    if (res?.code === 0) {
      // 等一下再刷新日志
      setTimeout(async () => {
        const l = await getAdminLogs();
        if (l.code === 0) logs.value = l.data;
        const s = await getSystemStatus();
        if (s.code === 0) status.value = s.data;
        loading[type as keyof typeof loading] = false;
      }, 3000);
    } else {
      loading[type as keyof typeof loading] = false;
    }
  } catch {
    loading[type as keyof typeof loading] = false;
  }
}

onMounted(load);
</script>

<style scoped>
.dashboard h2 {
  font-size: 18px;
  margin: 24px 0 12px;
}
.dashboard h2:first-child { margin-top: 0; }

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 12px;
  margin-bottom: 24px;
}
.stat-card {
  background: var(--bg);
  border: 1px solid var(--border-light);
  border-radius: var(--radius);
  padding: 16px;
  text-align: center;
}
.stat-value { font-size: 24px; font-weight: 800; color: var(--primary); }
.stat-label { font-size: 12px; color: var(--text-secondary); margin-top: 4px; }

.actions-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 12px;
  margin-bottom: 24px;
}
.action-card {
  background: var(--bg);
  border: 1px solid var(--border-light);
  border-radius: var(--radius);
  padding: 16px;
}
.action-title { font-weight: 600; margin-bottom: 4px; }
.action-desc { font-size: 13px; color: var(--text-secondary); margin-bottom: 12px; }

.btn {
  padding: 6px 16px;
  border: 1px solid var(--border);
  border-radius: var(--radius-sm);
  background: var(--bg);
  cursor: pointer;
  font-size: 13px;
  transition: all 0.2s;
}
.btn:hover:not(:disabled) { border-color: var(--primary); color: var(--primary); }
.btn:disabled { opacity: 0.5; cursor: not-allowed; }
.btn-primary {
  background: var(--primary);
  color: #fff;
  border-color: var(--primary);
}
.btn-primary:hover:not(:disabled) { background: #c0392b; color: #fff; }

.logs-table {
  background: var(--bg);
  border: 1px solid var(--border-light);
  border-radius: var(--radius);
  overflow: hidden;
}
.logs-table table { width: 100%; border-collapse: collapse; font-size: 13px; }
.logs-table th {
  background: var(--bg-secondary);
  padding: 8px 12px;
  text-align: left;
  font-weight: 600;
  border-bottom: 1px solid var(--border-light);
}
.logs-table td {
  padding: 8px 12px;
  border-bottom: 1px solid var(--border-light);
}
.logs-table tr:last-child td { border-bottom: none; }
.log-time { font-family: monospace; font-size: 12px; color: var(--text-muted); white-space: nowrap; }
.log-detail { max-width: 300px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

@media (max-width: 768px) {
  .actions-grid { grid-template-columns: 1fr; }
}
</style>
