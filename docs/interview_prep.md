# JobPilot 面试准备手册（深度版）

> 基于项目真实实现整理，深入到底层原理、代码细节、连环追问应对。
> 每个核心问题按「表层回答 → 深入原理 → 代码细节 → 追问应对」四层组织。
> 当前版本 v0.9.4（RAG 补全了分块、重排、真·检索质量评测）。

---

## 一、项目整体叙事

### Q：用 2 分钟介绍你的项目

**回答：**

我做的是 AI 求职助手 JobPilot，后端 FastAPI + Vue3，接入 DeepSeek。核心是从零手写的 ReAct Agent——Planner 决策器、代码状态机、Tool 注册中心、SessionMemory 记忆管理。

我特意先手写、不用 LangChain，因为想理解 Agent 底层：Reason→Act→Observe 循环的本质、LLM 决策为什么不稳定、以及如何把状态机从 prompt 迁移到代码。手写稳定后再做 LangChain 版本做同输入同输出对比。

技术上三层记忆（Redis 会话 + SQLite 画像 + 摘要压缩）、RAG 混合检索（非对称 embedding + BM25 + RRF 融合 + 来源溯源 + 分块/重排分层）、自建 24 条带标注评测集（Recall@k/MRR/NDCG 对比三种检索配置）。工程上有 107 后端测试 + 18 前端测试、Alembic 迁移、Docker 三服务、JWT 双 token。

### Q：这个项目最大的技术亮点？

**回答：**

"把状态机从 prompt 迁移到代码"这个决策，它体现了一个完整的工程思考闭环：

**发现问题** → 最初用 prompt 描述状态机规则，发现 LLM 不完全遵守，出现死循环（反复执行同一 action）。

**分析根因** → prompt 是"请求 LLM 遵守规则"，本质是软约束。LLM 是概率模型，不会百分百听话。

**架构决策** → 把规则下沉为确定性 Python 代码：代码计算"允许哪些 action"，LLM 只在合法集合内做语义选择。

**验证正确性** → 这本质是 constrained generation 思想，和 LangGraph 的 conditional_edge 是同一原理。所以我理解的不只是"怎么实现"，而是"这个设计在工业界的对应概念"。

这个闭环——发现问题、分析本质、架构决策、关联业界概念——才是面试官想看到的深度。

---

## 二、Agent 核心（深度）

### Q1：ReAct 模式是什么？为什么需要它？

**表层回答：**

ReAct = Reasoning + Acting，LLM Agent 的核心循环：思考 → 行动 → 观察 → 再思考，直到得出答案。

**深入原理：**

为什么需要 ReAct？要理解它解决的两个极端：

1. **纯推理（Chain-of-Thought）**：让 LLM 一步步推理，但不调用工具。问题是 LLM 只能基于训练数据推理，**会编造事实**——问"今天北京的天气"，它没有实时数据，只能瞎编。

2. **纯行动（只调工具）**：让 LLM 调工具，但缺乏推理规划——不知道"该调哪个工具、按什么顺序"。

ReAct 把两者结合：**推理指导行动，行动结果反哺推理**。推理决定"下一步调什么工具"，工具返回的观察结果作为新信息进入下一轮推理。这就是"边想边做"。

**代码细节（我的实现）：**

```
JobPilotAgent.execute(query):
  for step in range(1, max_steps+1):        # 防死循环
    allowed = AgentStateMachine.compute_allowed_actions(memory, query)  # 代码状态机
    plan = planner.think(query, tools, memory)   # LLM 从 allowed 里选 action
    result = tool.run(**plan.action_input)       # 执行工具
    memory = store_result(memory, action, result) # 观察结果存记忆
    if plan.action == "finish" or 单工具完成:
      return synthesize(memory)                   # 基于记忆生成最终答案
```

**追问应对：**

- **"ReAct 和 function calling 有什么区别？"** → function calling 是模型直接输出要调用的函数和参数，思考过程是隐式的；ReAct 是显式的思考-行动循环，每一步的思考（thought）是可见的。ReAct 更可控、可解释，function calling 更高效。我的项目两者都用了——Planner 输出结构化 Plan（类似 function calling），但外层是显式的 ReAct 循环。

- **"max_steps 为什么是 6？"** → 6 是我的场景（最多 resume→jd→match 三个工具 + 若干轮）够用的上限，防止异常时无限循环烧 token。实际正常流程 1-4 步就结束了。

### Q2：为什么状态机从 prompt 迁移到代码？

**表层回答：**

因为 prompt 约束 LLM 不可靠，会死循环。改成代码状态机后，规则由确定性代码保证。

**深入原理：**

这个决策的核心是**可靠性 vs 灵活性的权衡**：

| 维度 | prompt 状态机 | 代码状态机 |
|------|--------------|-----------|
| 可靠性 | 低（LLM 可能不遵守） | 高（确定性输出） |
| 灵活性 | 高（LLM 自由发挥） | 低（规则固定） |
| Token 成本 | 高（规则每次注入 prompt） | 零（代码不消耗 token） |
| 可测试性 | 难（依赖 LLM） | 易（纯函数） |

**我的方案是取两者之长**：代码状态机负责"规则"（确定性、零 token），LLM 负责"语义"（灵活性）。这是**分层的 constrained generation**——不是完全限制 LLM，而是限制它的选择范围，保留它的语义理解能力。

**代码细节：**

