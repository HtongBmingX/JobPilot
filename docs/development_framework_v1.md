# JobPilot v1.0 个性化开发框架

> 为 HP 定制的 v0.6.0 → v1.0 演进路线
> 模式：稳步模式（1-2 个月）｜ 重点：LangGraph 重构 + MCP 接入 + RAG 管线 + 功能丰富 ｜ 岗位：AI 应用开发
> 更新：2026-07-23

---

## 当前状态速览

```
已完成（v0.6.0）              待建设（v1.0）
─────────────────────────    ─────────────────────────
✅ 手写 ReAct Agent           ⬜ LangGraph StateGraph 重构
✅ 代码状态机                  ⬜ 自建评测体系
✅ SSE 流式输出                ⬜ MCP 协议接入（Server + Client）
✅ Redis 持久化 + 优雅降级     ⬜ RAG Hybrid Search + Reranker
✅ LangChain 双版本对比        ⬜ Docker 全项目容器化 + 云部署
✅ 文件摄入（PDF/DOCX）        ⬜ 鉴权系统（JWT）+ 投递看板
✅ 前端组件化 + ThinkChain     ⬜ 面试模拟 + 灵活对话场景
✅ API 限流 + 异常体系         ⬜ 工程能力可视化面板
                              ⬜ Human-in-the-Loop
```

---

## 总体路线

```
Phase 1               Phase 2                  Phase 3            Phase 4           Phase 5            Phase 6
生产化 + 产品化   →   Agent 能力扩展        →   自建评测体系  →   MCP 协议接入  →   RAG 检索管线  →   面试打磨
                    + LangGraph 重构
1.5 周                2-3 周                    1 周               1-2 周            1-2 周             1 周
────────────────────────────────────────────────────────────────────────────────────────────────────────
                    总计 7-10 周，每个 Phase 都是可演示的里程碑
```

**设计原则**：
- 技术深度（LangGraph → MCP → RAG）和产品完整度（投递看板 → 面试模拟 → 工程面板）**双线并行**
- 每一层都建立在前一层之上，让面试叙事形成递进逻辑
- Phase 1 先把"单次分析工具"升级为"求职管理中心"，让产品形态完整
- Phase 2 在完整的产品形态上叠加 Agent 架构深度

---

## Phase 1：生产化 + 产品化（1.5 周）

**目标：项目上线可访问 + 从"单次分析工具"升级为"求职管理中心"。**

> Phase 1 分两条线——部署线（1.1、1.2）和产品线（1.3、1.4、1.5）。两条线不冲突，可以并行走。

---

### Step 1.1 — Docker 全项目容器化（2 天）

**做什么**：
- 为后端写 Dockerfile（多阶段构建：第一阶段装依赖，第二阶段只复制 .venv + 源码，精简镜像体积）
- 为前端写 Dockerfile（第一阶段 `npm run build`，第二阶段用 nginx:alpine 托管 dist/）
- 完善 docker-compose.yml：后端（端口 8000）+ 前端（端口 5173）+ Redis（已就位）
- nginx 配置：前端静态文件 + `/api` 反向代理到后端，解决生产环境 CORS 问题

**为什么**：`docker compose up` 一键启动，消除"在我电脑上能跑"的尴尬。

**面试要点**：
- 多阶段构建减小镜像体积：构建阶段装 dev 依赖和编译器，运行阶段只留运行时依赖
- Nginx 反向代理：前端 `/` 走静态文件，`/api/*` → 后端 8000，统一域名避免 CORS
- `.env` 通过 docker-compose 的 `env_file` 注入，`.env` 不入 git

**涉及文件**：
- `backend/Dockerfile`（新建）
- `frontend/Dockerfile`（新建）
- `frontend/nginx.conf`（新建）
- `docker-compose.yml`（修改，加后端和前端服务）
- `.dockerignore`（新建）

**可检查点**：`docker compose up` → 浏览器 `http://localhost` 全功能可用

---

### Step 1.2 — 云部署（1 天）

**做什么**：
- 选云服务器（阿里云 ECS / 腾讯云轻量，学生价 ~100 元/年，2C2G 够用）
- 装 Docker + Docker Compose，clone 项目
- `docker compose up -d` 后台启动
- 配置安全组：开放 80/443 端口
- 绑定域名（可选，有域名更专业）

**面试要点**：
- 安全组配置：只开放 80/443，22 端口限制 IP 或用跳板机
- 为什么要 Docker 部署而不是直接 pip install：环境一致性、一键回滚、不污染宿主机

---

### Step 1.3 — JWT 鉴权 + 用户系统（2 天）

**做什么**：
- 用 `passlib` + `bcrypt` 做密码哈希，`python-jose` 做 JWT 签发和验证
- 注册端点 `POST /auth/register`：username + password → 存 SQLite
- 登录端点 `POST /auth/login`：验证密码 → 返回 access_token
- FastAPI Depends 中间件：`get_current_user()` 解析 JWT，注入到受保护端点
- Token 刷新端点 `POST /auth/refresh`

**为什么**：
- 任何对外暴露的 API 都需要鉴权，这是安全基线
- JWT 是无状态鉴权，适合 API 服务（不需要服务端存 session）
- SQLite 零配置，符合"演示期零运维成本"原则
- **用户系统是投递看板的前置依赖**——每个用户的投递记录需要关联到具体用户

**设计决策**：
- 用 SQLite 而非继续用 Redis 存用户信息：用户是持久数据，不应有过期时间；Redis 的 TTL 适合 session 缓存，不适合用户表
- SQLAlchemy ORM + Repository 模式，后续切 PostgreSQL 只改连接字符串
- JWT 过期时间：access_token 30 分钟，refresh_token 7 天

**面试要点**：
- 为什么不存明文密码：bcrypt 加盐哈希，彩虹表攻击无效
- 为什么 JWT 而不是 session cookie：前后端分离，JWT 不需要服务端存状态
- 为什么加了 Refresh Token：access_token 短时效降低泄露风险，refresh_token 长时效减少用户登录次数

**涉及文件**：
- `backend/app/models/user.py`（新建）
- `backend/app/repositories/user_repo.py`（新建）
- `backend/app/core/auth.py`（新建，JWT 签发/验证 + Depends）
- `backend/app/core/database.py`（新建，SQLAlchemy 引擎）
- `backend/main.py`（修改，加 auth 路由 + 保护端点）
- `backend/requirements.txt`（加 sqlalchemy, passlib[bcrypt], python-jose）

