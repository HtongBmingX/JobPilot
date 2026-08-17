# JobPilot v1.0 开发框架

> 从 v0.3.0（能跑的 Agent）到 v1.0（可上线、可演示、可面试）的完整路线图。
> 最后更新：2026-07-20

---

## 总体路线

```
Phase 1（体验层）──→ Phase 2（架构层）──→ Phase 3（数据层）──→ Phase 4（LangChain重构）──→ Phase 5（生产化）──→ Phase 6（进阶）
   4 steps              2 steps              3 steps               2 steps                   4 steps              秋招后
```

**设计原则**：每完成一个 Phase 都是一个**可演示的里程碑**，不是"做到一半"的状态。每个 Phase 内部的 steps 按依赖关系排序——前面没完成就不要开始后面的。

---

## Phase 1：体验层（让项目"好看"）

> **为什么先做体验层**：面试官/用户第一眼看到的是 UI 和交互。如果输出卡 30 秒、显示原始 Markdown、不能追问——再好的后端架构也展示不出来。这 4 步做完，项目就从一个"后端 API"变成了一个"完整产品"。

### Step 1.1 — SSE 流式输出

**做什么**：改造 LLM 调用链路，让 Agent 的每一步输出（Planner 思考 → Tool 执行 → Synthesize 生成）都通过 Server-Sent Events 实时推送到前端，前端逐字/逐段渲染。

**为什么做**：
- 当前 `POST /agent/run` 是阻塞调用，用户等 10-30 秒看到一片空白，体验极差
- 流式输出让用户「看到 Agent 在思考」，这是大模型应用的标配体验
- 技术上，SSE 比 WebSocket 更适合这个场景（单向推送、HTTP 协议兼容性好、FastAPI 原生支持）

**关键词学点**：在面试时你要能讲清楚：
- SSE 是单向（服务器→客户端）、text/event-stream、基于 HTTP 长连接；WebSocket 是全双工、ws://协议、适合双向实时通信，但这里不需要
- `StreamingResponse` + `asyncio` generator
- 前端用 `EventSource` 或 `fetch` + `ReadableStream` 消费事件流
- 为什么不用 WebSocket？
  - 技术：这里只需要服务器推送，不需要客户端随时向服务器发消息
  - 运维：SSE 走 HTTP，经过代理/负载均衡无额外配置；WS 需要特殊代理支持
- DeepSeek API 支持 `stream=True`，返回的 chunk 用 `response.iter_lines()` 消费

**涉及文件**：
- `backend/app/services/llm_service.py`：新增 `chat_stream()` 方法
- `backend/app/agent/jobpilot_agent.py`：`execute()` → ` execute_stream()`
- `backend/main.py`：`/agent/run/stream` 端点
- `frontend/src/App.vue`：消费 SSE 事件流

**前置依赖**：无（当前代码架构可以直接改造）

---

### Step 1.2 — Markdown 前端渲染

**做什么**：前端安装 `marked` 库，把后端返回的 Markdown 文本渲染为格式化 HTML，替代当前 `<pre>` 标签的原样展示。

**为什么做**：
- 后端 Synthesize 返回的是 Markdown 格式（含标题、列表、加粗等），前端用 `<pre>` 显示了原始标记
- 这个改进代码量极小（~10 行），效果极大，ROI 最高

**关键词学点**：
- XSS 风险：`v-html` 直接渲染 HTML 是危险的，`marked` 不防 XSS，需配合 `DOMPurify` 做清洗
- 或者：用 `marked.parse()` 输出纯 HTML，配合白名单过滤 `<script>`、`onclick` 等
- 为什么不后端渲染？保持前后端关注点分离——后端产出数据（Markdown 文本），前端负责呈现

**涉及文件**：
- `frontend/package.json`：加 `marked`
- `frontend/src/App.vue`：`<pre>` → `<div v-html>`
- 可选：`frontend/src/utils/markdown.js`：封装渲染逻辑 + 安全清洗

**前置依赖**：Step 1.1（流式输出后，渲染才有意义——否则渲染完再等 30 秒依然体验差）