```
compute_allowed_actions(memory, query) -> list[str]:
  # 规则 -1：面试进行中，持续 interview（除非喊停）
  # 规则 0.5：问"是什么/为什么/原理" → search
  # 规则 0：面试请求，有未分析的简历/JD 先分析
  # 规则 1：问简历 且 未分析 → resume
  # 规则 2：问 JD 且 未分析 → jd
  # 规则 3：简历+JD 都分析完 且 问匹配 → match
  # 规则 4/5：无意图 → chat
```

每个规则的"未分析"判断（`resume_done = memory.resume_analysis is not None`）是防死循环的关键——已完成的 action 不可重复执行。

**追问应对：**

- **"这和 LangGraph 的 conditional_edge 什么关系？"** → 本质相同。LangGraph 的 `conditional_edge("planner", lambda state: "match" if state.resume_done else "resume")` 就是我这个 `if resume_done and ... : allowed.append("match")` 的框架化表达。我手写就是为了理解这个底层逻辑，未来迁移 LangGraph 是 1:1 映射。

- **"关键词检测会不会误判？"** → 会，这是有意的权衡。关键词匹配是确定性的、零成本、零延迟；LLM 语义判断更准但每次都要调 API。误判代价低（最多多执行一次工具，或走了 chat 而非 search），所以选便宜的方案。如果未来要更精准，可以加轻量分类器。

### Q3：LLM 决策不稳定的根源是什么？你做了哪些兜底？

**深入原理：**

LLM 决策不稳定有三个根源：

1. **概率采样**：LLM 输出是概率分布采样，同一输入可能不同输出（temperature 越高越明显）
2. **格式不遵守**：让它输出 JSON，可能输出带 ```json 包裹的、或前后加解释的话
3. **语义越界**：让它从 allowed 里选，可能选 allowed 之外的 action

**我的三层兜底：**

**第一层：JSON 解析容错**（Planner._extract_json）：
```
1. 直接 json.loads(text)
2. 去掉 ```json ... ``` 包裹再解析
3. 正则提取第一个 {...} 块再解析
```
三个都失败才抛 LLMResponseError。因为 LLM 经常在 JSON 前后加解释性文字，或加代码块标记。

**第二层：action 越界校验**（jobpilot_agent 里）：
```
if plan.action not in allowed and plan.action != "finish":
    降级为直接 synthesize  # 不执行非法工具
```
LLM 返回了状态机不允许的 action（如未分析简历就 match），直接降级，不执行。

**第三层：重试 + 超时**（LLMService）：
- 指数退避重试（最多 3 次）
- 超时设置（60 秒，防止无限挂起）

**追问应对：**

- **"为什么不用结构化输出（function calling 的 JSON mode）？"** → DeepSeek 的 JSON mode 能保证输出是合法 JSON，但保证不了"内容语义正确"（可能返回合法 JSON 但 action 是错的）。所以 JSON mode 解决格式问题，我的越界校验解决语义问题，两者互补。

### Q4：手写 Agent 和 LangChain 的关系？

**表层回答：**

先手写理解本质，再用 LangChain 做同输入同输出对比，验证理解一致。

**深入原理（关键对应关系）：**

| 手写实现 | LangChain 对应 | 底层本质 |
|----------|---------------|---------|
| BaseTool | @tool 装饰器 | 给 LLM 描述工具名/参数 |
| Planner.think | function calling | LLM 输出结构化决策 |
| execute() 的 for 循环 | AgentExecutor | 循环：决策→执行→观察 |
| AgentStateMachine | conditional_edge | 条件路由 |
| SessionMemory | ConversationBufferMemory | 对话上下文存储 |

**追问应对：**

- **"AgentExecutor 内部怎么工作的？"** → 就是我的 execute() 的 for 循环：调 LLM 得到动作 → 执行工具 → 把结果追加到消息列表 → 再调 LLM，直到返回 finish。理解了这个，任何 Agent 框架都是语法糖。

- **"为什么不直接用 LangGraph？"** → LangGraph 的价值在复杂状态机、断点续跑（checkpointer）、human-in-the-loop。我的求职 Agent 状态简单，手写状态机够用且更可控。但关键是——我理解了"代码状态机 = conditional_edge"的对应关系，未来迁移 LangGraph 是 1:1 映射，不是重写。

### Q5：流式输出（SSE）的实现细节？

**表层回答：**

SSE 逐 token 推送，比阻塞等待体验好。选 SSE 因为单向推送够用。

**深入原理（完整链路）：**

```
LLMService.chat_stream()          # 调 DeepSeek stream=True，逐 chunk yield
  → JobPilotAgent.execute_stream() # 生成器，yield 事件字典
  → StreamingResponse(event_generator)  # FastAPI 转 SSE
  → 前端 fetch + ReadableStream   # 手动解析 SSE 流
