# Day01

完成：

- 初始化 FastAPI
- 创建项目目录
- 创建虚拟环境
- 配置 requirements.txt
- 创建 .env
- 实现 Settings 配置中心
- FastAPI 成功读取配置

学习：

- BaseSettings
- SettingsConfigDict
- Working Directory
- Python Package
- uvicorn 启动方式

问题：

1. app 模块导入失败
2. .env 未读取

答案：

1. FastAPI 是 ASGI 应用，应该由 Uvicorn 等 ASGI Server 启动。使用 uvicorn app.main:app --reload 可以正确加载应用对象，并保证模块导入路径正确。
2. 项目目录结构优化

下一步：

实现 LLMService

# Day 02

完成内容

- 实现 LLMService
- 封装 OpenAI Client
- 实现 chat() 接口
- 添加异常处理

学到的知识

- Service Layer
- 单一职责原则
- 封装
- API 调用流程
- try...except

问题

1. 为什么封装 LLMService？
2. 为什么 chat() 返回 str？
3. 为什么不直接传 messages？

答案：

1. 封装 LLMService 主要是为了降低业务层和具体大模型 SDK 之间的耦合。如果业务代码直接依赖 OpenAI SDK，那么未来切换模型供应商或者 SDK 接口变化时，需要修改大量业务代码。通过 Service 层进行封装，可以提供一个稳定的调用接口，同时把模型初始化、异常处理、重试、日志记录等公共逻辑集中管理，提高代码的可维护性和扩展性。
2. 隐藏底层实现细节。降低业务代码和第三方 SDK 的耦合，同时如果未来更换模型供应商，只需要修改 Service 层即可。
3. messages 属于底层模型调用协议，而不是业务概念。封装 system_prompt 和 user_prompt，可以让业务层关注任务本身，同时由 LLMService 负责转换成模型需要的消息格式。如果加入 PromptManager、多轮对话、Memory 等模块，也可以保持接口稳定。

# Day03

完成内容

- 学习 Python logging 模块
- 理解 Logger、Handler、Formatter 的职责
- 完成企业级日志系统
- 成功输出第一条项目日志

今日收获

1. Logger 不负责输出，只负责管理日志。
2. Handler 负责将日志输出到不同目标。
3. Formatter 负责定义日志格式。
4. 一个 Logger 可以拥有多个 Handler。
5. 一个 Handler 通常对应一个 Formatter。

# Day4：PromptManager 模块开发

# 完成内容

1. PromptManager 初始化
2. 实现 get_prompt()，完成 Prompt 文件读取功能。
3. 实现 render_prompt()，新增 Prompt 渲染功能。

今日收获：

1. pathlib定位项目资源目录。 相比字符串路径更加稳定，可跨平台运行。
2. Prompt Cache 学习缓存思想。
3. PromptManager 遵循了单一职责原则（SRP）。

# Day5：LLMService 与业务模块开发

# 完成内容

封装 LLMService，统一管理大模型调用逻辑。

新增 ChatResult 数据模型，统一封装模型返回结果。

完成 ResumeService，实现简历分析（analyze）。

完成 JDService，实现岗位描述分析（analyze）。

完成 MatchService，实现简历与岗位匹配分析（analyze）。

抽取 BaseService，统一封装 Prompt 加载、Prompt 渲染与 LLM 调用流程。

完成 ResumeService、JDService、MatchService 的测试，并全部运行通过。

# 今日收获

1. 学会使用 Pydantic 统一数据模型
2. 新增 ChatResult，统一管理：
   content（模型回复）
   model（模型名称）
   elapsed（接口耗时）
   token 统计
   使数据传递更加规范，也方便后续功能扩展。
3. 学会使用继承减少重复代码:
   抽取 BaseService，将所有 AI Service 的公共逻辑统一管理。
   ResumeService、JDService、MatchService 只负责自身业务，实现了 DRY（Don't Repeat Yourself） 原则，提高了代码复用性与可维护性。
4. 理解业务边界（Business Boundary）,不同 Service 分别负责不同业务：
   ResumeService：负责简历相关业务
   JDService：负责岗位相关业务
   MatchService：负责岗位匹配相关业务
   每个模块职责单一，符合 单一职责原则（SRP）。
5. 初步理解 Prompt Engineering:
   学习如何设计结构化 Prompt，而不是简单地向模型提问。
   通过：
   指定模型角色
   明确任务目标
   固定输出格式
   使用 Prompt 模板
   提高模型输出的稳定性和可维护性。
6. 建立完整的 AI Service 架构:
   目前项目已经形成完整的调用链：

   Prompt Template
           │
           ▼
   PromptManager
           │
           ▼
   BaseService
           │
           ▼
   ResumeService / JDService / MatchService
           │
           ▼
   LLMService
           │
           ▼
   DeepSeek API

   开始具备企业级 AI 项目的基础架构。

# Day6：ReAct Agent 核心

# 完成内容

- 实现 `JobPilotAgent`：手写 ReAct 多步推理循环（Reason → Act → Observe）
- 实现 `Planner`：LLM 决策器，输出结构化 `Plan`（`thought` / `action` / `action_input`）
- 实现 Tool 体系：`BaseTool` + `ToolRegistry` + `resume` / `jd` / `match` 工具
- 接入 `SessionMemory` / `MemoryManager`：跨步骤共享上下文

# 今日收获

1. ReAct 模式：以 Reason（思考）→ Act（行动）→ Observe（观察）的循环驱动任务，直到 `finish` 或达到 `max_steps` 防死循环。
2. 依赖注入雏形：Agent 接收已注册好的 `registry`，而非自己创建工具，职责更清晰。
3. Memory 是 Agent 与 Tool 之间共享的"笔记本"：每轮把已完成进度喂回 Planner，它才知道下一步该做什么。

# Day7：Synthesize 与 Planner 状态机

# 完成内容

- 新增 `synthesize.md` 模板与 `_synthesize()` 方法：`finish` 前基于 Memory 真实结果生成最终答案（修复"答案不接地/幻觉"缺陷）
- 重写 `planner.md` 为**严格状态机**（`resume → jd → match → finish`），支持"按用户要求"执行
- 新增 `test_agent_loop.py`：mock 隔离 Agent 循环与 Planner 决策，定位并修复 `resume` 循环卡死 bug
- `Planner` 增加 JSON 容错解析与 `logger` 接入

# 今日收获

1. 故障隔离（fault isolation）：一次只验证一个变量（把 Planner 决策"钉死"在正确序列），快速定位 bug 在 Planner prompt 而非 Agent 循环。
2. Prompt 工程：把"软建议"改成"硬状态机"，显著提升 LLM 决策稳定性。
3. Mock 测试：用 `unittest.mock` 把不可控的外部依赖（大模型 API）替换成可控假实现，专注测自身逻辑，不花 token。

# Day8：文件摄入（IngestTool + /upload）

# 完成内容

- 新增 `IngestTool`（`backend/app/tools/ingest_tool.py`）：继承 `BaseTool`，用 `PyMuPDF` 解析 PDF、`python-docx` 解析 DOCX，提取纯文本
- 新增 `POST /upload` 端点：接收 `UploadFile` → `IngestTool.run()` → 返回 `{filename, text}`
- `requirements.txt` 补登记 `PyMuPDF` / `python-docx` / `python-multipart`
- 端到端验证：uvicorn + curl 真实上传 docx，正确返回解析文本

# 今日收获

1. FastAPI 文件上传用 `UploadFile` + `FormData`；`python-multipart` 是必装依赖，否则 `UploadFile` 路由都注册不了（服务直接起不来）。
2. `IngestTool` 是"上传预处理"工具，不注册进 `ToolRegistry`——它由 `/upload` 直接调用，而不是交给 Planner 调度，职责边界要分清。
3. 临时文件用 `tempfile.NamedTemporaryFile(delete=False)` 落盘后解析，务必 `try/finally` 清理，否则解析失败会留垃圾文件。

# Day9：Vue3 前端 + CORS

# 完成内容

- 手写最小 Vite + Vue3 工程（`frontend/`）：`package.json` / `vite.config.js` / `index.html` / `src/main.js` / `src/App.vue`
- `App.vue` 用 `<script setup>` + `ref`：上传简历调 `/upload` 自动填入文本；填 query + JD 调 `/agent/run` 显示答案；含 `loading` / `error` 处理
- 后端 `main.py` 加 `CORSMiddleware` 放行前端 `:5173` 来源，否则浏览器同源策略拦截跨域请求
- `npm run build` 编译通过；dev server + 后端联调，CORS 预检与跨域上传均通过

# 今日收获

1. SPA 架构：浏览器只下载一个 HTML，之后所有交互由 Vue 在客户端动态改 DOM，不再整页刷新。
2. Vue3 `<script setup>` 里 `ref` / `reactive` / `computed` 等组合式 API **必须**从 `'vue'` 显式 `import`，不是全局变量——漏写会在运行时抛 `ReferenceError`，导致页面空白（build 不报错，很隐蔽）。
3. 跨域：前端 `:5173` 调后端 `:8000` 是不同源，浏览器默认拦截，需后端 CORS 放行；`fetch` 带 `FormData` 时不要手动设 `Content-Type`，让浏览器自动带 `boundary`。
4. 前后端数据流：上传拿到文本 → 存进 `resumeText` → 提问时随 `/agent/run` 的 `resume` 字段发给 Agent。

# Day10-12：Phase 1 体验层改造（SSE 流式 + Markdown 渲染 + 多轮对话 + 前端调试）

## 完成内容

- 实现 SSE 流式输出：LLMService.chat_stream() → JobPilotAgent.execute_stream() → /agent/run/stream 端点 → 前端 fetch + ReadableStream 消费
- 前端新增 Markdown 渲染：引入 marked.js，封装 renderMarkdown() + XSS sanitize，替代 <pre> 原样展示
- 实现多轮对话：SessionMemory 加 messages 字段，新建 TokenBudget 控制器，Planner/Synthesize 注入对话历史
- 前端自动生成 session_id 并跨请求携带，保持对话上下文
- vite.config.js 加 proxy 绕过 CORS 问题
- 思考链可视化：前端实时展示 Agent 每一步执行进度（step_start / step_done 事件）
- 修复 switch case 作用域 bug、缺少 __init__.py、CORS 预检 400 等 5 个 bug
- 制定完整的 v1.0 开发框架（6 个 Phase、20+ Steps）

## 今日收获