---

### Step 1.3 — 多轮对话

**做什么**：扩展 `SessionMemory`，增加对话历史（messages 列表）。Agent 执行时把历史传给 Planner 和 Synthesize，让用户能追问、澄清、深入。

**为什么做**：
- 当前每次 `/agent/run` 是独立上下文，用户不能说「刚才那个匹配结果，再详细解释一下」——但求职对话天然就是多轮的
- 这是 Agent 和「一次性的 LLM 调用」的本质区别——Agent 有记忆

**关键词学点**：
- 对话历史的 token 管理：不能无脑把整个历史塞进 prompt，需要滑动窗口或 token 预算控制
- 两种记忆的区别：`SessionMemory`（业务数据：简历/JD/匹配结果）vs `ConversationHistory`（对话上下文：用户说了什么、Agent 回了什么）
- 为什么不是简单存 `[{role, content}]` 而是自己设计数据结构？业务记忆（简历分析结果）和对话记忆（聊天记录）要分开管理，前者是「事实」，后者是「上下文」

**核心设计决策 — Token 预算控制器（为什么需要一个独立的类？）**

为什么不在 Service 里简单 `messages[:-N]` 截断？

因为多轮对话场景下，截断策略直接影响回答质量。把策略抽成独立类有三个好处：
- **可测试**：可以用纯数据测 token 估算和截断逻辑，不依赖 LLM API
- **可替换**：策略（简单截断 vs 摘要压缩 vs 滑动窗口）可以按成本/效果切换
- **单一职责**：LLMService 管调用，TokenBudget 管配额，各管各的

同时这是面试时很好的技术纵深话题——你可以讲 token 预算分配的优先级：system prompt 先保证 → Planner 决策规则不能少 → 近期对话优先于远期 → 业务记忆（简历/JD）尽可能保留。

更进阶的做法是 **auto-summarize**：当历史太长时，先让模型总结前一段对话，用摘要替代原始消息。

**涉及文件**：
- `backend/app/memory/session_memory.py`：加 `messages: list[dict]`
- `backend/app/memory/token_budget.py`：新增 TokenBudget 类
- `backend/app/services/llm_service.py`：加 `count_tokens()` 方法（tiktoken 或字符估算）
- `backend/app/agent/jobpilot_agent.py`：execute 时传入对话历史
- `backend/app/prompts/templates/planner.md`：增加对话历史占位符
- `backend/app/prompts/templates/synthesize.md`：增加对话历史占位符

**前置依赖**：Step 1.1、1.2（多轮对话 + 流式 + 渲染一起才能形成完整的对话体验）

---

### Step 1.4 — 前端 UI 升级

**做什么**：拆分单文件 `App.vue` 为独立组件，增加对话气泡、思考过程展示、打字机效果、复制/导出按钮。

**为什么要拆组件**：
- 当前 `App.vue` 是一个 125 行的单文件，所有逻辑混在一起。这在原型阶段可以，但随着功能增加会变得不可维护
- 「组件拆分本身就是架构能力的体现」——面试官如果看你的前端代码，一个 500 行的 App.vue 和一套清晰的组件树，给人的印象完全不同

**组件树设计**：
```
App.vue
├── ChatPanel.vue          ← 对话气泡列表 + 滚动容器
│   ├── ChatBubble.vue     ← 单条对话（用户/Agent 不同样式）
│   └── ThinkChain.vue     ← Agent 思考过程（"正在分析简历…" → "正在匹配…"）
├── InputPanel.vue         ← 文件上传 + 问题输入 + JD 粘贴
│   ├── FileUploader.vue   ← 上传简历组件
│   └── JDEditor.vue       ← JD 文本编辑器
└── useAgent.js            ← Composable：封装 fetch 逻辑 + 流式消费 + 状态管理
```