```

**代码细节：**

1. **事件类型**：step_start（含 thought）、step_done、synthesize_chunk（答案片段）、done、error

2. **前端 SSE 解析的 buffer 处理**（这是最容易出 bug 的地方）：
```javascript
buffer += decoder.decode(value, { stream: true })
const parts = buffer.split('\n\n')   // SSE 事件用空行分隔
buffer = parts.pop()                 // 最后一段可能是不完整的事件，留到下次
```
因为网络 chunk 可能在事件中间断开，必须用 buffer 缓存半截事件。

3. **Nginx 配置**：`proxy_buffering off` 是关键——不加这行，Nginx 会缓冲后端响应，攒成一大块才发，流式变成"卡 30 秒后一次性出全文"。

**追问应对：**

- **"为什么流式不做重试？"** → 同步调用可以做重试（用户还没看到结果，重试无感知）。但流式输出时前端已逐字渲染，重试意味着文字突然消失重来，体验比报错更差。所以流式失败直接报错，不重试。

- **"EventSource 为什么不能用？"** → EventSource 只支持 GET，我的端点需要 POST（query/resume/jd 在请求体里），所以用 fetch + ReadableStream 手动解析。

---

## 三、记忆系统（深度）

### Q6：三层记忆架构的完整设计？

**表层回答：**

短期 Redis 会话、长期 SQLite 画像、压缩 LLM 摘要，分别解决三类问题。

**深入原理（为什么是三层，不是一层）：**

记忆问题的本质是**时间尺度不同**：

| 时间尺度 | 问题 | 方案 |
|---------|------|------|
| 秒~分钟（一次会话内） | 跨请求上下文丢失 | Redis 会话（24h TTL） |
| 天~周（跨会话） | 换会话就忘身份 | SQLite 画像（永久） |
| 分钟~小时（长对话内） | 聊太久早期内容丢失 | LLM 摘要压缩 |

单层方案解决不了所有时间尺度：Redis 会话会过期（丢了长期记忆），SQLite 画像不适合存对话（太重），不做压缩长对话会撑爆上下文。

**代码细节：**

**短期记忆（SessionMemory）**——业务记忆和对话记忆分离：
```python
# 业务记忆（工具执行结果，事实）
resume_analysis / jd_analysis / match_result
# 对话记忆（交互历史）
messages: list[dict]
# 面试状态
interview_mode / interview_round
# 检索结果 + 来源
search_result / search_sources
# 摘要 + 进度
summary / summarized_count
```

**长期记忆（UserProfile）**——每次 Agent 执行时从 SQLite 读，注入 prompt：
```
main.py 读画像 → _format_user_profile() → 格式化文本 → 注入 chat/synthesize prompt
```
所以用户换会话，Agent 依然"记得"他的目标岗位/技术栈。

**追问应对：**

- **"你的长期记忆是语义化还是结构化？"** → 当前是结构化（SQLite 字段存技术栈/目标岗位），对这个场景够用。语义化记忆（向量检索相关记忆片段）可以和 RAG 的向量设施复用，是下一步方向。诚实说清边界。

- **"为什么不用 MemGPT 式的重要性评分/遗忘机制？"** → 那是研究型 Agent 的机制，适合记忆量大的场景。我的求职场景记忆量小（一份画像 + 对话），重要性评分和遗忘衰减是过度设计。能说清"什么场景需要什么记忆复杂度"，比堆功能更有判断力。

### Q7：上下文压缩怎么实现？和截断的本质区别？

**表层回答：**

截断是直接丢弃早期消息，压缩是用 LLM 总结成摘要保留要点。

**深入原理：**

**截断的问题**：TokenBudget 从最近往前取，token 用完就把更早的**直接丢弃**。问题是长对话时，早期消息里可能有关键信息（用户提到的求职意向、技术栈），丢弃后 Agent 彻底"失忆"。

**压缩的代价**：LLM 摘要会引入**信息损失**（摘要不如原文完整）和**一次 LLM 调用成本**。所以不能全部压缩，要分层：

**我的两层策略：**
```
消息数 ≤ 8  → 全部原文，token 截断
消息数 > 8  → 早期消息 LLM 摘要 + 最近 4 条原文
```

**代码细节（增量摘要）：**

关键设计是 `summarized_count` 记录"已摘要到第几条"，实现增量：
```python
new_early = early_messages[memory.summarized_count:]  # 只摘要新增的早期消息
if new_early:
    new_summary = summarizer.summarize(new_text)
    memory.summary = f"{memory.summary}\n{new_summary}"  # 追加到已有摘要
    memory.summarized_count = len(early_messages)
```

**追问应对：**

- **"为什么最近 4 条保留原文？"** → 近期对话细节对当前问题最重要（用户刚说的话，上下文强相关）。早期对话只需要"要点"，压缩成摘要。这个分界（4 条）是工程权衡，可配置。

- **"摘要失败怎么办？"** → 降级为纯截断（返回空摘要）。任何依赖 LLM 的辅助功能都要有 non-LLM 的兜底路径，不能因为摘要失败让整个 Agent 崩溃。

### Q8：Redis 优雅降级的完整设计？

**表层回答：**

Redis 不可用 → 内存 dict fallback，核心功能不受影响。

**深入原理（降级链路）：**

```
Redis 连接失败
  → redis_client.get_client() 返回 None（不抛异常）
  → MemoryManager 检测 Redis 不可用 → 用内存 dict
  → RateLimiter 检测 Redis 不可用 → 放行所有请求
  → 应用继续正常服务
