<script setup>
import { computed, ref } from 'vue'
import JobCard from './JobCard.vue'
import ApplicationDetailModal from './ApplicationDetailModal.vue'

const props = defineProps({
  apps: { type: Array, required: true },
  loading: { type: Boolean, default: false },
  saving: { type: Boolean, default: false },
  error: { type: String, default: '' },
})

const emit = defineEmits(['update-status', 'delete', 'refresh', 'save', 'create'])

// 活跃阶段 —— 四宫格分区
const activeColumns = [
  { key: 'applied',     label: '已投递',   icon: '📋', accent: '#f59e0b', hint: '等待回应' },
  { key: 'screening',   label: '初筛中',   icon: '🔍', accent: '#3b82f6', hint: '简历被查看' },
  { key: 'interviewing', label: '面试中',  icon: '💬', accent: '#8b5cf6', hint: '正在推进' },
  { key: 'offered',     label: '已 Offer', icon: '✅', accent: '#10b981', hint: '拿到机会' },
]

const activeKeys = activeColumns.map(c => c.key)

// 活跃阶段卡片
const activeApps = computed(() => props.apps.filter(a => activeKeys.includes(a.status)))
// 已拒绝 —— 底部独立区域
const rejectedApps = computed(() => props.apps.filter(a => a.status === 'rejected'))

function appsInCol(key) {
  return activeApps.value.filter(a => a.status === key)
}

// 统计
const totalCount = computed(() => props.apps.length)
const rejectedCount = computed(() => rejectedApps.value.length)

// 详情弹窗状态：编辑模式存对象，创建模式存 null
const editingApp = ref(null)
const showModal = ref(false)  // 区分「弹窗是否打开」（editingApp 为 null 时是创建模式）

function openDetail(app) {
  editingApp.value = app
  showModal.value = true
}
function openCreate() {
  editingApp.value = null
  showModal.value = true
}
function closeDetail() {
  showModal.value = false
  editingApp.value = null
}
function handleSave(payload) {
  if (payload.id) {
    emit('save', payload)      // 编辑
  } else {
    emit('create', payload)    // 创建
  }
  closeDetail()
}
function handleDelete(id) {
  emit('delete', id)
  closeDetail()
}
</script>

<template>
  <div class="board">
    <div class="board-header">
      <div>
        <h3 class="board-title">投递看板</h3>
        <p class="board-sub">{{ totalCount }} 条投递 · {{ rejectedCount }} 条已拒</p>
      </div>
      <div class="board-actions">
        <button class="refresh-btn" @click="emit('refresh')" :disabled="loading">
          {{ loading ? '加载中...' : '刷新' }}
        </button>
        <button class="new-app-btn" @click="openCreate">＋ 新建投递</button>
      </div>
    </div>

    <!-- 空状态：一条投递都没有 -->
    <!-- 错误态：加载失败 -->
    <div v-if="error && totalCount === 0" class="board-empty board-error">
      <div class="board-empty-icon">⚠️</div>
      <p class="board-empty-title">加载投递记录失败</p>
      <p class="board-empty-sub">{{ error }}</p>
      <button class="retry-btn" @click="emit('refresh')">重试</button>
    </div>

    <!-- 空状态：一条投递都没有 -->
    <div v-else-if="!loading && totalCount === 0" class="board-empty">
      <div class="board-empty-icon">🗂️</div>
      <p class="board-empty-title">还没有投递记录</p>
      <p class="board-empty-sub">点击「＋ 新建投递」手动录入，或在聊天中分析后用「保存到看板」一键添加</p>
    </div>

    <!-- 四宫格：四个活跃阶段 -->
    <div v-else class="zone-grid">
      <section
        v-for="col in activeColumns"
        :key="col.key"
        class="zone"
        :style="{ '--accent': col.accent }"
      >
        <header class="zone-header">
          <span class="zone-icon">{{ col.icon }}</span>
          <span class="zone-label">{{ col.label }}</span>
          <span class="zone-hint">{{ col.hint }}</span>
          <span class="zone-count">{{ appsInCol(col.key).length }}</span>
        </header>
        <div class="zone-body">
          <JobCard
            v-for="app in appsInCol(col.key)"
            :key="app.id"
            :app="app"
            @update-status="(id, status) => $emit('update-status', id, status)"
            @open="openDetail"
          />
          <p v-if="!appsInCol(col.key).length" class="zone-empty">暂无</p>
        </div>
      </section>
    </div>

    <!-- 已拒绝：底部弱化横条 -->
    <section v-if="rejectedApps.length" class="rejected-zone">
      <header class="rejected-header">
        <span class="zone-icon">❌</span>
        <span class="zone-label">已拒</span>
        <span class="zone-count">{{ rejectedApps.length }}</span>
      </header>
      <div class="rejected-body">
        <JobCard
          v-for="app in rejectedApps"
          :key="app.id"
          :app="app"
          @update-status="(id, status) => $emit('update-status', id, status)"
          @open="openDetail"
        />
      </div>
    </section>

    <!-- 详情编辑 / 新建弹窗 -->
    <ApplicationDetailModal
      v-if="showModal"
      :app="editingApp"
      :loading="saving"
      @close="closeDetail"
      @save="handleSave"
      @delete="handleDelete"
    />
  </div>
