# JobPilot 后续开发路线（v0.9.2 → v1.0）

> 当前状态：15 endpoints · 55+ modules · 7500+ lines · 7 docs  
> 更新日期：2026-08-14
>
> ⚠️ 本文件聚焦进度记录，详细路线图见 `roadmap.md`（已更新为四段式路径）。

---

## 当前进度总览

| Phase | 内容 | 状态 |
|-------|------|------|
| Phase 1 | 体验层（SSE流式、Markdown渲染、多轮对话、前端组件化） | ✅ |
| Phase 2 | 架构层（代码状态机、异常体系、全局错误处理） | ✅ |
| Phase 3 | 数据层（Redis持久化、API限流、Docker Compose） | ✅ |
| Phase 4 | LangChain 迁移（LangGraph prebuilt 版，流式有 workaround） | ✅ |
| Phase 5 | 生产化部署 — Docker 全项目容器化 | ✅ |
| Phase 6 | 产品化 — 鉴权 + 投递看板 + 工程面板 | ✅ |
| Phase 7 | Agent 能力扩展（灵活对话 + 面试模拟） | ✅ |
| Phase 8 | 自建评测体系（3 指标 + 5 用例 + 报告生成） | ✅ |
| Phase 9 | 2026-08-09 Bug 修复（agent_state crash + 安全问题） | ✅ |
| Phase 10 | 2026-08-14 前端整体改版 + 功能收尾（侧边栏 + 多会话 + 看板重构 + Toast 等） | ✅ |
| Phase 11 | 产品收尾（面试多轮 + 扫描件检测 + 回归测试） | ⬜ |
| Phase 12 | RAG 检索管线（Hybrid Search + Reranker） | ⬜ |
| Phase 13 | MCP 协议接入 | ⬜ |
| Phase 14 | LangGraph 手写图版（StateGraph + conditional_edge） | ⬜ |
| Phase 15 | 上线收尾（云部署 + 安全 + 文档定稿） | ⬜ |

---

## 下一阶段（Phase 11：产品收尾，约 1 周）

> 目标：把现有功能打磨到"没有明显断点"，为后续技术纵深打地基。

- [ ] 面试连续多轮 —— SessionMemory 加 interview_round 计数器 + interview_mode 状态，让面试模拟记住"正在面试中"
- [ ] 扫描件检测 —— /upload 提取文本为空时返回明确提示
- [ ] 回归测试 —— 今日大量改动后补一轮（重点 agent_state.py + useAgent.js）
- [ ] 边角清理 —— ChatBubble 保存按钮状态残留、useApplications 的 appsError 展示

---

## 历史记录：Phase 6 — 鉴权 + 投递看板 + 工程面板 ✅

> 完成日期：2026-07-29

### JWT 鉴权系统
- [x] `backend/app/core/database.py`：SQLAlchemy 引擎 + Session 工厂
- [x] `backend/app/core/auth.py`：bcrypt + JWT + get_current_user FastAPI Depends
- [x] `backend/app/models/user.py`：User ORM 模型
- [x] `backend/app/repositories/user_repo.py`：Repository 模式
- [x] `POST /auth/register`、`POST /auth/login`、`POST /auth/refresh`
- [x] 所有 Agent 端点 + upload 端点挂 get_current_user 鉴权
- [x] 前端登录/注册页 + 请求自动带 Authorization 头

### 投递看板
- [x] `backend/app/models/application.py`：Application ORM 模型
- [x] `backend/app/repositories/application_repo.py`：CRUD + 状态筛选 + 归属校验
- [x] `POST/GET/PUT/DELETE /applications` 四个 REST 端点
- [x] `frontend/src/components/JobBoard.vue`：五列看板视图
- [x] `frontend/src/components/JobCard.vue`：卡片组件（状态切换 + 删除）
- [x] ChatBubble "📌 保存到投递看板"一键保存（自动提取 + 手动兜底）

### 工程面板 + 聊天持久化
- [x] `GET /status` 端点 + StatusBar 底部状态栏
- [x] localStorage 聊天记录持久化（刷新恢复，退出清除）

### 踩坑
- [x] passlib + bcrypt 版本兼容性（锁死 `bcrypt==4.0.1`）
- [x] JWT datetime → Unix 时间戳转换
- [x] JWT sub 字段必须是字符串
- [x] /status 401 连锁反应
- [x] Nginx 缺少新路由代理规则

---

## 面试核心叙事（2 分钟版本）

> 这个叙事贯穿你整个项目，从手写 → 框架 → 生产化 → 产品化，层层递进。

「我做的是一个 AI 求职助手 JobPilot，后端用 FastAPI，前端 Vue3，接入 DeepSeek 大模型。核心是一个从零手写的 ReAct Agent——包括 Planner 决策器、代码状态机、Tool 注册中心、SessionMemory 记忆管理。我特意没有直接用 LangChain，因为我先手写一轮理解 Agent 的底层机制——Reason → Act → Observe 的循环本质是什么，为什么 LLM 的决策不稳定，以及如何把状态机从 prompt 迁移到代码中。在验证手写版稳定后，我又做了一个 LangChain 版本作为对比——同样的输入能拿到同样的输出，证明我的理解和框架是一致的。

产品层面不只是分析工具，而是覆盖求职全流程——简历解析、JD 分析、人岗匹配后可以一键保存到投递看板，用看板视图管理求职进度，还支持对话记录持久化。工程层面有 JWT 鉴权、Redis 持久化加优雅降级、API 固定窗口限流、Docker 一键部署这些生产级能力。目前部署在 Docker 容器中，`docker compose up -d` 一键启动整个项目。」