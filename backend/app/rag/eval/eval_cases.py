"""
RAG 检索质量评测集（带标注 ground truth）

与 evaluation/rag_test_cases.py 的区别：
- 那个只有 5 条、全部照着知识库标题出题，是「必然命中题」，测不出检索质量。
- 这里 24 条、6 类，故意设计了干扰项、负例、语义改写、多文档，
  才能区分出「纯向量检索」「混合检索」「混合+精排」的真实差距。

六类用例（各有各的测法目的）：

1. direct   —— 直接命中题：措辞接近文档原文，基线（任何配置都该命中）。
               测「最基础能不能行」，如果这类都掉分，说明管线有 bug。
2. paraphrase —— 语义改写题：换个说法问同一件事，文档里没有原词。
               测「向量检索的价值」——纯 BM25 会漏，向量语义能补上。
3. keyword  —— 精确关键词题：关键词在文档里原样出现，语义相近的干扰文档也在。
               测「BM25 的价值」——纯向量可能被语义近邻带偏，BM25 靠精确词锁定。
4. near_miss —— 近义干扰题：词面强烈指向某篇（错误），正确答案在另一篇。
               测「排序质量」——最吃精排/重排能力，混合检索能否把正确文档顶上去。
5. multi    —— 多文档题：一个问题需要命中多篇文档。
               测「Recall@k」在 k>1 时是否真的能召回全部相关文档。
6. negative —— 知识库外负例：知识库根本回答不了。
               测「拒答能力」——好检索不该强行召回无关文档（Precision 的极端形式）。

字段说明：
- id / name / category / question：自解释。
- expected_doc_ids：该问题的 ground truth（正确应命中的文档 id 列表）。
  negative 类为空列表，表示「不该命中任何文档」。
- key_points：答案应覆盖的关键点（供后续生成层评测用，检索评测暂不使用）。
- note：这条用例在测什么，写给自己和面试官看的。
"""

