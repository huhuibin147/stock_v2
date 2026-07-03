<template>
  <div class="supply-chain-list">
    <div class="page-header">
      <h1 class="page-title">供应链挖掘</h1>
      <p class="page-desc">从公司或行业出发，AI智能挖掘供应链关系</p>
    </div>

    <!-- 搜索和新建区域 -->
    <div class="action-bar">
      <div class="search-box">
        <input
          v-model="searchQuery"
          type="text"
          placeholder="输入公司名称或行业方向，如：长鑫存储、半导体设备"
          @keydown.enter="handleSearch"
        />
        <button class="btn btn-primary" @click="handleSearch">开始挖掘</button>
      </div>
    </div>

    <!-- 统计卡片 -->
    <div class="stats-cards" v-if="stats">
      <div class="stat-card">
        <div class="stat-number">{{ stats.total }}</div>
        <div class="stat-label">研究任务</div>
      </div>
      <div class="stat-card">
        <div class="stat-number">{{ stats.completed }}</div>
        <div class="stat-label">已完成</div>
      </div>
      <div class="stat-card">
        <div class="stat-number">{{ stats.relations }}</div>
        <div class="stat-label">供应链关系</div>
      </div>
    </div>

    <!-- 筛选条件 -->
    <div class="filter-bar">
      <div class="filter-group">
        <label>类型：</label>
        <select v-model="filterType" @change="loadList">
          <option value="">全部</option>
          <option value="company">公司</option>
          <option value="industry">行业</option>
        </select>
      </div>
      <div class="filter-group">
        <label>状态：</label>
        <select v-model="filterStatus" @change="loadList">
          <option value="">全部</option>
          <option value="pending">待处理</option>
          <option value="processing">处理中</option>
          <option value="completed">已完成</option>
          <option value="failed">失败</option>
        </select>
      </div>
    </div>

    <!-- 列表 -->
    <div class="research-grid">
      <div v-if="loading" class="loading">加载中...</div>
      <div v-else-if="list.length === 0" class="empty">暂无研究任务</div>
      <div
        v-for="item in list"
        :key="item.id"
        class="research-card"
        @click="goDetail(item.id)"
      >
        <div class="card-header">
          <span :class="['type-badge', item.target_type]">
            {{ item.target_type === 'company' ? '公司' : '行业' }}
          </span>
          <span :class="['status-badge', item.status]">
            {{ statusText(item.status) }}
          </span>
        </div>
        <div class="card-title">{{ item.target_name }}</div>
        <div v-if="item.target_code" class="card-code">{{ item.target_code }}</div>
        <div v-if="item.result_summary" class="card-summary">{{ item.result_summary }}</div>
        <div class="card-footer">
          <span class="card-time">{{ formatTime(item.created_at) }}</span>
          <div class="card-actions" @click.stop>
            <button
              v-if="item.status === 'pending'"
              class="btn btn-sm btn-primary"
              @click="runResearch(item.id)"
            >
              开始挖掘
            </button>
            <button
              class="btn btn-sm btn-danger"
              @click="deleteResearch(item.id)"
            >
              删除
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- 分页 -->
    <div class="pagination" v-if="total > pageSize">
      <button
        class="btn btn-sm"
        :disabled="currentPage <= 1"
        @click="changePage(currentPage - 1)"
      >
        上一页
      </button>
      <span class="page-info">{{ currentPage }} / {{ totalPages }}</span>
      <button
        class="btn btn-sm"
        :disabled="currentPage >= totalPages"
        @click="changePage(currentPage + 1)"
      >
        下一页
      </button>
    </div>

    <!-- 新建对话框 -->
    <div v-if="showCreate" class="modal-overlay" @click="showCreate = false">
      <div class="modal" @click.stop>
        <h3 class="modal-title">新建研究任务</h3>
        <div class="form-group">
          <label>研究类型</label>
          <select v-model="newResearch.target_type">
            <option value="company">公司</option>
            <option value="industry">行业</option>
          </select>
        </div>
        <div class="form-group">
          <label>{{ newResearch.target_type === 'company' ? '公司名称' : '行业方向' }}</label>
          <input
            v-model="newResearch.target_name"
            :placeholder="newResearch.target_type === 'company' ? '如：长鑫存储' : '如：半导体设备'"
          />
        </div>
        <div class="form-group" v-if="newResearch.target_type === 'company'">
          <label>股票代码（可选）</label>
          <input v-model="newResearch.target_code" placeholder="如：002371" />
        </div>
        <div class="modal-actions">
          <button class="btn" @click="showCreate = false">取消</button>
          <button class="btn btn-primary" @click="submitCreate">创建</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import {
  getSupplyChainList,
  getSupplyChainStats,
  createSupplyChainResearch,
  deleteSupplyChainResearch,
  runSupplyChainResearch,
} from "../api/supplyChain";
import type { SupplyChainResearch, SupplyChainStats } from "../types";