```

**设计哲学**：Redis 是"加分项"（持久化、多进程共享、TTL 自动过期），不是"必需品"（核心功能是 Agent 分析，不依赖 Redis 也能跑）。所以 Redis 挂了应该降级而非崩溃——**安全让位可用性**。

**追问应对：**

- **"内存 dict fallback 有什么代价？"** → 重启丢数据、多进程（uvicorn workers > 1）不共享。但这已经是"功能正常"和"完全崩溃"之间的最优选择。生产环境 Redis 本身有高可用方案（主从/哨兵/集群）。

- **"限流器降级为放行，安全怎么办？"** → 这是有意的权衡：限流是"保护成本"（防止 API 费用失控），Redis 挂了如果还限流会导致服务不可用。放行是"宁可被刷也不误杀"。生产环境会用更可靠的限流存储或独立部署。

### Q9：TokenBudget 的分配策略？

**表层回答：**

控制对话历史在 prompt 里占多少 token，近期优先。

**深入原理（分配优先级）：**

```
总预算 8000 token
  ├── reserve(2500) 预留给 system prompt + Planner 规则（不可压缩）
  └── 剩余 5500 给对话历史
        └── 近期优先：从最近的往前取，token 用完就停
```

**为什么 reserve 2500**：system prompt（角色定义）+ Planner 规则是"固定开销"，不可压缩。对话历史是可变的，用剩余预算。

**追问应对：**

- **"为什么不用 tiktoken 精确计数？"** → tiktoken 是 OpenAI 专有编码器，DeepSeek 的 tokenizer 不同。而且对预算控制来说 ±20% 误差不影响截断决策（截断位置差一两条消息无所谓）。中文 1 字符≈1.5 token、英文 1 词≈1.3 token 的粗略估算够用。

- **"TokenBudget 为什么独立成类？"** → 单一职责（LLMService 管调用，TokenBudget 管配额）+ 可测试（纯函数验证截断逻辑）+ 可替换（未来换摘要压缩、滑动窗口策略不动 Agent 代码）。

---

## 四、RAG 检索管线（深度）

### Q10：RAG 的完整链路？每一环为什么这么设计？

**表层回答：**

文档切片 → embedding → 向量库 → 检索 → 生成。我用了千问 embedding + BM25 + RRF 混合检索 + 来源溯源。

**深入原理（逐环拆解）：**

**1. Embedding 为什么用 text_type 区分 query/document？**

这是**非对称检索**（asymmetric retrieval）。query 是"用户想找什么"的简短表达，document 是"完整知识内容"，两者语义角色不同。千问 text-embedding-v3 支持 `text_type=query`（编码查询）和 `text_type=document`（编码文档），用不同方式编码，检索效果更好。这不是可有可无的细节——对称编码（query 和 document 用同一种方式）在语义检索里效果会打折。

**2. 为什么混合检索（向量 + BM25）？**

两个检索器互补：

- **向量检索**：语义匹配强，"后端开发"能匹配"服务端工程师"；但对精确关键词不敏感，搜"Python 3.12"可能返回 Python 3.11 的内容
- **BM25**：精确关键词匹配强；但不懂同义词，搜"服务端工程师"找不到"后端开发"

单一检索器都有盲区，混合才能互补。

**3. RRF 为什么优于加权融合？**

这是最容易追问的点，要讲透。BM25 分数（可能几百上千）和向量相似度（0-1 之间）**尺度完全不同**，加权融合需要大量实验找最佳权重比例。RRF 只看**排名**（rank），不看分数：

```
score(d) = Σ 1/(k + rank_i(d))，k 取 60
```

排名天然跨检索器可比，无需调超参。这是 RAG 领域（RAGAS 等）都验证过的做法。

**代码细节：**

```
HybridSearcher.search(query, query_vector, top_k):
  vector_results = vector_store.search(query_vector, top_k*2)  # 向量检索
  bm25_results = bm25.search(query, top_k*2)                    # BM25
  # RRF 融合
  for rank, r in enumerate(vector_results, 1): rrf_scores[r.id] += 1/(60+rank)
  for rank, (idx,_) in enumerate(bm25_results, 1): rrf_scores[doc_id] += 1/(60+rank)
  # 按 RRF 分数排序取 top_k
```

**追问应对：**

- **"你的 BM25 怎么分词的？"** → 中文按字切分 + 英文按词切分（正则 `[a-zA-Z]+|[一-鿿]`）。这是简化版（没有用 jieba 等分词库），对面试知识点这种短文本够用。能诚实说"简化分词"并说明局限，比吹"用了完整分词"更可信。

- **"为什么向量存储纯 Python，不用 Chroma？"** → 规模匹配：23 篇文档，纯 Python 余弦相似度对几百向量是毫秒级。Chroma 适合万级~十万级，当前是过度设计。接口已抽象（RAGPipeline），规模增长换 Chroma 不改业务代码。

### Q11：RAG 的幻觉问题怎么解决？还有哪些局限？

**表层回答：**

事前接地（基于检索结果生成）+ 来源溯源（代码强制标注）。

**深入原理（诚实说清边界）：**

我的幻觉抑制分三层，但**缺一层**：

| 手段 | 作用 | 是否已做 |
|------|------|---------|
| 事前接地 | Synthesize 基于真实工具产出/检索结果，不从零生成 | ✅ |
| 检索增强 | 知识库问答时检索相关文档喂给 LLM | ✅ |
| 来源溯源 | 代码强制标注，让编造可被发现 | ✅ |
| **事后校验** | 回答生成后逐条验证事实依据 | ❌ 未做 |

**为什么缺"事后校验"**：faithfulness 本质就是事后校验（把回答拆成陈述、逐条验证是否被来源支持）。但我们实测发现 LLM 判定的 faithfulness 噪声大（同一回答两次判定结果不同），所以改成了确定性指标。事后校验如果要做，得用非 LLM 的方式（如关键词匹配），这是下一步方向。

**追问应对（关键，体现深度）：**

- **"你说抑制幻觉，那你的系统能保证不幻觉吗？"** → 不能，我诚实说：我的系统是"事前接地 + 检索 + 可溯源"，但**没有事后校验**。我能保证的是"幻觉可被发现"（来源标注），不是"幻觉不发生"。这种诚实比吹"我解决了幻觉"更可信。

- **"为什么不用 RAGAS 等专业评测框架？"** → 套 RAGAS 只需要 pip install + 5 行代码，但面试官问"faithfulness 怎么算的"，答不出就是调包侠。我自建评测体系是为了理解原理。现在理解清楚了，也知道 LLM 判定评测的局限（噪声大），这是自建的意义。

### Q12：来源标注为什么代码强制，不靠 LLM？

**表层回答：**

LLM 不听话，规则由代码保证。

**深入原理（踩坑证据）：**

最初在 prompt 里要求 LLM 标注来源，实测发现 LLM 自由发挥时会把来源标注**淹没**——它忙着扩写，根本不遵守"标注来源"的指令。

这印证了项目一贯的原则：**规则由代码保证，LLM 只负责内容**。来源标注是"规则"（确定性要求），不该交给 LLM（概率模型）。

**代码细节：**

```
SearchTool.run() 返回 "【KB来源:标题】\n正文"
  → Agent._store_result() 用正则提取标题 → memory.search_sources
  → _synthesize() 代码强制在回答开头加 "📚 参考来源：..."
