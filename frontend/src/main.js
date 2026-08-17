// 应用入口：创建一个 Vue 应用，并把它挂载到 index.html 里的 #app 节点
import { createApp } from 'vue'
import App from './App.vue'
import './styles/tokens.css'  // 设计 token（全局 CSS 变量）

createApp(App).mount('#app')