</template>

<style scoped>
.board {
  display: flex;
  flex-direction: column;
  gap: 18px;
  padding: 4px 8px;
  max-width: 1200px;
  margin: 0 auto;
  width: 100%;
}

/* 头部 */
.board-header {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  margin-bottom: 2px;
}
.board-title { font-size: 20px; font-weight: 700; color: #111827; margin: 0; letter-spacing: -0.01em; }
.board-sub { font-size: 12px; color: #9ca3af; margin: 4px 0 0; }
.board-actions { display: flex; gap: 8px; }
.refresh-btn {
  font-size: 12px;
  padding: 6px 14px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
}
.refresh-btn:hover:not(:disabled) { background: #f3f4f6; }
.refresh-btn:disabled { opacity: 0.6; cursor: default; }
.new-app-btn {
  font-size: 12px;
  padding: 6px 14px;
  border: 1px solid transparent;
  border-radius: 8px;
  background: #2563eb;
  color: #fff;
  font-weight: 500;
  cursor: pointer;
  transition: 0.12s;
}
.new-app-btn:hover { background: #1d4ed8; }

/* 空状态 */
.board-empty {
  text-align: center;
  padding: 80px 20px;
  background: #fff;
  border: 1px dashed #d1d5db;
  border-radius: 12px;
}
.board-empty-icon { font-size: 44px; margin-bottom: 12px; }
.board-empty-title { font-size: 16px; font-weight: 600; color: #4b5563; margin: 0 0 6px; }
.board-empty-sub { font-size: 13px; color: #9ca3af; margin: 0; }
.board-error .board-empty-title { color: #dc2626; }
.retry-btn {
  margin-top: 16px;
  padding: 6px 16px;
  font-size: 13px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  background: #fff;
  color: #4b5563;
  cursor: pointer;
}
.retry-btn:hover { background: #f3f4f6; }

/* 四宫格 */
.zone-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 16px;
}
.zone {
  background: #fff;
  border: 1px solid #eef0f3;
  border-radius: 14px;
  display: flex;
  flex-direction: column;
  min-height: 260px;
  box-shadow: 0 1px 2px rgba(16, 24, 40, 0.03);
}
.zone-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 14px 16px;
  border-bottom: 1px solid #f1f3f6;
  border-top: 3px solid var(--accent);
  border-radius: 14px 14px 0 0;
}
.zone-icon { font-size: 15px; }
.zone-label { font-size: 14px; font-weight: 700; color: #1f2937; }
.zone-hint { font-size: 11px; color: #c0c7d1; }
.zone-count {
  margin-left: auto;
  background: #f3f4f6;
  color: #4b5563;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 9px;
  border-radius: 10px;
}
.zone-body {
  padding: 14px;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(230px, 1fr));
  gap: 10px;
  align-content: start;
  flex: 1;
}
.zone-empty {
  font-size: 12px;
  color: #d1d5db;
  text-align: center;
  padding: 40px 0;
  margin: 0;
}

/* 已拒绝：底部弱化横条 */
.rejected-zone {
  background: #fafbfc;
  border: 1px dashed #e5e7eb;
  border-radius: 12px;
}
.rejected-header {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 14px;
}
.rejected-zone .zone-label { color: #9ca3af; font-weight: 600; font-size: 13px; }
.rejected-zone .zone-count {
  margin-left: 0;
  background: #e5e7eb;
  color: #6b7280;
  font-size: 11px;
  font-weight: 600;
  padding: 2px 8px;
  border-radius: 10px;
}
.rejected-body {
  padding: 0 12px 12px;
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 8px;
}

@media (max-width: 900px) {
  .zone-grid { grid-template-columns: 1fr; }
}
</style>
