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

    <!-- 公司概况 -->
    <div v-if="profile.company" class="card company-card">
      <div class="company-header" @click="companyExpanded = !companyExpanded">
        <h3>公司概况</h3>
        <span class="expand-icon">{{ companyExpanded ? '收起' : '展开' }}</span>
      </div>
      <div v-if="companyExpanded" class="company-body">
        <div class="info-grid">
          <div class="info-item" v-if="profile.company.legal_rep">
            <span class="info-label">法人代表</span>
            <span class="info-value">{{ profile.company.legal_rep }}</span>
          </div>
          <div class="info-item" v-if="profile.company.found_date">
            <span class="info-label">成立日期</span>
            <span class="info-value">{{ profile.company.found_date }}</span>
          </div>
          <div class="info-item" v-if="profile.company.list_date">
            <span class="info-label">上市日期</span>
            <span class="info-value">{{ profile.company.list_date }}</span>
          </div>
          <div class="info-item" v-if="profile.company.reg_capital">
            <span class="info-label">注册资本</span>
            <span class="info-value">{{ profile.company.reg_capital }}</span>
          </div>
          <div class="info-item" v-if="profile.company.phone">
            <span class="info-label">电话</span>
            <span class="info-value">{{ profile.company.phone }}</span>
          </div>
          <div class="info-item" v-if="profile.company.website">
            <span class="info-label">官网</span>
            <span class="info-value"><a :href="profile.company.website" target="_blank">{{ profile.company.website }}</a></span>
          </div>
        </div>
        <div v-if="profile.company.office_address" class="info-block">
          <span class="info-label">办公地址</span>
          <span class="info-value">{{ profile.company.office_address }}</span>
        </div>
        <div v-if="profile.company.business_scope" class="info-block">
          <span class="info-label">经营范围</span>
          <span class="info-value long-text">{{ profile.company.business_scope }}</span>
        </div>
        <div v-if="profile.company.introduction" class="info-block">
          <span class="info-label">公司简介</span>
          <span class="info-value long-text">{{ profile.company.introduction }}</span>
        </div>
      </div>
    </div>

    <!-- 估值概览 -->
    <div v-if="hasValuation" class="card valuation-card">
      <div class="valuation-grid">
        <div class="val-item" v-if="profile.stock.pe_ttm != null">
          <span class="val-label">PE(TTM)</span>
          <span class="val-num">{{ profile.stock.pe_ttm.toFixed(1) }}</span>
        </div>
        <div class="val-item" v-if="profile.stock.pb != null">
          <span class="val-label">PB</span>
          <span class="val-num">{{ profile.stock.pb.toFixed(2) }}</span>
        </div>
        <div class="val-item" v-if="profile.stock.market_cap != null">
          <span class="val-label">总市值</span>
          <span class="val-num">{{ formatCap(profile.stock.market_cap) }}</span>
        </div>
        <div class="val-item" v-if="profile.stock.turnover_amount != null">
          <span class="val-label">成交额</span>
          <span class="val-num">{{ formatAmount(profile.stock.turnover_amount) }}</span>
        </div>
        <div class="val-item" v-if="profile.stock.dividend_yield != null">
          <span class="val-label">股息率</span>
          <span class="val-num">{{ profile.stock.dividend_yield.toFixed(2) }}%</span>
        </div>
      </div>
    </div>

    <!-- 近期K线 -->
    <div v-if="klineData.length" class="card">
      <h3>近期行情</h3>
      <div class="table-wrap">
        <table class="kline-table">
          <thead>
            <tr>
              <th>日期</th>
              <th class="num">收盘</th>
              <th class="num">涨跌%</th>
              <th class="num">成交额</th>
              <th class="num">换手%</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="k in klineData" :key="k.trade_date">
              <td class="date">{{ k.trade_date }}</td>
              <td class="num">{{ k.close != null ? k.close.toFixed(2) : '-' }}</td>
              <td class="num" :class="pctClass(k.pct_change)">{{ k.pct_change != null ? (k.pct_change > 0 ? '+' : '') + k.pct_change.toFixed(2) + '%' : '-' }}</td>
              <td class="num">{{ formatAmount(k.turnover) }}</td>
              <td class="num">{{ k.turnover_rate != null ? k.turnover_rate.toFixed(2) : '-' }}</td>
            </tr>
          </tbody>
        </table>
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

    <!-- 财务摘要 -->
    <div v-if="financials.length" class="card">
      <h3>财务摘要</h3>
      <div class="table-wrap">
        <table class="fin-table">
          <thead>
            <tr>
              <th>报告期</th>
              <th class="num">营收</th>
              <th class="num">净利润</th>
              <th class="num">EPS</th>
              <th class="num">ROE%</th>
              <th class="num">净利率%</th>
              <th class="num">负债率%</th>
            </tr>
          </thead>
          <tbody>
            <tr v-for="f in financials" :key="f.report_date">
              <td class="period">{{ formatPeriod(f.report_date) }}</td>
              <td class="num">{{ formatMoney(f.revenue) }}</td>
              <td class="num">{{ formatMoney(f.net_profit) }}</td>
              <td class="num">{{ f.eps != null ? f.eps.toFixed(2) : '-' }}</td>
              <td class="num">{{ f.roe != null ? f.roe.toFixed(1) : '-' }}</td>
              <td class="num">{{ f.net_margin != null ? f.net_margin.toFixed(1) : '-' }}</td>
              <td class="num">{{ f.equity_ratio != null ? f.equity_ratio.toFixed(1) : '-' }}</td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>

    <!-- 所属概念 -->
    <div v-if="profile.concepts && profile.concepts.length" class="card concepts-card">
      <h3>所属概念</h3>
      <div class="concepts-list">
        <span v-for="concept in profile.concepts" :key="concept" class="concept-tag">
          {{ concept }}
        </span>
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
      <router-link v-for="item in profile.recent_news" :key="item.id" :to="`/news/${item.id}`" class="news-item">
        <div class="news-header">
          <span :class="['badge', sentimentClass(item.sentiment)]">{{ sentimentText(item.sentiment) }}</span>
          <span class="news-time">{{ formatTime(item.published_at) }}</span>
        </div>
        <div class="news-title">{{ item.title }}</div>
        <div v-if="item.summary" class="news-summary">{{ item.summary }}</div>
      </router-link>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch, onUnmounted } from "vue";
