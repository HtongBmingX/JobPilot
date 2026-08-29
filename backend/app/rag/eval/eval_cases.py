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
]


def get_eval_cases() -> list[dict]:
    """返回评测用例列表（深拷贝，避免调用方误改全局）"""
    import copy
    return copy.deepcopy(EVAL_CASES)