```

结果：来源标注率 100%（确定性，跑多少次都一样）。

**追问应对：**

- **"这算不算过度工程？"** → 不算，因为溯源是 RAG 的核心价值。RAG 区别于纯 LLM 的关键就是"可核查"——回答哪句话有来源支撑，用户一眼能看到。如果溯源靠 LLM 自觉，它不遵守时 RAG 就退化成普通 LLM 了。

### Q13：分块（Chunking）你是怎么做的？chunk_size / overlap 多少？

**表层回答：**

我的知识库 23 篇、每篇是「一个独立知识点」（定义 + 要点 + 追问 + 易错点，500~1500 字），所以默认「整篇成块」。但分块是抽象成可配置策略的：超长文档自动滑动窗口切块 + 重叠。

**深入原理（什么时候必须切）：**

不是所有文档都该整篇向量化。整篇向量在三种情况下会出问题：

1. **文档长、跨主题** → 一个向量稀释多个主题，检索漂移
2. **检索粒度要求细** → 用户问一个子问题，希望命中段落而非整篇
3. **token 限制** → 一个 chunk 塞不进 prompt 预算

我的知识库恰好避开了这三个——每篇本身就是「最小可独立回答问题」的粒度，整篇就是天然的最优 chunk。

**代码细节（真实数字）：**

`TextChunker(chunk_size=500, chunk_overlap=50)`：文本 ≤500 字符整篇成块；超过则滑动窗口切块，相邻块重叠 50 字符（防止跨块边界信息丢失）。实际构建日志是「31/31 个 chunk」——23 篇文档里有 8 篇超长被切成了多块。单块时保留原 doc_id（与旧数据向后兼容），多块时才加 `#0/#1` 后缀。

**追问应对：**

- **"chunk_size 为什么是 500？"** → 对中文面试知识点，500 字符 ≈ 一段完整论述（一个考点），能独立回答一个问题。太小语义破碎，太大粒度粗。这是按「知识密度」定的，不是拍脑袋——我的知识库每篇结构就是「一个考点一段」。
- **"overlap 为什么是 50？"** → 10% 的 chunk_size，业界经验值。作用是让跨块边界的关键词/句子不丢。当前只有 8 篇被切，overlap 影响很小，但机制在，规模上来不用改。

### Q14：召回之后要不要重排？Reranker 你上了吗？

**表层回答：**

我做了重排层，但结论很有意思：**先上了词面精排，跑评测发现它在近义干扰题上帮倒忙，所以精排层最终留的是 cross-encoder 接口，召回用混合检索。**

**深入原理（这是最值钱的一问）：**

重排（rerank）解决的是「粗排快而不准、精排准而不快」的矛盾：

- **粗排（recall）**：向量检索是双塔模型（query 和 doc 分别编码，可离线建索引、在线快速算），BM25 是词频统计。快、全，但有盲区。
- **精排（precision）**：cross-encoder 把 query 和 doc 一起送进 Transformer，注意力机制让两者充分交互，准得多，但慢——所以只对召回后的 top-20 重排。

**我的实验（真实数据）：**

我先用零依赖的 `KeywordReranker`（词面精排：统计 query 词在候选里命中多少）做验证，跑完 24 条评测发现：`hybrid` 的 MRR 100%，`hybrid+rerank` 掉到 91.7%。原因是我的评测集里专门设计了 **near_miss（近义干扰）题**——这类题就是「词面强烈指向错误文档」，词面精排会**放大这个错误**，把错误文档顶得更靠前。

**追问应对：**