const router = useRouter();

const list = ref<SupplyChainResearch[]>([]);
const stats = ref<SupplyChainStats | null>(null);
const loading = ref(false);
const currentPage = ref(1);
const pageSize = ref(20);
const total = ref(0);
const filterType = ref("");
const filterStatus = ref("");
const searchQuery = ref("");
const showCreate = ref(false);

const newResearch = ref({
  target_type: "company",
  target_name: "",
  target_code: "",
});

const totalPages = computed(() => Math.ceil(total.value / pageSize.value));

function statusText(status: string) {
  const map: Record<string, string> = {
    pending: "待处理",
    processing: "处理中",
    completed: "已完成",
    failed: "失败",
  };
  return map[status] || status;
}

function formatTime(t?: string) {
  if (!t) return "";
  return t.replace("T", " ").substring(0, 16);
}

async function loadList() {
  loading.value = true;
  try {
    const res = await getSupplyChainList({
      page: currentPage.value,
      page_size: pageSize.value,
      target_type: filterType.value || undefined,
      status: filterStatus.value || undefined,
    });
    if (res.code === 0) {
      list.value = res.data.items;
      total.value = res.data.total;
    }
  } finally {
    loading.value = false;
  }
}

async function loadStats() {
  const res = await getSupplyChainStats();
  if (res.code === 0) {
    stats.value = res.data;
  }
}

function changePage(page: number) {
  currentPage.value = page;
  loadList();
}

function goDetail(id: number) {
  router.push(`/supply-chain/${id}`);
}

function handleSearch() {
  if (!searchQuery.value.trim()) return;
  newResearch.value.target_name = searchQuery.value.trim();
  showCreate.value = true;
}

async function submitCreate() {
  if (!newResearch.value.target_name) return;

  const res = await createSupplyChainResearch({
    target_type: newResearch.value.target_type,
    target_name: newResearch.value.target_name,
    target_code: newResearch.value.target_code || undefined,
  });

  if (res.code === 0) {
    showCreate.value = false;
    newResearch.value = { target_type: "company", target_name: "", target_code: "" };
    searchQuery.value = "";
    loadList();
    loadStats();
  }
}

async function runResearch(id: number) {
  const res = await runSupplyChainResearch(id);
  if (res.code === 0) {
    alert(res.data.message);
    loadList();
  }
}

async function deleteResearch(id: number) {
  if (!confirm("确定要删除这个研究任务吗？")) return;

  const res = await deleteSupplyChainResearch(id);
  if (res.code === 0) {
    loadList();
    loadStats();
  }
}

onMounted(() => {
  loadList();
  loadStats();
});
</script>

<style scoped>
.supply-chain-list {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
}

.page-header {
  margin-bottom: 32px;
}

.page-title {
  font-size: 28px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 8px;
}

.page-desc {
  font-size: 14px;
  color: var(--text-secondary);
}

/* 搜索区域 */
.action-bar {
  margin-bottom: 24px;
}

.search-box {
  display: flex;
  gap: 12px;
  max-width: 600px;
}

.search-box input {
  flex: 1;
  padding: 12px 16px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-size: 14px;
}

.search-box input:focus {
  outline: none;
  border-color: var(--primary);
}

/* 统计卡片 */
.stats-cards {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 24px;
}

.stat-card {
  background: var(--bg);
  border: 1px solid var(--border-light);
  border-radius: var(--radius);
  padding: 20px;
  text-align: center;
}