**可检查点**：`POST /auth/register` → `POST /auth/login` 拿到 token → 带 token 调 `/agent/run` 成功，不带 token 返回 401

---

### Step 1.4 — 投递看板（1 天）

**做什么**：给项目加一个轻量级的"求职管理中心"——用户每次完成人岗匹配后，可以一键保存到投递记录，前端用看板视图展示。

**为什么**：
- 当前项目是"用完即走"的单次分析工具。加上投递看板后，它变成"持续使用"的求职管理中心——产品的完整度完全不同
- 技术上不复杂（SQLite 一张表 + 两个 API + 前端一个卡片组件），但产品层面的提升巨大
- 面试时你可以说："用户不只是一次性分析简历和 JD，分析完成后可以保存为投递记录，跟踪每个岗位的进度。"

**后端设计**：

```python
# backend/app/models/application.py
class Application(Base):
    __tablename__ = "applications"
    id: int                    # 主键
    user_id: int               # 外键 → users 表
    company: str               # 公司名
    position: str              # 岗位名
    jd_text: str               # JD 原文（可选，用于后续回顾）
    match_score: str            # 匹配度评分（从 match_result 中提取）
    match_summary: str          # 匹配摘要（LLM 给出的关键建议）
    status: str                 # 当前状态：已投递 / 初筛中 / 面试中 / 已拒 / 已Offer
    applied_at: datetime        # 投递日期
    notes: str                  # 用户备注
    created_at: datetime
    updated_at: datetime
```

**API 端点**：
- `POST /applications` → 创建投递记录（用户完成匹配分析后，点击"加入投递记录"）
- `GET /applications` → 获取当前用户的所有投递记录（支持按状态筛选）
- `PUT /applications/{id}` → 更新状态或备注
- `DELETE /applications/{id}` → 删除记录

**前端设计**——看板视图（Trello 风格）：

```
┌──────────────────────────────────────────────────────────────┐
│  投递看板                                          [+ 新建]   │
├─────────────┬─────────────┬─────────────┬───────────────────┤
│ 📋 已投递    │ 🔍 初筛中    │ 💬 面试中    │ ✅ 已Offer / ❌ 已拒 │
│             │             │             │                   │
│ ┌─────────┐ │ ┌─────────┐ │ ┌─────────┐ │ ┌───────────────┐ │
│ │ 字节跳动  │ │ │ 阿里巴巴  │ │ │ 腾讯     │ │ │ 美团         │ │
│ │ 后端开发  │ │ │ 算法工程师│ │ │ 前端开发  │ │ │ 后端开发      │ │
│ │ 匹配度85% │ │ │ 匹配度72% │ │ │ 匹配度80% │ │ │ 匹配度91%     │ │
│ │ 07-20投递│ │ │ 07-18投递│ │ │ 07-15投递│ │ │ 07-10投递     │ │
│ │ [详情]   │ │ │ [详情]   │ │ │ [详情]   │ │ │ [详情]        │ │
│ └─────────┘ │ └─────────┘ │ └─────────┘ │ └───────────────┘ │
│             │             │             │                   │
│ ┌─────────┐ │             │             │                   │
│ │ 拼多多    │ │             │             │                   │
│ │ 数据分析  │ │             │             │                   │
│ │ 匹配度68% │ │             │             │                   │
│ └─────────┘ │             │             │                   │
└─────────────┴─────────────┴─────────────┴───────────────────┘
```

每个卡片可以拖拽切换状态（前端用 HTML5 Drag & Drop 或简单下拉选择），点击展开详情面板（JD 摘要、匹配分析、备注、时间线）。

**面试要点**：
- "投递看板的设计思路是'分析即记录'——用户做完人岗匹配后，一键保存为投递记录，不需要切换到另一个页面手动填写。这减少了用户的操作路径。"
- "看板的拖拽状态切换（已投递 → 面试中 → 已Offer）让用户可以直观地管理求职进度。技术上用 SQLite 存储，Repository 模式保证后续可以切到 PostgreSQL。"

**涉及文件**：
- `backend/app/models/application.py`（新建，SQLAlchemy 模型）
- `backend/app/repositories/application_repo.py`（新建）
- `backend/app/schemas/application.py`（新建，Pydantic 请求/响应模型）
- `backend/main.py`（修改，加 application 路由）
- `frontend/src/components/JobBoard.vue`（新建，看板视图）
- `frontend/src/components/JobCard.vue`（新建，单个卡片）
- `frontend/src/composables/useApplications.js`（新建，API 调用封装）

---

### Step 1.5 — 工程能力可视化面板（1 天）

**做什么**：把后端已有的工程化能力用前端组件展示出来，让面试官和用户能看到——而不只是"你知道它存在"。

**当前状况**：你做了 TokenBudget、Redis 双路径、Agent 版本切换、限流状态——但全部都在后端，前端完全不可见。面试官打开页面看不到任何工程能力的痕迹。

**新增前端组件**：

**1. 状态栏（StatusBar.vue）**——固定在页面底部的横条：

```
🔴 Redis 持久化    📊 本轮 Token: 1,247 / 4,096    ⚡ Agent: 手写 ReAct 版 [切换]    🛡 限流: 17/20
```

每个状态项都是实时刷新（SSE 或定时轮询 `/status` 端点）：
- Redis 连接状态：绿色圆点 + "Redis 持久化" / 橙色圆点 + "内存模式（Redis 不可用）"
- Token 消耗：本轮已用 / 预算上限，进度条颜色变化（绿→黄→红）
- Agent 版本切换按钮：手写 ReAct / LangChain / LangGraph（Phase 2 加第三个选项）
- 限流状态：当前窗口内已用次数 / 上限

**2. Agent 版本对比面板**（可选，2-3 小时额外工作量）：
在聊天区域的右上角加一个小按钮，点击后弹出一个对比面板，同时展示手写版和 LangChain 版的输出。这是面试演示时最能体现"双版本对比"设计思路的功能。

**后端新增**：`GET /status` 端点，返回当前系统状态快照。

```python
@router.get("/status")
async def get_status(current_user = Depends(get_current_user)):
    return {
        "redis_connected": redis_client.get_client() is not None,
        "token_usage": {"used": 1247, "budget": 4096},  # 从当前 session 读取
        "agent_mode": "react",  # 当前选中的 Agent 版本
        "rate_limit_remaining": 17,  # 当前窗口剩余次数
    }
```