1. **SSE vs WebSocket**：SSE 是单向推送（服务器→客户端）、基于 HTTP、无代理兼容问题、适合流式输出；WebSocket 是全双工、ws:// 协议、适合双向实时通信。这里 Agent 只需要推送结果给前端，SSE 是最合适的选择。

2. **fetch + ReadableStream vs EventSource**：EventSource 只支持 GET，我们的端点需要 POST 请求体（query + resume + jd），只能用 fetch 手动解析 SSE 流。

3. **流式不做重试**：同步调用可以做指数退避重试（用户还没看到结果，重试无感知），但流式输出时前端已逐字渲染——重试意味着文字突然消失又重来，体验比直接报错更差。

4. **Vite proxy 绕开跨域**：开发环境下用 Vite dev proxy 把前端请求代理到后端（同域），比配置 CORS 更可靠。浏览器对 localhost ↔ 127.0.0.1 的跨域策略不一致，proxy 从根源上消灭了跨域问题。

5. **switch case 的作用域陷阱**：JavaScript switch 语句的所有 case 共享同一个作用域，case 块内用 `const` 声明变量会导致重复定义错误。需要 `{}` 包裹独立块作用域。这是一个隐蔽但致命的 bug——不会在 build 时报错，只在运行时崩溃。

6. **Token 预算控制不是简单截断**：不能无脑 `messages[-N:]`，因为中英文 token 数不同（中文 ~1.5 token/字符，英文 ~1.3 token/单词）。TokenBudget 独立成类的好处：可测试（纯数据验证截断逻辑）、可替换策略（简单截断→摘要压缩→滑动窗口）、单一职责分离。

7. **业务记忆 vs 对话记忆**：SessionMemory 中两种记忆要分开管理——resume_analysis/jd_analysis 是「事实」（Tool 执行的持久结果），messages 是「上下文」（对话历史的临时记录）。前者用于后续分析，后者用于理解追问。

8. **dataclass 的 default_factory**：Python dataclass 不允许 `= []` 作为默认值（所有实例会共享同一个可变对象），必须用 `field(default_factory=list)` 让每个实例独立创建空列表。这是 Python 的经典陷阱。

9. **XSS 与 Markdown 渲染**：marked 不防 XSS，v-html 直接渲染 HTML 是危险的。本项目用最小化 sanitize（移除 <script>、<iframe>、on* 事件属性）作为防护——够本地开发用，上线需换 DOMPurify。

10. **架构决策记录（ADR）**：在 changelog 中记录每个关键设计决策及其替代方案和拒绝理由。这让面试官直观看到「你不是随便选的，你理解 trade-off」。例如为什么 SSE 而不是 WebSocket、为什么 fetch 而不是 EventSource、为什么流式端点独立路由。

## 踩坑记录

1. **前端 failed to fetch（排查最久的问题）**：
   - 症状：前端点「运行 Agent」→ failed to fetch，后端没有任何日志
   - 排查过程：后端 curl 测试正常 → 排除代码 bug → 怀疑 CORS → 加全局异常处理反而搞出 400 → 去掉全局异常处理 → 仍然 failed → 最终发现是 Vite dev 环境跨域不稳定
   - 根因：浏览器对 `localhost` ↔ `127.0.0.1` 的跨域策略不一致，即使后端 CORS 配置正确也会被浏览器拦截
   - 解决方案：Vite proxy 绕开跨域——前端请求同域的 `/agent/run/stream`，Vite 转发到后端
   - 教训：跨域问题优先用 proxy 解决而非反复调整 CORS 配置

2. **@app.exception_handler(Exception) 的副作用**：全局异常处理会拦截 CORS 中间件的 OPTIONS 预检请求，导致返回 400 而非 200。全局异常处理器应该只处理业务层的异常，让中间件层的请求正常流转。

3. **switch case const 作用域**：case 里 `const step = ...` 在 switch 共享作用域中会重复声明，导致 `handleSSEMessage()` 静默崩溃，fetch 链路中断。错误信息在 Console 中不显眼，容易被前端其他 noise（Chrome 插件报错）淹没。

# Day13-14：Phase 1 完成 + Phase 2 状态机代码化

## 完成内容

- 前端 UI 重构：从单文件 App.vue 拆分为 useAgent composable + ChatBubble + ThinkChain + InputPanel 四个组件
  - 组件树：App.vue（编排）→ ChatBubble（气泡）、ThinkChain（思考链）、InputPanel（输入）
  - 数据流：状态全部在 useAgent composable 中，子组件纯展示、props 接收、emit 通知
- Planner 状态机代码化：将 planner.md 中的自然语言状态机迁移为 AgentStateMachine 类
  - compute_allowed_actions() 根据 Memory 状态 + query 关键词，确定性返回当前允许的合法 action 列表
  - 单 Tool 请求直接执行（零 LLM 调用），多 Tool 请求走 Planner LLM
  - 移除 _all_done 安全阀（被状态机替代）
  - planner.md 重写：从 ~55 行精简到 ~45 行，状态机规则全部迁移到代码

## 今日收获

1. **YAGNI 原则（You Aren't Gonna Need It）**：当前项目没有多页面路由，不需要全局状态管理。Composable 够用。但为未来切换 Pinia 预留空间——把响应式变量从 Composable 移到 Store 时，调用方代码不变。

2. **流式 Markdown 渲染的挑战**：每次收到 SSE chunk 都重新调用 marked.parse() 渲染整个文本——对几百字的回复来说性能可接受，但面试时可以说出优化方案（按行触发渲染、debounce 控制）。

3. **单向数据流**：状态只存在于 composable 中，子组件不可直接修改父组件状态。这是 Vue 官方推荐的模式，面试中可以说「所有子组件都是纯展示组件，通过 props 接收数据、emit 通知事件」。

4. **为什么代码状态机比 prompt 状态机好**：这是 Agent 架构中最深刻的一课。
   - Prompt 状态机把规则交给 LLM 理解——LLM 可能不听话（resume 循环卡死）
   - 代码状态机确定性地计算允许的 action——相同输入永远相同输出
   - 但 LLM 仍然参与——当多个 action 都允许时，LLM 判断优先顺序（语义理解）
   - 这种「代码管规则、LLM 管选择」的分工，在工业界 Agent 系统中是标准做法

5. **从手写状态机到 LangGraph**：AgentStateMachine 本质上就是 LangGraph 的 conditional_edge
   - 手写的 `if resume_done and jd_done: next = match` 
   - 等价于 LangGraph 的 `conditional_edge("planner", lambda state: "match" if state.resume_done else "resume")`
   - 这是 Phase 4 迁移的核心前提——你已经理解底层原理了，框架只是语法糖

# Day15-16：Phase 3 Redis 集成 + Phase 4 LangChain 迁移

## 完成内容

Phase 3:
- 封装 Redis 客户端（redis_client.py）：连接池单例 + 懒加载 + 优雅降级
- 实现 RedisSessionStore（redis_store.py）：Redis String 存储会话 JSON，24 小时 TTL 自动过期
- 改造 MemoryManager（双路径）：Redis 优先，内存 fallback
- SessionMemory 加序列化支持：to_dict() / from_dict()
- API 限流（rate_limit.py）：固定窗口算法（INCR + EXPIRE），FastAPI Depends 声明式注入
- Docker Compose 启动 Redis：redis:7-alpine + AOF 持久化

Phase 4:
- LangChain LLM 包装器（langchain_agent/llm.py）：ChatOpenAI 替代 LLMService
- LangChain Tool 迁移（langchain_agent/tools.py）：@tool 装饰器替代 BaseTool 手写类
- LangChain Agent（langchain_agent/agent.py）：create_react_agent + InMemorySaver
- 新增端点：/agent/langchain/run + /agent/langchain/stream

## 今日收获

1. **Redis 连接池的意义**：每次 TCP 握手成本高（~1ms + 系统调用），连接池在应用启动时一次性创建 20 个连接，所有请求复用。没有连接池时高并发下可能耗尽 Redis 的 maxclients（默认 10000）。

2. **优雅降级的核心哲学**：Redis 是"加分项"不是"必需品"。`get_client()` 返回 None 时：MemoryManager fallback 到内存dict、限流器放行所有请求。核心功能不依赖 Redis。

3. **固定窗口 vs 滑动窗口**：固定窗口用 INCR+EXPIRE（2 条命令 O(1)），滑动窗口用 ZSET（更复杂但更精确）。当前场景选简单方案——误判代价低（窗口边界短期超限 60 秒后自动恢复）。

4. **INCR + EXPIRE 的原子性问题**：这两个命令不是原子的（分开发送）。如果 INCR 后、EXPIRE 前 Redis 崩溃，计数器永不过期。生产环境可以用 Lua 脚本或 MULTI/EXEC 事务保证原子性——面试时说「当前版本够用，上线前会用 Lua 封装」体现安全意识。

5. **LangChain 迁移中保持行为一致**：Tool 函数内部仍调手写的 Service 层（ResumeService/JDService/MatchService）——LLM 调 Tool 的输出和手写版完全一致。只换了框架壳子，没动业务逻辑。

6. **两套端点并行的设计**：手写版（/agent/run）和 LangChain 版（/agent/langchain/run）同时存在。面试时可以用同一个输入对比两个版本的输出——这是"框架迁移"最有力的验证。

7. **Docker Compose 即基础设施即代码**：redis:7-alpine 镜像只有 ~30MB，--appendonly yes 开启 AOF 持久化（每次写操作记录到磁盘，重启不丢数据）。`volumes` 把数据映射到宿主机，即使容器删除数据也保留。

6. **组件拆分不是炫技**：拆组件是为了三个工程目标：
   - 可维护（改一个功能只需改一个文件）
   - 可复用（ChatBubble 以后可以用于其他对话场景）
   - 可测试（纯展示组件的单元测试不需要真实 DOM）
   面试时被问「为什么不把逻辑写在组件里」，回答：「单一职责——组件管渲染，composable 管状态。逻辑和 UI 解耦后，可以单独测试状态管理而不需要渲染 DOM。」

7. **关键词匹配 vs LLM 分类的取舍**：agent_state.py 用关键词判断「用户是否在问简历/JD」，而不是再调一次 LLM
   - 关键词匹配：零成本、零延迟、确定性
   - LLM 分类：更精确，但每次决策都要调 API（+1s 延迟 + token 费用）
   - 取舍逻辑：误判代价低（最多多执行一次不必要的 Tool），所以选便宜的方案

