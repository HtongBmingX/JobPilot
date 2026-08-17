<script setup>
/**
 * ThinkChain.vue — Agent 思考过程可视化
 *
 * props:
 *   steps: [{ step: 'resume', thought: '...', status: 'running'|'done' }]
 *
 * 设计：垂直时间线 + 步骤状态，让"思考过程"有清晰的进度感。
 */
defineProps({
  steps: { type: Array, default: () => [] },
})

const stepMeta = {
  resume: { label: '分析简历', icon: '📄' },
  jd: { label: '分析 JD', icon: '📋' },
  match: { label: '岗位匹配', icon: '🎯' },
  interview: { label: '面试模拟', icon: '💬' },
}

function meta(step) {
  return stepMeta[step] || { label: step, icon: '•' }
}
</script>

<template>
  <div v-if="steps.length" class="think-chain" aria-live="polite">
    <div class="think-title">正在思考</div>
    <div
      v-for="(s, i) in steps"
      :key="i"
      class="think-step"
      :class="s.status"
    >
      <span class="think-icon" aria-hidden="true">{{ s.status === 'running' ? '⏳' : '✓' }}</span>
      <span class="think-main">
        <span class="think-label">{{ meta(s.step).icon }} {{ meta(s.step).label }}</span>
        <span v-if="s.thought && s.status === 'running'" class="think-thought">{{ s.thought }}</span>
      </span>
    </div>
  </div>
</template>

<style scoped>
.think-chain {
  margin: 0 auto 16px;
  max-width: 820px;
  padding: 12px 16px;
  background: #f8faff;
  border: 1px solid #e0e7ff;
  border-radius: 12px;
}
.think-title {
  font-size: 11px;
  font-weight: 600;
  color: #9ca3af;
  letter-spacing: 0.05em;
  text-transform: uppercase;
  margin-bottom: 8px;
}
.think-step {
  display: flex;
  align-items: flex-start;
  gap: 10px;
  padding: 5px 0;
}
.think-icon {
  flex-shrink: 0;
  width: 18px;
  height: 18px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  line-height: 1;
}
.think-step.running .think-icon {
  background: #eff6ff;
  color: #2563eb;
}
.think-step.done .think-icon {
  background: #ecfdf5;
  color: #059669;
}
.think-main { min-width: 0; display: flex; flex-direction: column; gap: 2px; }
.think-label { font-size: 13px; }
.think-step.running .think-label { color: #1d4ed8; font-weight: 500; }
.think-step.done .think-label { color: #6b7280; }
.think-thought {
  font-size: 12px;
  color: #9ca3af;
  font-style: italic;
  line-height: 1.5;
}
</style>