**面试要点**：
- "我在前端加了一个状态栏，实时展示 Redis 连接状态、Token 消耗、Agent 版本和限流情况。这不是刷 UI——它让后端所有的工程化设计变得可感知。面试官打开页面就能看到'Redis 持久化'的绿色指示灯，而不需要我口头解释。"
- "Token 消耗的进度条用的是 TokenBudget 类的实际数据——颜色会从绿变黄变红，让用户直观感受到对话还有多少容量。"

**涉及文件**：
- `backend/app/schemas/status.py`（新建）
- `backend/main.py`（修改，加 `/status` 端点）
- `frontend/src/components/StatusBar.vue`（新建）
- `frontend/src/components/AgentComparePanel.vue`（新建，可选）
- `frontend/src/composables/useStatus.js`（新建，定时轮询 status）
- `frontend/src/App.vue`（修改，引入 StatusBar）

---

## Phase 2：Agent 能力扩展 + LangGraph 深度重构（2-3 周）

**目标：业务层面——新增面试模拟场景，让 Agent 从"分析工具"变为"求职全流程助手"；架构层面——完成"手写 ReAct → LangChain AgentExecutor → LangGraph StateGraph"三层递进叙事。**

> Phase 2 分两条线：业务扩展线（2.1、2.2）和架构重构线（2.3、2.4、2.5）。业务线在现有手写 Agent 上就能做，不需要等 LangGraph。两条线可以在大约同一时间段内推进——业务线先出成果（第 1 周），架构线跟进（第 2-3 周）。

---

### Step 2.1 — 灵活对话引擎（2 天）

**做什么**：让 Agent 在没有工具需要调用时也能进行有价值的自然对话——不只是一个"分析机器"。

**当前问题**：AgentStateMachine 的逻辑是"resume → jd → match → finish"，一切路径都导向工具调用。用户问"自我介绍应该怎么写"或"你觉得我还缺什么技能"时，Agent 的状态机不知道怎么处理——这种问题不匹配任何工具，但用户期望得到有用的回答。

**改造方案**：

1. **AgentStateMachine 加一个"chat"状态**：当 query 不涉及简历/JD/匹配的 tool 调用，但用户在进行自然对话时，router 返回 `next_action = "chat"`。

2. **新增 ChatNode**（轻量 LLM 调用）：基于对话历史 + 已有的业务记忆（resume_analysis、jd_analysis、match_result），直接生成自然语言回答。它不调工具，只是基于已有信息做自由对话。

```
         ┌──────────┐
         │  router   │
         └────┬─────┘
              │
     ┌────────┼────────┬────────┐
     ▼        ▼        ▼        ▼
  resume    jd      match     chat ← 新增：灵活对话节点
     │        │        │        │
     └────────┴────────┴────────┘
              │
              ▼
         synthesize / finish
```

**ChatNode 的设计要点**：
- 它的 prompt 告诉 LLM："你是一个资深求职顾问。用户已经进行了简历分析、JD 分析和人岗匹配（如果有的话）。现在用户想和你聊聊。请基于已有的分析结果，自然地回答问题。"
- 如果用户问"我还缺什么技能"，LLM 能基于 match_result 中的技能差距部分来回答
- 如果用户问"自我介绍怎么写"，LLM 能基于 resume_analysis 中的亮点来回答
- 如果用户问一个超出求职范围的问题（比如"今天天气怎么样"），LLM 能礼貌地引导回求职话题

**涉及文件**：
- `backend/app/agent/agent_state.py`（修改，加 "chat" 动作判断逻辑）
- `backend/app/prompts/templates/chat.md`（新建，灵活对话 prompt）
- `backend/app/agent/jobpilot_agent.py`（修改，加 ChatNode 执行逻辑）

**面试要点**：
- "AgentStateMachine 的逻辑从'一切导向工具调用'升级为'按需分流'——明确的工具请求走 tool 节点，自然对话走 chat 节点。这让 Agent 从'分析工具'变成了真正的'对话助手'。"
- "ChatNode 的核心是**基于已有记忆做推断**——它不调工具不产生新分析，但它能从简历分析、JD 分析、匹配结果的记忆中提取相关信息来回答用户的自由问题。这是 memory 在 Agent 中的核心价值：不只是存储，而是支撑推理。"

---

### Step 2.2 — 面试模拟场景（1 天）

**做什么**：新增 InterviewTool + interview.md prompt，让 Agent 可以扮演面试官进行模拟面试。

**为什么**：
- 这是最直观的"产品功能升级"——从"两份文档的分析器"变成"求职全流程助手"
- 面试模拟是求职场景中最刚需的功能之一——用户上传简历和 JD 后，最自然的下一步就是"那我该怎么准备面试"
- 技术上很简单：一个新 Tool + 一个 prompt + 状态机加一个状态。但产品感知极强

**设计**：

```python
class InterviewTool(BaseTool):
    name = "mock_interview"
    description = "针对用户简历和目标岗位进行模拟面试，扮演面试官提问"
    parameters = ["mode"]  # "technical" | "behavioral" | "mixed"

    async def run(self, mode: str = "mixed") -> str:
        # 调用 LLM，基于 resume_analysis + jd_analysis 生成面试问题
        pass
```

**InterviewTool 的三种模式**：
- **技术面（technical）**：基于简历中的技术栈和 JD 中的技术要求，提问算法、系统设计、语言底层原理等问题
- **行为面（behavioral）**：基于简历中的项目经验，提问"你遇到过最大的技术挑战是什么""如何处理团队冲突"等
- **综合面（mixed）**：混合技术和行为问题

**交互流设计**：
```
用户: "帮我模拟面试，技术方向"
Agent: [调用 interview_tool(technical)]
       "好的，我扮演面试官。基于你的简历和后端开发岗位，第一个问题：
        请描述你在xx项目中使用Redis的场景，为什么选择Redis而不是其他缓存方案？"
用户: "我们当时需要...（回答）"
Agent: "不错的回答。追问：如果Redis挂了，你们的降级方案是什么？"
用户: "我们用了...（回答）"
Agent: [多轮问答后]
       "面试模拟结束。以下是你的表现评价：
        - 技术深度：⭐⭐⭐  (举例提到了缓存穿透但没有展开)
        - 表达清晰度：⭐⭐⭐⭐
        - 改进建议：Redis分布式锁的实现细节可以准备得更充分..."
```