**Composable 模式（为什么不用 Vuex/Pinia？）**：
- `useAgent.js` 是一个 Vue3 Composable——把 Agent 调用的状态（loading、error、messages、streamConsumer）封装成可复用的逻辑块
- 当前项目不需要全局状态管理。Pinia/Vuex 的引入时机是「多个组件需要共享同一份状态且不通过 props 传递」，例如用户登录信息、全局配置。现阶段用 composable + props 完全够
- 但面试时你要能说出：**等有了路由（多页面）或用户系统后，会用 Pinia 替代 composable 中的响应式变量**

**打字机效果**：消费 SSE 流时，收到一个 chunk 就追加到当前消息末尾 → `v-html` 实时重渲染 → 看起来像 AI 在打字。这不是炫技 —— 它解决了「用户不知道系统在干嘛」的等待焦虑。

**思考过程可视化**：Agent 每一步（resume → jd → match → synthesize）发一个事件给前端，前端显示「第 1 步：正在分析简历…」→「第 1 步：完成」→「第 2 步：正在分析 JD…」的进度链。这让面试官能看到 Agent 的工作过程，而不仅仅是最终结果。

**涉及文件**：
- `frontend/src/App.vue`：重构为组件编排器
- `frontend/src/components/ChatPanel.vue`
- `frontend/src/components/ChatBubble.vue`
- `frontend/src/components/ThinkChain.vue`
- `frontend/src/components/InputPanel.vue`
- `frontend/src/components/FileUploader.vue`
- `frontend/src/components/JDEditor.vue`
- `frontend/src/composables/useAgent.js`
- `frontend/src/utils/markdown.js`
- `frontend/index.html`：加 Google Fonts / CSS reset（可选）

**前置依赖**：Step 1.1、1.2、1.3

---

## Phase 2：架构层（让项目"稳固"）

> **为什么在体验层之后做架构层**：Phase 1 让你有东西可演示；Phase 2 让演示不出意外。Planner 状态机代码化是工程师和调包侠的分水岭——它证明你不是「调个 API 就完了」，而是真的理解了 Agent 的决策逻辑。

### Step 2.1 — Planner 状态机代码化

**做什么**：把 `planner.md` 中的「从上到下逐条判断」文本状态机，迁移为 Python 代码中的显式状态机（`enum` + 条件流转）。

**为什么做**：
- 这是 JobPilot 最核心的设计决策之一。当前 prompt 驱动的状态机有两个致命缺陷：
  1. LLM 可能不遵守（你已经遇到过 resume 循环卡死）
  2. 每次决策都花费额外的 token 让 LLM 「理解规则」，而这些规则是固定的代码逻辑，不需要 LLM 参与

**新架构**：
```
Planner.think()
  ├── Step 1: 代码状态机决定「当前允许哪些 action」
  │     if not memory.resume_analysis and has_resume(query):
  │         allowed = ["resume"]
  │     elif not memory.jd_analysis and has_jd(query):
  │         allowed = ["jd"]
  │     elif memory.resume_analysis and memory.jd_analysis and not memory.match_result:
  │         allowed = ["match"]
  │     else:
  │         allowed = ["finish"]
  │
  └── Step 2: LLM 从 allowed 中选一个，并提取 action_input
        prompt 不再包含「必须按顺序」的规则文本，只告诉 LLM「从以下合法动作中选一个」
```

这样 LLM 不需要理解状态机规则了，只需要做「语义匹配」：从 query 里提取对应字段。规则由代码保证，灵活部分交给 LLM——各司其职。

**关键词学点**：
- 这本质上是 **constrained generation** 的简化版——把 LLM 的输出空间从「所有可能的字符串」缩小到「有限的合法选项」
- LangChain/LangGraph 的 `conditional_edge` 做的是同一件事，只是封装得更优雅。你将来在 Phase 4 迁移时会发现，手写的状态机和 LangGraph 的 `StateGraph` 节点是一一对应的
- 代码状态机 vs prompt 约束的权衡：代码状态机更可靠但需要手动维护规则；prompt 约束更灵活但不可靠。这里选代码是因为求职流程固定（简历→JD→匹配→总结），规则不会频繁变化

