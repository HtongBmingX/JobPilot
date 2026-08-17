<script setup>
import { useToast } from '../composables/useToast.js'

const { toasts, dismiss } = useToast()
</script>

<template>
  <div class="toast-container" aria-live="polite" aria-atomic="false">
    <TransitionGroup name="toast">
      <div
        v-for="t in toasts"
        :key="t.id"
        class="toast"
        :class="'toast--' + t.type"
        :role="t.type === 'error' ? 'alert' : 'status'"
        @click="dismiss(t.id)"
        :tabindex="0"
        @keydown.enter="dismiss(t.id)"
      >
        <span class="toast-icon" aria-hidden="true">
          {{ t.type === 'success' ? '✓' : t.type === 'error' ? '⚠' : 'ℹ' }}
        </span>
        <span class="toast-msg">{{ t.message }}</span>
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.toast-container {
  position: fixed;
  top: 20px;
  left: 50%;
  transform: translateX(-50%);
  z-index: 100;
  display: flex;
  flex-direction: column;
  gap: 8px;
  align-items: center;
  pointer-events: none;
}
.toast {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 16px;
  border-radius: 10px;
  font-size: 13px;
  box-shadow: 0 6px 20px rgba(0,0,0,0.12);
  cursor: pointer;
  pointer-events: auto;
  max-width: 420px;
  background: #fff;
}
.toast-icon { font-weight: 700; flex-shrink: 0; }
.toast--success { border: 1px solid #a7f3d0; color: #047857; }
.toast--success .toast-icon { color: #10b981; }
.toast--error { border: 1px solid #fecaca; color: #b91c1c; }
.toast--error .toast-icon { color: #ef4444; }
.toast--info { border: 1px solid #bfdbfe; color: #1e40af; }
.toast--info .toast-icon { color: #3b82f6; }

.toast-enter-active, .toast-leave-active { transition: all 0.25s ease; }
.toast-enter-from { opacity: 0; transform: translateY(-12px); }
.toast-leave-to { opacity: 0; transform: translateY(-12px); }
</style>