**涉及文件**：
- `backend/app/tools/interview_tool.py`（新建）
- `backend/app/services/interview_service.py`（新建）
- `backend/app/prompts/templates/interview.md`（修改，当前是空模板）
- `backend/app/agent/agent_state.py`（修改，加 "interview" 状态判断）
- `backend/app/agent/jobpilot_agent.py`（修改，注册 InterviewTool）

**面试要点**：
- "面试模拟的设计核心是**基于真实数据生成个性化问题**——不是随机题库，而是针对简历中的具体项目经历和目标 JD 的技术要求来生成。比如用户的简历提到了 Redis 缓存，JD 要求分布式系统经验，面试官就会追问 Redis 分布式锁和降级策略。"
- "这个功能的技术实现不复杂——一个新 Tool + 一个 prompt 模板。但它让项目从一个'分析工具'变成了'求职全流程助手'，产品形态上有了明显的层次。"

---

### Step 2.3 — StateGraph 基础架构（3 天）

**做什么**：用 LangGraph 的 `StateGraph` 重新组织 Agent 执行流。这是"手写 → LangChain → LangGraph"递进叙事的关键一步。

**背景**：当前 `langchain_agent/agent.py` 用的是 LangGraph 预构建的 `create_react_agent`，不是真正的 LangGraph 重构——没有自定义节点、没有并行能力、流式是变通实现。

**State 设计**：

```python
from typing import TypedDict, Annotated
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    # 输入
    query: str
    resume: str
    jd: str
    session_id: str

    # 对话历史（add_messages 自动合并新消息）
    messages: Annotated[list, add_messages]

    # 业务记忆（各节点执行后写入）
    resume_analysis: str
    jd_analysis: str
    match_result: str

    # 控制流
    next_action: str  # "resume" | "jd" | "match" | "chat" | "interview" | "synthesize" | "finish"
    step_count: int

    # 最终输出
    final_response: str
```

**节点设计**：

```
         ┌──────────┐
         │  router   │ ← 代码状态机（等价于 AgentStateMachine）
         └────┬─────┘
              │ conditional_edge: next_action
     ┌────────┼────────┬────────┬──────────┐
     ▼        ▼        ▼        ▼          ▼
  resume    jd      match    chat    interview   synthesize
     │        │        │        │        │          │
     └────────┴────────┴────────┴────────┘          │
              │                                      │
              ▼                                      │
           router ←─────────────────────────────────┘
              │
              ▼
           finish
```

**关键设计**：
- router 节点 = AgentStateMachine 的 LangGraph 版本——确定性代码逻辑，不是 LLM 决策。检查 state 中的业务记忆 + query 关键词，返回下一个 action
- resume 和 jd 节点可以**并行执行**——当用户同时上传了简历和 JD 时，`StateGraph` 的并行边让两者同时调用 LLM，省一半时间
- chat 节点是新增——在没有 tool 需求时，直接基于已有记忆做自然对话
- synthesize 节点只做一件事：基于 state 中已有结果生成最终回答

**面试要点**：
- "我从 `create_react_agent` 升级到了自定义 `StateGraph`。前者是一个黑盒——你无法控制内部的执行流；后者让我显式定义了每个节点和条件分支。router 节点就是我的 AgentStateMachine 在 LangGraph 中的映射。"
- "resume 和 jd 分析是完全独立的，StateGraph 支持并行节点——这让 Agent 的执行时间从串行的 ~30 秒降到并行的 ~15 秒。"

**涉及文件**：
- `backend/app/langgraph_agent/state.py`（新建，AgentState TypedDict）
- `backend/app/langgraph_agent/nodes.py`（新建，router / resume / jd / match / chat / interview / synthesize 节点函数）
- `backend/app/langgraph_agent/graph.py`（新建，StateGraph 构建 + 编译）
- `backend/app/langgraph_agent/agent.py`（修改，替换 create_react_agent）
- `backend/main.py`（修改，更新 LangChain 端点指向新 StateGraph）

**可检查点**：同样的输入 → 手写版输出 == LangGraph 版输出（通过评测体系验证）

---

### Step 2.4 — Native 流式输出 + checkpointer（2 天）

**做什么**：
- 用 `graph.astream_events()` 替代当前的"先 sync invoke 再 stream synthesize"变通方案
- 用 `SqliteSaver` 替代 `InMemorySaver`，实现断点续跑

**流式方案设计**：

```python
async for event in graph.astream_events(input, config, version="v2"):
    kind = event["event"]
    if kind == "on_chat_model_stream":
        # LLM 输出的 token 级流
        chunk = event["data"]["chunk"].content
        yield f"data: {json.dumps({'type': 'token', 'content': chunk})}\n\n"
    elif kind == "on_tool_start":
        yield f"data: {json.dumps({'type': 'step_start', 'step': event['name']})}\n\n"
    elif kind == "on_tool_end":
        yield f"data: {json.dumps({'type': 'step_done', 'step': event['name']})}\n\n"
```

**checkpointer**：
- `SqliteSaver.from_conn_string("checkpoints.db")` → 会话状态自动持久化到 SQLite
- 支持断点续跑：用户刷新页面后，session_id 相同的请求从上次中断处继续
- 支持时间旅行：可以回溯到任何一个 checkpoint 查看当时的 state

**面试要点**：
- "LangGraph 的 astream_events 让我拿到了比手写 SSE 更细粒度的事件——不仅知道哪个 step 开始了，还能拿到 LLM 逐 token 的输出和 Tool 的中间结果。"
- "checkpointer 是 LangGraph 对 MemoryManager 的对应物。它自动做 state 增量持久化，支持断点续跑和时间旅行。我用 SqliteSaver 替换了 InMemorySaver，解决了服务重启丢会话的问题。"

**涉及文件**：
- `backend/app/langgraph_agent/agent.py`（修改，替换 astream_events）
- `backend/app/langgraph_agent/graph.py`（修改，接入 SqliteSaver）

---

### Step 2.5 — Human-in-the-Loop（1-2 天）

**做什么**：在 match 节点之前插入人工确认点。

```python
graph = StateGraph(AgentState)
# ... 添加节点 ...
graph.add_edge("jd", "human_approval")
graph.add_edge("human_approval", "match")

# 编译时标记中断点
app = graph.compile(checkpointer=checkpointer, interrupt_before=["match"])
```