**涉及文件**：
- `backend/app/agent/planner.py`：新增状态枚举 + 状态流转逻辑
- `backend/app/prompts/templates/planner.md`：删除状态机规则，精简为「从合法动作中选一个」
- `backend/app/agent/agent_state.py`：新增 AgentState 枚举
- `backend/tests/test_planner_state_machine.py`：新增状态机测试

**前置依赖**：Phase 1 全部完成

---

### Step 2.2 — 错误处理与优雅降级

**做什么**：建立统一的错误处理体系，包括：API 异常统一响应格式、LLM 调用失败的优雅降级策略、前端错误提示的 UI 规范。

**为什么做**：
- 当前错误处理分散在各处——`llm_service.py` 有重试但最终抛异常，`main.py` 没有全局异常处理器，前端只显示了 `e.message`
- 一个要上线演示的项目，至少需要：用户不会看到 500 的原始错误页面、LLM 挂了能有 fallback 提示

**涉及文件**：
- `backend/main.py`：加 `@app.exception_handler` 全局异常处理
- `backend/app/core/exceptions.py`：自定义异常类
- `frontend/src/composables/useAgent.js`：错误状态分类（网络错误 / 服务端错误 / 超时）

**前置依赖**：Step 2.1

---

## Phase 3：数据层（让项目"持久"）

> **为什么在架构层之后做数据层**：持久化引入的复杂度（连接池、序列化、数据迁移）在架构不稳时做会反复返工。Phase 2 把架构定下来后，再加持久层是「在稳定的结构上加一层存储」。

### Step 3.1 — Redis 集成

**做什么**：引入 Redis，替代内存 dict 做会话存储（`MemoryManager` 的后端），并加入限流功能。

**为什么用 Redis 而不是继续用内存**：
- 服务重启后会话不丢失（当前 dict 在重启后就空了）
- 为多进程部署做准备（uvicorn workers > 1 时，内存 dict 不能共享）
- 限流功能天然适合 Redis（`INCR` + `EXPIRE`）

**关键词学点**：
- `redis-py` + `async/await`（`aioredis` 或 `redis.asyncio`）
- 序列化方案：JSON 最简单但 dataclass 不能直接序列化 → 用 `asdict()` / `dataclasses.asdict`
- Redis 连接池管理：用单例或 FastAPI 的 `lifespan` 事件在应用启动时建池
- 限流算法：滑动窗口（用 `ZSET`）vs 固定窗口（`INCR` + `EXPIRE`），这里固定窗口就够

**涉及文件**：
- `backend/app/core/redis_client.py`：Redis 客户端单例
- `backend/app/memory/redis_store.py`：Redis 版本的 MemoryStore
- `backend/main.py`：lifespan 事件中初始化/关闭 Redis 连接
- `backend/requirements.txt`：加 `redis`
- `docker-compose.yml`：加 Redis 服务

**前置依赖**：Phase 2 全部完成

---

### Step 3.2 — 用户系统 + SQLite

**做什么**：引入用户概念，用 SQLite 存用户注册信息和历史会话记录。

**为什么先 SQLite 后 PostgreSQL**：
- SQLite 零配置、文件即数据库、适合开发/演示阶段
- 设计上保持 SQLAlchemy ORM 的抽象，后续切换到 PostgreSQL 只需改连接字符串
- 这是面试中的一个好话题：「我用了 Repository 模式，切换数据库只需要换一个 adapter」

**关键词学点**：
- Repository 模式：业务代码不直接操作 ORM，而是通过 `UserRepository` / `SessionRepository` 接口
- SQLAlchemy async vs sync：FastAPI 是 async 的，但 SQLAlchemy 1.4+ 才较好支持 async，可以用 `databases` 库或直接用同步 SQLAlchemy + `run_in_executor`
- 密码哈希：`passlib` + `bcrypt`，不存明文
- JWT token：`python-jose` 做无状态鉴权