# Day17-18：Phase 3 Redis 完整落地 + Docker 实操

## 完成内容

- Redis 客户端封装（redis_client.py）：连接池单例 + 懒加载 + 优雅降级
- RedisSessionStore（redis_store.py）：JSON 序列化 + 24h TTL 自动过期
- SessionMemory 加 to_dict() / from_dict() 序列化支持
- MemoryManager 双路径改造（Redis 优先 + 内存 dict fallback，透明切换）
- API 限流（rate_limit.py）：固定窗口 INCR + EXPIRE，FastAPI Depends 声明式注入
- Docker Desktop 安装 + Docker Compose 启动 Redis:7-alpine
- docker-compose.yml：AOF 持久化 + 数据卷映射

## 今日收获

1. **Redis 连接池的管理**：每次连接都是 TCP 握手（~1ms + 上下文切换）。连接池在应用启动时创建一次，所有请求复用——和 HTTP Keep-Alive 是一个道理

2. **优雅降级的核心设计**：Redis 是"加分项"不是"必需品"。get_client() 返回 None → MemoryManager fallback 到内存 dict → 限流器放行所有请求 → 核心功能不受影响。代码中每个 fallback 点都有日志标注

3. **固定窗口 vs 滑动窗口**：固定窗口 INCR+EXPIRE（2 条命令，O(1)），滑动窗口 ZSET（O(log N)）。当前场景选简单的——误判代价低（窗口边界短期超限 60 秒后自动恢复）

4. **Docker 即基础设施即代码**：docker-compose.yml 是声明式配置——任何人 clone 项目后 `docker compose up -d` 即可启动 Redis，不需要手配

5. **INCR + EXPIRE 非原子性的安全问题**：INCR 后 EXPIRE 前如果 Redis 崩溃/重连失败，key 永不过期。当前版本够用（local dev），但要记住：生产环境用 Lua 脚本或 SET key value NX EX seconds

# Day19：Phase 4 LangChain 迁移 + 项目 Review

## 完成内容

- LangChain LLM 包装器（langchain_agent/llm.py）：ChatOpenAI → DeepSeek
- @tool 装饰器迁移 3 个工具（langchain_agent/tools.py）
- LangChain Agent（langchain_agent/agent.py）：create_react_agent + InMemorySaver
- 新增端点：/agent/langchain/run + /agent/langchain/stream
- 手写版和 LangChain 版端点并行存在，可对比输出
- 项目全面 Review + 6 份文档更新（project_structure / architecture / roadmap / changelog / development_log / README）

## 今日收获

1. **LangChain 不是魔法——它是规范化的模板代码**：手写版的 for 循环 → LangChain 的 AgentExecutor；手写的 BaseTool → LangChain 的 @tool；手写的  SessionMemory → LangChain 的 InMemorySaver。理解了这个映射关系后，任何 Agent 框架都只是语法糖

2. **两版并行的「对比实验」思维**：软件工程中，重构的黄金标准是「行为不变性」——相同输入 → 相同输出。两版端点并存让你可以直接验证迁移是否正确

3. **astream_events 的坑**：LangChain 的异步事件流在 FastAPI 的同步端点中有适配问题。这不是框架的问题，是 async/sync 的阻抗不匹配——手写版用的是同步 generator，天然适配 FastAPI 的 def 端点。理解阻抗不匹配本身就是学习

4. **项目 Review 的价值**：每完成一个 Phase 做一次全面审查，检查「文档是否过时」「架构图是否还能反映真实代码」「模块间的映射关系是否清晰」。过时的文档比没有文档更危险——因为会误导阅读者

# Day 20：Phase 1.1 Docker 全项目容器化

> 日期：2026-07-24

## 完成内容

- 后端 Dockerfile（多阶段构建：builder 装依赖 + runner 运行）
- 前端 Dockerfile（node:alpine 构建 + nginx:alpine 托管）
- nginx.conf（SPA try_files + API 反向代理 + proxy_buffering off + gzip）
- docker-compose.yml（三服务编排：Redis healthcheck + 启动顺序 + 服务互发现）
- .dockerignore（跳过 .venv / node_modules / \_\_pycache\_\_）
- requirements.txt 补充 langgraph / langchain / langchain-core
- config.py Settings 增加 Redis 配置字段（REDIS_HOST 等，支持环境变量覆盖）
- main.py LangChain Agent 改为懒加载（`_get_langchain_agent()`）

## 今日收获

1. **多阶段构建的核心思想**：构建阶段可以膨胀（装 pip、gcc、npm），运行阶段从零开始只复制最终产物。前端镜像从 ~120MB（node:alpine）降到 ~10MB（nginx:alpine），后端不装编译器和 pip。

2. **hiredis + libgomp1 的坑**：`hiredis` 是 Redis C 解析器，编译后需要 `libgomp1` C 运行时库。构建阶段有 gcc 能编译通过，运行阶段缺少 libgomp1 就会 `ImportError: libgomp.so.1: cannot open`。Dockerfile 里 `apt-get install libgomp1` 这行就是修这个的。

3. **Docker 网络中的服务发现**：容器间通信用服务名而非 localhost——`REDIS_HOST=redis`、`proxy_pass http://backend:8000`。Docker Compose 内置 DNS 解析，服务名自动映射到容器内网 IP。这是 Docker 网络栈的核心概念。

4. **Nginx 反向代理的 SSE 支持**：`proxy_buffering off` 是关键。Nginx 默认缓冲后端响应（攒够量再发），SSE 流式输出需要逐 token 推送。不加这行，用户等 30 秒看到一整坨文本。

5. **懒加载的设计哲学**：`_get_langchain_agent()` 让主模块启动时不 import langgraph。这不仅加速冷启动（~2 秒），更重要的是降低依赖耦合——主 Agent 挂了不影响 LangChain，反过来也一样。

6. **Pydantic Settings 的环境变量覆盖**：Settings 类声明字段 → 自动从环境变量读取同名值 → docker-compose 的 `environment` 注入覆盖。三层优先级：环境变量 > .env 文件 > 默认值。

   - 这是工程师思维——技术选型不是「哪个更高级」，而是「哪个更适合当前场景」

# Day 21：Phase 1.3 JWT 鉴权系统 + Phase 1.4 投递看板 + Phase 1.5 工程面板

> 日期：2026-07-29

## 完成内容

### JWT 鉴权系统
- SQLAlchemy 引擎 + Session 工厂（`core/database.py`），SQLite 存储，check_same_thread=False 适配 FastAPI 线程池
- User ORM 模型（`models/user.py`）+ UserRepository Repository 层
- bcrypt 密码哈希（`passlib[bcrypt]`）+ JWT 签发/验证（`python-jose`）
- `get_current_user()` FastAPI Depends——从 `Authorization: Bearer <token>` 头提取 token，解码验证，查数据库确认用户存在
- 3 个鉴权端点 + 所有 Agent 端点挂 `/applications` CRUD 端点
- 前端登录/注册页 + 所有请求自动带 Authorization 头

### 投递看板
- Application ORM 模型 + ApplicationRepository（CRUD + 状态筛选 + 归属校验）
- 4 个 REST 端点：POST/GET/PUT/DELETE /applications
- 五列看板视图（JobBoard.vue）+ 卡片组件（JobCard.vue）+ useApplications Composable
- ChatBubble "📌 保存到投递看板" 一键保存——自动提取公司/岗位/分数，提取不到时弹出手动输入框

### 工程面板
- `/status` 端点 + StatusBar 底部状态栏（Redis 指示灯 + Token 进度条 + 限流计数 + Agent 版本切换）
- 5 秒定时轮询

### 聊天记录持久化
- localStorage 持久化对话记录，SSE 流结束时自动保存，刷新后自动恢复

## 踩坑记录

1. **passlib + bcrypt 版本兼容性问题**
   现象：`POST /auth/register` 返回 500，报 `ValueError: password cannot be longer than 72 bytes`。
   排查：这个错误信息具有误导性——不是密码太长，而是 passlib 调用 bcrypt 内部 `detect_wrap_bug` 函数时，传参方式在新版 bcrypt 中不兼容。
   解决：在 requirements.txt 中锁死 `bcrypt==4.0.1`。passlib 的 `CryptContext(schemes=["bcrypt"])` 依赖 bcrypt 特定版本的内部行为，版本不匹配时 `detect_wrap_bug` 函数传入的参数格式错误。

2. **JWT 签发 datetime 直接传 dict 导致 token 无法验证**
   现象：登录成功返回 token，但所有带 token 的请求返回 401，后端日志无任何错误输出。用 jwt.io 在线解码 token 发现 exp 字段是 ISO 日期字符串而非数字时间戳。
   根源：`jwt.encode({"exp": datetime.now()}, ...)` —— python-jose 不会自动把 datetime 转为 Unix 时间戳。它要么静默忽略，要么产生格式错误的 token，导致解码时 exp 验证失败。
   解决：签发时手动 `int(expire.timestamp())` 转 Unix 时间戳。

3. **JWT `sub` 必须是字符串**
   现象：签发给改了时间戳格式后，仍然 401。后端日志终于有输出了：`Subject must be a string`。
   根源：python-jose 的 `jwt.decode()` 默认配置要求 `sub` 字段是字符串（符合 RFC 7519 规范）。实际签发时 `"sub": user_id` 是整数。
   解决：签发时 `"sub": str(user_id)`，解码后 `int(payload["sub"])` 恢复整数。
   教训：PyJWT 对 sub 类型要求宽松（自动转换），python-jose 严格遵照 RFC 规范。跨库迁移时要注意这种差异。另外，**在异常处理中加日志是调试 JWT 问题的关键**——最初 `except JWTError` 没有任何日志输出，导致花了很长时间才定位到具体错误。

4. **`/status` 端点 401 连锁反应**
   现象：状态栏显示 Redis 不可用、Token 0/0、限流 0/0，投递看板一直报 401。但聊天功能正常。
   排查：`/status` 挂了 `get_current_user` 鉴权。useStatus.js 的 fetch 带了 Authorization 头。当 token 过期（30 分钟）后，状态轮询持续触发 401，但因为是静默错误处理，用户看不到任何提示，只看到状态栏全是默认值（红色/灰色）。
   解决：`/status` 改为公开接口，不需要鉴权。useStatus.js 的 fetch 去掉 Authorization 头。