- **"所以你的结论是 reranker 没用？"** → 不是。结论是「**词面重排**在近义干扰场景有害，需要的是 **cross-encoder 语义重排**」。我的 rerank 接口已经抽象好，`CrossEncoderReranker`（bge-reranker）接入点留着，当前 23 篇规模不需要。这个负结果比「样样都涨」可信——它证明我跑过实验、理解了「词面 vs 语义」的权衡，而不是堆了个 reranker 名词。
- **"bi-encoder 和 cross-encoder 区别？"** → bi-encoder（双塔）把 query 和 doc 分别编码成向量再算相似度，编码可以离线缓存、检索快，但两者没有交互，精度低；cross-encoder 把 query 和 doc 拼接一起输入，注意力机制跨两者交互，精度高但每次查询都要重算、慢。所以业界标准是「粗排 bi-encoder + 精排 cross-encoder」两阶段。

### Q15：你的 RAG 怎么评测的？数据真实吗？

**表层回答：**

自建 24 条带标注 ground truth 的评测集，用 Recall@k / Precision@k / MRR / NDCG@k 对比三种检索配置（纯向量 / 混合检索 / 混合+词面重排），外加 RRF 参数敏感性实验。

**深入原理（评测集怎么设计的）：**

24 条分 6 类，每类有明确的测法目的：

| 类别 | 数量 | 测什么 |
|------|------|--------|
| direct 直接命中 | 5 | 基线，任何配置都该命中；掉了说明管线有 bug |
| paraphrase 语义改写 | 4 | 向量检索的价值（纯 BM25 会漏同义改写） |
| keyword 精确关键词 | 4 | BM25 的价值（纯向量可能被语义近邻带偏） |
| near_miss 近义干扰 | 4 | 排序质量（词面指向错误文档，最吃精排） |
| multi 多文档 | 4 | Recall@k 在 k>1 时能否召回全部相关文档 |
| negative 知识库外 | 3 | 拒答能力（不该强行召回无关文档） |

**关键设计理念：不是「出难题」，是「每道题逼出一个维度的能力差异」。** 如果我全出直接命中题，三个配置都 100%，评测就白做了。

**真实数据怎么读（诚实版本）：**

我用真实 DashScope embedding 跑出来的结果，recall@5 和 MRR 几乎满分（hybrid 的 MRR 100%）——**这恰恰说明我的评测集还不够难**，不是「检索完美」：知识库 23 篇主题干净分离，正确文档稳居 top-1，指标饱和、没有区分度。所以我在简历上**不写「MRR 100%」**，只写「自建带标注评测集 + 三类指标对比」的方法论，以及那个有信息量的负结果（词面重排放大近义干扰）。

**追问应对：**

- **"Precision 为什么只有 20%+，是不是检索很差？"** → 不是，是**结构性低**。我的用例大部分是「单个正确文档」，单文档在 top-5 里命中，precision 天然封顶 1/5=20%；多文档题最多 2/5=40%。这个指标被用例设计封死了上限，所以我不用它做主指标。这恰恰说明「指标要理解它的前提」——不看 ground truth 基数就比 precision，是会被问穿的。
- **"你的 MRR 100% 能写进简历吗？"** → 不写。它是「评测集不够难」的信号。我写的是「评测集设计方法论 + 一个真实负结果」——比一个虚假的满分更有说服力。
- **"负例怎么处理的？"** → 知识库外问题（「今天天气」「给狗做绝育」）我统计「最高相似度」，实测 0.374，显著低于命中题。说明系统不会强行召回不相关内容。但 0.374 不是 0，我现在还没做**拒答阈值**（相似度低于阈值就不返回），这是已知的下一步。
- **"为什么不用 RAGAS？"** → 检索层 ground truth 是「哪篇文档该被命中」，是确定性的、可人工标注的，用确定性指标（Recall/MRR/NDCG）比 LLM 打分更可靠。RAGAS 的 faithfulness 用 LLM 判定「陈述是否被支持」，噪声大（同一回答两次判定可能不同），我做生成层评测才考虑它。检索层用确定性指标，是「能确定性测的用确定性测」。

---

## 五、后端工程（深度）

### Q13：JWT 双 token 的完整设计？

**表层回答：**

access_token 30 分钟 + refresh_token 7 天，短效减少泄露影响，长效减少登录次数。

**深入原理（为什么双 token）：**

单 token 的困境：
- token 短效 → 用户频繁登录，体验差
- token 长效 → 泄露后影响时间长，安全差

双 token 解决这个矛盾：access_token 短效（30min，泄露影响小），refresh_token 长效（7 天，用于无感续期）。

**代码细节（踩过的坑，面试可讲）：**

1. **JWT exp 必须是整数 Unix 时间戳**：python-jose 不会自动把 datetime 转时间戳，直接传 datetime 会生成格式错误的 token，导致解码失败。要手动 `int(expire.timestamp())`。

2. **JWT sub 必须是字符串**：RFC 7519 规范要求，python-jose 严格（PyJWT 宽松）。签发时 `str(user_id)`，解码后 `int(payload["sub"])`。

3. **refresh_token 用 Body 传递而非 query 参数**：URL 会被代理/浏览器历史/服务器日志记录，泄露风险。

**追问应对：**

- **"refresh_token 泄露了怎么办？"** → 这就是为什么 refresh 也要有有效期（7 天），且续期时返回新的 refresh_token（旧的作废）。更进一步可以加 refresh token 轮换 + 撤销机制，但对当前规模够用。

### Q14：限流固定窗口的实现和原子性问题？

**表层回答：**

Redis INCR + EXPIRE，固定窗口，每 IP 每端点 20 req/min。

**深入原理（原子性隐患）：**

```
INCR key          # 计数 +1
if 首次: EXPIRE key 60  # 设过期
```

