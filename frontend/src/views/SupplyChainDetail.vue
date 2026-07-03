<template>
  <div class="supply-chain-detail">
    <div v-if="loading" class="loading">加载中...</div>
    <div v-else-if="!research" class="empty">研究任务不存在</div>
    <template v-else>
      <!-- 头部信息 -->
      <div class="detail-header">
        <div class="header-left">
          <button class="btn btn-back" @click="goBack">← 返回列表</button>
          <h1 class="detail-title">{{ research.target_name }}</h1>
          <div class="detail-meta">
            <span :class="['type-badge', research.target_type]">
              {{ research.target_type === 'company' ? '公司' : '行业' }}
            </span>
            <span v-if="research.target_code" class="target-code">{{ research.target_code }}</span>
            <span :class="['status-badge', research.status]">
              {{ statusText(research.status) }}
            </span>
            <span v-if="research.status === 'processing'" class="refresh-hint">
              🔄 分析中，页面自动刷新...
            </span>
          </div>
        </div>
        <div class="header-actions">
          <button
            v-if="research.status === 'pending' || research.status === 'failed'"
            class="btn btn-primary"
            @click="runResearch"
          >
            {{ research.status === 'failed' ? '重新挖掘' : '开始挖掘' }}
          </button>
          <button class="btn btn-secondary" @click="showSupplement = true">
            📎 补充采集
          </button>
          <button class="btn btn-danger" @click="handleDeleteResearch">
            🗑️ 删除任务
          </button>
        </div>
      </div>

      <!-- 供应链关系统计 -->
      <div v-if="research.relations && research.relations.length" class="relation-stats">
        <div class="stat-item">
          <div class="stat-number">{{ upstreamCount }}</div>
          <div class="stat-label">上游供应商</div>
        </div>
        <div class="stat-item">
          <div class="stat-number">{{ downstreamCount }}</div>
          <div class="stat-label">下游客户</div>
        </div>
        <div class="stat-item">
          <div class="stat-number">{{ partnerCount }}</div>
          <div class="stat-label">合作伙伴</div>
        </div>
      </div>

      <!-- 分析摘要 -->
      <div v-if="research.result_summary" class="summary-section">
        <h2 class="section-title">分析摘要</h2>
        <div class="summary-content">{{ research.result_summary }}</div>
      </div>

      <!-- 笔记模块 -->
      <div class="notes-section">
        <h2 class="section-title">
          个人笔记
          <span class="count">共 {{ notes.length }} 条</span>
          <button class="btn btn-sm btn-primary" @click="showAddNote = true">+ 新增笔记</button>
        </h2>

        <div v-if="notes.length" class="notes-list">
          <div v-for="note in notes" :key="note.id" class="note-card">
            <div class="note-content" v-if="editingNoteId !== note.id">{{ note.content }}</div>
            <textarea
              v-else
              v-model="editingNoteContent"
              class="note-textarea"
              rows="3"
            ></textarea>
            <div class="note-footer">
              <span class="note-time">{{ formatTime(note.updated_at || note.created_at) }}</span>
              <div class="note-actions">
                <template v-if="editingNoteId === note.id">
                  <button class="btn btn-sm btn-primary" @click="saveEditNote(note.id)">保存</button>
                  <button class="btn btn-sm" @click="cancelEditNote">取消</button>
                </template>
                <template v-else>
                  <button class="btn btn-sm btn-secondary" @click="startEditNote(note)">编辑</button>
                  <button class="btn btn-sm btn-danger" @click="handleDeleteNote(note.id)">删除</button>
                </template>
              </div>
            </div>
          </div>
        </div>
        <div v-else class="empty-notes">
          暂无笔记，点击"+ 新增笔记"添加
        </div>
      </div>

      <!-- 供应链关系列表 -->
      <div class="relations-section">
        <h2 class="section-title">
          供应链关系
          <span class="count">共 {{ research.relations?.length || 0 }} 家公司</span>
          <button class="btn btn-sm btn-primary" @click="showAddRelation = true">+ 新增关系</button>
        </h2>

        <!-- 按类型分组显示 -->
        <div v-for="group in relationGroups" :key="group.type" class="relation-group">
          <h3 class="group-title">
            <span class="group-icon">{{ group.icon }}</span>
            {{ group.label }}
            <span class="group-count">({{ group.relations.length }})</span>
          </h3>
          <div class="relation-list">
            <div
              v-for="rel in group.relations"
              :key="rel.id"
              class="relation-card"
            >
              <div class="relation-header">
                <div class="company-info">
                  <span class="company-name">{{ rel.company_name }}</span>
                  <router-link
                    v-if="rel.company_code"
                    :to="`/stock/${rel.company_code}`"
                    class="company-code"
                    @click.stop
                  >
                    {{ rel.company_code }}
                  </router-link>
                </div>
                <div class="relation-actions">
                  <div class="confidence" v-if="rel.confidence">
                    <div class="confidence-bar">
                      <div class="confidence-fill" :style="{ width: (rel.confidence * 100) + '%' }"></div>
                    </div>
                    <span class="confidence-value">{{ (rel.confidence * 100).toFixed(0) }}%</span>
                  </div>
                  <button class="btn btn-sm btn-secondary" @click="editRelation(rel)">编辑</button>
                  <button class="btn btn-sm btn-danger" @click="handleDeleteRelation(rel.id)">删除</button>
                </div>
              </div>

              <div v-if="rel.relation_desc" class="relation-desc">{{ rel.relation_desc }}</div>

              <div class="relation-details">
                <div v-if="rel.product_service" class="detail-item">
                  <span class="detail-label">产品/服务：</span>
                  <span class="detail-value">{{ rel.product_service }}</span>
                </div>
                <div v-if="rel.cooperation_detail" class="detail-item">
                  <span class="detail-label">合作详情：</span>
                  <span class="detail-value">{{ rel.cooperation_detail }}</span>
                </div>
                <div v-if="rel.business_volume" class="detail-item">
                  <span class="detail-label">业务规模：</span>
                  <span class="detail-value">{{ rel.business_volume }}</span>
                </div>
                <div v-if="rel.start_time" class="detail-item">
                  <span class="detail-label">合作时间：</span>
                  <span class="detail-value">{{ rel.start_time }}</span>
                </div>
              </div>

              <div class="relation-source">
                <span v-if="rel.source" class="source-text">来源：{{ rel.source }}</span>
                <a v-if="rel.source_url" :href="rel.source_url" target="_blank" class="source-link" @click.stop>
                  查看原文 ↗
                </a>
                <span v-if="rel.news_date" class="news-date">{{ rel.news_date }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- 空状态 -->
        <div v-if="!research.relations?.length && research.status === 'completed'" class="empty">
          暂未发现供应链关系
        </div>
        <div v-if="!research.relations?.length && research.status === 'pending'" class="empty">
          点击"开始挖掘"按钮，AI将自动分析供应链关系
        </div>
        <div v-if="!research.relations?.length && research.status === 'processing'" class="empty">
          AI正在分析中，请稍后刷新查看结果...
        </div>
      </div>

      <!-- 采集来源 -->
      <div v-if="research.search_sources && research.search_sources.length" class="sources-section">
        <h2 class="section-title">
          采集来源
          <span class="count">共 {{ research.search_sources.length }} 条</span>
        </h2>
        <div class="sources-list">
          <a
            v-for="(source, idx) in research.search_sources"
            :key="idx"
            :href="fixUrl(source.url)"
            target="_blank"
            rel="noopener noreferrer"
            class="source-item"
          >
            <span class="source-idx">{{ idx + 1 }}</span>
            <div class="source-info">
              <div class="source-title">{{ source.title }}</div>
              <div class="source-url">{{ source.url }}</div>
            </div>
            <span class="source-badge">{{ source.source }}</span>
          </a>
        </div>
      </div>

      <!-- 时间信息 -->
      <div class="time-info">
        <span>创建时间：{{ formatTime(research.created_at) }}</span>
        <span>更新时间：{{ formatTime(research.updated_at) }}</span>
      </div>
    </template>

    <!-- 补充采集对话框 -->
    <div v-if="showSupplement" class="modal-overlay" @click="showSupplement = false">
      <div class="modal" @click.stop>
        <h3 class="modal-title">补充采集</h3>
        <p class="modal-desc">输入相关链接或补充信息，AI将基于这些内容继续分析</p>
        <div class="form-group">
          <label>链接或内容</label>
          <textarea
            v-model="supplementContent"
            placeholder="请输入链接URL或相关文字内容，每行一个链接或一段描述..."
            rows="6"
          ></textarea>
        </div>
        <div class="form-group">
          <label>补充说明（可选）</label>
          <input v-model="supplementNote" placeholder="如：这是公司的年报链接、这是供应商的公告..." />
        </div>
        <div class="modal-actions">
          <button class="btn" @click="showSupplement = false">取消</button>
          <button class="btn btn-primary" @click="submitSupplement" :disabled="supplementSubmitting">
            {{ supplementSubmitting ? '提交中...' : '提交补充' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 新增/编辑关系对话框 -->
    <div v-if="showAddRelation || editingRelationId" class="modal-overlay" @click="closeRelationModal">
      <div class="modal modal-lg" @click.stop>
        <h3 class="modal-title">{{ editingRelationId ? '编辑关系' : '新增关系' }}</h3>
        <div class="form-row">
          <div class="form-group">
            <label>公司名称 *</label>
            <input v-model="relationForm.company_name" placeholder="如：雅克科技" />
          </div>
          <div class="form-group">
            <label>股票代码</label>
            <input v-model="relationForm.company_code" placeholder="如：002409" />
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>关系类型 *</label>
            <select v-model="relationForm.relation_type">
              <option value="upstream">上游供应商</option>
              <option value="downstream">下游客户</option>
              <option value="partner">合作伙伴</option>
            </select>
          </div>
          <div class="form-group">
            <label>置信度</label>
            <input v-model.number="relationForm.confidence" type="number" min="0" max="1" step="0.1" placeholder="0.8" />
          </div>
        </div>
        <div class="form-group">
          <label>关系描述</label>
          <textarea v-model="relationForm.relation_desc" rows="2" placeholder="描述供应链关系..."></textarea>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>产品/服务</label>
            <input v-model="relationForm.product_service" placeholder="提供什么产品或服务" />
          </div>
          <div class="form-group">
            <label>合作时间</label>
            <input v-model="relationForm.start_time" placeholder="如：2023年" />
          </div>
        </div>
        <div class="form-group">
          <label>合作详情</label>
          <textarea v-model="relationForm.cooperation_detail" rows="2" placeholder="具体合作内容..."></textarea>
        </div>
        <div class="form-group">
          <label>业务规模</label>
          <input v-model="relationForm.business_volume" placeholder="如：年供应额约1亿元" />
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>来源</label>
            <input v-model="relationForm.source" placeholder="信息来源" />
          </div>
          <div class="form-group">
            <label>来源链接</label>
            <input v-model="relationForm.source_url" placeholder="https://..." />
          </div>
        </div>
        <div class="form-row">
          <div class="form-group">
            <label>新闻标题</label>
            <input v-model="relationForm.news_title" placeholder="相关新闻标题" />
          </div>
          <div class="form-group">
            <label>新闻日期</label>
            <input v-model="relationForm.news_date" type="date" />
          </div>
        </div>
        <div class="modal-actions">
          <button class="btn" @click="closeRelationModal">取消</button>
          <button class="btn btn-primary" @click="saveRelation" :disabled="!relationForm.company_name">
            {{ editingRelationId ? '保存修改' : '新增关系' }}
          </button>
        </div>
      </div>
    </div>

    <!-- 新增笔记对话框 -->
    <div v-if="showAddNote" class="modal-overlay" @click="showAddNote = false">
      <div class="modal" @click.stop>
        <h3 class="modal-title">新增笔记</h3>
        <div class="form-group">
          <label>笔记内容</label>
          <textarea v-model="newNoteContent" rows="6" placeholder="输入你的笔记内容..."></textarea>
        </div>
        <div class="modal-actions">
          <button class="btn" @click="showAddNote = false">取消</button>
          <button class="btn btn-primary" @click="handleAddNote" :disabled="!newNoteContent.trim()">
            添加笔记
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted } from "vue";
import { useRouter, useRoute } from "vue-router";
import {
  getSupplyChainDetail,
  runSupplyChainResearch,
  supplementResearch,
  deleteSupplyChainResearch,
  addSupplyChainRelation,
  updateSupplyChainRelation,
  deleteSupplyChainRelation,
  getSupplyChainNotes,
  addSupplyChainNote,
  updateSupplyChainNote,
  deleteSupplyChainNote,
} from "../api/supplyChain";
import type { SupplyChainResearch, SupplyChainRelation, SupplyChainNote } from "../types";

const router = useRouter();
const route = useRoute();

const research = ref<SupplyChainResearch | null>(null);
const loading = ref(true);
let refreshTimer: ReturnType<typeof setInterval> | null = null;

// 补充采集
const showSupplement = ref(false);
const supplementContent = ref("");
const supplementNote = ref("");
const supplementSubmitting = ref(false);

// 关系编辑
const showAddRelation = ref(false);
const editingRelationId = ref<number | null>(null);
const relationForm = ref({
  company_name: "",
  company_code: "",
  relation_type: "upstream",
  relation_desc: "",
  product_service: "",
  cooperation_detail: "",
  business_volume: "",
  start_time: "",
  confidence: null as number | null,
  source: "",
  source_url: "",
  news_title: "",
  news_date: "",
});

// 笔记
const notes = ref<SupplyChainNote[]>([]);
const showAddNote = ref(false);
const newNoteContent = ref("");
const editingNoteId = ref<number | null>(null);
const editingNoteContent = ref("");

interface RelationGroup {
  type: string;
  label: string;
  icon: string;
  relations: SupplyChainRelation[];
}

const relationGroups = computed<RelationGroup[]>(() => {
  if (!research.value?.relations) return [];

  const upstreamTypes = ["upstream", "supplier", "上游供应商"];
  const downstreamTypes = ["downstream", "customer", "下游客户"];
  const partnerTypes = ["partner", "合作伙伴"];

  const upstream = research.value.relations.filter(r => upstreamTypes.includes(r.relation_type));
  const downstream = research.value.relations.filter(r => downstreamTypes.includes(r.relation_type));
  const partner = research.value.relations.filter(r => partnerTypes.includes(r.relation_type));

  const groups: RelationGroup[] = [];
  if (upstream.length) groups.push({ type: "upstream", label: "上游供应商", icon: "⬆️", relations: upstream });
  if (downstream.length) groups.push({ type: "downstream", label: "下游客户", icon: "⬇️", relations: downstream });
  if (partner.length) groups.push({ type: "partner", label: "合作伙伴", icon: "🤝", relations: partner });

  return groups;
});

const upstreamCount = computed(() => {
  return research.value?.relations?.filter(r =>
    ["upstream", "supplier", "上游供应商"].includes(r.relation_type)
  ).length || 0;
});

const downstreamCount = computed(() => {
  return research.value?.relations?.filter(r =>
    ["downstream", "customer", "下游客户"].includes(r.relation_type)
  ).length || 0;
});

const partnerCount = computed(() => {
  return research.value?.relations?.filter(r =>
    ["partner", "合作伙伴"].includes(r.relation_type)
  ).length || 0;
});

function statusText(status: string) {
  const map: Record<string, string> = {
    pending: "待处理",
    processing: "分析中",
    completed: "已完成",
    failed: "失败",
  };
  return map[status] || status;
}

function fixUrl(url: string): string {
  if (!url) return "#";
  // 如果已经有协议，直接返回
  if (url.startsWith("http://") || url.startsWith("https://")) {
    return url;
  }
  // 如果以 // 开头，添加 https:
  if (url.startsWith("//")) {
    return "https:" + url;
  }
  // 其他情况添加 https://
  return "https://" + url;
}

function formatTime(t?: string) {
  if (!t) return "";
  return t.replace("T", " ").substring(0, 19);
}

async function loadDetail() {
  const id = Number(route.params.id);
  if (!id) return;

  loading.value = true;
  try {
    const res = await getSupplyChainDetail(id);
    if (res.code === 0) {
      research.value = res.data;

      // 如果状态是处理中或待处理，启动自动刷新
      if (res.data.status === "processing" || res.data.status === "pending") {
        startAutoRefresh();
      } else {
        stopAutoRefresh();
      }
    }
  } finally {
    loading.value = false;
  }
}

async function loadNotes() {
  const id = Number(route.params.id);
  if (!id) return;

  try {
    const res = await getSupplyChainNotes(id);
    if (res.code === 0) {
      notes.value = res.data;
    }
  } catch (e) {
    console.error("加载笔记失败:", e);
  }
}

function goBack() {
  router.push("/supply-chain");
}

async function runResearch() {
  if (!research.value) return;

  const res = await runSupplyChainResearch(research.value.id);
  if (res.code === 0) {
    alert(res.data.message);
    loadDetail();
  }
}

async function handleDeleteResearch() {
  if (!research.value) return;
  if (!confirm(`确定要删除研究任务"${research.value.target_name}"吗？`)) return;

  const res = await deleteSupplyChainResearch(research.value.id);
  if (res.code === 0) {
    alert("删除成功");
    router.push("/supply-chain");
  }
}

async function submitSupplement() {
  if (!research.value || !supplementContent.value.trim()) {
    alert("请输入链接或内容");
    return;
  }

  supplementSubmitting.value = true;
  try {
    const res = await supplementResearch(research.value.id, {
      content: supplementContent.value.trim(),
      note: supplementNote.value.trim(),
    });
    if (res.code === 0) {
      alert(res.data.message);
      showSupplement.value = false;
      supplementContent.value = "";
      supplementNote.value = "";
      loadDetail();
    }
  } finally {
    supplementSubmitting.value = false;
  }
}

// 关系编辑
function editRelation(rel: SupplyChainRelation) {
  editingRelationId.value = rel.id;
  relationForm.value = {
    company_name: rel.company_name || "",
    company_code: rel.company_code || "",
    relation_type: rel.relation_type || "upstream",
    relation_desc: rel.relation_desc || "",
    product_service: rel.product_service || "",
    cooperation_detail: rel.cooperation_detail || "",
    business_volume: rel.business_volume || "",
    start_time: rel.start_time || "",
    confidence: rel.confidence ?? null,
    source: rel.source || "",
    source_url: rel.source_url || "",
    news_title: rel.news_title || "",
    news_date: rel.news_date || "",
  };
}

function closeRelationModal() {
  showAddRelation.value = false;
  editingRelationId.value = null;
  relationForm.value = {
    company_name: "",
    company_code: "",
    relation_type: "upstream",
    relation_desc: "",
    product_service: "",
    cooperation_detail: "",
    business_volume: "",
    start_time: "",
    confidence: null,
    source: "",
    source_url: "",
    news_title: "",
    news_date: "",
  };
}

async function saveRelation() {
  if (!research.value || !relationForm.value.company_name) return;

  const formData = { ...relationForm.value };
  // 构建提交数据，清理空值
  const data: Record<string, any> = {};
  Object.entries(formData).forEach(([key, value]) => {
    if (value !== "" && value !== null && value !== undefined) {
      data[key] = value;
    }
  });

  try {
    if (editingRelationId.value) {
      const res = await updateSupplyChainRelation(editingRelationId.value, data as any);
      if (res.code === 0) {
        alert("更新成功");
        closeRelationModal();
        loadDetail();
      }
    } else {
      const res = await addSupplyChainRelation(research.value.id, data as any);
      if (res.code === 0) {
        alert("新增成功");
        closeRelationModal();
        loadDetail();
      }
    }
  } catch (e) {
    alert("操作失败");
  }
}

async function handleDeleteRelation(relationId: number) {
  if (!confirm("确定要删除这条关系吗？")) return;

  const res = await deleteSupplyChainRelation(relationId);
  if (res.code === 0) {
    alert("删除成功");
    loadDetail();
  }
}

// 笔记操作
async function handleAddNote() {
  if (!research.value || !newNoteContent.value.trim()) return;

  const res = await addSupplyChainNote(research.value.id, newNoteContent.value.trim());
  if (res.code === 0) {
    alert("笔记已添加");
    showAddNote.value = false;
    newNoteContent.value = "";
    loadNotes();
  }
}

function startEditNote(note: SupplyChainNote) {
  editingNoteId.value = note.id;
  editingNoteContent.value = note.content;
}

function cancelEditNote() {
  editingNoteId.value = null;
  editingNoteContent.value = "";
}

async function saveEditNote(noteId: number) {
  if (!editingNoteContent.value.trim()) return;

  const res = await updateSupplyChainNote(noteId, editingNoteContent.value.trim());
  if (res.code === 0) {
    editingNoteId.value = null;
    editingNoteContent.value = "";
    loadNotes();
  }
}

async function handleDeleteNote(noteId: number) {
  if (!confirm("确定要删除这条笔记吗？")) return;

  const res = await deleteSupplyChainNote(noteId);
  if (res.code === 0) {
    alert("笔记已删除");
    loadNotes();
  }
}

function startAutoRefresh() {
  stopAutoRefresh();
  refreshTimer = setInterval(async () => {
    const id = Number(route.params.id);
    if (!id) return;

    try {
      const res = await getSupplyChainDetail(id);
      if (res.code === 0) {
        research.value = res.data;
        // 如果状态不再是处理中，停止刷新
        if (res.data.status !== "processing" && res.data.status !== "pending") {
          stopAutoRefresh();
        }
      }
    } catch (e) {
      console.error("刷新失败:", e);
    }
  }, 3000); // 每3秒刷新一次
}

function stopAutoRefresh() {
  if (refreshTimer) {
    clearInterval(refreshTimer);
    refreshTimer = null;
  }
}

onMounted(() => {
  loadDetail();
  loadNotes();
});

onUnmounted(() => {
  stopAutoRefresh();
});
</script>

<style scoped>
.supply-chain-detail {
  max-width: 1200px;
  margin: 0 auto;
  padding: 24px;
}

/* 头部 */
.detail-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 32px;
  padding-bottom: 24px;
  border-bottom: 1px solid var(--border-light);
}

.header-left {
  flex: 1;
}

.btn-back {
  background: none;
  border: none;
  color: var(--text-secondary);
  cursor: pointer;
  font-size: 13px;
  padding: 0;
  margin-bottom: 12px;
}

.btn-back:hover {
  color: var(--primary);
}

.detail-title {
  font-size: 28px;
  font-weight: 700;
  color: var(--text);
  margin-bottom: 12px;
}

.detail-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.type-badge {
  font-size: 12px;
  padding: 4px 10px;
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

.target-code {
  font-family: "SF Mono", monospace;
  font-size: 13px;
  color: var(--text-muted);
}

.status-badge {
  font-size: 12px;
  padding: 4px 10px;
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

.refresh-hint {
  font-size: 12px;
  color: var(--primary);
  animation: pulse 2s infinite;
}

@keyframes pulse {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

.header-actions {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
}

/* 按钮 */
.btn {
  padding: 10px 20px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-size: 14px;
  cursor: pointer;
  transition: all 0.2s;
  background: var(--bg);
  color: var(--text);
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

.btn-secondary {
  background: var(--bg);
  color: var(--text);
}

.btn-danger {
  background: #ffebee;
  color: #d32f2f;
  border-color: #ffcdd2;
}

.btn-danger:hover {
  background: #ffcdd2;
}

.btn-sm {
  padding: 6px 12px;
  font-size: 12px;
}

/* 摘要 */
.summary-section {
  background: var(--bg);
  border: 1px solid var(--border-light);
  border-radius: var(--radius);
  padding: 24px;
  margin-bottom: 24px;
}

.section-title {
  font-size: 18px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.section-title .count {
  font-size: 13px;
  font-weight: 400;
  color: var(--text-muted);
}

.section-title .btn {
  margin-left: auto;
}

.summary-content {
  font-size: 14px;
  line-height: 1.8;
  color: var(--text-secondary);
}

/* 采集来源 */
.sources-section {
  background: var(--bg);
  border: 1px solid var(--border-light);
  border-radius: var(--radius);
  padding: 24px;
  margin-bottom: 24px;
}

.sources-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.source-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px 16px;
  background: var(--bg-secondary);
  border-radius: var(--radius);
  text-decoration: none;
  color: inherit;
  transition: all 0.2s;
}

.source-item:hover {
  background: var(--border-light);
  text-decoration: none;
}

.source-idx {
  font-size: 12px;
  font-weight: 600;
  color: var(--primary);
  background: var(--primary-light);
  width: 24px;
  height: 24px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.source-info {
  flex: 1;
  min-width: 0;
}

.source-title {
  font-size: 14px;
  font-weight: 500;
  color: var(--text);
  margin-bottom: 4px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.source-url {
  font-size: 12px;
  color: var(--text-muted);
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.source-badge {
  font-size: 11px;
  padding: 2px 8px;
  background: var(--bg);
  border-radius: 4px;
  color: var(--text-secondary);
  flex-shrink: 0;
}

/* 统计 */
.relation-stats {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 16px;
  margin-bottom: 32px;
}

.stat-item {
  background: var(--bg);
  border: 1px solid var(--border-light);
  border-radius: var(--radius);
  padding: 20px;
  text-align: center;
}

.stat-number {
  font-size: 36px;
  font-weight: 700;
  color: var(--primary);
}

.stat-label {
  font-size: 13px;
  color: var(--text-secondary);
  margin-top: 4px;
}

/* 关系列表 */
.relations-section {
  margin-bottom: 32px;
}

.relation-group {
  margin-bottom: 32px;
}

.group-title {
  font-size: 16px;
  font-weight: 600;
  color: var(--text);
  margin-bottom: 16px;
  display: flex;
  align-items: center;
  gap: 8px;
}

.group-icon {
  font-size: 18px;
}

.group-count {
  font-size: 14px;
  font-weight: 400;
  color: var(--text-muted);
}

.relation-list {
  display: grid;
  gap: 16px;
}

.relation-card {
  background: var(--bg);
  border: 1px solid var(--border-light);
  border-radius: var(--radius);
  padding: 20px;
  transition: all 0.2s;
}

.relation-card:hover {
  box-shadow: var(--shadow-md);
}

.relation-header {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  margin-bottom: 12px;
}

.company-info {
  display: flex;
  align-items: center;
  gap: 12px;
}

.company-name {
  font-size: 18px;
  font-weight: 600;
  color: var(--text);
}

.company-code {
  font-family: "SF Mono", monospace;
  font-size: 12px;
  color: var(--primary);
  background: var(--primary-light);
  padding: 2px 8px;
  border-radius: 4px;
  text-decoration: none;
}

.company-code:hover {
  text-decoration: underline;
}

.relation-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

.confidence {
  display: flex;
  align-items: center;
  gap: 8px;
}

.confidence-bar {
  width: 60px;
  height: 6px;
  background: var(--border-light);
  border-radius: 3px;
  overflow: hidden;
}

.confidence-fill {
  height: 100%;
  background: var(--primary);
  border-radius: 3px;
  transition: width 0.3s;
}

.confidence-value {
  font-size: 12px;
  font-weight: 600;
  color: var(--primary);
  min-width: 35px;
}

.relation-desc {
  font-size: 14px;
  color: var(--text-secondary);
  line-height: 1.6;
  margin-bottom: 12px;
}

.relation-details {
  display: grid;
  gap: 8px;
  margin-bottom: 12px;
  padding: 12px;
  background: var(--bg-secondary);
  border-radius: var(--radius);
}

.detail-item {
  font-size: 13px;
  line-height: 1.5;
}

.detail-label {
  color: var(--text-muted);
  font-weight: 500;
}

.detail-value {
  color: var(--text);
}

.relation-source {
  display: flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  color: var(--text-muted);
  padding-top: 12px;
  border-top: 1px solid var(--border-light);
}

.source-text {
  flex: 1;
}

.source-link {
  color: var(--primary);
  text-decoration: none;
}

.source-link:hover {
  text-decoration: underline;
}

.news-date {
  flex-shrink: 0;
}

/* 笔记模块 */
.notes-section {
  margin-bottom: 32px;
}

.notes-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.note-card {
  background: var(--bg);
  border: 1px solid var(--border-light);
  border-radius: var(--radius);
  padding: 16px;
}

.note-content {
  font-size: 14px;
  line-height: 1.8;
  color: var(--text);
  white-space: pre-wrap;
}

.note-textarea {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-size: 14px;
  font-family: inherit;
  resize: vertical;
}

.note-textarea:focus {
  outline: none;
  border-color: var(--primary);
}

.note-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid var(--border-light);
}

.note-time {
  font-size: 12px;
  color: var(--text-muted);
}

.note-actions {
  display: flex;
  gap: 8px;
}

.empty-notes {
  text-align: center;
  padding: 40px;
  color: var(--text-muted);
  font-size: 14px;
  background: var(--bg);
  border: 1px dashed var(--border-light);
  border-radius: var(--radius);
}

/* 时间信息 */
.time-info {
  display: flex;
  gap: 24px;
  font-size: 12px;
  color: var(--text-muted);
  padding-top: 24px;
  border-top: 1px solid var(--border-light);
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
  max-width: 560px;
  max-height: 90vh;
  overflow-y: auto;
}

.modal-lg {
  max-width: 720px;
}

.modal-title {
  font-size: 18px;
  font-weight: 600;
  margin-bottom: 8px;
}

.modal-desc {
  font-size: 13px;
  color: var(--text-secondary);
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
.form-group textarea,
.form-group select {
  width: 100%;
  padding: 10px 12px;
  border: 1px solid var(--border);
  border-radius: var(--radius);
  font-size: 14px;
  font-family: inherit;
}

.form-group input:focus,
.form-group textarea:focus,
.form-group select:focus {
  outline: none;
  border-color: var(--primary);
}

.form-group textarea {
  resize: vertical;
}

.form-row {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
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
  padding: 60px 20px;
  color: var(--text-muted);
  font-size: 14px;
}

/* 响应式 */
@media (max-width: 768px) {
  .supply-chain-detail {
    padding: 16px;
  }

  .detail-header {
    flex-direction: column;
    gap: 16px;
  }

  .detail-title {
    font-size: 22px;
  }

  .header-actions {
    width: 100%;
  }

  .header-actions .btn {
    flex: 1;
  }

  .relation-stats {
    grid-template-columns: 1fr;
  }

  .company-info {
    flex-direction: column;
    align-items: flex-start;
    gap: 4px;
  }

  .relation-header {
    flex-direction: column;
    gap: 12px;
  }

  .relation-actions {
    width: 100%;
    justify-content: flex-end;
  }

  .confidence {
    width: 100%;
  }

  .time-info {
    flex-direction: column;
    gap: 8px;
  }

  .relation-source {
    flex-direction: column;
    align-items: flex-start;
    gap: 8px;
  }

  .form-row {
    grid-template-columns: 1fr;
  }
}
</style>
