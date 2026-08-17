<script setup>
import { reactive, watch, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  profile: { type: Object, default: null },
  loading: { type: Boolean, default: false },
})

const emit = defineEmits(['close', 'save'])

// Esc 关闭弹窗
function onKeydown(e) {
  if (e.key === 'Escape') emit('close')
}
onMounted(() => document.addEventListener('keydown', onKeydown))
onUnmounted(() => document.removeEventListener('keydown', onKeydown))

const form = reactive({
  tech_stack: '',
  target_role: '',
  target_companies: '',
  education: '',
  experience_summary: '',
})

watch(
  () => props.profile,
  (p) => {
    if (!p) return
    form.tech_stack = p.tech_stack || ''
    form.target_role = p.target_role || ''
    form.target_companies = p.target_companies || ''
    form.education = p.education || ''
    form.experience_summary = p.experience_summary || ''
  },
  { immediate: true }
)

function handleSave() {
  emit('save', {
    tech_stack: form.tech_stack || null,
    target_role: form.target_role || null,
    target_companies: form.target_companies || null,
    education: form.education || null,
    experience_summary: form.experience_summary || null,
  })
}
</script>

<template>
  <div class="modal-overlay" @click.self="emit('close')">
    <div class="modal" role="dialog" aria-modal="true">
      <header class="modal-header">
        <div>
          <h3 class="modal-title">求职画像</h3>
          <p class="modal-subtitle">Agent 会记住这些信息，跨对话持续引用</p>
        </div>
        <button class="modal-close" @click="emit('close')" aria-label="关闭">×</button>
      </header>

      <div class="modal-body">
        <label class="field">
          <span class="field-label">目标岗位</span>
          <input v-model="form.target_role" class="field-input" placeholder="如：后端开发工程师" />
        </label>

        <label class="field">
          <span class="field-label">技术栈</span>
          <textarea v-model="form.tech_stack" class="field-input" rows="2" placeholder="如：Python, FastAPI, Redis, SQL"></textarea>
        </label>

        <label class="field">
          <span class="field-label">目标公司</span>
          <input v-model="form.target_companies" class="field-input" placeholder="如：字节跳动, 腾讯, 阿里" />
        </label>

        <label class="field">
          <span class="field-label">学历背景</span>
          <input v-model="form.education" class="field-input" placeholder="如：本科 / 计算机科学" />
        </label>

        <label class="field">
          <span class="field-label">经历摘要</span>
          <textarea v-model="form.experience_summary" class="field-input" rows="3" placeholder="如：2 段后端实习，参与过 XX 项目"></textarea>
        </label>
      </div>

      <footer class="modal-footer">
        <button class="btn btn-ghost" @click="emit('close')">取消</button>
        <button class="btn btn-primary" @click="handleSave" :disabled="loading">
          {{ loading ? '保存中…' : '保存' }}
        </button>
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
  width: 520px;
  max-width: 100%;
  max-height: 90vh;
  display: flex;
  flex-direction: column;
  box-shadow: 0 20px 50px rgba(0,0,0,0.18);
}
.modal-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 18px 22px 14px;
  border-bottom: 1px solid #eef0f3;
  flex-shrink: 0;
}
.modal-title { font-size: 17px; font-weight: 700; color: #1f2937; margin: 0; }
.modal-subtitle { font-size: 12px; color: #9ca3af; margin: 3px 0 0; }
.modal-close {
  background: none; border: none; font-size: 24px; line-height: 1;
  color: #9ca3af; cursor: pointer; padding: 0 4px;
}
.modal-close:hover { color: #4b5563; }
.modal-body {
  padding: 16px 22px 20px;
  overflow-y: auto;
  display: flex;
  flex-direction: column;
  gap: 14px;
}
.field { display: flex; flex-direction: column; gap: 6px; }
.field-label { font-size: 13px; font-weight: 500; color: #4b5563; }
.field-input {
  padding: 9px 12px;
  border: 1px solid #d1d5db;
  border-radius: 8px;
  font-size: 14px;
  font-family: inherit;
  color: #1f2937;
  resize: vertical;
  width: 100%;
  box-sizing: border-box;
}
.field-input:focus { outline: none; border-color: #2563eb; box-shadow: 0 0 0 3px rgba(37,99,235,0.12); }
.modal-footer {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
  padding: 14px 22px;
  border-top: 1px solid #eef0f3;
  flex-shrink: 0;
}
.btn {
  padding: 8px 16px;
  border-radius: 8px;
  font-size: 13px;
  font-weight: 500;
  cursor: pointer;
  border: 1px solid transparent;
}
.btn:disabled { opacity: 0.6; cursor: default; }
.btn-primary { background: #2563eb; color: #fff; }
.btn-primary:hover:not(:disabled) { background: #1d4ed8; }
.btn-ghost { background: #fff; color: #4b5563; border-color: #d1d5db; }
.btn-ghost:hover { background: #f3f4f6; }
</style>