这两条命令**不是原子的**——如果 INCR 后、EXPIRE 前 Redis 崩溃，key 永远不过期，限流永久失效。

**追问应对：**

- **"怎么解决原子性问题？"** → 生产环境用 Lua 脚本（Redis 单线程执行 Lua 保证原子性）或 `SET key value NX EX` 一条命令。面试时主动说出这个隐患，体现安全意识——"当前版本够用，上线前用 Lua 封装"。

- **"固定窗口 vs 滑动窗口怎么选？"** → 固定窗口 O(1) 简单，但窗口边界可能短期超限（第 59 秒和第 61 秒各发 20 次，实际 2 秒内 40 次）。滑动窗口用 ZSET O(log N) 更精确。我的场景限流是"防止 API 费用失控"，不是"精确限流"，所以选简单的。

### Q15：为什么用 Repository 模式 + Alembic？

**表层回答：**

Repository 解耦数据访问，Alembic 版本化迁移。

**深入原理：**

**Repository 模式**：业务代码通过 Repository 操作数据库，不直接依赖 SQLAlchemy Session。好处：单测 mock Repository 即可（不需要真实数据库）、切数据库只改 Repository 内部。这是"依赖倒置"的体现——高层（业务逻辑）不依赖低层（具体 ORM），都依赖抽象（Repository 接口）。

**Alembic**：之前用 `Base.metadata.create_all` 建表，开发期没问题。但上线后加表（UserProfile/Resume）就没法平滑迁移了——create_all 只建不存在的表，改不了已存在的表结构。Alembic 提供版本化迁移（可升级、可回滚、可 autogenerate）。

**追问应对：**

- **"踩过什么坑？"** → RAG 数据持久化路径算错（parents[3] vs parents[2]），数据落在没挂载 docker 卷的目录，每次 --build 丢。这是"路径计算 + Docker 卷挂载"组合的经典 bug。

---

## 六、工程质量与评测（深度）

### Q16：测试策略怎么定的？为什么重点测纯函数？

**表层回答：**

107 后端 + 18 前端测试，重点测状态机、TokenBudget、RAG 检索。

**深入原理（测试金字塔的落地）：**

测试金字塔：单元测试最多（快、稳定）、集成次之、端到端最少（慢、脆弱）。

我的落地：**优先测纯函数和核心逻辑**——状态机路由（15 个）、TokenBudget（6 个）、序列化（5 个）、RAG 检索（6 个）。因为这些：

1. 逻辑密集（状态机一堆 if-else 规则，容易出边界 bug）
2. 纯函数（无副作用，好测）
3. 曾经踩过坑（状态机的 NameError、空函数体）

**追问应对：**

- **"测试抓到过真 bug 吗？"** → 抓到了。useToast 的 success/error/info 不返回 id，导致调用方无法 dismiss 特定 toast——这个隐患是写测试时发现的。还有状态机测试锁住了"什么是/是什么"两种中文语序的边界 case。

### Q17：为什么评测用确定性指标，不用 LLM 打分的 faithfulness？

**表层回答：**

LLM 判定噪声大、不可复现；确定性指标（触发率/命中率/标注率）100% 可复现。

**深入原理（这是最体现判断力的问题）：**

最初用 faithfulness（LLM 判定"陈述是否被来源支持"），发现两个致命问题：

1. **噪声大**：同一个回答两次判定，LLM 可能给出不同结果——数据不可复现，写进简历就是定时炸弹（面试官问"怎么测的"，答不出稳定路径）

2. **对象错位**：faithfulness 测"编造"，适合 RAG 知识库问答（有明确 sources）。但简历分析的回答天然含评价/建议（"技术栈选得好"），这些合理分析全被判为"幻觉"，导致分数系统性偏低

**重构为确定性指标**：检索触发率（状态机是否路由 search）、命中率（search 是否返回非空）、来源标注率（回答是否带参考来源）。这三个都是**代码行为**，不经过 LLM 判定，跑多少次结果都一样。

**追问应对：**

- **"这不就放弃了对回答质量的评测了吗？"** → 我承认确定性指标测的是"工程可靠性"（管线对不对），不是"语义质量"（回答好不好）。语义质量评测用 LLM 判定有固有噪声，这是行业难题（RAGAS 也在解决）。我的选择是：能确定性测的用确定性测，语义质量留给人工评估，不用不可复现的数据骗自己。

---

## 七、技术选型横向对比（深度版）

> 每个选型都列出多个候选 + 各自的优劣势 + 我的选择 + 一句话依据。面试官问"为什么选 A 不选 B"，这些就是答案。

### 7.1 Agent 框架

| 方案 | 优势 | 劣势 | 决策 |
|------|------|------|------|
| 纯手写 ReAct | 完全理解底层、可控、面试讲得透 | 开发慢、边界自己处理 | ✅ 主选 |
| LangChain | 生态成熟、快速、生产常用 | 黑盒、易被问穿 | ✅ 并行对比 |
| LangGraph | 显式状态图、checkpointer、HITL | 学习成本、对简单场景偏重 | 用了 prebuilt |
| AutoGPT/BabyAGI | 自主任务分解 | 过度设计、不稳定、成本高 | ❌ |

**核心观点**：纯手写和纯调包是两个极端，我走中间——手写为主、框架对比。既能讲清原理，又证明理解正确。

### 7.2 状态机