当前端调用 `run_stream` 到达 match 节点前，StateGraph 会暂停并返回当前 state。前端展示"准备进行人岗匹配，是否继续？"确认按钮。用户点击确认后，用 `Command(resume=...)` 恢复执行。

**面试要点**：
- "Human-in-the-Loop 是 AI 安全的核心实践。关键决策——比如是否基于当前分析结果继续匹配——需要用户确认。这在发送邮件、提交申请等场景更关键。"
- "LangGraph 的 `interrupt_before` 让这件事的实现从'自己写状态保存 + 等待 + 恢复'的复杂逻辑变成了一个参数配置。"

**涉及文件**：
- `backend/app/langgraph_agent/graph.py`（修改，加 interrupt_before）
- `frontend/src/composables/useAgent.js`（修改，处理 pause 事件 + 恢复请求）
- `frontend/src/components/ThinkChain.vue`（修改，渲染确认按钮）

---

## Phase 3：自建评测体系（1 周）

**目标：量化系统表现，建立工程师可信度。**

### 为什么自建而不套 RAGAS

套 RAGAS 只需要 `pip install ragas` + 5 行代码。面试官问"faithfulness 怎么算的"，你说"我不知道，RAGAS 内部实现的"——这就是调包侠。

自己实现三个指标，每个都能讲清楚原理——这就是工程师。

### Step 3.1 — Faithfulness（忠实度）指标（2 天）

**定义**：回答中的每个陈述是否都能在来源材料（简历分析结果、JD 分析结果、匹配结果）中找到依据。

**算法**：
1. 用 LLM 将回答拆分为独立的原子陈述（atomic claims）
2. 对每个 claim，用 LLM 检查它是否被来源材料支持
3. Faithfulness = 被支持的 claim 数 / 总 claim 数

**实现**：
```python
class FaithfulnessMetric:
    def __init__(self, llm_service: LLMService):
        self.llm = llm_service

    def extract_claims(self, answer: str) -> list[str]:
        """用 LLM 把回答拆成原子陈述"""
        prompt = f"将以下回答拆分为独立的原子陈述，每行一条：\n\n{answer}"
        response = self.llm.chat(prompt)
        return [line.strip("- ") for line in response.split("\n") if line.strip()]

    def check_claim(self, claim: str, sources: str) -> bool:
        """检查一条陈述是否被来源材料支持"""
        prompt = f"""来源材料：
{sources}

请判断以下陈述是否完全被来源材料支持。只回答 YES 或 NO。
陈述：{claim}"""
        response = self.llm.chat(prompt)
        return "YES" in response.upper()

    def score(self, answer: str, sources: str) -> float:
        claims = self.extract_claims(answer)
        if not claims:
            return 1.0
        supported = sum(1 for c in claims if self.check_claim(c, sources))
        return supported / len(claims)
```

---

### Step 3.2 — Answer Relevancy（回答相关性）指标（1 天）

**定义**：回答是否紧扣用户的问题，有没有答非所问。

**算法**：
1. 用 LLM 从回答反推可能的问题（generated questions）
2. 计算每个 generated question 与原始 question 的语义相似度
3. Relevancy = 平均相似度

**关键洞察**：如果回答真正在回答问题，那么从回答反推出来的问题应该与原始问题高度相似。如果回答跑偏了（比如你问匹配度，它一直在分析简历），反推出来的问题就不像原始问题。

**实现**：
```python
class AnswerRelevancyMetric:
    def score(self, question: str, answer: str, embed_fn) -> float:
        # 从回答反推问题
        generated_qs = self._generate_questions(answer)
        # 计算相似度
        orig_emb = embed_fn(question)
        scores = [cosine_sim(orig_emb, embed_fn(q)) for q in generated_qs]
        return sum(scores) / len(scores)
```

这里 embedding 可以用 DeepSeek API 的 embedding 端点（`text-embedding-3-small`），不需要本地模型。

---

### Step 3.3 — Context Recall（上下文召回）指标（1 天）

**定义**：来源材料中的关键信息有没有在回答中被覆盖。

**算法**：
1. 用 LLM 从来源材料中提取关键信息点
2. 对每个关键信息点，检查它是否在回答中出现
3. Recall = 被覆盖的关键信息点数 / 总关键信息点数

---

### Step 3.4 — 评测集构建 + 回归测试（1 天）

**做什么**：
- 手写 10-20 条评测用例，覆盖典型场景：
  - "分析我的简历"
  - "评估这个岗位是否适合我"
  - "我的技能与这个 JD 的匹配度"
  - 追问场景："刚才的分析再详细一些"
  - 边缘场景：只上传简历、只上传 JD、都上传
- 每个用例包含：question、resume、jd、expected_key_points
- 跑评测脚本：对每个用例，调用 Agent → 拿到回答 → 计算三个指标 → 输出报告
- 每次改 prompt 或换模型后，重新跑一遍看分数变化

**面试要点**：
- "我自己实现了 faithfulness、relevancy、recall 三个评测指标。faithfulness 的核心是 claim extraction + claim verification——先把回答拆成原子陈述，再逐条检查是否被来源支持。这和 RAGAS 的原理一样，但我自己实现后才真正理解评价体系。"
- "我建了 15 条评测用例的测试集，每次改 prompt 换模型都会跑回归。这也帮我发现了 prompt 调整中的问题——有一次改 synthesizer prompt 后 relevancy 从 0.8 掉到了 0.6，原来是新 prompt 让 LLM 倾向复述简历而不是回答问题。"

**涉及文件**：
- `backend/app/evaluation/metrics/faithfulness.py`（新建）
- `backend/app/evaluation/metrics/relevancy.py`（新建）
- `backend/app/evaluation/metrics/recall.py`（新建）
- `backend/app/evaluation/test_cases.json`（新建）
- `backend/app/evaluation/runner.py`（新建，批量评测脚本）
- `backend/app/evaluation/report.py`（新建，Markdown 报告生成）

---

## Phase 4：MCP 协议接入（1-2 周）

**目标：从 Tool Use 演进到标准协议，体现行业视野和技术敏感度。**

### MCP 是什么（30 秒讲清楚）

MCP（Model Context Protocol）是 Anthropic 推动的 AI Agent 工具调用标准协议。你可以把它理解为"AI 世界的 USB 协议"——不同的 AI 应用通过 MCP 统一接口发现和调用各种外部工具，就像 USB 让各种设备通过统一接口连接电脑。

