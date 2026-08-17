# Changelog

---

## v0.9.3（前端整体改版 + 看板重构 + 功能收尾）

> 日期：2026-08-14

### ✨ 界面改版
- **全宽布局**：去掉 840px 居中限制，改为侧边栏 + 内容区 flex 布局
- **对话侧边栏**：新建对话、会话列表（按更新时间倒序）、删除、用户区（头像 + 用户名 + 退出）
- **多会话数据层**：localStorage 从单会话升级为 `conversations` 数组 + `activeId`，会话标题自动生成

### ✨ 看板重构
- **四宫格分区**：4 活跃状态 2×2 + 已拒底部弱化横条
- **卡片信息架构**：匹配分色阶（≥75 绿 / 50-74 琥珀 / <50 灰）+ 相对日期 + 备注徽标 + 两行摘要
- **详情编辑弹窗**：编辑/创建双模式，暴露全部字段，阶段 pill 按钮，两步删除确认
- **新建入口 + 空状态引导**

### ✨ 功能收尾
- **Toast 消息系统**：替换所有 alert/confirm，success/error/info 三种类型
- **停止生成**：AbortController + stopGenerating，生成中"发送"变红色"停止"
- **复制原文**：AI 消息 hover 显示复制按钮
- **输入框多行**：Enter 发送 / Shift+Enter 换行
- **XSS 强化**：svg/math/form/meta 等危险标签 + src/xlink:href javascript: 拦截

### 🗑️ 移除
- token/限流状态栏显示（流式不统计 token、/status 硬编码 0、nginx 未转发 XFF，投入产出比低）

### 🔧 修复
- 后端 update 的 None 语义陷阱：前端保存空字段用空字符串而非 null，避免"清空备注"失效

---

## v0.9.2（Bug 修复 + 代码审查 + 安全加固 + 文档整理）

> 日期：2026-08-09

### 🔴 严重 Bug 修复
- **agent_state.py** — `_query_mentions_jd` 空函数体：有 docstring 但没有函数体，永远返回 `None`，导致状态机从不识别 JD 相关请求
- **agent_state.py** — NameError：`wants_resume`/`wants_jd` 未定义，实际变量名为 `has_resume_in_query`/`has_jd_in_query`，运行时直接崩溃

### 🟡 重要修复
- **jobpilot_agent.py** — `_is_followup` 逻辑过激：只需任何分析存在即跳过 Planner，改为同时检查 query 是否含新分析意图
- **jobpilot_agent.py** — execute/execute_stream 会话保存不一致：在多条 return 路径上统一补上 save_session
- **main.py** — `refresh_token` 从 URL 查询参数改为 Body 传递（安全：防止代理/日志/浏览器历史泄露）
- **evaluation/relevancy.py** — 非确定性 hash：`hash()` 受 PYTHONHASHSEED 影响，改为 `hashlib.sha256`

### 🔵 小修复
- **frontend/useAgent.js** — 实现 token 自动刷新（401 时自动用 refresh_token 续期后重试）
- **frontend/InputPanel.vue** — `upload` 事件补充到 `defineEmits`
- **frontend/JobCard.vue** — 修复短文也显示省略号
- **frontend/useStatus.js** / **JobBoard.vue** — 移除未使用的 import
- **main.py** — 移除未使用的 `LLMServiceError` / `ValidationError` 导入
- **planner.py** — 更新过时注释（引用不存在的 `_all_done`）
- **prompt_manager.py** — 按 key 长度降序替换，防止短键破坏长键占位符
- **evaluation/runner.py** — 评分统计增加 `score is not None` 检查

### 📝 文档
- development_log.md 追加 Day 24 日志
- roadmap.md 同步进度并重组优先级表
- next_steps.md 修正 Phase 7/8 状态
- optimization_list.md 更新已完成项

---

## v0.9.1（自建评测体系 + Token 状态栏 + 投递看板联动 + 记忆系统分析）

> 日期：2026-07-31

### 新增

#### 自建评测体系
- 新建 `backend/app/evaluation/` 目录：Faithfulness / AnswerRelevancy / ContextRecall 三个指标实现
- 5 条评测用例（简历分析、人岗匹配、追问、聊天、边缘场景）
- 评测执行器 + Markdown 报告自动生成

#### 投递看板联动
- ChatBubble 新增"📌 保存到投递看板"按钮——Agent 分析结束后一键保存，自动提取公司/岗位/匹配分数
- 提取失败时弹出手动输入框兜底

#### 工程面板
- 底部 StatusBar：Redis 连接指示灯 + Token 消耗进度条 + 限流计数 + Agent 版本切换
- `/status` 端点（公开接口，不鉴权）
- 5 秒定时轮询

### 设计决策