.stat-number {
  font-size: 32px;
  font-weight: 700;
  color: var(--primary);
}

.stat-label {
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 4px;
}

/* 筛选条件 */
.filter-bar {
  display: flex;
  gap: 24px;
  margin-bottom: 24px;
  padding: 16px;
  background: var(--bg);
  border: 1px solid var(--border-light);
  border-radius: var(--radius);
}

.filter-group {
  display: flex;
  align-items: center;
  gap: 8px;
}

.filter-group label {
  font-size: 13px;
  color: var(--text-secondary);
}

.filter-group select {
  padding: 6px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-size: 13px;
}

/* 列表网格 */
.research-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 16px;
  margin-bottom: 24px;
}

.research-card {
  background: var(--bg);
  border: 1px solid var(--border-light);
  border-radius: var(--radius);
  padding: 20px;
  cursor: pointer;
  transition: all 0.2s;
}

.research-card:hover {
  box-shadow: var(--shadow-md);
  transform: translateY(-2px);
}

.card-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 12px;
}

.type-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
  font-weight: 600;
}

.type-badge.company {
  background: #e3f2fd;
  color: #1976d2;
}

.type-badge.industry {
  background: #f3e5f5;
  color: #7b1fa2;
}

.status-badge {
  font-size: 11px;
  padding: 2px 8px;
  border-radius: 4px;
}

.status-badge.pending {
  background: #fff3e0;
  color: #f57c00;
}

.status-badge.processing {
  background: #e3f2fd;
  color: #1976d2;
}

.status-badge.completed {
  background: #e8f5e9;
  color: #388e3c;
}

.status-badge.failed {
  background: #ffebee;
  color: #d32f2f;
}

.card-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 4px;
}

.card-code {
  font-size: 13px;
  font-family: "SF Mono", monospace;
  color: var(--text-muted);
  margin-bottom: 8px;
}

.card-summary {
  font-size: 13px;
  color: var(--text-secondary);
  line-height: 1.5;
  margin-bottom: 12px;
  display: -webkit-box;
  -webkit-line-clamp: 3;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.card-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.card-time {
  font-size: 12px;
  color: var(--text-muted);
}

.card-actions {
  display: flex;
  gap: 8px;
}

/* 按钮 */
.btn {
  padding: 8px 16px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-size: 13px;
  cursor: pointer;
  transition: all 0.2s;
}

.btn:hover {
  background: var(--bg-secondary);
}

.btn-primary {
  background: var(--primary);
  color: #fff;
  border-color: var(--primary);
}

.btn-primary:hover {
  opacity: 0.9;
}

.btn-danger {
  color: #d32f2f;
  border-color: #d32f2f;
}

.btn-danger:hover {
  background: #ffebee;
}

.btn-sm {
  padding: 4px 10px;
  font-size: 12px;
}

/* 分页 */
.pagination {
  display: flex;
  justify-content: center;
  align-items: center;
  gap: 16px;
}

.page-info {
  font-size: 13px;
  color: var(--text-secondary);
}

/* 模态框 */
.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.5);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal {
  background: var(--bg);
  border-radius: var(--radius);
  padding: 24px;
  width: 100%;
  max-width: 480px;
}

.modal-title {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 20px;
}

.form-group {
  margin-bottom: 16px;
}

.form-group label {
  display: block;
  font-size: 13px;
  font-weight: 500;
  color: var(--text-secondary);
  margin-bottom: 6px;
}

.form-group input,
.form-group select {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-size: 14px;
}

.form-group input:focus,
.form-group select:focus {
  outline: none;
  border-color: var(--primary);
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 24px;
}

/* 状态提示 */
.loading,
.empty {
  text-align: center;
  padding: 40px;
  color: var(--text-muted);
  grid-column: 1 / -1;
}

/* 响应式 */
@media (max-width: 768px) {
  .supply-chain-list {
    padding: 16px;
  }

  .page-title {
    font-size: 22px;
  }

  .search-box {
    flex-direction: column;
  }

  .stats-cards {
    grid-template-columns: 1fr;
  }

  .filter-bar {
    flex-direction: column;
    gap: 12px;
  }

  .research-grid {
    grid-template-columns: 1fr;
  }
}
</style>
