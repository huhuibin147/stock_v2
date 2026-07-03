<template>
  <div class="admin-supply-chain">
    <div class="page-header">
      <h1 class="page-title">供应链管理</h1>
      <button class="btn btn-primary" @click="showCreate = true">新增研究</button>
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
    <div class="table-container">
      <table class="data-table">
        <thead>
          <tr>
            <th>ID</th>
            <th>类型</th>
            <th>名称</th>
            <th>代码</th>
            <th>状态</th>
            <th>创建时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <tr v-if="loading">
            <td colspan="7" class="loading">加载中...</td>
          </tr>
          <tr v-else-if="list.length === 0">
            <td colspan="7" class="empty">暂无数据</td>
          </tr>
          <tr v-for="item in list" :key="item.id">
            <td>{{ item.id }}</td>
            <td>
              <span :class="['type-badge', item.target_type]">
                {{ item.target_type === 'company' ? '公司' : '行业' }}
              </span>
            </td>
            <td>{{ item.target_name }}</td>
            <td>{{ item.target_code || '-' }}</td>
            <td>
              <span :class="['status-badge', item.status]">
                {{ statusText(item.status) }}
              </span>
            </td>
            <td>{{ formatTime(item.created_at) }}</td>
            <td>
              <div class="action-btns">
                <button class="btn btn-sm" @click="viewDetail(item.id)">查看</button>
                <button class="btn btn-sm" @click="editItem(item)">编辑</button>
                <button class="btn btn-sm btn-danger" @click="deleteItem(item.id)">删除</button>
              </div>
            </td>
          </tr>
        </tbody>
      </table>
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
      <span class="page-info">第 {{ currentPage }} 页，共 {{ totalPages }} 页</span>
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
        <h3 class="modal-title">新增研究任务</h3>
        <div class="form-group">
          <label>研究类型</label>
          <select v-model="formData.target_type">
            <option value="company">公司</option>
            <option value="industry">行业</option>
          </select>
        </div>
        <div class="form-group">
          <label>{{ formData.target_type === 'company' ? '公司名称' : '行业方向' }}</label>
          <input
            v-model="formData.target_name"
            :placeholder="formData.target_type === 'company' ? '如：长鑫存储' : '如：半导体设备'"
          />
        </div>
        <div class="form-group" v-if="formData.target_type === 'company'">
          <label>股票代码（可选）</label>
          <input v-model="formData.target_code" placeholder="如：002371" />
        </div>
        <div class="modal-actions">
          <button class="btn" @click="showCreate = false">取消</button>
          <button class="btn btn-primary" @click="submitCreate">创建</button>
        </div>
      </div>
    </div>

    <!-- 编辑对话框 -->
    <div v-if="showEdit" class="modal-overlay" @click="showEdit = false">
      <div class="modal" @click.stop>
        <h3 class="modal-title">编辑研究任务</h3>
        <div class="form-group">
          <label>研究类型</label>
          <select v-model="editData.target_type" disabled>
            <option value="company">公司</option>
            <option value="industry">行业</option>
          </select>
        </div>
        <div class="form-group">
          <label>名称</label>
          <input v-model="editData.target_name" />
        </div>
        <div class="form-group" v-if="editData.target_type === 'company'">
          <label>股票代码</label>
          <input v-model="editData.target_code" />
        </div>
        <div class="form-group">
          <label>状态</label>
          <select v-model="editData.status">
            <option value="pending">待处理</option>
            <option value="processing">处理中</option>
            <option value="completed">已完成</option>
            <option value="failed">失败</option>
          </select>
        </div>
        <div class="modal-actions">
          <button class="btn" @click="showEdit = false">取消</button>
          <button class="btn btn-primary" @click="submitEdit">保存</button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRouter } from "vue-router";
import { get, post, put, del } from "../../api/request";
import type { SupplyChainResearch } from "../../types";

const router = useRouter();

const list = ref<SupplyChainResearch[]>([]);
const loading = ref(false);
const currentPage = ref(1);
const pageSize = ref(20);
const total = ref(0);
const filterType = ref("");
const filterStatus = ref("");
const showCreate = ref(false);
const showEdit = ref(false);

const formData = ref({
  target_type: "company",
  target_name: "",
  target_code: "",
});

const editData = ref({
  id: 0,
  target_type: "company",
  target_name: "",
  target_code: "",
  status: "pending",
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
    const params: any = {
      page: currentPage.value,
      page_size: pageSize.value,
    };
    if (filterType.value) params.target_type = filterType.value;
    if (filterStatus.value) params.status = filterStatus.value;

    const res = await get("/api/v1/admin/supply-chain", params);
    if (res.code === 0) {
      list.value = res.data.items;
      total.value = res.data.total;
    }
  } finally {
    loading.value = false;
  }
}

function changePage(page: number) {
  currentPage.value = page;
  loadList();
}

function viewDetail(id: number) {
  router.push(`/supply-chain/${id}`);
}

function editItem(item: SupplyChainResearch) {
  editData.value = {
    id: item.id,
    target_type: item.target_type,
    target_name: item.target_name,
    target_code: item.target_code || "",
    status: item.status,
  };
  showEdit.value = true;
}

async function submitCreate() {
  if (!formData.value.target_name) {
    alert("请输入名称");
    return;
  }

  const params: any = {
    target_type: formData.value.target_type,
    target_name: formData.value.target_name,
  };
  if (formData.value.target_code) {
    params.target_code = formData.value.target_code;
  }

  const res = await post("/api/v1/admin/supply-chain", null, { params });
  if (res.code === 0) {
    showCreate.value = false;
    formData.value = { target_type: "company", target_name: "", target_code: "" };
    loadList();
  }
}

async function submitEdit() {
  if (!editData.value.target_name) {
    alert("请输入名称");
    return;
  }

  const params: any = {
    target_name: editData.value.target_name,
    status: editData.value.status,
  };
  if (editData.value.target_code) {
    params.target_code = editData.value.target_code;
  }

  const res = await put(`/api/v1/admin/supply-chain/${editData.value.id}`, null, { params });
  if (res.code === 0) {
    showEdit.value = false;
    loadList();
  }
}

async function deleteItem(id: number) {
  if (!confirm("确定要删除这个研究任务吗？")) return;

  const res = await del(`/api/v1/admin/supply-chain/${id}`);
  if (res.code === 0) {
    loadList();
  }
}

onMounted(() => {
  loadList();
});
</script>

<style scoped>
.admin-supply-chain {
  padding: 0;
}

.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 24px;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
}

/* 筛选条件 */
.filter-bar {
  display: flex;
  gap: 24px;
  margin-bottom: 20px;
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

/* 表格 */
.table-container {
  background: var(--bg);
  border: 1px solid var(--border-light);
  border-radius: var(--radius);
  overflow-x: auto;
}

.data-table {
  width: 100%;
  border-collapse: collapse;
}

.data-table th,
.data-table td {
  padding: 12px 16px;
  text-align: left;
  border-bottom: 1px solid var(--border-light);
  font-size: 13px;
}

.data-table th {
  background: var(--bg-secondary);
  font-weight: 600;
  color: var(--text-secondary);
}

.data-table tr:hover {
  background: var(--bg-secondary);
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

.action-btns {
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
  margin-top: 20px;
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

.form-group select:disabled {
  background: var(--bg-secondary);
  cursor: not-allowed;
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
}
</style>