#### ADR-013: Token 计数共享架构
**问题**：状态栏 Token 数字始终为 0。
**根因**：`agent.llm` 和 Tool 内部 Service 的 LLMService 是**不同实例**。每个 Service `__init__` 里 `new` 了独立的 LLMService，Tool 调用 LLM 时计数器加到独立实例上，`agent.llm` 的计数器永远是 0。
**修复**：`BaseService.__init__` 支持注入外部 `llm` 实例 → `main.py` 启动后将 `agent.llm` 注入所有 Tool 的 Service 层。
**教训**：当系统中存在多个 LLMService 实例时，任何需要全局统计的功能（Token 消耗、API 调用次数）都必须在单例上维护——要么用模块级单例，要么显式注入共享实例。

### 踩坑记录

#### 坑 6: evaluation 目录缺少 `__init__.py` 导致 502
**现象**：后端容器启动后所有请求返回 502 Bad Gateway。
**原因**：新建 `evaluation/` 和 `evaluation/metrics/` 目录时没建 `__init__.py`，Python 未将其视为合法包，`import` 链断在 `runner.py` 的 `from backend.app.evaluation.metrics.faithfulness import FaithfulnessMetric` 这一行。
**解决**：补上两个 `__init__.py`。
**教训**：Python 包目录必须包含 `__init__.py`（即使内容为空）。Docker 容器内首次 import 时失败会阻止整个应用启动。

#### 坑 7: `interview_tool.py` 语法错误导致 502
**现象**：修复 `__init__.py` 后仍然 502。
**原因**：编辑时误删了 `return self.service.interview(...)` 语句，留下孤立的 `)`。
**教训**：Edit 工具替换多行文本时容易漏掉部分代码行。

---

## v0.9.0（灵活对话引擎 + 面试模拟 — Agent 能力扩展）

> 日期：2026-07-29

### 新增

#### 灵活对话引擎（Phase 2.1）
- `AgentStateMachine` 新增 `chat` 状态：当用户 query 不涉及任何工具调用时，直接路由到 ChatNode
- 新增 `_chat()` / `_chat_stream()` 方法（`jobpilot_agent.py`)：基于已有业务记忆做自然对话，不调工具
- 新建 `backend/app/prompts/templates/chat.md`：自由对话 prompt 模板
- 状态机路由逻辑更新：interview > chat/finish > tool actions，优先级明确

#### 面试模拟（Phase 2.2）
- 新建 `backend/app/services/interview_service.py`：面试服务层
- 新建 `backend/app/tools/interview_tool.py`：InterviewTool（支持 technical / behavioral / mixed 三种模式）
- 更新 `backend/app/prompts/templates/interview.md`（之前为空模板），完整面试 prompt——包含简历分析、JD 分析、模式、轮次、指令五大变量
- `AgentStateMachine` 新增 `_query_mentions_interview()` 检测函数 + interview 路由规则
- `main.py` 注册 InterviewTool 到 ToolRegistry
- `planner.md` 更新动作列表，加上 interview
- `jobpilot_agent.py` 同步/流式两个执行路径均支持 interview action
- 补充 `langchain-openai>=0.2` 依赖

### 设计决策

#### ADR-012: 面试模拟的交互设计
**决策**：InterviewTool 只生成第一轮的"暖场问题"，后续多轮由用户自由追问，AgentStateMachine 根据关键词判断是否维持面试模式。
**理由**：Agent 当前是单轮 Tool 调用模式——每次用户发消息，Agent 重新判断应该走哪个 Tool。如果 InterviewTool 一次性生成 6 轮问答，用户体验类似于"看一份面试题清单"而非"和面试官对话"。只生成第一轮、后续让用户自由追问，保持了对话感。
**未来改进**：可以给 SessionMemory 加一个 `interview_round` 计数器，AgentStateMachine 检测到"当前仍在面试中"时自动维持 interview 模式，让体验更连贯。

### 踩坑记录

#### 坑 5: LangChain 端点报 `No module named 'langchain_openai'`
**现象**：切换到 LangChain Agent 模式后，发送消息报 `ModuleNotFoundError: No module named 'langchain_openai'`。
**原因**：`langchain_agent/llm.py` 从 `langchain_openai` 导入 `ChatOpenAI`——这是 langchain 的独立子包，但 `requirements.txt` 里只声明了 `langchain` 和 `langchain-core`，没有 `langchain-openai`。本地 `.venv` 里碰巧装了（作为 `langchain` 的传递依赖），Docker 构建时纯净环境中没有。
**解决**：在 `requirements.txt` 中补充 `langchain-openai>=0.2`。教训：所有直接 import 的包必须在 requirements.txt 里显式声明，不能依赖传递安装。

---

## v0.8.0（鉴权系统 + 投递看板 + 工程面板 — 产品化完成）