5. **Nginx 缺少新路由的代理规则**
   现象：新增鉴权和投递端点后，前端所有 `/auth/*` 和 `/applications` 请求返回 405。
   排查：Nginx 只配置了 `/agent/` 和 `/upload` 的代理。新路由的请求走到静态文件 location，静态文件服务器不支持 POST/PUT/DELETE，返回 405 Method Not Allowed。
   解决：在 nginx.conf 中逐条添加 `/auth/`、`/applications/`、`/applications`、`/status` 四个 location 规则。教训：每次新增后端路由都要同步检查 nginx 配置。

## 今日收获

1. **Repository 模式的价值**：业务代码通过 `UserRepository` / `ApplicationRepository` 操作数据库，不直接依赖 SQLAlchemy Session。这带来两个好处：一是单元测试时 mock Repository 即可，不需要真实数据库；二是后续切数据库（SQLite → PostgreSQL）只改 repository 内部实现和连接字符串。面试时这是一个很好的「设计模式在真实项目中的应用」话题。

2. **JWT 的 `exp` 和 `sub` 是实践中最容易踩的坑**：`exp` 必须是整数 Unix 时间戳，`sub` 必须是字符串。这两个要求都来自 RFC 7519，但不同的 JWT 库实现严格程度不同。PyJWT 宽松（自动转换），python-jose 严格（直接报错）。面试时能讲清楚这些细节是加分项。

3. **FastAPI Depends 的声明式依赖注入**：`get_current_user` 作为 Depends 注入到端点，比装饰器（`@login_required`）更清晰——Swagger 文档中可以看到每个端点需要哪些依赖，测试时可以用 `dependency_overrides` 替换。这是 FastAPI 区别于 Flask/Django 的核心设计理念。

4. **Nginx location 匹配的优先级陷阱**：`location /applications` 和 `location /applications/` 在 nginx 中是两个不同的匹配规则。前者精确匹配前缀（不带尾部斜杠），后者匹配目录前缀。写反了会导致部分请求走不到后端。最佳实践是两条都配——确保 `/applications` 和 `/applications/123` 都能正确转发。

5. **前端 localStorage 持久化的适用场景**：localStorage 只适合小数据量（< 5MB）、非敏感数据（明文存储）、简单结构的场景。对话记录恰好满足这三个条件。但它不适合存储 token（有 XSS 风险——应改用 httpOnly cookie）、大量结构化数据（应用 IndexedDB）、需要版本管理的配置（应用后端接口）。

6. **自动提取 vs 手动输入的设计权衡**：ChatBubble 的"保存到看板"功能先尝试自动从 Agent 回复中提取公司/岗位/分数，提取不到时弹出手动输入框。这个设计原则是「先用技术能力减少用户操作，再用兜底方案保证功能可用」——而不是在"全自动"和"全手动"之间二选一。

# Day 22：Phase 2.1 灵活对话引擎 + Phase 2.2 面试模拟

> 日期：2026-07-29

## 完成内容

### 灵活对话引擎
- AgentStateMachine 新增 chat 状态和路由规则
- jobpilot_agent.py 新增 `_chat()` / `_chat_stream()` 方法
- 新建 chat.md prompt 模板

### 面试模拟
- 新建 InterviewService（interview_service.py）+ InterviewTool
- 更新 interview.md（之前为空模板），完整面试 prompt
- AgentStateMachine 新增 `_query_mentions_interview()` 检测 + interview 路由
- main.py 注册 InterviewTool
- jobpilot_agent.py 同步/流式两个执行路径均支持 interview action
- planner.md 更新动作列表

## 踩坑记录

6. **LangChain 端点报 `No module named 'langchain_openai'`**
   现象：切换到 LangChain Agent 后发送消息报找不到 langchain_openai 模块。手写版 Agent 正常。
   排查：`langchain_agent/llm.py` 从 `langchain_openai` 导入 `ChatOpenAI`——这是 langchain 的独立子包。`requirements.txt` 只声明了 `langchain` 和 `langchain-core`，没有 `langchain-openai`。本地 `.venv` 碰巧装了（作为传递依赖），Docker 纯净环境中缺失。
   解决：requirements.txt 补充 `langchain-openai>=0.2`。教训：所有直接 import 的包必须显式声明依赖，不能依赖传递安装。

## 今日收获

1. **状态机扩展的设计原则**：新增一个 Tool 类型（interview）只需改四个地方——AgentStateMachine 的检测函数和路由规则、jobpilot_agent.py 的 action_input 处理、planner.md 的动作列表、main.py 的 ToolRegistry 注册。这种"插入式"扩展得益于代码状态机的确定性设计——新 Tool 不影响已有 Tool 的执行逻辑。

2. **对话感 vs 报告感的取舍**：InterviewTool 只生成第一轮暖场问题，后续让用户自由追问。如果一次性生成 6 轮问答，用户体验是看一份"面试题清单"而非"和面试官对话"。Agent 的每次交互应该是自然的一轮对话，而不是一份预制报告。

3. **单轮 Tool 模式的局限性**：当前 ReAct 循环每次用户发消息都重新判断路由。面试场景的理想体验是多轮连续对话（Agent 记住"我正在面试中"）。未来应该给 SessionMemory 加 `interview_round` 计数器，AgentStateMachine 检测到仍在面试中时自动维持 interview 模式。这个改进是下一步 LangGraph 重构的典型用例——LangGraph 的 StateGraph 天然支持这种有状态的多轮交互。

# Day 23：Phase 3 自建评测体系 + 状态栏修复 + 投递看板联动

> 日期：2026-07-31

## 完成内容

### 自建评测体系
- Faithfulness 指标（claim extraction + claim verification）
- AnswerRelevancy 指标（反向生成问题 + n-gram 哈希 embedding 相似度）
- ContextRecall 指标（关键信息点覆盖检查）
- 5 条评测用例 + 评测执行器 + Markdown 报告生成

### 状态栏修复
- LLMService 加累计 Token 计数器（`_total_prompt_tokens` / `_total_completion_tokens`）
- `/status` 端点改为读取 `agent.llm.total_tokens`
- `execute()` / `execute_stream()` 每次执行开始时重置计数器
- BaseService 支持注入外部 LLMService 实例
- main.py 启动时将 agent.llm 注入所有 Tool 的 Service 层

### 投递看板联动
- ChatBubble "📌 保存到投递看板" 按钮（自动提取 + 手动输入兜底）
- 聊天记录 localStorage 持久化

## 踩坑记录

7. **evaluation 目录缺少 `__init__.py` 导致整个应用 502**
   现象：后端容器启动，所有请求返回 502，容器日志显示 `ModuleNotFoundError`。
   原因：新建 `evaluation/` 和 `evaluation/metrics/` 目录时没建 `__init__.py`，Python 不认为它们是合法包。虽然 `main.py` 不 import 任何 evaluation 代码，但 Python 的模块发现机制在扫描 `backend/app/` 目录时触发了路径解析异常。
   解决：补上两个 `__init__.py`。
   教训：Docker 容器内 Python 包目录必须包含 `__init__.py`。本地开发时 `.venv` 的 sys.path 解析逻辑可能更宽松，但 Docker 的纯净环境更严格。

8. **Token 状态栏显示 0/8000——多实例问题**
   现象：状态栏 Token 始终为 0/8000，发完消息后也不变化。
   排查：`agent.llm` 和 Tool 内部 Service 的 LLMService 是**不同实例**。`BaseService.__init__` 里 `self.llm = LLMService()` 创建了新实例，Tool 调用 LLM 时计数器加到这个独立实例上，而 `/status` 端点读取的是 `agent.llm.total_tokens`——两个完全不同的计数器。
   解决：`BaseService.__init__` 改为 `def __init__(self, llm: LLMService | None = None)`，允许外部注入共享实例。`main.py` 启动后遍历 ToolRegistry，将 `agent.llm` 注入所有 Tool 的 Service。Token 重置逻辑加到 `execute()` 和 `execute_stream()` 开头——每次 Agent 调用前清零，状态栏显示的始终是最新一轮对话的消耗。

9. **`interview_tool.py` 语法错误**
   现象：修复 `__init__.py` 后仍然 502。容器启动日志显示 `SyntaxError: unmatched ')'` at line 36。
   原因：之前修改 `interview_tool.py` 时 `run()` 方法中误删了 `return self.service.interview(...)` 调用行，留下孤立的 `)`。
   解决：重写 `run()` 方法，恢复正确的 return 语句。
   教训：Edit 工具做多行替换时要格外小心——尤其 Python 的缩进和括号匹配在 diff 视图中不明显。

## 今日收获

1. **LLMService 实例管理的教训**：当系统中有多个组件调用 LLM（Agent 本体、各 Tool 的 Service、评测指标），全局统计（Token 消耗、API 调用次数、费用估算）必须在单例上维护。不是每个使用者都该有自己的 LLMService 实例——这类似于数据库连接池不应该被每个 Repository 自己创建。依赖注入（DI）是解决这个问题的最简单方案。

2. **评测指标的设计哲学**：Faithfulness 做的是 claim extraction + claim verification，不是直接问 LLM"这段回答忠实吗"。为什么？因为后者是模糊的二进制判断——LLM 只能说"忠实"或"不忠实"，你得不到逐条的量化证据。前者是可审计的——哪条陈述被支持、哪条没有被支持，每一行都有据可查。这是工程师和调包侠的本质区别：不是"用了什么指标"，而是"为什么这个指标这样设计"。

3. **Token 窗口 vs 实际消耗**：状态栏显示的 8000 是 DeepSeek 的上下文窗口预算，不是实际消耗。状态栏应该展示两者——已消耗 / 预算上限。这给用户一个直观的感知"对话还有多少容量"。面试时可以展开讲 TokenBudget 的分配策略：system prompt 优先 → Planner 规则 → 业务记忆 → 近期对话。

4. **Docker 构建的 `--no-cache` vs `--build` 选择**：今天反复遇到一个问题——改了代码但 Docker 不走缓存，反复 `--no-cache` 重装 pip 包非常慢。最终总结出规则：只有 Dockerfile 或 requirements.txt 改了才需要 `--no-cache`，日常只改 .py 源码时 `docker compose up -d --build` 足够——Docker 判断 COPY 语句的文件哈希变化，只重建变化的层。

# Day 24：Code Review + Bug 修复 + 文档整理

> 日期：2026-08-09

## 完成内容

### 🔴 严重 Bug 修复

