<script setup>
/**
 * AboutView.vue — 关于我们页面
 * 介绍项目、核心功能、使用指南、技术架构
 */

const features = [
  {
    icon: '📄',
    title: '简历分析',
    desc: '上传 PDF/DOCX 简历或粘贴文本，AI 从 HR 视角指出优点、不足和优化建议。',
  },
  {
    icon: '📋',
    title: 'JD 解析',
    desc: '解析岗位描述，提炼核心职责、技能要求、加分项，帮你吃透目标岗位。',
  },
  {
    icon: '🎯',
    title: '人岗匹配',
    desc: '基于简历和 JD 的分析结果，给出匹配度评分、优势、差距和改进方向。',
  },
  {
    icon: '💬',
    title: '模拟面试',
    desc: '支持技术面、行为面、综合面三种模式，多轮追问，最后给出整体评价。',
  },
  {
    icon: '📊',
    title: '投递看板',
    desc: '用看板管理求职进度，一键保存分析结果，五阶段跟踪每个岗位的进展。',
  },
  {
    icon: '🧠',
    title: '求职画像',
    desc: '沉淀你的目标岗位、技术栈、目标公司，Agent 跨对话记住你的求职背景。',
  },
  {
    icon: '🔍',
    title: '知识库检索',
    desc: '内置多岗位面试知识库，覆盖后端/Agent/前端/算法等方向，回答有来源可溯源。',
  },
]

const steps = [
  {
    title: '第一步：设置求职画像',
    desc: '点击左下角「画像」，填写目标岗位、技术栈、目标公司。Agent 会记住这些信息，跨对话持续引用。',
  },
  {
    title: '第二步：上传简历',
    desc: '在输入区拖拽 PDF/DOCX 简历，或直接粘贴简历文本，也可以保存多份简历到简历库。',
  },
  {
    title: '第三步：粘贴 JD 并提问',
    desc: '粘贴目标岗位的 JD，然后提问，例如「分析我的简历」「我和这个岗位匹配吗」。',
  },
  {
    title: '第四步：保存到看板',
    desc: 'AI 给出匹配分析后，点「保存到看板」一键创建投递记录，随时跟踪进度。',
  },
  {
    title: '第五步：模拟面试',
    desc: '准备面试时问「帮我模拟面试」，选择面试模式，多轮练习直到「结束面试」。',
  },
]

const techStack = [
  { name: '后端', items: 'FastAPI · Python 3.11 · SQLAlchemy · Redis' },
  { name: 'AI Agent', items: '手写 ReAct · LangChain 双版本 · 代码状态机 · RAG 混合检索' },
  { name: '前端', items: 'Vue 3 · Vite · Composition API · 设计 Token 系统' },
  { name: '基础设施', items: 'Docker Compose · Nginx · SQLite · Alembic' },
  { name: '大模型', items: 'DeepSeek（生成） · 通义千问 Embedding（向量化）' },
]
</script>

<template>
  <div class="about">
    <!-- 头部 -->
    <header class="about-hero">
      <div class="hero-badge">🤖 JobPilot</div>
      <h1 class="hero-title">AI 驱动的求职助手</h1>
      <p class="hero-sub">
        从简历分析到面试模拟，覆盖求职全流程。基于手写 ReAct Agent，
        不是简单的调包——每一个环节都理解底层原理。
      </p>
    </header>

    <!-- 核心功能 -->
    <section class="about-section">
      <h2 class="section-title">核心功能</h2>
      <div class="feature-grid">
        <div v-for="f in features" :key="f.title" class="feature-card">
          <span class="feature-icon">{{ f.icon }}</span>
          <h3 class="feature-title">{{ f.title }}</h3>
          <p class="feature-desc">{{ f.desc }}</p>
        </div>
      </div>
    </section>

    <!-- 使用指南 -->
    <section class="about-section">
      <h2 class="section-title">使用指南</h2>
      <div class="steps">
        <div v-for="(s, i) in steps" :key="i" class="step">
          <span class="step-num">{{ i + 1 }}</span>
          <div class="step-body">
            <h3 class="step-title">{{ s.title }}</h3>
            <p class="step-desc">{{ s.desc }}</p>
          </div>
        </div>
      </div>
    </section>

    <!-- 技术架构 -->
    <section class="about-section">
      <h2 class="section-title">技术架构</h2>
      <div class="tech-stack">
        <div v-for="t in techStack" :key="t.name" class="tech-row">
          <span class="tech-name">{{ t.name }}</span>
          <span class="tech-items">{{ t.items }}</span>
        </div>
      </div>
    </section>

    <!-- 底部说明 -->
    <footer class="about-footer">
      <p>JobPilot 是一个求职作品项目，展示从零构建 AI Agent 的完整过程。</p>
      <p class="footer-version">版本 v0.9.3</p>
    </footer>
  </div>