**涉及文件**：
- `backend/app/models/user.py`：SQLAlchemy User 模型
- `backend/app/models/session.py`：SQLAlchemy Session 模型
- `backend/app/repositories/user_repo.py`
- `backend/app/repositories/session_repo.py`
- `backend/app/core/database.py`：SQLAlchemy 引擎 + session factory
- `backend/main.py`：注册/登录端点
- `backend/requirements.txt`：加 `sqlalchemy`、`passlib`、`python-jose`

**前置依赖**：Step 3.1

---

### Step 3.3 — 长期用户画像

**做什么**：跨会话积累用户画像——用户的技能栈、投递偏好、历史岗位，用于个性化分析和推荐。

**为什么做**：
- 这是从「单次工具」到「持续助手」的跨越——用户第一次使用时分析简历，后续追问时 Agent 已经「认识」他了
- 在技术层面，这是 RAG 的前置准备——画像数据就是后续检索的 query 来源

**涉及文件**：
- `backend/app/memory/user_profile.py`：用户画像数据类
- `backend/app/memory/profile_store.py`：画像存储（Redis 短期 + SQLite 长期）
- `backend/app/prompts/templates/system.md`：注入用户画像

**前置依赖**：Step 3.2

---

## Phase 4：LangChain / LangGraph 重构

> **为什么放在 Phase 4 而不是更早**：你已经在 roadmap 里写了「先手写 → 再 LangChain → 再 LangGraph」，这是项目的核心叙事。但重构应该在有明确的对比基础时做——先用完 Phase 1-3 把自己的 Agent 跑稳了，再去对比「哪些是框架替你做的、哪些框架也做不了」。

### Step 4.1 — LangChain 迁移

**做什么**：把手写的 ReAct 组件 1:1 映射到 LangChain 的对应模块。

**为什么做**：
- 工业界面试高频考点——问你是否用过 LangChain/LangGraph
- 有了手写版做对比，你能讲出「LangChain 替你做了什么」和「LangChain 的坑在哪」
- 不是重写功能，是**等价替换实现**——行为和 Phase 3 保持一致

**映射关系（你 roadmap 里已经画好了）**：

| 手写 | LangChain |
|------|-----------|
| `BaseTool` | `@tool` 装饰器 / `StructuredTool` |
| `LLMService.chat` | `ChatOpenAI`（DeepSeek base_url） |
| `Planner.think` 输出 `Plan` | `ChatOpenAI.with_structured_output(Plan)` |
| `execute()` 的 for 循环 | `AgentExecutor` 或 Chain 串接 |
| `SessionMemory` | `ConversationBufferMemory` 或自定义 memory |

**面试要点**：当面试官问「你为什么不用 LangChain 而要自己写」，正确回答是「我两个版本都有——我先手写理解了 Agent 的本质，然后用 LangChain 重构验证了我的理解和框架的一致性。手写帮我理解了 ReAct 循环、状态机、tool calling 的底层机制；LangChain 版本的优点是生态集成（配合 LangSmith 可观测性、checkpointer 持久化等）。我可以在面试中展示两个版本的代码对比。」

**涉及文件**：
- 整个 `backend/app/agent/` 的 LangChain 等价实现
- 新目录 `backend/app/langchain_agent/`
- 测试对比：同样的输入 → 同样的输出

**前置依赖**：Phase 3 全部完成（在持久层之上重构，保证数据兼容）

---

### Step 4.2 — LangGraph 引入

**做什么**：用 LangGraph 的 `StateGraph` 替代 LangChain 的线性 Chain，引入并行节点、conditional edge、human-in-the-loop。

**为什么做**：
- 这是 roadmap 中「手写 → LangChain → LangGraph」叙事的终章
- LangGraph 带来的新能力：
  1. resume 和 jd 分析可以**并行**（两者独立，省一半时间）
  2. `interrupt_before("match")` 让用户在匹配结果出来前确认
  3. `checkpointer` 替代你的 MemoryManager 做持久化

**关键词学点**：
- `StateGraph`：定义节点和边，每个节点修改 state
- `conditional_edge`：根据 state 内容决定下一个节点——这就是你手写状态机的框架化版本
- `checkpointer`：自动持久化 state，支持断点续跑和时间旅行

