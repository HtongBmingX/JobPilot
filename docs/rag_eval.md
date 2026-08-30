# RAG 检索质量评测与工程化说明

> 本文档回答三件事：① RAG 管线的技术全景；② 评测怎么做、真实数据怎么读；③ 面试被问到怎么答。
> 最后更新：2026-08-30

---

## 一、RAG 管线技术全景

一条标准的「两阶段」RAG 管线：

```
分块 → 非对称 embedding → 混合检索（粗排）→ 可选精排 → 拒答阈值 → 可溯源生成
```

| 环节 | 实现 | 关键技术点 |
|------|------|-----------|
| 分块 | `rag/chunker.py` | `chunk_size=500`、`overlap=50`；短文档整篇成块，超长文档滑动窗口切块 |
| 向量化 | `rag/embedding.py` | 通义千问 text-embedding-v3，`text_type` 区分 query/document（非对称检索），带内存缓存 |
| 存储 | `rag/vector_store.py` | 纯 Python 余弦相似度 + JSON 持久化（规模匹配，接口可替换 Chroma） |
| 粗排 | `rag/hybrid_searcher.py` | 向量检索 + BM25（中文按字/英文按词分词）+ RRF 融合（k=60 可配置） |
| 精排 | `rag/reranker.py` | KeywordReranker（词面精排）+ CrossEncoderReranker（接口预留，未启用） |
| 拒答 | `rag_pipeline.top1_vector_similarity` + `RAG_SIMILARITY_THRESHOLD` | 基于 top-1 余弦相似度，低于阈值返回「知识库外问题」 |
| 溯源 | `search_tool.py` + `jobpilot_agent._prepend_sources` | 来源标注代码强制注入，不依赖 LLM 自觉 |

---

## 二、评测体系

### 指标（两层，各有各的用途）

**检索层（确定性、可复现、能写简历）**——`rag/eval/metrics.py`：

- `recall@1` / `recall@k`：正确文档排第一 / 进 top-k 的比例
- `mrr`：第一个正确文档的排名倒数平均（「排第几」的核心指标）
- `ndcg@k`：排序质量（正确文档越靠前分越高）
- `hit_rate@k` / `precision@k`

**生成层（LLM 判定、有噪声、只作参考）**——`evaluation/metrics/`：

- faithfulness / answer relevancy / context recall / context precision（RAGAS 四件套）
- 这层依赖 LLM 判定，噪声大、不可复现，**不产出简历数据**，只作人工参考

### 评测集设计（57 篇语料 → 56 条用例，多类别）

| 类别 | 测什么 | 理想表现 |
|------|--------|---------|
| direct | 基线，任何配置都该命中 | 接近 100%（掉了说明有 bug） |
| keyword | 精确关键词匹配（BM25 的价值） | 接近 100% |
| paraphrase / paraphrase_hard | 语义改写（向量检索的价值） | 有区分度，hybrid 明显高于 vector |
| near_miss / near_miss_hard | 词面指向错误文档（排序质量） | 有区分度 |
| multi / multi_hard | 跨主题多文档 | 看 mrr 而非 recall@1 |
| negative | 知识库外拒答 | 不该强行召回 |

---

## 三、真实数据（2026-08-30，DashScope embedding，57 篇语料 / 56 条用例）

### 总表

| 配置 | recall@1 | mrr | ndcg@5 | 负例top1相似度 |
|---|---|---|---|---|
| vector（纯向量） | 76.4% | 92.1% | 94.1% | 0.377 |
| **hybrid（混合检索）** | **82.1%** | **95.3%** | **95.9%** | 0.377 |
| hybrid+rerank（词面重排） | 71.7% | 86.9% | 87.5% | 0.377 |

### 关键类别（区分度在这里）

| 类别 | vector recall@1 | hybrid recall@1 |
|------|----------------|----------------|
| keyword（基线） | 100.0% | 100.0% |
| **paraphrase_hard（语义改写难题）** | 60.0% | **90.0%** |
| near_miss | 75.0% | 75.0%（mrr 83.3%→87.5%） |

### 拒答阈值校准

| 阈值 | 误拒率（正例被挡） | 漏挡率（负例被放行） |
|---|---|---|
| 0.40 | 0.0% | 0.0% |

正例和负例的 top-1 相似度分布干净分离，阈值 0.40 时误拒和漏挡都为 0。

---

## 四、这组数据怎么读（诚实版）

**能写进简历的三个真实结论：**

1. 混合检索相对纯向量，**recall@1 从 76.4% 提升到 82.1%**（+5.7 点），**MRR 从 92.1% 到 95.3%**
2. 在语义改写难题上，**recall@1 从 60% 提升到 90%**（+30 点）——这是混合检索价值最清晰的证据
3. 词面重排反而拉低 MRR 到 86.9%（负结果），据此保留 cross-encoder 语义精排接口

**不能写、但要能解释的：**

- ❌ 不写「recall@5」——57 篇语料下 top-5 几乎必中，指标饱和、无区分度
- ❌ 不写「precision」——单文档题结构性封顶，数字低但不代表检索差
- ✅ keyword 类 100% 是**健康的**——证明精确词匹配的底线能力没坏，不是虚高

**面试话术：**

> 我用自建的多类别评测集（含语义改写、近义干扰、跨主题、知识库外负例）对比三种检索配置。关键结论是：混合检索在语义改写难题上把 recall@1 从 60% 提到 90%，这是 BM25 补上向量检索语义盲区的直接证据；而词面重排反而有害（MRR 降到 86.9%），因为它放大词面误导——所以精排层留了 cross-encoder 接口。另外我做了拒答阈值校准，正负例相似度分布在 0.40 处干净分离。

---

## 五、怎么跑

```bash
cd backend

# 1. 离线冒烟（无需 API key，验证流程 + 词面可区分行为）
python -m backend.app.rag.eval.runner

# 2. 真实评测（需 DASHSCOPE_API_KEY，先建库再评测）
python -m backend.app.rag.build_knowledge_base
python -m backend.app.rag.eval.runner --real

# 3. 逐题明细 / 导出报告
python -m backend.app.rag.eval.runner --real --detail
python -m backend.app.rag.eval.runner --real --out docs/rag_eval_report.md
```

> ⚠️ 离线模式用哈希 n-gram 代理 embedding（词面、非语义），只验证流程，**不产出简历数据**。真实数据必须来自 `--real`。

---

## 六、认知清单（知道即可，当前规模不必写代码）

| 技术点 | 现状 | 何时才需要做 |
|--------|------|-------------|
| Query 改写 / HyDE | 没做，直接拿原 query | 口语/模糊查询多、检索漂移明显时 |
| cross-encoder 真精排 | 接口预留未启用 | 规模上来、或岗位明确要求重排精度 |
| 检索结果上下文管理 | 固定 top_k=5 | 文档变长、结果超 prompt 预算时 |
| 向量存储换 Chroma | 纯 Python | 万级~十万级文档时 |

这些「知道何时不做」的判断力，本身就是面试加分项。