1. **agent_state.py — `_query_mentions_jd` 空函数体**
   - 问题：函数有 docstring 但没有函数体，永远返回 `None` (falsy)
   - 影响：状态机永远不识别 JD 相关请求，resume→jd→match 流水线被破坏
   - 修复：补充完整的 JD 关键词匹配逻辑（"jd", "岗位", "职位", "招聘", "job description" 等）

2. **agent_state.py — `wants_resume`/`wants_jd` NameError**
   - 问题：第 105/109/113/117 行使用 `wants_resume`/`wants_jd`，但实际变量名为 `has_resume_in_query`/`has_jd_in_query`
   - 影响：`compute_allowed_actions()` 运行时抛出 `NameError`，整个 Agent 崩溃
   - 修复：全部改为正确的变量名

### 🟡 高优先级修复

3. **jobpilot_agent.py — `_is_followup` 逻辑过激**
   - 问题：只要有任何分析结果就把所有后续请求当追问，用户上传新简历后无法获得新分析
   - 修复：`_is_followup` 接受 `query` 参数，同时检查 query 是否包含新的分析意图关键词

4. **jobpilot_agent.py — execute() 与 execute_stream() 会话保存不一致**
   - 问题：同步 `execute()` 多条返回路径缺 `save_session()`，而异步 `execute_stream()` 对应路径有
   - 修复：在所有 return 路径上统一添加 `save_session()`

### 🟠 中等优先级修复

5. **main.py — `refresh_token` 通过 URL 查询参数传递**
   - 风险：URL 被代理/浏览器历史/服务器日志记录
   - 修复：改为 Pydantic Body 模式（`RefreshRequest.body.refresh_token`）

6. **evaluation/relevancy.py — 非确定性 hash**
   - 问题：`hash()` 受 `PYTHONHASHSEED` 影响，每次运行结果不同
   - 修复：改用 `hashlib.sha256` 提供确定性 hash

7. **evaluation/runner.py — 评分统计改进**
   - 新增 `score is not None` 检查，防止 None 值进入统计
   - 过滤掉的用例改为显式检查而非依赖 falsy 短路

8. **frontend/useAgent.js — 实现 token 自动刷新**
   - 问题：`refreshToken` 存储但从未使用，遇到 401 直接登出
   - 修复：新增 `tryRefreshToken()` 函数，401 时自动续期后重试

### 🔵 小问题修复

9. **frontend/InputPanel.vue** — `upload` 事件未在 `defineEmits` 中声明（Vue 警告）
10. **frontend/JobCard.vue** — 修复 match_summary 无论是否截断都显示省略号
11. **frontend/useStatus.js** — 移除未使用的 `onMounted` 导入
12. **frontend/JobBoard.vue** — 移除未使用的 `computed` 导入
13. **backend/main.py** — 移除未使用的 `LLMServiceError` 导入
14. **backend/agent/planner.py** — 更新过时的注释（引用不存在的 `_all_done` 方法）
15. **backend/prompts/prompt_manager.py** — 按 key 长度降序替换，防止短键破坏长键占位符

### 文档

16. **roadmap.md** — 同步进度：更新日期为 2026-08-09，新增 v0.9.2 Bug 修复条目，重写"开发中/待完善"和"下一阶段规划"表格，移除已完成的先做项（Docker、评测体系），重新按优先级排序
17. **next_steps.md** — 修正进度总览表：Phase 7（Agent 能力扩展）和 Phase 8（自建评测体系）从 ⬜ 改为 ✅，新增 Phase 9（Bug 修复）条目，移除对已废弃 development_framework_v1.md 的引用
18. **optimization_list.md** — 更新已完成项状态（Docker 容器化 ✅、鉴权系统 ✅、投递看板 ✅、AI Agent 核心 ✅、自建评测 ✅），重写优先级建议表，新增 XSS DOMPurify 升级条目
19. **changelog.md** — 新增 v0.9.2 条目，记录全部 15 项修复 + 文档变更

### 改动文件统计

| 类别 | 文件数 | 具体文件 |
|------|--------|---------|
| 🔴 严重 Bug | 1 | agent_state.py |
| 🟡 重要修复 | 2 | jobpilot_agent.py, main.py |
| 🟠 中等修复 | 3 | relevancy.py, runner.py, useAgent.js |
| 🔵 小修复 | 6 | InputPanel.vue, JobCard.vue, useStatus.js, JobBoard.vue, planner.py, prompt_manager.py |
| 📝 文档 | 4 | development_log.md, roadmap.md, next_steps.md, optimization_list.md, changelog.md |
| **总计** | **17** | |

## 今日收获

1. **代码 Review 的价值**：写完代码后隔一段时间再重新审视，能发现很多当初写的时候没注意到的问题。agent_state.py 的两个严重 Bug（空函数体 + NameError）如果没有人 Review，可能一直隐藏到运行时才会暴露。这也是为什么 Code Review 是工程团队的标配流程。

2. **变量命名一致性是基本工程素养**：同一个变量，不同位置用了不同名字（`wants_resume` vs `has_resume_in_query`），这本质上是一个重构不彻底的问题。写完代码后用 IDE 的 References 功能检查所有引用点，确保命名一致。Git diff 中这类错误会被淹没在大量代码中，需要逐行对比。

3. **查询参数 vs Body 的安全差异**：虽然 HTTPS 加密了传输层，但 URL 本身会留在浏览器历史、代理日志、服务器访问日志中。Auth token 这种敏感数据，必须用 POST Body 或 Header 传递。这也是 OWASP 安全规范中的基础要求。

4. **Python `hash()` 的随机化机制**：Python 3 为了安全（防止基于哈希碰撞的 DoS 攻击），通过 `PYTHONHASHSEED` 让 `hash()` 每次进程启动返回不同值。这是一个很多人不知道的 Python 特性——需要确定性哈希时必须用 `hashlib`。

5. **前端 token 过期处理的用户体验**：与其让用户频繁登出重新输入密码，不如在 401 时自动用 refresh_token 续期。对用户来说完全无感知，对安全性来说也没损失（refresh_token 本身也有过期时间）。这是一个典型的"沉默的优雅"设计——用户不需要知道发生了什么，但体验好了很多。

6. **文档一致性是项目成熟度的标志**：修复代码后最容易被忽略的就是文档。三份规划文档（roadmap / next_steps / optimization_list）之间的内容矛盾会让后续开发产生困惑——"评测体系到底做完了没有？"。统一整理后，所有文档指向同一份事实。这也是面试时可以说的加分项："每次代码变更我都会同步更新文档，过时的文档比没有文档更危险"。

## 下一步

- 实现 LangGraph Agent 迁移（langgraph_agent/state.py 已定义状态结构，AgentStateMachine 可 1:1 映射到 conditional_edge）
- 为 Agent 添加 interview_round 计数器，支持连续多轮面试（当前每次输入重置 interview 上下文）
- 将 XSS 防护升级为 DOMPurify（当前自制清洗器不防御 SVG/math 等高级攻击向量）

# Day 25：前端整体改版 + 看板重构 + 功能收尾

> 日期：2026-08-14

## 完成内容

### 一、整体界面改版（全宽 + 侧边栏）

- **全宽布局**：去掉原来 840px 居中限制，改为「左侧栏 260px + 右侧内容区撑满」的 flex 布局，解决"居中显得空"的问题
- **对话侧边栏（新增 ConversationSidebar.vue）**：仿主流 AI 产品
  - 顶部「＋ 新建对话」按钮
  - 会话列表按更新时间倒序，显示标题 + 时间（今天显示 HH:mm，更早显示月/日），当前会话高亮
  - 删除按钮 hover 才出现
  - 底部用户区：头像（用户名首字母）+ 用户名 + 退出登录
- **多会话数据层（重构 useAgent.js）**：localStorage 结构从单会话升级为 `{conversations: [{id, title, messages, updatedAt}], activeId}`，新增 newConversation / switchConversation / deleteConversation，会话标题自动从首条消息生成
- **顶栏重构**：Logo + 对话/看板 tab 切换 + 右侧 Agent 版本开关

### 二、看板重构（信息架构 + 编辑 + 分区）

- **卡片重设计（JobCard.vue）**：匹配分色阶（≥75 绿 / 50-74 琥珀 / <50 灰）作为视觉锚点 + 相对日期（"3 天前投递"）+ 备注徽标 + 两行摘要截断
- **详情编辑弹窗（ApplicationDetailModal.vue）**：支持编辑/创建两种模式，暴露全部字段（公司/岗位/分数/日期/阶段/摘要/备注/JD 原文），阶段改为 5 个 pill 按钮平铺，删除改为"两次点击确认"
- **四宫格分区（JobBoard.vue）**：4 个活跃状态做成 2×2 宫格，每个分区有顶部色条 + 图标 + 名称 + 提示 + 数量徽标；「已拒」单独放底部弱化横条
- **看板新建入口**：头部「＋ 新建投递」按钮 + 看板空状态引导页
- 修复隐性 bug：后端 update 用 `value is not None` 跳过字段，前端保存时用空字符串而非 null，否则"清空备注"会失效

### 三、功能收尾

- **Toast 消息系统（新增 useToast.js + ToastContainer.vue）**：替换所有 alert/confirm，支持 success/error/info 三种类型 + 动画 + 点击关闭
- **停止生成按钮**：useAgent 加 AbortController + stopGenerating，输入框生成中时"发送"变红色"停止"
- **复制原文按钮**：AI 消息 hover 显示复制，点击复制 Markdown 原文
- **输入框多行**：查询输入从 input 改 textarea，Enter 发送 / Shift+Enter 换行，中文输入法保护
- **去除重复控件**：StatusBar 里的 Agent 版本切换和顶栏重复，只保留顶栏
- **会话切换自动滚到底部**
- **强化 XSS 清洗**：新增 svg/math/form/meta/link/style 等危险标签移除 + src/xlink:href 的 javascript: 协议拦截

### 四、过程中回退的改动

- 曾尝试修复「状态栏 token/限流恒为 0」：token 恒 0 是因为流式调用 `chat_stream()` 不统计 token；限流恒 0 是因为 `/status` 硬编码 `rate_limit_used=0`。修到一半发现 DeepSeek 不一定支持 `include_usage`、且 nginx 未转发 X-Forwarded-For 导致限流 key 对不上。**最终决定删除这两个状态显示**，只保留能正常工作的 Redis 指示灯 + Agent 版本切换。留下的合理改动：`llm_service.py` 新增 `reset_token_counters()` 方法替代直接操作私有属性。

## 踩坑记录