**涉及文件**：
- `backend/app/langgraph_agent/graph.py`：StateGraph 定义
- `backend/app/langgraph_agent/nodes.py`：各节点实现
- `backend/app/langgraph_agent/state.py`：AgentState TypedDict

**前置依赖**：Step 4.1

---

## Phase 5：生产化（让项目"可上线"）

> **这个 Phase 的目标**：让项目从「本地能跑」变成「部署到服务器别人能用」。

### Step 5.1 — 鉴权中间件

**做什么**：FastAPI 的 `Depends` 机制做 JWT 鉴权中间件，保护 `/agent/run` 等核心端点。

**为什么做**：任何对外暴露的 API 都需要鉴权。这是安全基线，不是高级功能。

### Step 5.2 — Docker 容器化

**做什么**：`Dockerfile` + `docker-compose.yml`，一键启动后端 + 前端 + Redis + 数据库。

**为什么做**：
- 部署时不需要「在我的电脑上能跑」的尴尬
- 面试时可以现场 `docker compose up` 演示

### Step 5.3 — 前端部署优化

**做什么**：Nginx 反向代理（前端静态文件 + API 代理到后端），替代开发时的 CORS 直接调用。

**为什么做**：CORS 是开发期的临时方案。生产环境前后端应该同域（通过 Nginx 或 API Gateway），否则暴露后端地址、无法做统一的限流和鉴权。

### Step 5.4 — API 限流

**做什么**：基于 Redis 的固定窗口限流，限制每个用户/IP 的每分钟请求次数。

**为什么做**：防止 LLM API 费用失控。DeepSeek 虽然便宜，但无限制调用仍然危险。

**前置依赖**：Phase 3 全部完成（Redis 已就绪）

---

## Phase 6：进阶（秋招后 / 长期）

> 这些方向是 roadmap 里列的高含金量技术，可以在秋招面试中「预告」，入职前或毕业后深入。

- **Hybrid Search + Reranker（RAG）**：BM25 + 向量检索 + RRF 融合 + cross-encoder 重排
- **评测体系自建**：faithfulness / answer relevancy / context recall 指标
- **LoRA 微调**：简历理解专用小模型
- **多 Agent 协作**：resume agent / search agent / decision agent 分工
- **MCP 协议接入**：让 JobPilot 可以调用外部工具（发邮件、查天气、日历）

---

## 附录 A：每个 Step 的标准交付格式

之后的每个 Step，我会按以下格式交付：

1. **Step 概览**（做什么、为什么、设计决策）
2. **修改文件清单与 diff**
3. **关键代码的解释**（不只是"这行代码是什么意思"，而是"为什么这样设计"）
4. **可验证的检查点**（运行某个命令、看到某个输出 = 这步做对了）
5. **面试中可以讲的关键点**（每步提炼 1-3 句可以放进简历/面试中的技术亮点）

---

## 附录 B：技术选型决策记录

| 决策 | 选择了 | 为什么不用替代方案 |
|------|--------|-------------------|
| 流式协议 | SSE | WebSocket 是双向的，这里只需要推送；SSE 走 HTTP 无代理兼容问题 |
| 前端状态管理 | Composable | 当前无多页面路由，Pinia 引入时机未到 |
| 数据库 | SQLite → PostgreSQL | 开发期 SQLite 零配置；Repository 模式保证后续切换成本低 |
| 缓存 | Redis | 比内存 dict 多持久化+共享；比 Memcached 多数据结构 |
| 框架重构 | 先手写 → LangChain → LangGraph | 渐进式：手写理解本质 → LangChain 获得生态 → LangGraph 获得编排能力 |
| 内存存储 | TokenBudget 类 | 比简单截断更灵活（可测、可换策略） |

---

> **下一步**：确认框架后，我们从 **Phase 1, Step 1.1（SSE 流式输出）** 开始。这是整个改造的第一步，也是最需要仔细设计的一步——它牵动整个调用链路（LLM → Agent → API → 前端）。