架构上分两层：
- **MCP Server**：暴露工具的一方（比如 JobPilot 暴露 resume/jd/match 工具）
- **MCP Client**：调用工具的一方（比如 Claude Desktop 或你的 Agent 作为 Client 连接 MCP Server）

### Step 4.1 — MCP Server：暴露 JobPilot 工具（3-4 天）

**做什么**：把 JobPilot 的 resume / jd / match 三个工具包装成 MCP Server，让 Claude Desktop 或其他 MCP 客户端可以直接调用。

**技术方案**：用 `mcp` Python SDK（`pip install mcp`）。

**架构**：
```python
# jobpilot_mcp_server.py
from mcp.server import Server
from mcp.types import Tool, TextContent

server = Server("jobpilot")

@server.list_tools()
async def list_tools() -> list[Tool]:
    return [
        Tool(
            name="analyze_resume",
            description="分析求职者简历，提取技能、经验、教育背景等信息",
            inputSchema={
                "type": "object",
                "properties": {
                    "resume_text": {"type": "string", "description": "简历全文"}
                },
                "required": ["resume_text"]
            }
        ),
        Tool(name="analyze_jd", ...),
        Tool(name="match_position", ...),
    ]

@server.call_tool()
async def call_tool(name: str, arguments: dict) -> list[TextContent]:
    if name == "analyze_resume":
        result = await resume_service.analyze(arguments["resume_text"])
        return [TextContent(type="text", text=result)]
    # ... jd, match
```

然后在 Claude Desktop 的配置文件中注册：
```json
{
  "mcpServers": {
    "jobpilot": {
      "command": "python",
      "args": ["backend/jobpilot_mcp_server.py"],
      "env": {"OPENAI_API_KEY": "sk-xxx"}
    }
  }
}
```

**面试要点**：
- "我原来的 Tool 体系（BaseTool + ToolRegistry）和 MCP 的核心概念是一一对应的——Tool 定义、参数 schema、执行器。所以迁移到 MCP 时，本质上是把现有的 Tool 注册中心包装了一层 MCP 协议的 JSON-RPC 接口。"
- "MCP 解决的问题是：每个 AI 应用都自己定义 Tool 格式，互相不兼容。有了 MCP 标准后，JobPilot 的简历分析能力可以被 Claude Desktop、Cursor、甚至其他开发者复用。"

---

### Step 4.2 — MCP Client：让 Agent 调用外部工具（2-3 天）

**做什么**：让 JobPilot 作为一个 MCP Client，连接外部的 MCP Server，扩展 Agent 的能力边界。

**场景设计**：
- 接入天气 MCP → Agent 可以回答"北京这周天气怎么样，适合面试吗"
- 接入日历 MCP → Agent 可以帮安排面试时间
- 接入邮件 MCP → Agent 可以代发求职跟进邮件

**架构**：

```python
class MCPToolAdapter(BaseTool):
    """将 MCP 工具适配为 JobPilot 的 BaseTool 接口"""
    def __init__(self, mcp_tool_def: dict, session):
        self.name = mcp_tool_def["name"]
        self.description = mcp_tool_def["description"]
        self.parameters = list(mcp_tool_def["inputSchema"]["properties"].keys())
        self._session = session

    async def run(self, **kwargs) -> str:
        result = await self._session.call_tool(self.name, kwargs)
        return result.content[0].text

class MCPToolRegistry:
    """连接多个 MCP Server，动态发现工具"""
    async def connect(self, server_config: dict) -> list[MCPToolAdapter]:
        # 通过 MCP Client 连接 server
        # 调用 list_tools() 发现所有工具
        # 为每个工具创建 MCPToolAdapter
        pass
```

这样 MCP 工具就和手写工具一样注册到 ToolRegistry 中，Agent 不需要知道工具的来源——它只看到 name、description、parameters。

**面试要点**：
- "MCP 的 Client-Server 架构和 ToolRegistry 的设计天然契合——MCP Client 发现外部工具后，用 Adapter 模式适配到 ToolRegistry 接口。Agent 不关心工具是本地的还是远程的。"
- "接入外部 MCP Server 后，Agent 的能力边界从 3 个工具扩展到 N 个——只要社区有人写了 MCP Server，JobPilot 就能用。这是 MCP 协议最大的价值：工具生态的复用。"

**涉及文件**：
- `backend/app/mcp/jobpilot_server.py`（新建，MCP Server 实现）
- `backend/app/mcp/mcp_client.py`（新建，MCP Client + 工具发现）
- `backend/app/mcp/mcp_tool_adapter.py`（新建，适配器模式）
- `backend/app/agent/jobpilot_agent.py`（修改，支持 MCP 工具的注册）
- `backend/requirements.txt`（加 mcp）

---

## Phase 5：RAG 检索增强生成（1-2 周）

**目标：不只做简单的向量检索，自己实现完整的 Hybrid Search + Reranker 管线。**

### 为什么 RAG 放在 Phase 5

你在 next_steps.md 中说过一句话很对：**"如果 Agent 连正确的 Tool 都调不对，检索回来的东西也用不上。"** Phase 2-4 已经把 Agent 的决策和执行能力做稳了，Phase 5 的 RAG 是锦上添花——给 Agent 一个知识库去检索，让回答更丰富。

### Step 5.1 — Embedding + 向量存储（2 天）

**做什么**：
- 部署中文 embedding 模型：`BAAI/bge-small-zh-v1.5`，用 `sentence-transformers` 加载，本地推理
- 向量数据库：Chroma（`pip install chromadb`），支持持久化存储
- 建索引脚本：把示例简历、常见 JD 模板、面试技巧文档向量化存入 Chroma

**为什么用 bge-small-zh 而不是 OpenAI embedding**：
- 本地推理：不消耗 API 费用，不依赖网络
- 中文优化：BAAI 的中文 embedding 在中文语义匹配上比多语言模型表现更好
- 384 维向量，轻量但足够

**面试要点**：
- "为什么不用 OpenAI 的 embedding API？一是成本——本地推理零费用；二是延迟——本地推理毫秒级响应，API 有网络延迟；三是中文优化——bge 系列专门针对中文做了训练。"

---

### Step 5.2 — Hybrid Search（3 天）

**做什么**：不只依赖向量检索，加入 BM25 关键词检索，两者融合。

**为什么需要 Hybrid Search**：
- 向量检索擅长语义匹配："后端开发" 能匹配到 "服务端工程师"
- 但向量检索对精确匹配不敏感：搜 "Python 3.12" 可能返回 Python 3.11 的内容
- BM25 擅长精确匹配：技能名、公司名、技术栈关键词