EVAL_CASES = [
    # ============================================================
    #  1. direct —— 直接命中（基线，任何配置都该命中）
    # ============================================================
    {
        "id": "direct_001",
        "category": "direct",
        "question": "MySQL 索引为什么用 B+ 树而不是哈希或红黑树？",
        "expected_doc_ids": ["backend_db_index"],
        "key_points": ["B+ 树", "磁盘 IO", "范围查询", "回表"],
        "note": "措辞与文档标题几乎一致，纯向量也该命中",
    },
    {
        "id": "direct_002",
        "category": "direct",
        "question": "缓存穿透、缓存击穿、缓存雪崩有什么区别？",
        "expected_doc_ids": ["backend_redis"],
        "key_points": ["穿透", "击穿", "雪崩", "布隆过滤器"],
        "note": "三个专有名词直击文档，关键词密度极高",
    },
    {
        "id": "direct_003",
        "category": "direct",
        "question": "什么是 ReAct 模式？",
        "expected_doc_ids": ["agent_react"],
        "key_points": ["Reason", "Act", "Observe", "循环"],
        "note": "专有名词 ReAct，几乎无歧义",
    },
    {
        "id": "direct_004",
        "category": "direct",
        "question": "Vue 的响应式原理是什么？",
        "expected_doc_ids": ["frontend_vue"],
        "key_points": ["Proxy", "Object.defineProperty", "依赖收集"],
        "note": "响应式 + Vue 双关键词锁定",
    },
    {
        "id": "direct_005",
        "category": "direct",
        "question": "RDB 和 AOF 这两种持久化方式有什么区别？",
        "expected_doc_ids": ["backend_redis_persistence"],
        "key_points": ["RDB", "AOF", "快照", "追加日志"],
        "note": "RDB/AOF 是文档专属缩写",
    },

    # ============================================================
    #  2. paraphrase —— 语义改写（测向量检索的价值）
    # ============================================================
    {
        "id": "para_001",
        "category": "paraphrase",
        "question": "为什么写简历项目经历要用情境、任务、行动、结果这样的结构？",
        "expected_doc_ids": ["job_resume"],
        "key_points": ["STAR", "量化成果", "三段式"],
        "note": "没提 STAR 四个字母，用中文解释，纯关键词会漏",
    },
    {
        "id": "para_002",
        "category": "paraphrase",
        "question": "浏览器因为同源策略拦了我的请求，有哪些绕开的办法？",
        "expected_doc_ids": ["frontend_http_browser"],
        "key_points": ["CORS", "同源策略", "代理", "JSONP"],
        "note": "没说 CORS 缩写，'绕开办法'是语义表达",
    },
    {
        "id": "para_003",
        "category": "paraphrase",
        "question": "Python 里做计算密集的任务，为什么多线程反而不如多进程？",
        "expected_doc_ids": ["backend_os_process"],
        "key_points": ["GIL", "多进程", "CPU 密集"],
        "note": "全文没说 GIL，但问的就是 GIL 的后果",
    },
    {
        "id": "para_004",
        "category": "paraphrase",
        "question": "面试让我设计一个系统，说'先想清楚再动手'，具体该按什么步骤？",
        "expected_doc_ids": ["backend_system_design"],
        "key_points": ["需求澄清", "规模估算", "trade-off"],
        "note": "'系统设计'未直呼其名，靠语义识别",
    },

    # ============================================================
    #  3. keyword —— 精确关键词（测 BM25 的价值）
    # ============================================================
    {
        "id": "kw_001",
        "category": "keyword",
        "question": "LRU 缓存用哈希表加双向链表怎么实现？",
        "expected_doc_ids": ["algo_common"],
        "key_points": ["哈希表", "双向链表", "O(1)"],
        "note": "哈希表+双向链表是精确词，语义上'缓存'可能漂到 Redis",
    },
    {
        "id": "kw_002",
        "category": "keyword",
        "question": "HTTP/2 的多路复用具体解决了什么问题？",
        "expected_doc_ids": ["backend_http_https"],
        "key_points": ["多路复用", "头部压缩", "队头阻塞"],
        "note": "多路复用是精确术语，其他网络类文档没有",
    },
    {
        "id": "kw_003",
        "category": "keyword",
        "question": "Promise.then 和 setTimeout 的回调，哪个先执行？",
        "expected_doc_ids": ["frontend_js_core"],
        "key_points": ["微任务", "宏任务", "事件循环"],
        "note": "Promise/setTimeout 是精确关键词",
    },
    {
        "id": "kw_004",
        "category": "keyword",
        "question": "TopK 问题用小顶堆，时间复杂度是多少？",
        "expected_doc_ids": ["algo_common"],
        "key_points": ["小顶堆", "O(nlogK)", "快速选择"],
        "note": "小顶堆/TopK 精确词；'时间复杂度'会吸引 algo_complexity 干扰",
    },

    # ============================================================
    #  4. near_miss —— 近义干扰（测排序质量，最吃精排）
    # ============================================================
    {
        "id": "near_001",
        "category": "near_miss",
        "question": "Redis 为什么单线程还那么快？",
        "expected_doc_ids": ["backend_redis_persistence"],
        "key_points": ["纯内存", "IO 多路复用", "单线程"],
        "note": "词面都是 Redis，正确答案在'持久化与分布式锁'篇的追问点，而非'缓存三大问题'篇",
    },
    {
        "id": "near_002",
        "category": "near_miss",
        "question": "RAG 和微调这两个方案，应该怎么选？",
        "expected_doc_ids": ["agent_llm_engineering"],
        "key_points": ["知识动态更新", "成本", "溯源"],
        "note": "'RAG'会强烈吸引 agent_rag，但答案在 LLM 工程化篇",
    },
    {
        "id": "near_003",
        "category": "near_miss",
        "question": "浏览器缓存里的 ETag 和 304 是怎么回事？",
        "expected_doc_ids": ["frontend_http_browser"],
        "key_points": ["强缓存", "协商缓存", "ETag"],
        "note": "'缓存'可能漂到 Redis 篇，'HTTP'可能漂到网络基础篇",
    },
    {
        "id": "near_004",
        "category": "near_miss",
        "question": "Python 的生成器和迭代器有什么区别？",
        "expected_doc_ids": ["backend_python"],
        "key_points": ["迭代器", "yield", "惰性求值"],
        "note": "'协程/并发'类文档是强干扰，别被带偏",
    },

    # ============================================================
    #  5. multi —— 多文档（测 Recall@k，k>1 时的召回能力）
    # ============================================================
    {
        "id": "multi_001",
        "category": "multi",
        "question": "RAG 和 ReAct 分别解决什么问题，两者是什么关系？",
        "expected_doc_ids": ["agent_rag", "agent_react"],
        "key_points": ["检索增强", "幻觉", "思考行动循环"],
        "note": "需要同时召回两篇 agent 文档",
    },
    {
        "id": "multi_002",
        "category": "multi",
        "question": "协程这个概念，在前端事件循环和后端 IO 多路复用里分别是什么角色？",
        "expected_doc_ids": ["backend_os_process", "frontend_js_core"],
        "key_points": ["协程", "事件循环", "IO 多路复用"],
        "note": "跨前后端两篇，单文档召回不够",
    },
    {
        "id": "multi_003",
        "category": "multi",
        "question": "手写一个 Agent 要理解哪些底层原理，LangChain 又把这些封装成了什么？",
        "expected_doc_ids": ["agent_react", "agent_langchain"],
        "key_points": ["ReAct 循环", "AgentExecutor", "conditional_edge"],
        "note": "ReAct 原理 + LangChain 概念，两篇强相关",
    },
    {
        "id": "multi_004",
        "category": "multi",
        "question": "面试做算法题，除了会写解法，复杂度分析有什么要注意的？",
        "expected_doc_ids": ["algo_common", "algo_complexity"],
        "key_points": ["边界条件", "大 O", "均摊分析"],
        "note": "算法题型 + 复杂度分析，两篇都要",
    },

    # ============================================================
    #  6. negative —— 知识库外负例（测拒答，不该强行召回）
    # ============================================================
    {
        "id": "neg_001",
        "category": "negative",
        "question": "今天杭州的天气怎么样？",
        "expected_doc_ids": [],
        "key_points": [],
        "note": "知识库没有天气信息，理想情况一个都不该召回",
    },
    {
        "id": "neg_002",
        "category": "negative",
        "question": "怎么给小狗做绝育手术？",
        "expected_doc_ids": [],
        "key_points": [],
        "note": "完全无关领域",
    },
    {
        "id": "neg_003",
        "category": "negative",
        "question": "2026 年诺贝尔物理学奖颁给了谁？",
        "expected_doc_ids": [],
        "key_points": [],
        "note": "时效性问题，知识库没有也不该编",
    },

    # ============================================================
    #  【区分度扩展】针对扩语料后新增的难题
    #  目的：制造「词面强烈指向错误文档」的场景，让 baseline 犯错，
    #        只有混合检索/精排/精确区分才能答对。
    # ============================================================

    # ---------- 7. near_miss_hard —— 主题重叠后的硬干扰题（词面全指向错误文档） ----------
    {
        "id": "near_hard_001",
        "category": "near_miss_hard",
        "question": "Redis 的事务执行到一半失败了，会自动回滚吗？",
        "expected_doc_ids": ["backend_redis_transaction"],
        "key_points": ["不回滚", "MULTI/EXEC", "Lua 脚本原子"],
        "note": "词面 Redis 会吸引锁/集群/淘汰多篇，答案在「事务」篇",
    },
    {
        "id": "near_hard_002",
        "category": "near_miss_hard",
        "question": "MySQL 的索引失效会让锁发生什么变化？",
        "expected_doc_ids": ["backend_mysql_lock"],
        "key_points": ["行锁", "索引", "锁升级", "表锁"],
        "note": "词面「索引」强烈指向 backend_db_index，答案在「锁」篇",
    },
    {
        "id": "near_hard_003",
        "category": "near_miss_hard",
        "question": "Redis 内存满了写不进去，要淘汰 key，用哪个参数配置？",
        "expected_doc_ids": ["backend_redis_eviction"],
        "key_points": ["maxmemory", "淘汰策略", "lru/lfu"],
        "note": "词面 Redis 有多篇干扰，答案在「淘汰」篇，非锁非集群",
    },
    {
        "id": "near_hard_004",
        "category": "near_miss_hard",
        "question": "Agent 的「长期记忆」用什么方案持久化、为什么不能只靠对话上下文？",
        "expected_doc_ids": ["agent_memory"],
        "key_points": ["SQLite", "跨会话", "时间尺度", "对话记忆"],
        "note": "词面「记忆」会吸引 RAG/LLM工程化等多篇，答案在「记忆机制」篇",
    },
    {
        "id": "near_hard_005",
        "category": "near_miss_hard",
        "question": "redo log 和 binlog 分别记什么，主从复制用的是哪个？",
        "expected_doc_ids": ["backend_mysql_binlog_redo"],
        "key_points": ["redo log", "binlog", "两阶段提交", "主从复制"],
        "note": "词面 MySQL 日志，答案在「binlog/redo」篇，非索引非隔离",
    },
    {
        "id": "near_hard_006",
        "category": "near_miss_hard",
        "question": "Redis 的哨兵模式解决了主从复制的什么问题？",
        "expected_doc_ids": ["backend_redis_cluster"],
        "key_points": ["哨兵", "自动故障转移", "主从复制", "脑裂"],
        "note": "词面「主从复制」在集群篇，但锁/事务篇也提 Redis，易漂",
    },

    # ---------- 8. para_hard —— 极致语义改写（纯 BM25 必漏） ----------
    {
        "id": "para_hard_001",
        "category": "paraphrase_hard",
        "question": "Redis 加锁之后，如果业务还没跑完、锁就自动过期了，怎么防止别的线程提前拿到锁？",
        "expected_doc_ids": ["backend_redis_distributed_lock"],
        "key_points": ["看门狗", "续期", "锁过期", "Redisson"],
        "note": "全文没出现「看门狗」「续期」原词，靠语义识别",
    },
    {
        "id": "para_hard_002",
        "category": "paraphrase_hard",
        "question": "一个事务里读同一行数据，两次读到的值不一样，这种问题叫什么、什么隔离级别能解决？",
        "expected_doc_ids": ["backend_mysql_isolation"],
        "key_points": ["不可重复读", "可重复读", "隔离级别"],
        "note": "问「不可重复读」但没直呼其名，靠语义",
    },
    {
        "id": "para_hard_003",
        "category": "paraphrase_hard",
        "question": "给一个任务先让模型写出完整步骤清单，再一步步执行，这种和 ReAct 不同的做法叫什么？",
        "expected_doc_ids": ["agent_planning"],
        "key_points": ["Plan-and-Execute", "Planner", "Executor", "规划"],
        "note": "问 Plan-and-Execute 但没直呼其名，ReAct 是干扰",
    },
    {
        "id": "para_hard_004",
        "category": "paraphrase_hard",
        "question": "Python 里一段「读变量、判断、写变量」的代码，为什么在多线程下还是会出错，即使有 GIL？",
        "expected_doc_ids": ["backend_concurrency_safe"],
        "key_points": ["竞态条件", "非原子", "锁", "GIL"],
        "note": "词面 GIL 会漂到 backend_os_process，答案在「线程安全」篇",
    },

    # ---------- 9. multi_hard —— 跨主题多文档（k>1 才够） ----------
    {
        "id": "multi_hard_001",
        "category": "multi_hard",
        "question": "Redis 和 MySQL 都用「日志」来保证数据安全，它们各自的日志分别叫什么、作用有什么不同？",
        "expected_doc_ids": ["backend_redis_persistence", "backend_mysql_binlog_redo"],
        "key_points": ["AOF/RDB", "redo log", "binlog", "持久化"],
        "note": "跨 Redis 和 MySQL 两篇，单篇召回不够",
    },
    {
        "id": "multi_hard_002",
        "category": "multi_hard",
        "question": "Agent 既需要「记得对话历史」，又需要「规划任务步骤」，这两件事分别对应什么机制？",
        "expected_doc_ids": ["agent_memory", "agent_planning"],
        "key_points": ["记忆分层", "Planner", "Executor", "规划范式"],
        "note": "跨「记忆」和「规划」两篇，主题相近易漂",
    },

    # ============================================================
    #  【第一批扩量】针对新增的 LLM/后端/算法/安全文档
    # ============================================================

    # ---------- 10. direct_ext —— 新增文档的直接命中题（基线） ----------
    {
        "id": "direct_006",
        "category": "near_miss_hard",
        "question": "LoRA 微调的原理是什么？",
        "expected_doc_ids": ["llm_finetune"],
        "key_points": ["低秩矩阵", "PEFT", "冻结权重"],
        "note": "词面「微调」在 RAG/LLM工程化多篇也出现，实为 near_miss，非纯 direct",
    },
    {
        "id": "direct_007",
        "category": "direct",
        "question": "KV Cache 的作用是什么？",
        "expected_doc_ids": ["llm_inference_opt"],
        "key_points": ["缓存 K/V", "减少重复计算", "显存"],
        "note": "KV Cache 专有名词，直接命中",
    },
    {
        "id": "direct_008",
        "category": "direct",
        "question": "XSS 和 CSRF 分别是什么攻击？",
        "expected_doc_ids": ["security_web"],
        "key_points": ["跨站脚本", "跨站请求伪造", "防御"],
        "note": "XSS/CSRF 专有缩写",
    },
    {
        "id": "direct_009",
        "category": "near_miss_hard",
        "question": "快速排序的时间复杂度是多少？",
        "expected_doc_ids": ["algo_sort"],
        "key_points": ["O(nlogn)", "最坏 O(n^2)", "pivot"],
        "note": "词面「时间复杂度」是 algo_complexity 的主题词，实为 near_miss，非纯 direct",
    },

    # ---------- 11. near_miss_hard_ext —— 新主题的词面干扰题 ----------
    {
        "id": "near_hard_007",
        "category": "near_miss_hard",
        "question": "微调一个模型时，想不更新原参数、只训练旁路的小矩阵，这个技术叫什么？",
        "expected_doc_ids": ["llm_finetune"],
        "key_points": ["LoRA", "低秩", "旁路"],
        "note": "词面「微调」会吸引 RAG/提示工程多篇，答案在「微调」篇",
    },
    {
        "id": "near_hard_008",
        "category": "near_miss_hard",
        "question": "生成式模型推理时，把之前算过的 K、V 向量存起来复用，是为了解决什么？",
        "expected_doc_ids": ["llm_inference_opt"],
        "key_points": ["KV Cache", "重复计算", "显存"],
        "note": "词面「生成/推理」会吸引注意力/提示工程，答案在「推理优化」篇",
    },
    {
        "id": "near_hard_009",
        "category": "near_miss_hard",
        "question": "有人在你登录状态下诱导你点击链接，用你的身份发请求，这种攻击怎么防？",
        "expected_doc_ids": ["security_web"],
        "key_points": ["CSRF", "Token", "SameSite"],
        "note": "词面「攻击/登录」会吸引认证篇，答案在「Web安全」篇的 CSRF",
    },
    {
        "id": "near_hard_010",
        "category": "near_miss_hard",
        "question": "用「递归分成两半再合并」的排序算法，稳定性和空间复杂度怎么样？",
        "expected_doc_ids": ["algo_sort"],
        "key_points": ["归并排序", "稳定", "O(n) 空间"],
        "note": "词面「排序」在算法篇，但树/图篇也有复杂度讨论，易漂",
    },
    {
        "id": "near_hard_011",
        "category": "near_miss_hard",
        "question": "给消息中间件发消息后，怎么保证消息不丢？",
        "expected_doc_ids": ["backend_mq"],
        "key_points": ["生产确认", "持久化", "消费确认"],
        "note": "词面「消息」可能漂到网络/TCP 篇，答案在「消息队列」篇",
    },
    {
        "id": "near_hard_012",
        "category": "near_miss_hard",
        "question": "HTTP 的 PUT 和 PATCH 在语义和幂等性上有什么区别？",
        "expected_doc_ids": ["backend_http_status"],
        "key_points": ["整体替换", "部分更新", "幂等"],
        "note": "词面「HTTP」会吸引网络/TCP 篇，答案在「HTTP状态码」篇",
    },

    # ---------- 12. para_hard_ext —— 新主题的语义改写题 ----------
    {
        "id": "para_hard_005",
        "category": "paraphrase_hard",
        "question": "让模型在回答问题前，先把中间推理过程一步步写出来，这种技巧为什么能提升正确率？",
        "expected_doc_ids": ["llm_prompting"],
        "key_points": ["CoT", "思维链", "逐步推理"],
        "note": "问 CoT 但没直呼其名",
    },
    {
        "id": "para_hard_006",
        "category": "paraphrase_hard",
        "question": "怎么防止模型调用一个根本不存在的工具？",
        "expected_doc_ids": ["agent_tool_calling"],
        "key_points": ["白名单", "校验", "约束生成"],
        "note": "问工具调用但没直呼 function calling",
    },
    {
        "id": "para_hard_007",
        "category": "paraphrase_hard",
        "question": "高并发秒杀时，怎么把突然涌入的请求先缓冲起来，让系统按自己的能力慢慢处理？",
        "expected_doc_ids": ["backend_mq"],
        "key_points": ["削峰", "消息队列", "异步"],
        "note": "问削峰但没直呼消息队列",
    },
    {
        "id": "para_hard_008",
        "category": "paraphrase_hard",
        "question": "把 32 位浮点数的模型权重存成 8 位整数，为了省显存，这个做法叫什么？",
        "expected_doc_ids": ["llm_inference_opt"],
        "key_points": ["量化", "INT8", "显存"],
        "note": "问量化但没直呼其名",
    },
    {
        "id": "para_hard_009",
        "category": "paraphrase_hard",
        "question": "一个主控制器把大任务拆成几块，分给不同的专职模块去做，最后汇总，这种 Agent 架构叫什么？",
        "expected_doc_ids": ["agent_multi_agent"],
        "key_points": ["Orchestrator", "Worker", "多智能体"],
        "note": "问 Orchestrator-Worker 但没直呼其名",
    },
    {
        "id": "para_hard_010",
        "category": "paraphrase_hard",
        "question": "发请求时不用 session 而用带签名的令牌，服务端只验签不查库，这种方案的优势和代价是什么？",
        "expected_doc_ids": ["security_auth"],
        "key_points": ["JWT", "无状态", "无法主动吊销"],
        "note": "问 JWT 但没直呼其名",
    },

    # ---------- 13. multi_hard_ext —— 跨主题多文档 ----------
    {
        "id": "multi_hard_003",
        "category": "multi_hard",
        "question": "「缓存」在后端和「缓存」在 LLM 推理里分别是解决什么问题的？",
        "expected_doc_ids": ["backend_cache_pattern", "llm_inference_opt"],
        "key_points": ["缓存一致性", "KV Cache", "加速"],
        "note": "跨后端缓存和 LLM 推理优化两篇",
    },
    {
        "id": "multi_hard_004",
        "category": "multi_hard",
        "question": "「微调」和「RAG」都能让模型获得知识，两者的适用场景和取舍是什么？",
        "expected_doc_ids": ["llm_finetune", "agent_rag"],
        "key_points": ["微调", "RAG", "知识更新", "成本"],
        "note": "跨微调和 RAG 两篇",
    },
    {
        "id": "multi_hard_005",
        "category": "multi_hard",
        "question": "「认证」和「Web 攻击防御」都涉及安全，JWT 和 CSRF 分别解决什么？",
        "expected_doc_ids": ["security_auth", "security_web"],
        "key_points": ["JWT", "CSRF", "认证", "跨站"],
        "note": "跨认证和 Web 安全两篇",
    },
    {
        "id": "multi_hard_006",
        "category": "multi_hard",
        "question": "「图的最短路径」和「树的遍历」在算法面试里各有什么经典题？",
        "expected_doc_ids": ["algo_graph", "algo_tree"],
        "key_points": ["Dijkstra", "拓扑排序", "前中后序"],
        "note": "跨图和树两篇",
    },
]



def get_eval_cases() -> list[dict]:
    """返回评测用例列表（深拷贝，避免调用方误改全局）"""
    import copy
    return copy.deepcopy(EVAL_CASES)
