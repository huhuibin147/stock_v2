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
      <div class="action-card disabled">
        <div class="action-title">概念板块导入</div>
        <div class="action-desc">从AKShare导入概念板块列表</div>
        <div class="unavailable">⚠ 依赖东方财富API，当前不可用</div>
      </div>
      <div class="action-card disabled">
        <div class="action-title">概念成分股关联</div>
        <div class="action-desc">导入各概念板块的成分股</div>
        <div class="unavailable">⚠ 依赖东方财富API，当前不可用</div>
      </div>
      <div class="action-card">
        <div class="action-title">东方财富快讯</div>
        <div class="action-desc">7x24快讯，含股票代码</div>
        <button class="btn btn-primary" @click="doAction('eastmoney')" :disabled="loading.eastmoney">
          {{ loading.eastmoney ? '采集中...' : '立即采集' }}
        </button>
      </div>
      <div class="action-card">
        <div class="action-title">同花顺资讯</div>
        <div class="action-desc">公告+新闻，自带股票关联</div>
        <button class="btn btn-primary" @click="doAction('ths')" :disabled="loading.ths">
          {{ loading.ths ? '采集中...' : '立即采集' }}
        </button>
      </div>
      <div class="action-card">
        <div class="action-title">新浪财经</div>
        <div class="action-desc">财经要闻，覆盖面广</div>
        <button class="btn btn-primary" @click="doAction('sina')" :disabled="loading.sina">
          {{ loading.sina ? '采集中...' : '立即采集' }}
        </button>
      </div>
      <div class="action-card highlight">
        <div class="action-title">一键全部采集</div>
        <div class="action-desc">依次采集全部数据源</div>
        <button class="btn btn-primary" @click="doAction('all')" :disabled="loading.all">
          {{ loading.all ? '采集中...' : '全部采集' }}
        </button>
      </div>
    </div>

    <h2>基本面数据</h2>
    <div class="actions-grid">
      <div class="action-card">
        <div class="action-title">估值数据更新</div>
        <div class="action-desc">全市场PE/PB/市值（东方财富源）</div>
        <button class="btn btn-primary" @click="doAction('valuation')" :disabled="loading.valuation">
          {{ loading.valuation ? '更新中...' : '立即更新' }}
        </button>
      </div>
      <div class="action-card">
        <div class="action-title">成交额数据更新</div>
        <div class="action-desc">全市场成交额，用于热门股票筛选</div>
        <button class="btn btn-primary" @click="doAction('turnover')" :disabled="loading.turnover">
          {{ loading.turnover ? '更新中...' : '立即更新' }}
        </button>
      </div>
      <div class="action-card">
        <div class="action-title">K线数据采集</div>
        <div class="action-desc">热门股票日K线（前500只，近5日）</div>
        <button class="btn btn-primary" @click="doAction('kline')" :disabled="loading.kline">
          {{ loading.kline ? '采集中...' : '立即采集' }}
        </button>
      </div>
      <div class="action-card">
        <div class="action-title">财务数据采集</div>
        <div class="action-desc">同花顺源，22项关键指标×最近8季度</div>
        <button class="btn btn-primary" @click="doAction('financials')" :disabled="loading.financials">
          {{ loading.financials ? '采集中...' : '立即采集' }}
        </button>
      </div>
      <div class="action-card">
        <div class="action-title">产业链映射</div>
        <div class="action-desc">将股票匹配到五层产业链节点</div>
        <button class="btn btn-primary" @click="doAction('mapChains')" :disabled="loading.mapChains">
          {{ loading.mapChains ? '映射中...' : '立即映射' }}
        </button>
      </div>
      <div class="action-card">
        <div class="action-title">巨潮公告采集</div>
        <div class="action-desc">热门股票公告（成交额≥10亿前500）</div>
        <button class="btn btn-primary" @click="doAction('cninfo')" :disabled="loading.cninfo">
          {{ loading.cninfo ? '采集中...' : '立即采集' }}
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
  triggerImportStocks, triggerImportConcepts, triggerImportConceptStocks,
  triggerCollectEastmoney, triggerCollectTHS, triggerCollectSina, triggerCollectAll, triggerCollectCninfo,
  triggerImportValuation, triggerImportTurnover, triggerImportKline, triggerImportFinancials, triggerMapChains,
} from "../../api/admin";
import type { SystemStatus, AdminLog } from "../../api/admin";

const status = ref<SystemStatus | null>(null);
const logs = ref<AdminLog[]>([]);
const loading = reactive({
  stocks: false,
  concepts: false,
  conceptStocks: false,
  eastmoney: false,
  ths: false,
  sina: false,
  all: false,
  valuation: false,
  turnover: false,
  kline: false,
  financials: false,
  mapChains: false,
  cninfo: false,
});

const tableLabels: Record<string, string> = {
  stocks: "股票",
  news: "资讯",
  events: "事件",
  concepts: "概念",
  industry_chains: "产业链",
  news_stocks: "资讯关联",
  stock_financials: "财务数据",
};

const actionLabels: Record<string, string> = {
  import_stocks: "股票导入",
  import_concepts: "概念导入",
  import_concept_stocks: "成分股关联",
  collect_eastmoney: "东方财富采集",
  collect_ths: "同花顺采集",
  collect_sina: "新浪采集",
  import_valuation: "估值数据更新",
  import_turnover: "成交额数据更新",
  import_kline: "K线数据采集",
  import_financials: "财务数据采集",
  import_profiles: "公司概况导入",
  collect_cninfo: "巨潮公告采集",
  cleanup_news: "资讯清理",
  map_chains: "产业链映射",
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
      case "ths": res = await triggerCollectTHS(); break;
      case "sina": res = await triggerCollectSina(); break;
      case "all": res = await triggerCollectAll(); break;
      case "valuation": res = await triggerImportValuation(); break;
      case "turnover": res = await triggerImportTurnover(); break;
      case "kline": res = await triggerImportKline(); break;
      case "financials": res = await triggerImportFinancials(); break;
      case "mapChains": res = await triggerMapChains(); break;
      case "cninfo": res = await triggerCollectCninfo(); break;
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
.action-card.disabled { opacity: 0.6; background: var(--bg-secondary); }
.action-card.highlight { border-color: var(--primary); background: var(--primary-light); }
.unavailable { font-size: 12px; color: var(--orange); }

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