**实现**：
```python
class HybridSearcher:
    def __init__(self, chroma_collection, bm25_index):
        self.vector_store = chroma_collection
        self.bm25 = bm25_index

    def search(self, query: str, top_k: int = 10) -> list[Document]:
        # 1. 向量检索
        vector_results = self.vector_store.query(query, n_results=top_k)

        # 2. BM25 关键词检索
        bm25_results = self.bm25.search(query, top_k)

        # 3. RRF 融合排序
        fused = self._reciprocal_rank_fusion(vector_results, bm25_results)
        return fused[:top_k]

    def _reciprocal_rank_fusion(self, list_a, list_b, k=60):
        """RRF: 不需要调权重的融合算法"""
        scores = {}
        for rank, doc in enumerate(list_a):
            scores[doc.id] = scores.get(doc.id, 0) + 1 / (k + rank + 1)
        for rank, doc in enumerate(list_b):
            scores[doc.id] = scores.get(doc.id, 0) + 1 / (k + rank + 1)
        return sorted(scores.items(), key=lambda x: x[1], reverse=True)
```

**面试要点**：
- "为什么用 RRF 而不是加权融合？RRF 不需要调权重超参——BM25 和向量检索的分数尺度不同，直接加权融合需要大量实验找最佳比例。RRF 基于排名而非分数，天然跨检索器可比。"
- "BM25 和向量检索的互补性：前者擅长精确匹配——比如用户搜 'Python'，BM25 一定返回包含 'Python' 的文档；后者擅长语义匹配——'后端开发' 和 '服务端工程师' 向量距离很近但关键词完全不重叠。"

---

### Step 5.3 — Reranker 重排（2 天）

**做什么**：Hybrid Search 返回 top-k 后，用 cross-encoder 做精排。

**为什么需要 Reranker**：
- 向量检索和 BM25 都是在"宽泛地找相关"，返回 top-20 里有不少噪声
- cross-encoder 做的是"精细地判断相关性"——把 query 和 document 拼在一起输入模型，输出一个相关性分数
- 这是一个经典的"粗排 → 精排"两阶段架构

**方案**：`BAAI/bge-reranker-base`，本地推理

```python
class RerankerPipeline:
    def __init__(self):
        self.reranker = CrossEncoder("BAAI/bge-reranker-base")

    def rerank(self, query: str, docs: list[Document], top_k: int = 5) -> list[Document]:
        pairs = [[query, doc.content] for doc in docs]
        scores = self.reranker.predict(pairs)
        ranked = sorted(zip(docs, scores), key=lambda x: x[1], reverse=True)
        return [doc for doc, _ in ranked[:top_k]]
```

**面试要点**：
- "向量检索和 Reranker 的区别：向量检索是双塔模型——query 和 document 分别编码，离线算好 document 向量，检索时只算 query 向量，速度快但精度损失。Reranker 是交叉编码——query 和 document 一起输入模型，注意力机制可以跨 query-document 交互，精度高但速度慢。所以实际架构是粗排用向量 + BM25 快速筛选，精排用 cross-encoder 精细化排序。"

---

### Step 5.4 — RAG 集成到 Agent（1-2 天）

**做什么**：把 RAG 做成一个新 Tool（SearchTool），注册到 ToolRegistry，Agent 在需要时可以调用。

```python
class SearchTool(BaseTool):
    name = "search_knowledge_base"
    description = "搜索求职知识库，包括面试技巧、行业信息、岗位要求等"
    parameters = ["query"]

    async def run(self, query: str) -> str:
        pipeline = get_rag_pipeline()  # 从 app state 获取
        docs = pipeline.search(query)
        return "\n\n".join([d.content for d in docs])
```

这样 Agent 在用户问"xx 岗位的面试一般问什么"时，可以自动调用 SearchTool 从知识库检索。

**涉及文件**：
- `backend/app/rag/embedding.py`（新建）
- `backend/app/rag/bm25_index.py`（新建）
- `backend/app/rag/hybrid_searcher.py`（新建）
- `backend/app/rag/reranker.py`（新建）
- `backend/app/rag/rag_pipeline.py`（新建，封装完整管线）
- `backend/app/tools/search_tool.py`（新建）
- `backend/main.py`（修改，启动时初始化 RAG 管线）
- `backend/requirements.txt`（加 chromadb, sentence-transformers, rank-bm25）

---

## Phase 6：面试打磨（1 周）

**目标：代码、文档、话术都准备好，面试时从容自信。**

### Step 6.1 — 代码规范 + CI/CD（1 天）

- 后端：`black` + `isort` + `ruff`（格式化 + lint）
- 前端：ESLint + Prettier
- GitHub Actions：push → lint → test → build Docker（验证可构建）

### Step 6.2 — 文档整理（1 天）

- README.md：加项目简介、技术栈、快速启动、架构图、演示截图
- 删除开发期日志（development_log.md），保留架构文档
- 写一个 `INTERVIEW.md`：核心叙事、高频问题、技术亮点清单（见下方）

### Step 6.3 — 测试补全（2 天）

- 从 print 式手动验证改为 pytest assert
- 加 conftest.py（fixture 管理：mock LLM、测试用 SessionMemory）
- 关键路径覆盖：Agent 完整流程、Memory CRUD、TokenBudget 截断、评测指标

### Step 6.4 — 演示演练（1 天）

- 准备好 3 条演示用例（简单/中等/复杂）
- 录一个 3 分钟演示视频
- 准备"如果 LLM 挂了"的降级演示
- 准备"展示代码"的 IDE 切屏流程

---

## 面试叙事升级（2 分钟版本）

> 每个 Phase 完成后，你的叙事都多一层深度。

**v0.6.0 叙事**（当前）：
"我做了一个 AI 求职助手，手写了 ReAct Agent 循环和代码状态机，还做了 LangChain 版本对比。"

