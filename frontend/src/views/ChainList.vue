<template>
  <div class="chain-page">
    <div class="page-header">
      <h2>产业链图谱</h2>
      <p class="desc">五层架构 · {{ totalChains }} 个产业节点</p>
    </div>

    <div v-if="loading" class="loading">加载中...</div>
    <div v-else class="layers">
      <div v-for="layer in layers" :key="layer.id" class="layer-section">
        <div class="layer-header" @click="toggle(layer.id)">
          <div class="layer-info">
            <span class="layer-badge" :style="{ background: layerColors[layer.id] }">Layer {{ layer.id }}</span>
            <span class="layer-name">{{ layer.name }}</span>
            <span class="layer-count">{{ layer.chains.length }} 个产业</span>
          </div>
          <span class="expand-icon">{{ expanded[layer.id] ? '收起' : '展开' }}</span>
        </div>
        <div v-if="expanded[layer.id]" class="chain-grid">
          <div
            v-for="c in layer.chains"
            :key="c.id"
            class="chain-tag"
            :class="{ active: selectedChain?.id === extractId(c.id) }"
            @click="selectChain(c)"
          >
            <span class="chain-name">{{ c.name }}</span>
            <span v-if="c.stock_count" class="chain-count">{{ c.stock_count }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 关联公司列表 -->
    <div v-if="selectedChain" class="chain-stocks-section">
      <div class="section-header">
        <h3>{{ selectedChain.name }} - 关联公司</h3>
        <span class="stock-count">{{ chainStocks.length }} 家</span>
        <button class="close-btn" @click="selectedChain = null">✕</button>
      </div>
      <div v-if="loadingStocks" class="loading-stocks">加载中...</div>
      <div v-else-if="!chainStocks.length" class="empty">暂无关联公司</div>
      <div v-else class="stocks-table">
        <router-link
          v-for="s in chainStocks"
          :key="s.code"
          :to="`/stock/${s.code}`"
          class="stock-row"
        >
          <span class="stock-code">{{ s.code }}.{{ s.market }}</span>
          <span class="stock-name">{{ s.name }}</span>
          <span class="stock-price">{{ s.last_price != null ? s.last_price.toFixed(2) : '-' }}</span>
          <span class="stock-pct" :class="pctClass(s.pct_change)">
            {{ s.pct_change != null ? (s.pct_change > 0 ? '+' : '') + s.pct_change.toFixed(2) + '%' : '-' }}
          </span>
          <span class="stock-cap">{{ formatCap(s.market_cap) }}</span>
          <span class="stock-turnover">{{ formatAmount(s.turnover_amount) }}</span>
        </router-link>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from "vue";
import { useRoute } from "vue-router";
import { get } from "../api/request";

interface ChainNode {
  id: string;
  type: string;
  name: string;
  layer: number;
  stock_count?: number;
}

interface StockItem {
  code: string;
  name: string;
  market: string;
  industry: string | null;
  last_price: number | null;
  pct_change: number | null;
  market_cap: number | null;
  turnover_amount: number | null;
}

interface ChainStocksData {
  chain: { id: number; name: string; layer: number } | null;
  stocks: StockItem[];
}

const route = useRoute();
const loading = ref(true);
const allNodes = ref<ChainNode[]>([]);
const expanded = reactive<Record<number, boolean>>({ 1: true, 2: true, 3: true, 4: true, 5: true });

const selectedChain = ref<{ id: number; name: string } | null>(null);
const chainStocks = ref<StockItem[]>([]);
const loadingStocks = ref(false);

const layerColors: Record<number, string> = {
  1: "#27ae60",
  2: "#3498db",
  3: "#f39c12",
  4: "#e74c3c",
  5: "#9b59b6",
};

const layerNames: Record<number, string> = {
  1: "能源电力",
  2: "芯片硬件",
  3: "基础设施",
  4: "AI基础",
  5: "AI应用",
};

const layers = computed(() => {
  const result: { id: number; name: string; chains: ChainNode[] }[] = [];
  for (let i = 1; i <= 5; i++) {
    const chains = allNodes.value.filter(n => n.layer === i);
    result.push({ id: i, name: layerNames[i] || `Layer ${i}`, chains });
  }
  return result;
});

const totalChains = computed(() => {
  const seen = new Set<string>();
  allNodes.value.forEach(n => seen.add(n.name));
  return seen.size;
});

function extractId(id: string): number {
  // 从 "chain_123" 格式提取数字 ID
  const match = id.match(/\d+/);
  return match ? parseInt(match[0]) : 0;
}

function toggle(id: number) {
  expanded[id] = !expanded[id];
}

async function selectChain(chain: ChainNode) {
  const chainId = extractId(chain.id);
  if (selectedChain.value?.id === chainId) {
    selectedChain.value = null;
    chainStocks.value = [];
    return;
  }

  selectedChain.value = { id: chainId, name: chain.name };
  loadingStocks.value = true;
  chainStocks.value = [];

  try {
    const res = await get<ChainStocksData>(`/api/v1/graph/chain/${chainId}/stocks`);
    if (res.code === 0) {
      chainStocks.value = res.data.stocks;
    }
  } finally {
    loadingStocks.value = false;
  }
}

function pctClass(val?: number | null) {
  if (val == null) return "";
  if (val > 0) return "pct-up";
  if (val < 0) return "pct-down";
  return "";
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

onMounted(async () => {
  const res = await get<{ nodes: ChainNode[] }>("/api/v1/graph/industry-chain");
  if (res.code === 0) {
    allNodes.value = res.data.nodes;
  }
  loading.value = false;

  // 如果 URL 带有 layer 参数，展开对应层级
  const layerParam = route.query.layer;
  if (layerParam) {
    const layerNum = parseInt(layerParam as string);
    if (layerNum >= 1 && layerNum <= 5) {
      expanded[layerNum] = true;
    }
  }
});
</script>

<style scoped>
.chain-page {
  max-width: 1000px;
  margin: 0 auto;
  padding: 24px;
}
.page-header { margin-bottom: 24px; }
.page-header h2 { font-size: 20px; font-weight: 700; margin-bottom: 4px; }
.desc { font-size: 13px; color: var(--text-muted); }

.loading { text-align: center; padding: 60px; color: var(--text-muted); }

.layers {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.layer-section {
  background: var(--bg);
  border: 1px solid var(--border-light);
  border-radius: var(--radius);
  overflow: hidden;
}
.layer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 20px;
  cursor: pointer;
  user-select: none;
  transition: background 0.15s;
}
.layer-header:hover { background: var(--bg-secondary); }
.layer-info {
  display: flex;
  align-items: center;
  gap: 12px;
}
.layer-badge {
  font-size: 11px;
  font-weight: 700;
  color: #fff;
  padding: 3px 10px;
  border-radius: 4px;
  text-transform: uppercase;
  letter-spacing: 0.5px;
}
.layer-name { font-size: 16px; font-weight: 600; }
.layer-count { font-size: 12px; color: var(--text-muted); }
.expand-icon { font-size: 13px; color: var(--primary); }

.chain-grid {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  padding: 0 20px 16px;
}
.chain-tag {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 13px;
  padding: 5px 12px;
  background: var(--bg-secondary);
  border: 1px solid var(--border-light);
  border-radius: 6px;
  color: var(--text);
}
.chain-count {
  font-size: 11px;
  background: var(--primary-light);
  color: var(--primary);
  padding: 1px 6px;
  border-radius: 10px;
  font-weight: 600;
}
.chain-tag.active {
  background: var(--primary);
  color: #fff;
  border-color: var(--primary);
}
.chain-tag.active .chain-count {
  background: rgba(255, 255, 255, 0.2);
  color: #fff;
}

/* 关联公司列表 */
.chain-stocks-section {
  margin-top: 24px;
  background: var(--bg);
  border: 1px solid var(--border-light);
  border-radius: var(--radius);
  overflow: hidden;
}
.chain-stocks-section .section-header {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 16px 20px;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-light);
}
.chain-stocks-section .section-header h3 {
  font-size: 16px;
  font-weight: 600;
  margin: 0;
}
.chain-stocks-section .stock-count {
  font-size: 13px;
  color: var(--text-muted);
}
.chain-stocks-section .close-btn {
  margin-left: auto;
  background: none;
  border: none;
  font-size: 18px;
  color: var(--text-muted);
  cursor: pointer;
  padding: 4px 8px;
}
.chain-stocks-section .close-btn:hover {
  color: var(--primary);
}

.loading-stocks {
  text-align: center;
  padding: 24px;
  color: var(--text-muted);
}
.empty {
  text-align: center;
  padding: 24px;
  color: var(--text-muted);
}
.stocks-table {
  padding: 0;
}
.stocks-table .stock-row {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 20px;
  border-bottom: 1px solid var(--border-light);
  text-decoration: none;
  color: inherit;
  transition: background 0.15s;
}
.stocks-table .stock-row:last-child {
  border-bottom: none;
}
.stocks-table .stock-row:hover {
  background: var(--bg-secondary);
  text-decoration: none;
}
.stocks-table .stock-code {
  font-family: "SF Mono", monospace;
  font-size: 12px;
  color: var(--primary);
  font-weight: 600;
  min-width: 70px;
}
.stocks-table .stock-name {
  font-weight: 500;
  min-width: 80px;
}
.stocks-table .stock-price {
  font-variant-numeric: tabular-nums;
  min-width: 60px;
  text-align: right;
}
.stocks-table .stock-pct {
  font-variant-numeric: tabular-nums;
  min-width: 60px;
  text-align: right;
}
.stocks-table .stock-cap {
  font-size: 12px;
  color: var(--text-muted);
  min-width: 60px;
  text-align: right;
  margin-left: auto;
}
.stocks-table .stock-turnover {
  font-size: 12px;
  color: var(--text-muted);
  min-width: 60px;
  text-align: right;
}
.pct-up { color: var(--primary); }
.pct-down { color: var(--success); }
</style>
