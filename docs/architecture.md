# JobPilot 架构设计（v0.9.3）

> 最后更新：2026-08-17

## 整体架构

```
                        用户界面（Vue3 SPA）
                              │
                              │ fetch / SSE
                              ▼
                     FastAPI 入口（main.py）
                    ╔═══════════════════════╗
                    ║  CORS 中间件           ║
                    ║  JWT 鉴权              ║
                    ║  API 限流（Rate Limiter）║
                    ║  Error Handlers        ║
                    ╚═══════════════════════╝
                              │
          ┌───────────────────┼───────────────────┬────────────────┐
          ▼                   ▼                   ▼                ▼
   手写 ReAct Agent      LangChain Agent       文件摄入        业务 API
   (/agent/run)         (/agent/langchain)     (/upload)    (/applications
          │                   │                   │          /resumes
          │                   │                   │          /profile)
          │                   │                   ▼
          │                   │              IngestTool (PDF/DOCX)
          │                   │
          │           ┌───────┴────────┐
          │           │ create_react_agent│
          │           │ @tool × 3       │
          │           └────────────────┘
          │
  ┌───────┴───────┬─────────────┬──────────────┐
  ▼               ▼             ▼              ▼
 Planner      AgentStateMachine  │          SearchTool
 (LLM 语义判断) (代码确定性规则)  │          (RAG 检索)
  │               │             │              │
  └───────┬───────┘             │              ▼
          │ 决策：允许哪些 action │        RAG 管线
          ▼                      │        (Embedding + BM25 + RRF)
     ToolRegistry ──► Tool ──► Service ──► PromptManager ──► LLMService ──► DeepSeek
          │
          ▼ 结果写回
     SessionMemory（业务记忆 + 对话记忆 + 画像 + 摘要）
          │
          ├── TokenBudget（token 配额 + 摘要压缩）
          │
          ▼
     MemoryManager ──► Redis（会话，24h TTL）/ 内存 dict（fallback）

     SQLite（SQLAlchemy）
          ├── users（用户）
          ├── applications（投递记录）
          ├── resumes（简历库）
          └── user_profiles（用户画像，跨会话长期记忆）
```

---

## 核心设计决策

### 1. 双 Agent 架构（手写 + LangChain 并行）

| 层级 | 手写版 | LangChain 版 |
|------|--------|-------------|
| LLM 调用 | `LLMService.chat()` | `ChatOpenAI.invoke()` |
| 流式输出 | `LLMService.chat_stream()` | `ChatOpenAI.stream()` |
| Tool 定义 | `BaseTool` 抽象类 | `@tool` 装饰器 |
| 决策器 | `Planner.think()` | `create_react_agent()` 内置 |
| 状态管理 | `AgentStateMachine`（代码）| LangGraph conditional_edge |
| 记忆 | `SessionMemory` + `MemoryManager` | `InMemorySaver` (checkpointer) |

**为什么并存**：手写版验证对 Agent 本质的理解，LangChain 版验证理解和框架的一致性。面试时可当面对比两个版本的输出。

### 2. 状态机代码化（AgentStateMachine）

**旧（prompt 驱动）**：用自然语言描述「resume → jd → match → finish」规则，依赖 LLM 遵守。

**新（代码驱动）**：`compute_allowed_actions()` 确定性返回当前允许的合法 action：
- 单 Tool 请求 → 跳过 LLM 决策，直接执行（零延迟、零 token）
- 多 Tool 请求 → LLM 判断优先顺序
- 已完成的 Tool 不可重复执行（规则由代码保证）
- Planner 输出越界校验（LLM 返回非法 action 时降级兜底）

### 3. 三层记忆架构

| 层 | 存储 | 解决的问题 |
|----|------|-----------|
| 短期 | Redis 会话（24h TTL） | 记不住（跨请求上下文丢失） |
| 长期 | SQLite 用户画像 | 换会话就忘（跨会话身份记忆） |
| 压缩 | LLM 增量摘要 | 聊太久失忆（长对话早期内容丢失） |

### 4. RAG 混合检索

- **Embedding**：通义千问 text-embedding-v3，`text_type` 区分 query/document 非对称编码
- **检索**：向量相似度（纯 Python）+ BM25 关键词，RRF 基于排名融合
- **溯源**：来源标注由代码从检索结果提取、强制注入回答，不依赖 LLM 自觉
- **评测**：确定性指标（检索触发率/命中率/来源标注率），替代 LLM 打分的噪声

### 5. 优雅降级（Redis 双路径）

```
MemoryManager
  ├── Redis 可用 → RedisSessionStore（持久化 + TTL 自动过期）
  └── Redis 不可用 → 内存 dict（功能正常，重启丢数据）

Rate Limiter
  ├── Redis 可用 → 固定窗口限流（INCR + EXPIRE）
  └── Redis 不可用 → 放行所有请求（安全让位可用性）
```

---

## 数据流（一次完整的 RAG 问答请求）

```
1. 用户问「MySQL 索引为什么用 B+ 树」
2. FastAPI JWT 鉴权 + 限流检查
3. Agent 接收 → AgentStateMachine 检测知识库意图 → ["search"]
4. SearchTool.run(query) → RAG 管线
   - embedding 查询向量（text_type=query）
   - 向量检索 + BM25 检索 → RRF 融合 → top-5 文档
5. 来源标题代码强制提取 → 存入 memory.search_sources
6. Synthesize 基于检索结果生成回答
7. 代码在回答开头强制注入「📚 参考来源：...」
8. SSE 逐 token 推送 → 前端实时渲染
```

---

## 前端组件树

```
App.vue（编排层）
├── ConversationSidebar   ← 多会话管理 + 画像入口
├── 顶栏                   ← 视图切换 + Agent 版本选择
├── ChatBubble × N        ← 对话气泡（Markdown + 复制 + 保存看板）
├── ThinkChain            ← 思考链可视化
├── InputPanel            ← 简历/JD 双卡片 + 拖拽上传 + 简历库
├── JobBoard              ← 投递看板（四宫格 + 详情弹窗）
├── ProfileModal          ← 求职画像编辑
├── AboutView             ← 关于页面
├── StatusBar             ← Redis 状态
└── ToastContainer        ← 全局消息提示
```

Composables：useAgent（多会话/SSE）、useApplications、useResumes、useProfile、useStatus、useToast

---

## 下一阶段

- MCP 协议接入（Client：GitHub + 搜索）
- 云部署（公网 URL + HTTPS）
- 上线前安全加固（DOMPurify、JWT secret 硬化）