1. **Docker Hub 网络问题**：`docker compose up -d --build` 报 `failed to fetch oauth token: Post "https://auth.docker.io/token": EOF`。这是国内访问 Docker Hub 的常见网络问题（buildkit 想联网查镜像元数据被断）。解决：日常前端开发改用 `npm run dev`（Vite 热更新，秒级生效），后端容器保持运行，只有最终部署才需要 `--build`。

2. **后端 update 的 None 语义陷阱**：`ApplicationRepository.update` 用 `value is not None` 跳过字段，意味着前端传 `null` 会被当作"没这个字段"而非"清空"。这导致清空备注/摘要失败。正确做法：前端把要清空的字段传空字符串 `""`。

3. **图片无法查看时用文字描述**：用户截图格式不支持时（Unsupported Image），根据文字描述"排版乱"直接判断根因——弹窗两列网格错位、卡片信息挤在一起，用结构化分组（group 标题 + 统一间距 + 三段式卡片）解决，比反复索要截图更高效。

## 今日收获

1. **信息架构 > 视觉装饰**：看板"差"的根因不是缺炫技功能，而是数据模型里 notes/jd_text 等字段在 UI 里是死数据、卡片信息密度不足。先补齐信息架构（编辑能力 + 死字段暴露），再做视觉（分色阶、分区），顺序不能反。

2. **"沉默的优雅"设计**：alert/confirm 是打断式的，toast 是非阻塞的；token 自动续期让用户无感知地避免重新登录。好的体验往往是不需要用户知道发生了什么。

3. **功能取舍要果断**：token/限流状态栏修到一半发现依赖的外部条件（DeepSeek 的 include_usage 支持、nginx 头转发）不确定，果断删除而非死磕。投入产出比不划算的东西，砍掉是对的——这也是产品判断力的一部分。

4. **本地开发用 dev server，部署才 build**：Docker 构建慢且依赖网络，日常前端开发应该用 Vite 热更新，只在最终部署时 `--build`。这是前后端分离开发的基本工作流。

## 下一步

- 云部署（Docker 已就绪，上 ECS/轻量服务器拿公网 URL）
- 面试连续多轮（interview_round 计数器）
- RAG 检索管线（Phase 5 方案已规划，等 Agent 稳定后实施）

# Day 26：Phase 11 产品收尾（面试多轮 + 扫描件检测 + 边角清理）

> 日期：2026-08-14

## 完成内容

### 一、面试连续多轮（interview_round 计数器）

**问题**：用户说"开始面试"后，第一轮面试结束，用户回答问题时 query 里不再含"面试"关键词，状态机就不认识了，面试上下文丢失——每次输入都重新判断路由，面试模拟"记不住自己正在面试"。

**方案**：
- `SessionMemory` 新增两个字段：`interview_mode`（当前面试模式）、`interview_round`（已完成轮数）；`to_dict`/`from_dict` 做旧数据兼容（Redis 里没有这两个字段的旧会话能正常加载）
- `agent_state.py` 新增**规则 -1**：`memory.interview_mode` 非 None 时（正在面试中），除非用户明确喊停，否则始终路由到 `interview`；新增 `_query_mentions_end_interview()` 检测"结束面试/停止面试/不面试了"等
- 关键修复：`_is_followup` 在面试进行中时**不短路**——否则用户回答会被误判为追问直接走 Synthesize，跳过 interview
- `jobpilot_agent.py`：
  - `_store_result` 在 interview 后递增 `interview_round`
  - interview 的 action_input 注入 `round_number` + `conversation_history`
  - `_clear_interview_if_requested` 在用户喊停时清除面试状态
- `interview_tool.py`：按轮数生成指令——第 1 轮暖场、2-5 轮追问、第 6 轮给整体评价（技术深度/表达清晰度 1-5 星 + 改进建议）

### 二、扫描件检测

- `/upload` 端点：提取文本为空时返回 422 + 明确提示"这像是扫描版/图片型 PDF，无法直接提取文字。请上传可编辑的 PDF / DOCX，或直接粘贴简历文字"
- 前端 `uploadFile` 解析后端 `detail` 字段展示具体错误；`handleUpload` 用 toast 提示 + 重置文件选择器（允许重选同一文件）

### 三、边角清理

- ChatBubble 保存后清空 manual 输入值（修复"下次保存时残留旧数据"）
- `useApplications.fetchApps` 抛出错误，App.vue 所有调用点 catch 后用 toast 展示——`appsError` 这个一直暴露但从未被消费的字段终于用上了

## 今日收获

1. **多轮对话的状态要显式建模**：面试"记不住自己在面试中"的本质，是状态只存在于隐式的对话历史里，没有显式的状态字段。加一个 `interview_mode` 字段 + 状态机规则，问题就解决了。这和之前"把状态机从 prompt 迁移到代码"是同一个思想——**确定性状态要由代码保证，而不是靠 LLM 从对话里猜**。

2. **状态机的插入式扩展**：新增 interview 多轮能力，只改了四个地方（SessionMemory 字段、agent_state 路由规则、jobpilot_agent 状态更新、interview_tool 指令生成），没有动已有 resume/jd/match 的逻辑。这正是代码状态机设计的好处——之前开发日志里就写过"新增 Tool 只需改四个地方"，这次验证了它。

3. **错误信息要具体、可行动**：扫描件检测不是简单返回"解析失败"，而是告诉用户"为什么失败"（扫描版无文本层）+ "怎么办"（换可编辑文件或粘贴文字）。好的错误提示是"引导下一步"，不是"报一个状态码"。

4. **暴露但未消费的变量是死代码**：`appsError` 从 useApplications 一开始就返回，但从来没被展示——直到今天 fetchApps 抛出错误由 toast 接管，它才真正起作用。review 时要注意：一个变量被 return 了不代表它被用了。

## 下一步

- Phase 12：RAG 检索管线（bge-small-zh + Chroma + Hybrid Search + RRF + Reranker + SearchTool）
- ⚠️ 开工前先解决模型下载源问题（bge 模型数百 MB，HuggingFace 国内需镜像）
- Phase 13：MCP 协议接入
- Phase 14：LangGraph 手写图版（1-2 天，基础设施已齐）
- Phase 15：上线收尾（云部署 + 安全 + 文档定稿）

# Day 27：数据库迁移 + 简历库 + 用户画像 + Agent 主线逻辑修复

> 日期：2026-08-15

## 完成内容

### 一、Alembic 数据库迁移地基

- `requirements.txt` 加 `alembic>=1.13`
- 手写 `alembic.ini` + `alembic/env.py`（复用项目 DATABASE_URL + Base，`render_as_batch` 适配 SQLite）
- `alembic/script.py.mako` 迁移模板
- 基线迁移 `0001_baseline`（标记现有 users/applications）
- 新增表迁移 `0002_resume_profile`（resumes + user_profiles）

### 二、简历库（多简历管理）

- `models/resume.py`：Resume 模型（user_id、name、content、is_default）
- `schemas/resume_library.py` + `repositories/resume_repo.py`（CRUD + 默认简历逻辑）
- 4 个端点：POST/GET/PUT/DELETE `/resumes`
- 前端：`useResumes.js` composable + InputPanel 里"💾 存库"按钮 + "📂 简历库"下拉切换

### 三、用户画像（跨会话长期记忆）

- `models/user_profile.py`：UserProfile 模型（tech_stack、target_role、target_companies、education、experience_summary）
- `schemas/user_profile.py` + `repositories/user_profile_repo.py`（get_or_create 惰性创建）
- 2 个端点：GET/PUT `/profile`
- 前端：`useProfile.js` composable + ProfileModal 弹窗（点侧边栏用户名打开）
- **Agent 接入**：main.py 两个 agent 端点读画像 → 注入 prompt（chat.md / synthesize.md 加 `{{user_profile}}` 占位符）

### 四、Agent 主线逻辑修复（遍历发现的核心 bug）

**问题 1：换新简历/JD 后无法重新分析**
- 根因：状态机用"是否已有分析结果"（resume_done）判断，没考虑"本次带了新内容"
- 修复：execute/execute_stream 开头检测传入 resume/jd 与 memory 缓存是否不同，不同则清除旧分析结果

**问题 2：单工具分析后走 chat 而非出正式报告**
- 根因：单分析简历后，状态机第二轮返回 `["chat"]`，走了闲聊
- 修复：工具执行后判断——单工具（resume/jd）且用户只带一种内容时，直接 synthesize 出报告

**问题 3：Planner 返回的 action 未校验**
- 根因：LLM 可能返回 allowed 之外的 action（如未分析就 match）
- 修复：同步+流式都加校验，越界则降级为直接 synthesize

**问题 4：user_profile 被持久化到 Redis**
- 修复：`to_dict()` 排除 user_profile——画像属于 SQLite 长期记忆，不走 Redis 会话存储

**问题 5（前一轮修复）：简历正文污染意图判断**
- 根因：main.py 把简历全文拼进 query，简历里的"期望岗位"等词命中了 JD 关键词
- 修复：resume/jd 单独传，意图判断只看纯 query

## 今日收获

1. **意图判断的输入必须和内容数据分离**：判断"用户想干什么"只能看用户的原始指令，不能看要处理的数据。之前把简历拼进 query，简历里"期望岗位"污染了 JD 意图判断——这是架构层面的错误，不是 bug 层面的。

2. **缓存失效是 Agent 状态的经典难题**：状态机用"是否已有分析结果"做判断，但"新输入"应该使"旧结果"失效。任何带缓存的系统都要回答一个问题——什么条件下缓存失效？这里是"新简历内容 ≠ 旧简历内容"。

3. **单工具执行后要直接收敛**：分析完一个工具，如果任务已经完成，就应该 synthesize 出结果，而不是再走一轮状态机。否则会落到 chat 分支，输出和用户预期不符的闲聊。

4. **LLM 输出不可信，代码要兜底**：Planner 是 LLM，可能返回状态机不允许的 action。代码层必须校验"LLM 的决策是否在合法范围内"，越界就降级——这正是"代码状态机"存在的意义：规则由代码保证，LLM 只做选择。

5. **序列化边界要清晰**：哪些数据属于 Redis 会话记忆（短期、会过期），哪些属于 SQLite 长期记忆（跨会话、持久），要明确区分。user_profile 属于后者，不该进 Redis 的 to_dict。

## 下一步