| 方案 | 可靠性 | Token | 灵活性 |
|------|--------|-------|--------|
| prompt 状态机 | 低（LLM 不听话） | 高（规则注入 prompt） | 高 |
| 代码状态机 | 高（确定性） | 零 | 低 |
| function calling | 中（仍是 LLM） | 低 | 中 |

**我的方案**：代码状态机（规则）+ LLM（语义选择），取两者之长。这是 constrained generation 的分层思想。

### 7.3 向量存储

| 方案 | 规模 | 优势 | 劣势 |
|------|------|------|------|
| 纯 Python | 百~千级 | 零依赖、讲得清 | 无索引加速 |
| Chroma | 万~十万 | 轻量、LangChain 集成 | 额外依赖 |
| Faiss | 百万+ | 极致性能、GPU | C++ 依赖、复杂 |
| Milvus | 千万+ | 分布式、生产级 | 部署重 |

**依据**：23 篇文档，纯 Python 毫秒级，专用库过度设计。接口已抽象，可替换。

### 7.4 Embedding

| 方案 | 优势 | 劣势 |
|------|------|------|
| 千问 API | OpenAI 兼容零依赖、中文优、绕下载坑 | API 延迟/成本 |
| 本地 bge | 零成本、离线、隐私 | 数百 MB 下载坑、占内存 |
| OpenAI | 生态成熟 | 国内难、成本高 |

**依据**：DeepSeek 官方不支持 embedding（查证了 GitHub issue），千问是零新依赖的最优解。

### 7.5 检索融合

| 方案 | 优势 | 劣势 |
|------|------|------|
| 单一向量 | 语义强 | 关键词不敏感 |
| 单一 BM25 | 关键词强 | 不懂同义词 |
| 加权融合 | 灵活 | 分数尺度不可比、要调参 |
| RRF | 排名可比、无超参 | 略粗粒度 |

### 7.6 记忆方案

| 方案 | 优势 | 劣势 |
|------|------|------|
| Redis 会话 | 持久化、共享、TTL | 需部署 Redis |
| 纯内存 | 零依赖 | 重启丢、不共享 |
| 向量记忆 | 语义检索、重要性评分 | 过度设计 |

**依据**：三层各解决一个时间尺度的问题，向量记忆对求职场景过度设计。

### 7.7 流式 / 限流 / 迁移

| 选型 | 选择 | 拒绝 | 依据 |
|------|------|------|------|
| 流式 | SSE | WebSocket/轮询 | 单向够用、代理兼容好 |
| 限流 | 固定窗口 | 滑动窗口/令牌桶 | 场景简单、误判代价低 |
| 迁移 | Alembic | create_all/手写 SQL | 上线需版本化平滑迁移 |

---

## 八、高频追问速查（深度版）

**"你项目里最难的 bug 是什么？"**
→ agent_state.py 的两个严重 bug：`_query_mentions_jd` 空函数体（有 docstring 没函数体，永远返回 None）+ `wants_resume/wants_jd` 变量名写错（NameError）。这两个 bug 导致 Agent 完全崩溃。发现方式是代码 review + mock 隔离测试。教训：变量命名一致性是基本素养，写完要用 References 检查所有引用点。

**"如果用户量从 100 涨到 100 万，架构哪里先崩？"**
→ 1. SQLite 最先崩（单文件写锁、单点、并发写差）→ 换 PostgreSQL；2. Redis 单实例（内存/连接数）→ 主从/集群；3. DeepSeek API 调用成本 + 限流（20 req/min 不够）→ 缓存 + 配额管理；4. 单机后端 → 无状态水平扩展 + 负载均衡。

**"你的长期记忆是语义化还是结构化？"**
→ 结构化（SQLite 字段存技术栈/目标岗位）。对当前场景够用。语义化记忆（向量检索记忆片段）可以和 RAG 向量设施复用，是下一步方向。诚实说清边界，不夸大。

**"RAG 有 reranker 吗？"**
→ 有，但要分两层讲清楚。我做了重排层：先加了零依赖的 KeywordReranker（词面精排），跑完评测发现它在「近义干扰题」上反而拉低了 MRR——因为近义干扰题的本质就是「词面指向错误文档」，词面精排会放大这个错误。所以真正纠正近义干扰需要 cross-encoder 的语义交互，我把这一层留成了 `CrossEncoderReranker` 接口（bge-reranker），当前 23 篇规模没启用。这个负结果比我「吹样样都涨」更可信——它证明我真跑过实验、理解了「词面 vs 语义」的权衡，而不是堆了个 reranker 名词。详见下方「RAG 检索质量评测」一节。

**"为什么不用多 Agent 协作？"**
→ 单 Agent + 代码状态机已够用（求职场景工具少、流程清晰：resume→jd→match）。多 Agent 适合复杂任务分解（如同时需要检索、计算、代码执行），当前是过度设计。

**"你的 SSE 和 WebSocket 选型依据？"**
→ AI 回答只需服务器→客户端单向推送，SSE 够用。WebSocket 全双工能力用不上，且需要特殊代理配置。Nginx 只需 proxy_buffering off 就支持 SSE。

**"RAG 的 embedding 为什么用 query/document 不同编码？"**
→ 非对称检索。query 是简短查询意图，document 是完整知识内容，语义角色不同，用不同编码方式检索效果更好。这是千问 text-embedding-v3 的 text_type 参数支持的能力。

---

> 本手册所有内容均可从代码和 docs/ 目录验证，面试时可现场演示或引用。
