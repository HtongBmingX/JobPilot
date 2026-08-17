<script setup>
/**
 * InputPanel.vue — 用户输入面板
 *
 * 体验要点：
 * 1. 简历/JD 用常驻卡片（不折叠），用户随时看到当前状态
 * 2. 上传支持点击 + 拖拽，有字数统计
 * 3. 底部上下文 chips 实时显示"本次会带上什么"
 * 4. 有内容时可一键清空、保存到简历库、从简历库切换
 */
import { ref, computed } from 'vue'

const emit = defineEmits(['run', 'upload', 'stop', 'save-resume', 'load-resume'])
const props = defineProps({
  loading: { type: Boolean, default: false },
  fileName: { type: String, default: '' },
  uploading: { type: Boolean, default: false },
  resumes: { type: Array, default: () => [] },
})

const innerResume = defineModel('resumeText', { default: '' })
const innerJd = defineModel('jdText', { default: '' })
const innerQuery = defineModel('query', { default: '' })

const dragging = ref(false)

const resumeLen = computed(() => (innerResume.value || '').trim().length)
const jdLen = computed(() => (innerJd.value || '').trim().length)

function handleKeydown(e) {
  if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
    e.preventDefault()
    handleRun()
  }
}

function handleRun() {
  if (props.loading) return
  emit('run')
}

function onDrop(e) {
  dragging.value = false
  const file = e.dataTransfer.files && e.dataTransfer.files[0]
  if (!file) return
  emit('upload', { target: { files: [file], value: '' } })
}

function handleSaveResume() {
  if (!innerResume.value.trim()) return
  const name = window.prompt('给这份简历起个名字：', '我的简历') || '我的简历'
  emit('save-resume', name)
}

function handleLoadResume(e) {
  const id = e.target.value
  e.target.value = ''
  if (id) emit('load-resume', Number(id))
}
</script>

<template>
  <div class="input-panel">
    <!-- 简历 & JD 双卡片 -->
    <div class="doc-cards">
      <!-- 简历卡片 -->
      <div
        class="doc-card"
        :class="{ 'doc-card--drag': dragging, 'doc-card--filled': resumeLen > 0 }"
        @dragover.prevent="dragging = true"
        @dragleave="dragging = false"
        @drop.prevent="onDrop"
      >
        <div class="doc-card-head">
          <span class="doc-card-title">📄 简历</span>
          <span v-if="resumeLen > 0" class="doc-card-count">{{ resumeLen }} 字</span>
          <button
            v-if="resumeLen > 0"
            class="doc-clear"
            title="清空简历"
            @click="innerResume = ''"
          >清空</button>
        </div>
        <textarea
          v-model="innerResume"
          placeholder="拖拽 PDF/DOCX 到此处，或粘贴简历文本"
          rows="4"
          class="doc-textarea"
        ></textarea>
        <div class="doc-card-foot">
          <label class="upload-hint">
            <span v-if="props.uploading">解析中…</span>
            <span v-else-if="fileName">✅ {{ fileName }}</span>
            <span v-else>点击上传文件</span>
            <input
              type="file"
              accept=".pdf,.docx"
              @change="emit('upload', $event)"
              :disabled="loading || props.uploading"
              class="file-input-hidden"
            />
          </label>
          <div class="doc-card-actions">
            <button
              v-if="resumeLen > 0"
              class="doc-action"
              title="保存到简历库"
              @click="handleSaveResume"
            >💾 存库</button>
            <select
              v-if="props.resumes.length"
              class="doc-action-select"
              @change="handleLoadResume"
              title="从简历库加载"
            >
              <option value="">📂 简历库（{{ props.resumes.length }}）</option>
              <option v-for="r in props.resumes" :key="r.id" :value="r.id">
                {{ r.is_default ? '⭐ ' : '' }}{{ r.name }}
              </option>
            </select>
          </div>
        </div>
      </div>

      <!-- JD 卡片 -->
      <div class="doc-card" :class="{ 'doc-card--filled': jdLen > 0 }">
        <div class="doc-card-head">
          <span class="doc-card-title">📋 岗位 JD</span>
          <span v-if="jdLen > 0" class="doc-card-count">{{ jdLen }} 字</span>
          <button
            v-if="jdLen > 0"
            class="doc-clear"
            title="清空 JD"
            @click="innerJd = ''"
          >清空</button>
        </div>
        <textarea
          v-model="innerJd"
          placeholder="粘贴岗位描述（可选）"
          rows="3"
          class="doc-textarea"
        ></textarea>
      </div>
    </div>

    <!-- 上下文 chips：实时显示本次会带上什么 -->
    <div v-if="resumeLen > 0 || jdLen > 0" class="context-chips">
      <span v-if="resumeLen > 0" class="chip chip--resume">简历 · {{ resumeLen }} 字</span>
      <span v-if="jdLen > 0" class="chip chip--jd">JD · {{ jdLen }} 字</span>
      <span class="chip-hint">本次提问将带上以上内容</span>
    </div>

    <!-- 输入行 -->
    <div class="query-row">
      <textarea
        v-model="innerQuery"
        rows="1"
        placeholder="输入你的问题…（Shift+Enter 换行）"
        @keydown="handleKeydown"
        :disabled="loading"
        class="query-input"
      ></textarea>

      <button v-if="loading" @click="emit('stop')" class="stop-btn" title="停止生成">停止</button>
      <button v-else @click="handleRun" :disabled="loading" class="run-btn">发送</button>
    </div>
  </div>