- 上下文压缩（摘要策略，成本低，补叙事）
- 前端简历库/画像的体验打磨（按需）
- Phase 12：RAG 检索管线
- Phase 13：MCP 协议接入
- Phase 14：LangGraph 手写图版
- Phase 15：上线收尾

# Day 28：上下文压缩（对话摘要）

> 日期：2026-08-15

## 完成内容

### 上下文压缩（解决长对话失忆）

**问题**：之前 TokenBudget 只有"纯截断"——对话超过 8 条时，早期消息被直接丢弃，Agent 会"失忆"，完全不记得之前聊过什么。

**方案**：摘要压缩策略——早期对话用 LLM 压缩成一段要点，替代直接丢弃。

### 新增

- `prompts/templates/summarize.md` — 摘要 prompt（第三人称、150 字内、只输出摘要本身）
- `memory/conversation_summarizer.py` — `ConversationSummarizer`（LLM 压缩对话文本，失败降级返回空）

### 修改

- `session_memory.py` — 加 `summary` 字段（持久化缓存，避免每次重新压缩）
- `token_budget.py` — 加 `fit_text()` 方法（纯文本 token 级截断，用于"摘要+原文"混合文本）
- `jobpilot_agent.py` — `_build_conversation_history` 重写，接入摘要压缩

### 核心策略

```
消息数 ≤ 8 条 → 全部原文，token 截断（和之前一样）
消息数 > 8 条 → 早期消息 LLM 压缩成摘要（缓存）+ 最近 4 条保留原文
```

**四个设计要点**：

1. **摘要缓存**：`memory.summary` 存一次后复用，不会每次请求都重新压缩（省 token）
2. **近期原文优先**：最近 4 条保留原文，近期细节对当前对话最重要
3. **失败降级**：LLM 摘要失败返回空，退化成纯截断（不阻塞主流程）
4. **两层截断**：语义层压缩（摘要）+ token 层截断（fit_text 兜底）

## 今日收获

1. **压缩 vs 截断的本质区别**：截断是"直接丢弃"，压缩是"保留要点"。长对话时截断会导致失忆，压缩让 Agent 仍然"记得大概聊了什么"——信息有损但核心保留。

2. **摘要要缓存，不能每次重新压**：如果每次请求都重新调用 LLM 压缩全部历史，成本会随对话长度线性增长。缓存摘要后，只在首次超阈值时压缩一次，后续复用——这是压缩策略能落地的关键。

3. **近期原文 + 早期摘要的混合**：不需要压缩全部历史——近期对话细节对当前问题最重要，保留原文；早期对话只需要"要点"，压缩成摘要。这个"分界"（KEEP_RECENT = 4）是工程权衡，可配置。

4. **失败降级是 LLM 功能的标配**：摘要依赖 LLM，可能失败（网络、超时、限流）。失败时必须降级到"纯截断"而非让整个 Agent 崩溃——任何依赖 LLM 的辅助功能都要有 non-LLM 的兜底路径。

## 记忆系统叙事完整了

现在三层记忆齐全：

- **短期记忆**：Redis 会话（24h TTL，优雅降级到内存）
- **长期记忆**：SQLite 用户画像（跨会话持久化）
- **记忆压缩**：早期对话 LLM 摘要（解决长对话失忆）

面试时可以讲："我的记忆系统分三层——会话级用 Redis 存近期对话，跨会话用 SQLite 存用户画像，长对话用摘要压缩控制上下文长度。这三层分别解决'记不住'、'换个会话就忘'、'聊太久失忆'三个不同的问题。"

## 下一步

- 前端简历库/画像的体验打磨（按需）
- Phase 12：RAG 检索管线（bge-small-zh + Chroma + Hybrid Search + RRF + Reranker + SearchTool）
- Phase 13：MCP 协议接入
- Phase 14：LangGraph 手写图版
- Phase 15：上线收尾

# Day 29：RAG 检索增强生成（多岗位知识库 + 混合检索 + 来源溯源）

> 日期：2026-08-15

## 完成内容

### 技术选型的两个关键决策

**1. Embedding 用千问 API 而非本地 bge 模型**
- 原计划：bge-small-zh-v1.5 本地推理（几百 MB，需解决 HuggingFace 国内下载源）
- 实际选择：通义千问 text-embedding-v3 API
- 理由：DeepSeek 官方不支持 embedding 接口（查证 GitHub issue）；千问提供 OpenAI 兼容的 embedding 接口，直接复用项目已有的 OpenAI SDK，零下载、零新依赖

**2. 向量存储用纯 Python 而非 Chroma**
- 原计划：Chroma 向量数据库
- 实际选择：纯 Python 余弦相似度 + JSON 持久化
- 理由：知识库规模小（几十篇文档），专用向量数据库是过度设计；避免 chromadb 重依赖和 Docker 环境兼容问题；符合项目"自建"调性

### 实现的模块

- `rag/embedding.py` — 千问 embedding 封装（text_type 区分 query/document，非对称检索）
- `rag/vector_store.py` — 纯 Python 向量存储（余弦相似度 + JSON 持久化 + 幂等写入）
- `rag/hybrid_searcher.py` — BM25 + 向量 + RRF 融合（基于排名融合，跨检索器可比）
- `rag/rag_pipeline.py` — 统一入口（embedding + 存储 + 检索）
- `rag/knowledge_docs.py` — 知识库数据（23 篇，覆盖 7 个方向）
- `rag/build_knowledge_base.py` — 知识库构建脚本
- `tools/search_tool.py` — SearchTool，注册进 ToolRegistry

### 知识库内容（23 篇，覆盖 7 个岗位方向）

| 方向 | 篇数 | 覆盖 |
|------|------|------|
| 后端 | 7 | HTTP/HTTPS、数据库索引与 MVCC、缓存三兄弟、Redis 持久化与分布式锁、进程线程与 GIL、系统设计、Python 高频 |
| AI Agent | 5 | ReAct、LangChain、RAG、LLM 工程化、SSE 流式 |
| 前端 | 4 | JS 核心、Vue、浏览器与跨域、性能优化 |
| 算法 | 3 | 高频题型、复杂度、DP 与图 |
| 产品 | 2 | 产品思维、案例分析 |
| 测试 | 2 | 用例设计、自动化 |
| 求职通用 | 2 | 简历撰写、行为面试 |

每篇都是"定义 + 要点 + 追问点 + 易错点"的完整结构，能独立回答一个面试问题。

### 来源溯源（代码强制，不依赖 LLM）

- 检索结果用 `【KB来源:标题】` 标记
- Agent 端代码用正则提取来源标题存 `memory.search_sources`
- synthesize 时代码在回答开头强制加 `> 📚 参考来源：xxx、xxx`

**关键教训**：最初靠 prompt 要求 LLM 标注来源，结果 LLM 自由发挥时把标注淹没了。改成代码强制后 100% 生效——这是"规则由代码保证，LLM 只负责内容"的又一例证。

### 踩坑

1. **知识库数据里中文/英文引号冲突**：Python 字符串用 `"` 包裹时，内容里出现 `"..."` 引述会提前闭合字符串，报 SyntaxError。反复修了三轮才清干净。教训：写长字符串内容时，引述一律用 `「」`。

2. **同步版有、流式版漏的 search 收敛逻辑**：search 工具执行后，同步版有"直接 synthesize"的收尾，流式版漏了，导致循环到 max_steps 报"任务未完成"。同步/流式两套代码路径必须严格对齐——这是老毛病，会话保存、画像注入、action 校验都踩过。

## 今日收获

1. **RAG 的幻觉风险来自"检索太薄 + LLM 补全"**：知识库内容太薄，LLM 拿到几句 seed 就自由扩写，你无法区分哪些是知识库说的、哪些是模型编的。解法：知识库加厚到每条能独立回答问题，检索结果本身就够用。

2. **来源标注是 RAG 的生命线，必须代码强制**：RAG 区别于纯 LLM 的关键是"可溯源"。但靠 prompt 要求 LLM 标注不可靠（LLM 会不听话），必须代码强制——提取来源、拼接标注，都不经过 LLM。

3. **Hybrid Search 的价值在文档多时才体现**：向量检索（语义）+ BM25（精确关键词）互补，RRF 基于排名融合。但知识库只有 6 篇时这个优势完全体现不出来，文档多了才有意义。

4. **技术选型要务实**：原计划的 bge 本地模型 + Chroma，实际用千问 API + 纯 Python 存储——绕开了模型下载坑和重依赖，零新依赖。选型不是"哪个更高级"，是"哪个更适合当前场景"。

## 下一步

- Phase 13：MCP 协议接入
- Phase 14：LangGraph 手写图版（1-2 天）
- Phase 15：上线收尾（云部署 + 安全 + 文档定稿）

# Day 30：全面代码 Review + Bug 修复 + 前端校验收窄

> 日期：2026-08-15

## 完成内容

### 全面代码 Review（派 agent 系统性审查）

对整个项目做了一次回归审查，重点放在最近改动最多的部分：Agent 主线逻辑、状态机、RAG 模块、记忆系统、前端多会话、main.py 端点。共发现 15 个问题（2 严重、7 中等、6 轻微）。

### 已修复的 11 个问题

| # | 问题 | 严重度 |
|---|------|--------|
| 1 | `LLMServiceError` 未导入，`/agent/run` 的 502 分支是死代码，LLM 故障被误报为 500 | 🔴 |
| 2 | 匹配意图完全无法识别——"匹配"不在任何关键词列表，多轮场景 match 永远触发不了 | 🔴 |
| 5 | 上传简历/JD 但 query 未提及时，面试不先分析（基于 query 关键词而非 memory 原文判断） | 🟡 |
| 7 | ChatBubble 手动兜底保存损坏——提取不到公司名时一闪而过，直接存"待填写" | 🟡 |
| 4 | `fit_text` 截断方向反了——丢掉近期原文、保留摘要，与"近期优先"设计相反 | 🟡 |
| 8 | 错误响应用 `message` 字段，前端只读 `detail`，错误信息丢失 | 🟡 |
| 11 | VectorStore 加载时无结构校验（合法 JSON 但非 list 会崩） | 🟢 |
| 12 | SessionMemory.from_dict 对未知字段无容错 | 🟢 |
| 13 | 登出后状态轮询未停止 | 🟢 |
| 14 | 切换/删除会话未重置 loading（生成中切换会导致输入框禁用） | 🟢 |
| — | 前端发送前校验过宽——匹配类追问误报"未上传简历/JD" | 🟡 |