</template>

<style scoped>
.about {
  max-width: 900px;
  margin: 0 auto;
  padding: 8px 0 40px;
}

/* 头部 */
.about-hero {
  text-align: center;
  padding: 40px 20px 32px;
}
.hero-badge {
  display: inline-block;
  font-size: 15px;
  font-weight: 600;
  color: #2563eb;
  background: #eff6ff;
  padding: 6px 16px;
  border-radius: 9999px;
  margin-bottom: 16px;
}
.hero-title {
  font-size: 28px;
  font-weight: 700;
  color: #111827;
  margin: 0 0 12px;
  letter-spacing: -0.02em;
}
.hero-sub {
  font-size: 15px;
  color: #6b7280;
  line-height: 1.7;
  max-width: 560px;
  margin: 0 auto;
}

/* 章节 */
.about-section {
  margin-top: 32px;
}
.section-title {
  font-size: 18px;
  font-weight: 700;
  color: #1f2937;
  margin: 0 0 16px;
  padding-bottom: 10px;
  border-bottom: 1px solid #eef0f3;
}

/* 功能卡片 */
.feature-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(240px, 1fr));
  gap: 14px;
}
.feature-card {
  background: #fff;
  border: 1px solid #eef0f3;
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 1px 2px rgba(16,24,40,0.04);
}
.feature-icon { font-size: 22px; }
.feature-title {
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
  margin: 10px 0 4px;
}
.feature-desc {
  font-size: 13px;
  color: #6b7280;
  line-height: 1.6;
  margin: 0;
}

/* 使用指南步骤 */
.steps {
  display: flex;
  flex-direction: column;
  gap: 0;
}
.step {
  display: flex;
  gap: 14px;
  padding: 16px 0;
  border-bottom: 1px solid #f1f3f6;
}
.step:last-child { border-bottom: none; }
.step-num {
  flex-shrink: 0;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  background: #2563eb;
  color: #fff;
  font-size: 14px;
  font-weight: 600;
  display: flex;
  align-items: center;
  justify-content: center;
}
.step-title {
  font-size: 14px;
  font-weight: 600;
  color: #1f2937;
  margin: 0 0 4px;
}
.step-desc {
  font-size: 13px;
  color: #6b7280;
  line-height: 1.6;
  margin: 0;
}

/* 技术架构 */
.tech-stack {
  background: #fff;
  border: 1px solid #eef0f3;
  border-radius: 12px;
  padding: 6px 16px;
}
.tech-row {
  display: flex;
  gap: 14px;
  padding: 12px 0;
  border-bottom: 1px solid #f1f3f6;
}
.tech-row:last-child { border-bottom: none; }
.tech-name {
  flex-shrink: 0;
  width: 90px;
  font-size: 13px;
  font-weight: 600;
  color: #1f2937;
}
.tech-items {
  font-size: 13px;
  color: #6b7280;
  line-height: 1.6;
}

/* 底部 */
.about-footer {
  text-align: center;
  margin-top: 40px;
  padding-top: 20px;
  border-top: 1px solid #eef0f3;
  font-size: 13px;
  color: #9ca3af;
}
.about-footer p { margin: 0 0 4px; }
.footer-version { font-size: 12px; }

@media (max-width: 768px) {
  .feature-grid { grid-template-columns: 1fr; }
  .tech-name { width: 70px; }
}
</style>
