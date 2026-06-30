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
          <div v-for="c in layer.chains" :key="c.id" class="chain-tag">
            <span class="chain-name">{{ c.name }}</span>
            <span v-if="c.stock_count" class="chain-count">{{ c.stock_count }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted } from "vue";
import { get } from "../api/request";

interface ChainNode {
  id: string;
  type: string;
  name: string;
  layer: number;
  stock_count?: number;
}

const loading = ref(true);
const allNodes = ref<ChainNode[]>([]);
const expanded = reactive<Record<number, boolean>>({ 1: true, 2: true, 3: false, 4: false, 5: false });

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
    // 去重（按名称）
    const seen = new Set<string>();
    const unique = chains.filter(c => {
      if (seen.has(c.name)) return false;
      seen.add(c.name);
      return true;
    });
    result.push({ id: i, name: layerNames[i] || `Layer ${i}`, chains: unique });
  }
  return result;
});

const totalChains = computed(() => {
  const seen = new Set<string>();
  allNodes.value.forEach(n => seen.add(n.name));
  return seen.size;
});

function toggle(id: number) {
  expanded[id] = !expanded[id];
}

onMounted(async () => {
  const res = await get<{ nodes: ChainNode[] }>("/api/v1/graph/industry-chain");
  if (res.code === 0) {
    allNodes.value = res.data.nodes;
  }
  loading.value = false;
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
</style>
