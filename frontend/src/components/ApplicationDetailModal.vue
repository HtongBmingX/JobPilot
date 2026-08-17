<script setup>
import { reactive, ref, watch, computed, onMounted, onUnmounted } from 'vue'
import { scoreTier, relativeDate } from '../utils/application.js'

const props = defineProps({
  // 编辑模式传入投递对象；创建模式传 null
  app: { type: Object, default: null },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['close', 'save', 'delete'])

// Esc 关闭弹窗
function onKeydown(e) {
  if (e.key === 'Escape') emit('close')
}
onMounted(() => document.addEventListener('keydown', onKeydown))
onUnmounted(() => document.removeEventListener('keydown', onKeydown))

const form = reactive({
  company: '',
  position: '',
  match_score: '',
  applied_at: '',
  status: 'applied',
  notes: '',
  jd_text: '',
  match_summary: '',
})

const showConfirm = ref(false)
const deleting = ref(false)
const isCreate = computed(() => !props.app)

watch(
  () => props.app,
  (a) => {
    if (!a) {
      // 创建模式：重置为空表单
      form.company = ''
      form.position = ''
      form.match_score = ''
      form.applied_at = new Date().toISOString().slice(0, 10)
      form.status = 'applied'
      form.notes = ''
      form.jd_text = ''
      form.match_summary = ''
      showConfirm.value = false
      deleting.value = false
      return
    }
    form.company = a.company || ''
    form.position = a.position || ''
    form.match_score = a.match_score || ''
    form.applied_at = a.applied_at || ''
    form.status = a.status || 'applied'
    form.notes = a.notes || ''
    form.jd_text = a.jd_text || ''
    form.match_summary = a.match_summary || ''
    showConfirm.value = false
    deleting.value = false
  },
  { immediate: true }
)

const tier = () => scoreTier(form.match_score)

const statusOptions = [
  { value: 'applied', label: '📋 已投递' },
  { value: 'screening', label: '🔍 初筛中' },
  { value: 'interviewing', label: '💬 面试中' },
  { value: 'offered', label: '✅ 已 Offer' },
  { value: 'rejected', label: '❌ 已拒' },
]

function handleSave() {
  if (!form.company.trim() || !form.position.trim()) return
  emit('save', {
    // 创建模式不带 id；编辑模式带 id
    id: props.app ? props.app.id : undefined,
    company: form.company.trim(),
    position: form.position.trim(),
    match_score: form.match_score || '',
    applied_at: form.applied_at || '',
    status: form.status,
    notes: form.notes || '',
    jd_text: form.jd_text || '',
    match_summary: form.match_summary || '',
  })
}

function handleDelete() {
  if (!showConfirm.value) {
    showConfirm.value = true
    return
  }
  deleting.value = true
  emit('delete', props.app.id)
}
</script>

<template>
  <div class="modal-overlay" @click.self="emit('close')">
    <div class="modal" role="dialog" aria-modal="true">
      <header class="modal-header">
        <div class="header-text">
          <h3 class="modal-title">{{ isCreate ? '新建投递' : (form.company || '投递详情') }}</h3>
          <p v-if="!isCreate" class="modal-subtitle">
            {{ form.position }}
            <span v-if="relativeDate(form.applied_at)" class="modal-date">· {{ relativeDate(form.applied_at) }}</span>
          </p>
          <p v-else class="modal-subtitle">手动录入一条投递记录</p>
        </div>
        <button class="modal-close" @click="emit('close')" aria-label="关闭">×</button>
      </header>

      <div class="modal-body">
        <!-- 基本信息 -->
        <section class="group">
          <h4 class="group-title">基本信息</h4>
          <div class="grid-2">
            <label class="field">
              <span class="field-label">公司</span>
              <input v-model="form.company" class="field-input" placeholder="公司名" />
            </label>
            <label class="field">
              <span class="field-label">岗位</span>
              <input v-model="form.position" class="field-input" placeholder="岗位名" />
            </label>
          </div>
        </section>

        <!-- 进度 -->
        <section class="group">
          <h4 class="group-title">进度</h4>
          <label class="field">
            <span class="field-label">阶段</span>
            <div class="status-grid">
              <button
                v-for="opt in statusOptions"
                :key="opt.value"
                type="button"
                class="status-pill"
                :class="{ 'status-pill--active': form.status === opt.value }"
                @click="form.status = opt.value"
              >{{ opt.label }}</button>
            </div>
          </label>

          <div class="grid-2">
            <label class="field">
              <span class="field-label">投递日期</span>
              <input v-model="form.applied_at" type="date" class="field-input" />
            </label>
            <label class="field">
              <span class="field-label">匹配度</span>
              <div class="score-row">
                <input v-model="form.match_score" class="field-input" placeholder="85%" />
                <span class="score-dot" :class="'score-dot--' + tier()" :title="'匹配度：' + (form.match_score || '未填')"></span>
              </div>
            </label>
          </div>
        </section>

        <!-- 内容 -->
        <section class="group">
          <h4 class="group-title">内容</h4>
          <label class="field">
            <span class="field-label">匹配摘要</span>
            <textarea v-model="form.match_summary" class="field-input" rows="3" placeholder="匹配分析的结论摘要"></textarea>
          </label>

          <label class="field">
            <span class="field-label">我的备注</span>
            <textarea v-model="form.notes" class="field-input" rows="3" placeholder="面试进度、跟进计划、联系人…"></textarea>
          </label>

          <details class="field jd-details">
            <summary class="jd-summary">查看 / 编辑 JD 原文</summary>
            <textarea v-model="form.jd_text" class="field-input" rows="6" placeholder="岗位描述原文"></textarea>
          </details>
        </section>
      </div>

      <footer class="modal-footer">
        <button v-if="!isCreate" class="btn btn-danger" @click="handleDelete" :disabled="deleting">
          {{ showConfirm ? '再次点击确认删除' : '删除' }}
        </button>
        <span v-else></span>
        <div class="footer-right">
          <button class="btn btn-ghost" @click="emit('close')">取消</button>
          <button class="btn btn-primary" @click="handleSave" :disabled="loading">
            {{ loading ? '保存中…' : (isCreate ? '创建' : '保存') }}
          </button>
        </div>
      </footer>
    </div>
  </div>
</template>

<style scoped>
.modal-overlay {
  position: fixed;
  inset: 0;
  background: rgba(17, 24, 39, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 50;
  padding: 20px;
}
.modal {
  background: #fff;
  border-radius: 14px;
  width: 600px;
  max-width: 100%;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 50px rgba(0,0,0,0.18);
}

/* 头部 */
.modal-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 20px 24px 16px;
  border-bottom: 1px solid #eef0f3;
  flex-shrink: 0;
}
.modal-title { font-size: 17px; font-weight: 700; color: #1f2937; margin: 0; }
.modal-subtitle { font-size: 13px; color: #6b7280; margin: 3px 0 0; }
.modal-date { color: #9ca3af; }
.modal-close {
  background: none;
  border: none;
  font-size: 24px;
  line-height: 1;
  color: #9ca3af;
  cursor: pointer;
  padding: 0 4px;
}
.modal-close:hover { color: #4b5563; }

/* 正文 */
.modal-body {
  padding: 8px 24px 20px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 6px;
}
.group { padding: 14px 0; }
.group + .group { border-top: 1px solid #f1f3f6; }
.group-title {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  color: #9ca3af;
  margin: 0 0 12px;
}
.grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 14px;
}
.field { display: flex; flex-direction: column; gap: 6px; margin-bottom: 14px; }
.group .field:last-child { margin-bottom: 0; }
.field-label { font-size: 13px; font-weight: 500; color: #4b5563; }
.field-input {
  padding: 9px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 14px;
  font-family: inherit;
  color: #1f2937;
  resize: vertical;
  background: #fff;
  width: 100%;
  box-sizing: border-box;
  transition: border-color 0.12s;
}
.field-input:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 3px rgba(37,99,235,0.12);
}

/* 阶段选择 —— 用 pill 按钮替代下拉，一眼看清五个阶段 */
.status-grid {
  display: grid;
  grid-template-columns: repeat(5, 1fr);
  gap: 6px;
}
.status-pill {
  padding: 7px 4px;
  font-size: 12px;
  border: 1px solid #e5e7eb;
  border-radius: 7px;
  background: #fff;
  color: #6b7280;
  cursor: pointer;
  white-space: nowrap;
  transition: 0.12s;
}
.status-pill:hover { border-color: #cbd5e1; }
.status-pill--active {
  background: #eff6ff;
  border-color: #2563eb;
  color: #1d4ed8;
  font-weight: 500;
}

/* 匹配度 —— 输入框 + 色阶点 */
.score-row { display: flex; align-items: center; gap: 8px; }
.score-row .field-input { flex: 1; }
.score-dot {
  width: 14px; height: 14px;
  border-radius: 50%;
  flex-shrink: 0;
  border: 2px solid #fff;
  box-shadow: 0 0 0 1px #e5e7eb;
}
.score-dot--high { background: #10b981; }
.score-dot--mid  { background: #f59e0b; }
.score-dot--low  { background: #9ca3af; }
.score-dot--none { background: #e5e7eb; }

/* JD 折叠 */
.jd-details { border-top: 1px dashed #e5e7eb; padding-top: 12px; }
.jd-summary {
  font-size: 13px;
  font-weight: 500;
  color: #6b7280;
  cursor: pointer;
  user-select: none;
}
.jd-summary:hover { color: #2563eb; }
.jd-details[open] .jd-summary { margin-bottom: 8px; }

/* 底部 */
.modal-footer {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 24px;
  border-top: 1px solid #eef0f3;
  flex-shrink: 0;
}
.footer-right { display: flex; gap: 8px; }
.btn {
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid transparent;
  transition: 0.12s;
}
.btn:disabled { opacity: 0.6; cursor: default; }
.btn-primary { background: #2563eb; color: #fff; }
.btn-primary:hover:not(:disabled) { background: #1d4ed8; }
.btn-ghost { background: #fff; color: #4b5563; border-color: #d1d5db; }
.btn-ghost:hover { background: #f3f4f6; }
.btn-danger { background: #fff; color: #dc2626; border-color: #fecaca; }
.btn-danger:hover:not(:disabled) { background: #fef2f2; }

@media (max-width: 520px) {
  .grid-2 { grid-template-columns: 1fr; }
  .status-grid { grid-template-columns: repeat(3, 1fr); }
}
</style>