</template>

<style scoped>
.input-panel {
  border-top: 1px solid #eef0f3;
  padding: 14px 20px 16px;
  background: #fff;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

/* 双卡片 */
.doc-cards {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}
.doc-card {
  border: 1px solid #e5e7eb;
  border-radius: 10px;
  padding: 10px 12px;
  display: flex;
  flex-direction: column;
  gap: 8px;
  transition: border-color 0.12s, background 0.12s;
  background: #fafbfc;
}
.doc-card--filled {
  border-color: #bfdbfe;
  background: #f8faff;
}
.doc-card--drag {
  border-color: #2563eb;
  border-style: dashed;
  background: #eff6ff;
}
.doc-card-head {
  display: flex;
  align-items: center;
  gap: 8px;
}
.doc-card-title {
  font-size: 13px;
  font-weight: 600;
  color: #374151;
}
.doc-card-count {
  font-size: 11px;
  color: #9ca3af;
  background: #f3f4f6;
  padding: 1px 7px;
  border-radius: 8px;
}
.doc-clear {
  margin-left: auto;
  background: none;
  border: none;
  color: #9ca3af;
  font-size: 12px;
  cursor: pointer;
  padding: 2px 4px;
}
.doc-clear:hover { color: #ef4444; }

.doc-textarea {
  width: 100%;
  box-sizing: border-box;
  border: 1px solid #e5e7eb;
  border-radius: 7px;
  padding: 8px 10px;
  font-size: 13px;
  font-family: system-ui, sans-serif;
  line-height: 1.5;
  resize: vertical;
  background: #fff;
  color: #1f2937;
}
.doc-textarea:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 2px rgba(37,99,235,0.1);
}

.doc-card-foot { display: flex; align-items: center; gap: 8px; }
.doc-card-actions { margin-left: auto; display: flex; align-items: center; gap: 6px; }
.doc-action {
  font-size: 11px;
  padding: 3px 8px;
  border: 1px solid #d1d5db;
  border-radius: 5px;
  background: #fff;
  color: #6b7280;
  cursor: pointer;
}
.doc-action:hover { color: #2563eb; border-color: #bfdbfe; background: #eff6ff; }
.doc-action-select {
  font-size: 11px;
  padding: 3px 6px;
  border: 1px solid #d1d5db;
  border-radius: 5px;
  background: #fff;
  color: #6b7280;
  cursor: pointer;
  max-width: 140px;
}
.upload-hint {
  font-size: 12px;
  color: #2563eb;
  cursor: pointer;
  user-select: none;
}
.upload-hint:hover { text-decoration: underline; }
.file-input-hidden { display: none; }

/* 上下文 chips */
.context-chips {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
}
.chip {
  font-size: 11px;
  padding: 3px 8px;
  border-radius: 6px;
  font-weight: 500;
}
.chip--resume { background: #eff6ff; color: #1d4ed8; }
.chip--jd { background: #f5f3ff; color: #6d28d9; }
.chip-hint { font-size: 11px; color: #c0c7d1; }

/* 输入行 */
.query-row {
  display: flex;
  gap: 8px;
  align-items: flex-end;
}
.query-input {
  flex: 1;
  box-sizing: border-box;
  padding: 9px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 14px;
  font-family: system-ui, sans-serif;
  line-height: 1.5;
  resize: none;
  max-height: 160px;
  color: #1f2937;
}
.query-input:focus {
  outline: none;
  border-color: #2563eb;
  box-shadow: 0 0 0 2px rgba(37,99,235,0.12);
}

.run-btn, .stop-btn {
  padding: 9px 18px;
  border: none;
  border-radius: 8px;
  font-size: 14px;
  font-weight: 500;
  cursor: pointer;
  white-space: nowrap;
  transition: background 0.15s;
}
.run-btn { background: #2563eb; color: #fff; }
.run-btn:hover:not(:disabled) { background: #1d4ed8; }
.run-btn:disabled { background: #9ca3af; cursor: not-allowed; }
.stop-btn { background: #fef2f2; color: #dc2626; border: 1px solid #fecaca; }
.stop-btn:hover { background: #fee2e2; }

@media (max-width: 700px) {
  .doc-cards { grid-template-columns: 1fr; }
}
</style>