### 前端校验逻辑收窄（两次迭代）

**第一版问题**：校验用"query 提到简历/匹配"判断，导致多轮场景下用户清空输入框后问匹配，被误报"未上传简历/JD"（但后端有缓存，回答正常）。

**第二版问题**：正则 `分析.*岗位` 把"分析一下我和这个岗位匹配吗"误判成"分析 JD"。

**最终方案**：
1. 先判断是否匹配类请求（匹配/契合/适合/对比/差距），是则跳过所有提醒（依赖后端缓存）
2. 只有"首次分析"请求（明确说分析简历/JD）且输入框确实为空才提醒

### 关键发现：问题 2（匹配意图无法识别）

这是最严重的 bug。之前测试"都成功了"是因为把简历+JD+匹配放在**同一条 query** 里（"分析简历和JD并匹配"），那条 query 同时命中简历和JD关键词，绕过了问题。但真实的多轮场景（一步步来：先分析简历 → 再分析 JD → 最后单独说"帮我匹配"）是彻底断的——"匹配"这个词不在任何关键词列表里。

修复：新增 `_query_mentions_match()`，状态机规则 3 改用 `wants_match`，`_is_followup` 里对 `wants_match` 返回 False。

## 待后续处理（3 个，不阻塞）

- **摘要缓存过期**：`memory.summary` 只算一次，后续对话增长的早期消息被静默丢弃，需要增量摘要
- **401 刷新重试消息重复**：sendMessage 递归重试会重复 push 消息，需要重构请求逻辑
- **关键词过宽**：`_query_mentions_resume` 含"求职"、`_query_mentions_knowledge` 含"方法/技巧"等过宽词，路由可能误判

## 今日收获

1. **多轮场景的测试盲区**：测试时"简历+JD+匹配"放一条 query 里，掩盖了"匹配意图无法单独识别"的 bug。真实的 Agent 是多轮交互的，测试必须覆盖"分步提问"的场景，而不是只测"一次性全给"。

2. **前端校验要考虑"缓存的合理存在"**：后端 memory 缓存了分析结果，多轮追问时输入框为空是正常的。校验不能只看"输入框有没有内容"，还要看"这次请求是否依赖缓存"。

3. **正则误判的连锁反应**：`分析.*岗位` 这个正则在"分析一下我和这个岗位匹配吗"上误判——因为"分析"和"岗位"中间隔了"我和这个"。正则匹配这种自然语言要特别小心，宁可收窄也不要过宽。

4. **systematic review 的价值**：这轮派 agent 系统性审查，比之前零散的"边做边看"找到了更多问题（15 个）。尤其是同步/流式对齐这种跨方法的问题，逐行对比才能发现。

## 下一步

- 前端体验细节打磨（loading/空态/交互一致性）
- 工程质量补强（断言式 pytest、vitest、死代码清理）
- 文档统一整理（roadmap/changelog/README 对齐）
- Phase 13：MCP 协议接入
- Phase 14：LangGraph 手写图版
- Phase 15：上线收尾

# Day 31：工程质量补强（后端 pytest + 前端 vitest + 前端系统打磨）

> 日期：2026-08-16

## 完成内容

### 一、后端断言式 pytest（47 个测试全部通过）

之前只有 test_llm_retry.py 是断言式，其余多是 print 诊断脚本。现在补上核心逻辑的规范测试：

- **test_agent_state.py**（15 个）——状态机关键词检测 + 路由规则。覆盖之前踩过的坑：`_query_mentions_jd` 空函数体、NameError、匹配意图无法识别、关键词收窄后的验证
- **test_token_budget.py**（6 个）——近期优先截断、fit_text 保留尾部、token 估算
- **test_session_memory_serialization.py**（5 个）——序列化往返、user_profile 不持久化、旧数据兼容、未知字段容错
- **test_rag_search.py**（6 个）——余弦相似度、向量存储、BM25、混合检索
- 新增 pytest.ini 配置

### 二、前端 vitest（18 个测试全部通过）

- package.json 加 vitest 依赖 + test script
- **application.test.js**（13 个）——parseScore/scoreTier/relativeDate 纯函数
- **useToast.test.js**（5 个）——toast 队列逻辑
- vitest.config.js（node 环境）

### 三、前端系统性打磨（按顶尖前端标准）

1. **设计 Token 系统**：新建 styles/tokens.css，统一颜色/间距/字号/圆角/阴影/焦点环。之前同一语义出现 4-5 种近似值（浅蓝底 4 种、浅灰背景 5 种、状态色 3 套）
2. **可访问性**：JobCard/ConversationSidebar 加 role/tabindex/键盘操作、modal 加 Esc 关闭、toast/status/thinkchain 加 aria-live
3. **三态覆盖**：JobBoard error 态（修复 appsError 死代码）、useResumes error 态
4. **响应式**：侧边栏窄屏收窄成图标栏
5. **安全**：移除明文 token console.log、logout 清除 agent_mode、轮询后台暂停
6. **关于页面**：AboutView（项目介绍、功能、使用指南、技术架构）
7. **Agent 版本切换**：checkbox 改下拉框
8. **画像入口**：侧边栏用户名旁加显式"画像"按钮

## 踩坑记录

1. **手动 pip install 进容器是临时的**：容器一 `--build` 重建，手动装的 pytest 就没了。依赖必须进 requirements.txt，这是 Docker 开发的基本规矩。

2. **测试文件要重新 build 才进镜像**：`docker compose exec` 用的是已构建的镜像，宿主机新写的测试文件不 `--build` 根本看不到。

3. **旧测试失败 ≠ 代码 bug**：3 个旧测试失败是因为代码进步了（单工具收尾替代死循环、自定义异常替代原始异常、模板改名），测试没跟上。这提醒我们：改代码时同步更新测试。

4. **测试真的能抓 bug**：useToast 的 success/error/info 不返回 id，导致调用方无法 dismiss 特定 toast——这个隐患是写测试时才发现的。

5. **npm 的 vulnerabilities 提示**：vite/marked 传递依赖有 7 个漏洞，本地开发无碍，上线前要 npm audit fix。

## 今日收获

1. **测试的价值在于"抓真问题"**：这一轮测试不是走过场，真的抓到了 2 个问题（3 个过时旧测试暴露的同步缺失、useToast 不返回 id 的 API 缺陷）。写测试的过程就是重新审视代码的过程。

2. **纯函数是最值得测的**：application.js、TokenBudget、状态机的关键词检测这些纯函数，测试成本最低、收益最高。它们逻辑密集、容易出边界 bug（比如 token 估算的算术、日期解析）。

3. **Docker 环境的依赖和代码都要进镜像**：宿主机改的代码、装的包，都必须通过 build 或 requirements 进镜像才生效。这是容器化开发的思维转变。

## 下一步

- 前端体验细节打磨（继续，可选）
- 文档统一整理（roadmap/changelog/README 对齐）
- Phase 13：MCP 协议接入
- ~~Phase 14：LangGraph 手写图版~~（已决定不做，见 roadmap）
- Phase 15：上线收尾（云部署 + 安全 + npm audit fix）

> 补充决策（2026-08-16）：LangGraph 手写图版重构决定不做。理由：已有手写 ReAct + 代码状态机 + LangGraph prebuilt 版，再手写 StateGraph 只是换成框架语法、无新增量。手写 ReAct 已是项目最强叙事点。

# Day 32：评测体系重构（确定性指标替代 LLM 打分的噪声）

> 日期：2026-08-17

## 完成内容

### 一、发现并修复 RAG 持久化 bug

**根因**：`rag_pipeline.py` 的 `STORE_PATH` 用了 `parents[3]`，算错一层目录，导致知识库数据 `rag_store.json` 落在容器内 `/app/data/`（没被 docker 卷挂载），而 SQLite 在 `/app/backend/data/`（挂载了 `sqlite_data` 卷）。结果每次 `docker compose --build` 重建镜像，知识库数据全部丢失。

**修复**：`parents[3]` 改为 `parents[2]`，统一到 `backend/data/`，和 database.py 的 DATA_DIR 一致，被 docker 卷持久化。

### 二、评测体系重构：从 LLM 打分到确定性指标

**背景**：原来的 faithfulness/recall/relevancy 用 LLM 判定"陈述是否被来源支持"，发现两个问题：
1. LLM 判定噪声大——同一个回答两次判定结果不同，数据不可复现
2. 评测对象错位——faithfulness 该测 RAG 知识库问答，不该测简历分析（分析性回答天然含评价/建议，全被判为"幻觉"）

**重构方案**：
1. 新建 `rag_test_cases.py`：知识库问答用例（5 个，sources 用知识库文档原文）
2. 新建 `deterministic_metrics.py`：三个不依赖 LLM 的确定性指标
   - 检索触发率：状态机是否路由到 search（代码判定，确定）
   - 检索命中率：search 是否返回非空（代码判定，确定）
   - 来源标注率：回答是否带「参考来源」（代码强制，确定）
3. 修复知识库路由的触发边界：`_query_mentions_knowledge` 加"什么是"（之前只有"是什么"），补上中文语序变体

### 三、最终评测结果（可复现）

| 指标 | 结果 |
|------|------|
| 检索触发率 | 5/5 = 100% |
| 检索命中率 | 5/5 = 100% |
| 来源标注率 | 5/5 = 100% |

## 今日收获

1. **LLM 打分的评测指标有固有噪声**：faithfulness 用 LLM 判定"陈述是否被支持"，同一个回答两次判定可能不同。这对简历数据是致命的——面试官问"怎么测的"，答不出稳定复现路径。确定性指标（检查代码行为）反而更可信。

2. **评测对象要和指标匹配**：faithfulness 测"编造"，适合 RAG 知识库问答（有明确 sources）；不适合简历分析（分析性回答天然含评价建议）。用错对象会导致分数系统性偏低，误导判断。

3. **路径计算错误是 Docker 数据丢失的经典根因**：`parents[N]` 少算/多算一层，数据就落到没挂载卷的目录，`--build` 全丢。两个 data 目录（SQLite vs RAG）不一致，就是这类 bug 的信号。

4. **中文语序是关键词匹配的隐形坑**：「是什么」和「什么是」两种语序，只覆盖一种就会漏匹配。测试用例要覆盖语序变体。

## 下一步

- 文档统一整理（roadmap/changelog/README 对齐，含评测结果）
- Phase 13：MCP 协议接入
- Phase 15：上线收尾（云部署 + 安全 + npm audit fix）