**v1.0 叙事**（完成后）：
"我做了一个 AI 求职助手 JobPilot，它覆盖了求职全流程——从简历解析、JD 分析、人岗匹配，到模拟面试、投递记录管理。Agent 架构上，我从零手写了 ReAct 循环验证了对 Agent 底层机制的理解，然后用 LangGraph 的 StateGraph 重构了执行流——实现了 resume 和 jd 的并行分析、灵活对话路由、以及 Human-in-the-Loop 确认机制。工具调用上，我从自定义的 Tool 注册中心演进到 MCP 标准协议——做了 Server 暴露工具和 Client 调用外部工具两个方向。评测上，我自建了 faithfulness、relevancy、recall 三个指标，不套 RAGAS 而是自己实现核心算法。检索上，我实现了 Hybrid Search（BM25 + 向量 + RRF 融合）+ cross-encoder Reranker 的完整 RAG 管线。产品层有投递看板、面试模拟、Token 消耗可视化。项目已部署在云服务器上，Docker 一键启动、JWT 鉴权、Redis 持久化、API 限流这些生产级能力都是完整的。"

---

## 高频面试问题（更新版）

**Q: 你的项目和其他求职助手有什么不同？**

"大部分类似项目是调个 API + 套个 LangChain。我的核心区别在三点：一是从零实现了 Agent 的完整循环和代码状态机，然后用 LangGraph 的 StateGraph 做了框架化重构——三层递进证明我不是只会用框架。二是产品形态完整——不只是分析简历，还有投递看板管理求职进度、模拟面试准备实战，是一个真正可以持续使用的求职管理中心。三是工程化深度——自建评测体系、Hybrid Search + Reranker 的 RAG 管线、MCP 协议接入、Redis 优雅降级、Docker 容器化部署，不是 demo 级别的项目。"

**Q: 面试模拟是怎么做的？**

"面试模拟不是随机题库——而是基于用户真实的简历项目和目标 JD 的技术要求来生成个性化问题。Agent 先分析简历中的技术栈和项目经历，再结合 JD 中的岗位要求，生成针对性的技术问题、行为问题和综合问题。多轮对话后给出表现评价——包括技术深度、表达清晰度和改进建议。技术上就是一个新 Tool + 一个 prompt 模板，但它让项目从分析工具变成了求职全流程助手。"

**Q: 投递看板的设计思路是什么？**

"'分析即记录'——用户做完人岗匹配后，一键保存为投递记录，不需要切换到另一个页面手动填写。看板用看板视图展示投递进度——已投递、初筛中、面试中、已Offer/已拒。拖拽切换状态，点击展开详情。后端用 SQLite + Repository 模式，后续可以切到 PostgreSQL 做多用户支持。"

---

## 附录 A：可并行的工作

如果时间紧，以下工作可以并行推进：

| 工作 | 可以和什么并行 | 原因 |
|------|--------------|------|
| Docker 容器化 | 任何 Phase | 纯基础设施，不依赖 Agent 代码 |
| 鉴权系统 + 投递看板 | Phase 2 业务线 | 独立模块，用单独的 SQLite 表，不改 Agent 逻辑 |
| 工程可视化面板 | Phase 2 业务线 | 只读展示后端已有数据，需要 `/status` 端点 |
| 评测集编写 | Phase 2（LangGraph）| 用例设计不需要等代码完成 |
| MCP Server | Phase 4（MCP Client）| Server 和 Client 独立开发 |

---

## 附录 B：每个 Phase 的"到此为止"

每个 Phase 有一个明确的停止点——不要陷入完美主义：

**Phase 1 停止点**：浏览器输入域名 → 登录 → 上传简历 → 问问题 → 拿到流式回答 → 保存到投递看板 → 拖拽改变状态 → 底部状态栏绿色指示灯亮起。Done。
**Phase 2 停止点**：可以用对话模式聊求职建议；可以发起模拟面试并得到评价；同样的输入手写版 == LangGraph 版输出；并行节点确实比串行快。Done。
**Phase 3 停止点**：15 条用例跑通，三个指标都有数值，报告能生成 Markdown。Done。
**Phase 4 停止点**：Claude Desktop 能调用 JobPilot MCP Server；JobPilot 能调用天气 MCP Server。Done。
**Phase 5 停止点**：SearchTool 注册到 ToolRegistry，Agent 能检索知识库回答问题。Done。
**Phase 6 停止点**：自信地讲完 2 分钟项目介绍，所有高频问题有准备。Done。

---

## 附录 C：技术选型决策记录

| 决策 | 选择了 | 为什么不用替代方案 |
|------|--------|-------------------|
| Agent 框架 | LangGraph StateGraph | 手写循环已完成理解阶段；LangChain AgentExecutor 是黑盒；StateGraph 给控制流 + 并行 + checkpointer |
| Agent 分流策略 | 代码 router + LLM chat | 工具调用必须确定性路由（代码）；自由对话交给 LLM 语义理解 |
| 投递看板存储 | SQLite（和用户表共用） | 投递记录和用户是 1:N 关系，天然放关系型数据库 |
| 向量数据库 | Chroma | Pinecone 云服务收费且本地无法演示；Qdrant 功能强但部署复杂；Chroma 一行 `pip install` 即用 |
| Embedding 模型 | bge-small-zh-v1.5 | OpenAI embedding 依赖 API 网络且有费用；m3e 也是好的中文模型，bge 生态更完整（有配套 reranker）|
| Reranker | bge-reranker-base | 和 bge embedding 同源，中文优化；Cohere 的 reranker 需要 API key 且英文为主 |
| MCP SDK | `mcp` Python SDK | Anthropic 官方维护，和 Claude Desktop 兼容性最好 |
| 评测框架 | 自建 | RAGAS 是黑盒，面试时讲不清原理 |
| 用户数据库 | SQLite | 开发期零配置；Repository 模式保证后续切 PostgreSQL 成本低 |
| JWT 库 | python-jose | 成熟稳定，和 FastAPI 生态兼容好 |

---

## 附录 D：Phase 1 和 Phase 2 的产品形态变化

```
v0.6.0（当前）                      v1.0 Phase 1 完成                  v1.0 Phase 2 完成
─────────────────────────          ─────────────────────────          ─────────────────────────
                                   + 用户登录/注册                     + 灵活对话（聊求职建议）
用户打开页面                        + 投递看板（拖拽管理）                + 模拟面试（三种模式）
  ↓                                + 底部状态栏（Redis/Token/限流）      + Agent 版本切换（手写/LangChain/LangGraph）
上传简历 + JD                       + Agent 版本对比面板                  + Human-in-the-Loop 确认
  ↓                                + 云服务器公网访问                    + 并行节点加速
Agent 分析 + 匹配                      ↓                                  ↓
  ↓                                从"用完即走"到"持续管理中心"            从"分析工具"到"求职全流程助手"
结果展示
  ↓
结束
```