import { useRoute } from "vue-router";
import { getStockProfile, getStockFinancials, getStockKline } from "../api/stock";
import type { StockProfile, FinancialRecord, KlineRecord } from "../types";

const route = useRoute();
const profile = ref<StockProfile | null>(null);
const financials = ref<FinancialRecord[]>([]);
const klineData = ref<KlineRecord[]>([]);
const loading = ref(true);
const companyExpanded = ref(false);
let refreshTimer: ReturnType<typeof setTimeout> | null = null;

async function loadProfile(code: string) {
  loading.value = true;
  // 取消之前的定时刷新
  if (refreshTimer) {
    clearTimeout(refreshTimer);
    refreshTimer = null;
  }

  const res = await getStockProfile(code);
  profile.value = res.code === 0 ? res.data : null;
  loading.value = false;

  // 异步加载财务数据和K线
  if (profile.value) {
    const [finRes, klineRes] = await Promise.all([
      getStockFinancials(code),
      getStockKline(code, 10),
    ]);
    if (finRes.code === 0) financials.value = finRes.data;
    if (klineRes.code === 0) klineData.value = klineRes.data;

    // 延迟3秒后自动刷新一次，获取后台采集的最新数据
    refreshTimer = setTimeout(() => refreshData(code), 3000);
  }
}

async function refreshData(code: string) {
  try {
    const [profileRes, klineRes] = await Promise.all([
      getStockProfile(code),
      getStockKline(code, 10),
    ]);
    if (profileRes.code === 0 && profileRes.data) {
      profile.value = profileRes.data;
    }
    if (klineRes.code === 0) klineData.value = klineRes.data;
  } catch (e) {
    // 静默失败，不影响用户体验
  }
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

const hasValuation = computed(() => {
  const s = profile.value?.stock;
  if (!s) return false;
  return s.pe_ttm != null || s.pb != null || s.market_cap != null;
});

function formatCap(val?: number | null) {
  if (val == null) return "-";
  if (val >= 1e12) return (val / 1e12).toFixed(1) + "万亿";
  if (val >= 1e8) return (val / 1e8).toFixed(0) + "亿";
  return val.toLocaleString();
}

function formatPeriod(d: string) {
  // 20251231 → 2025年报, 20250331 → 2025Q1
  if (d.length === 8) {
    const year = d.substring(0, 4);
    const mm = d.substring(4, 6);
    if (mm === "12") return year + "年报";
    if (mm === "09") return year + "Q3";
    if (mm === "06") return year + "中报";
    if (mm === "03") return year + "Q1";
  }
  return d;
}

function formatMoney(val?: number | null) {
  if (val == null) return "-";
  if (Math.abs(val) >= 1e8) return (val / 1e8).toFixed(1) + "亿";
  if (Math.abs(val) >= 1e4) return (val / 1e4).toFixed(0) + "万";
  return val.toFixed(0);
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

onMounted(() => loadProfile(route.params.code as string));
onUnmounted(() => {
  if (refreshTimer) {
    clearTimeout(refreshTimer);
    refreshTimer = null;
  }
});
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

/* 公司概况 */
.company-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  cursor: pointer;
  user-select: none;
}
.company-header h3 { margin-bottom: 0; }
.expand-icon {
  font-size: 13px;
  color: var(--primary);
}
.company-body {
  margin-top: 16px;
  padding-top: 16px;
  border-top: 1px solid var(--border-light);
}
.info-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
  gap: 12px 24px;
  margin-bottom: 12px;
}
.info-item {
  display: flex;
  flex-direction: column;
  gap: 2px;
}
.info-block {
  display: flex;
  flex-direction: column;
  gap: 2px;
  margin-top: 8px;
}
.info-label {
  font-size: 12px;
  color: var(--text-muted);
}
.info-value {
  font-size: 14px;
  color: var(--text);
}
.long-text {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.7;
}

/* 估值概览 */
.valuation-card {
  padding: 16px 20px;
}
.valuation-grid {
  display: flex;
  gap: 32px;
  flex-wrap: wrap;
}
.val-item {
  display: flex;
  flex-direction: column;
  align-items: center;
  min-width: 80px;
}
.val-label {
  font-size: 12px;
  color: var(--text-muted);
  margin-bottom: 4px;
}
.val-num {
  font-size: 20px;
  font-weight: 700;
  font-variant-numeric: tabular-nums;
  color: var(--text);
}

/* 所属概念 */
.concepts-card {
  padding: 16px 20px;
}
.concepts-card h3 {
  margin-bottom: 12px;
}
.concepts-list {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}
.concept-tag {
  display: inline-block;
  padding: 4px 12px;
  background: var(--primary-light, #e3f2fd);
  color: var(--primary, #1976d2);
  border-radius: 16px;
  font-size: 13px;
  font-weight: 500;
  transition: all 0.2s;
}
.concept-tag:hover {
  background: var(--primary, #1976d2);
  color: #fff;
}

/* 财务表格 */
.table-wrap {
  overflow-x: auto;
}
.fin-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.fin-table th {
  background: var(--bg-secondary);
  padding: 8px 10px;
  text-align: left;
  font-weight: 600;
  border-bottom: 1px solid var(--border-light);
  white-space: nowrap;
}
.fin-table td {
  padding: 8px 10px;
  border-bottom: 1px solid var(--border-light);
}
.fin-table tr:last-child td { border-bottom: none; }
.fin-table .num { text-align: right; font-variant-numeric: tabular-nums; }
.fin-table .period { font-weight: 500; white-space: nowrap; }

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
  display: block;
  padding: 12px 0;
  border-bottom: 1px solid var(--border);
  text-decoration: none;
  color: inherit;
  transition: background 0.15s;
  cursor: pointer;
}
.news-item:hover {
  background: var(--bg-secondary);
  text-decoration: none;
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

.empty {
  color: var(--text-secondary);
  font-size: 14px;
}

/* K线表格 */
.kline-table {
  width: 100%;
  border-collapse: collapse;
  font-size: 13px;
}
.kline-table th {
  background: var(--bg-secondary);
  padding: 8px 10px;
  text-align: left;
  font-weight: 600;
  border-bottom: 1px solid var(--border-light);
  white-space: nowrap;
}
.kline-table td {
  padding: 8px 10px;
  border-bottom: 1px solid var(--border-light);
}
.kline-table tr:last-child td { border-bottom: none; }
.kline-table .num { text-align: right; font-variant-numeric: tabular-nums; }
.kline-table .date { font-family: monospace; font-size: 12px; color: var(--text-muted); }
.pct-up { color: var(--primary); }
.pct-down { color: var(--success); }
</style>
