# RAG 检索质量评测与工程化说明

> 本文档回答三件事：① 我补了什么、怎么跑；② 原来缺的技术点现在各是什么状态；
> ③ 面试被问到「RAG 你做到什么程度」时，怎么有底气地答。
> 最后更新：2026-08-25

---

## 一、这次补了什么

### 1. 真·检索质量评测（替换掉原来的「三个 100%」）

原来 `evaluation/deterministic_metrics.py` 的「检索触发率/命中率/来源标注率 100%」，
测的是「工程可靠性」（有没有路由到 search、有没有返回非空、有没有标注来源），
**不测检索质量**——hit 率只判断「返回非空」，没判断「返回的文档对不对」。

新增 `backend/app/rag/eval/`：

| 文件 | 作用 |
|------|------|
| `metrics.py` | Recall@k / Precision@k / MRR / NDCG@k 四个指标纯函数 |
| `eval_cases.py` | 24 条带标注 ground truth 的评测集（6 类） |
| `runner.py` | 评测执行器：三种检索配置对比 + RRF 参数敏感性 + 报告输出 |

**评测集的 6 类设计（每类各有测法目的）：**

| 类别 | 数量 | 测什么 |
|------|------|--------|
| direct（直接命中） | 5 | 基线，任何配置都该命中；掉了说明管线有 bug |
| paraphrase（语义改写） | 4 | 向量检索的价值——纯 BM25 会漏同义改写 |
| keyword（精确关键词） | 4 | BM25 的价值——纯向量可能被语义近邻带偏 |
| near_miss（近义干扰） | 4 | 排序质量——词面指向错误文档，最吃精排 |
| multi（多文档） | 4 | Recall@k 在 k>1 时能否召回全部相关文档 |
| negative（知识库外） | 3 | 拒答能力——不该强行召回无关文档 |

### 2. 分块器（Chunker）

`backend/app/rag/chunker.py`。当前知识库 23 篇、每篇 500~1500 字、一个独立知识点，
**默认「整篇成块」**（单块时保留原 doc_id，与旧数据向后兼容）。
但把分块抽象成可替换策略：`chunk_size` / `chunk_overlap` 可配置，
文档变长或检索粒度要求变细时改配置即可，不动检索代码。

### 3. 重排器（Reranker）

`backend/app/rag/reranker.py` 里：
- `Reranker` 抽象接口（业务代码只依赖接口，实现可替换）
- `KeywordReranker`：零依赖关键词精排，用于「近义干扰」场景把正确文档顶上去，
  验证「重排这一层有增益」
- `CrossEncoderReranker`：cross-encoder 接入点（预留，当前 23 篇规模不需要）

### 4. 管线集成 + 增量 + 缓存

- `rag_pipeline.py`：三种检索模式 `vector` / `hybrid` / `hybrid+rerank`
- 增量更新：`index_batch` 跳过「已存在且内容未变」的文档（`vector_store.get_text` 对比）
- embedding 缓存：`EmbeddingService` 加内存缓存（`(text, text_type) → 向量`），
  相同文本不再重复调 API
- `hybrid_searcher.py`：`rrf_k` 参数可配置（供敏感性实验）
- `vector_store.py`：新增 `get_text` / `get_ids`

---

## 二、怎么跑

```bash
cd backend

# 1. 离线冒烟（无需任何 API key，验证评测流程 + 展示词面可区分的行为）
python -m backend.app.rag.eval.runner

# 2. 真实评测（需要 DASHSCOPE_API_KEY，先建库再评测）
python -m backend.app.rag.build_knowledge_base
python -m backend.app.rag.eval.runner --real

# 3. 逐题明细（定位「哪一题、哪篇文档」被重排顶了上来）
python -m backend.app.rag.eval.runner --real --detail

# 4. 导出完整报告为 markdown（总表 + RRF 敏感性 + 逐题明细）
python -m backend.app.rag.eval.runner --real --out docs/rag_eval_report.md

# 5. 跑新增单测
pytest tests/test_rag_eval.py -v
```

> ⚠️ 离线模式用「哈希 n-gram 代理 embedding」，是词面的、不是语义的。
> 它只能验证「评测流程能跑通 + 关键词/干扰题这类词面可区分的行为」。
> **简历上那条「纯向量 → 混合检索 → 精排」的命中率曲线，必须来自 `--real` 的真实数据。**

### 已跑出的真实结果（2026-08-29，DashScope embedding）

| 配置 | recall@5 | precision@5 | mrr | ndcg@5 | 负例top1相似度 |
|---|---|---|---|---|---|
| vector | 100.0% | 28.9% | 97.6% | 98.2% | 0.374 |
| hybrid | 100.0% | 27.4% | 100.0% | 99.2% | 0.374 |
| hybrid+rerank | 97.6% | 23.1% | 91.7% | 91.6% | 0.374 |

怎么读这组数据（诚实版，别过度解读）：

- **recall@5 / MRR 接近满分 = 评测集还不够难**，不是「检索完美」。知识库 23 篇主题干净分离，正确文档稳居 top-1，指标饱和、没有区分度。所以不写「MRR 100%」进简历。
- **precision@5 只有 20-29% 是结构性低**：用例大多是单文档，单文档在 top-5 命中，precision 天然封顶 1/5=20%。不用它做主指标。
- **负例 top1 相似度 0.374** 显著低于命中题，说明不会强行召回无关文档；但 0.374 ≠ 0，尚未做拒答阈值（已知下一步）。
- **最有信息量的是 hybrid+rerank 反而变差**（mrr 100→91.7）：词面精排在近义干扰题上帮了倒忙——这正是 near_miss 类用例的设计目的。结论是「词面重排有害，需要 cross-encoder 语义重排」，接口已预留。这个负结果比「样样都涨」可信。
- **RRF 四个 k 值分数全同**：小规模下对 k 不敏感，k=60 稳健；但这不是「调参证明最优」，是「小语料伪象」，别吹。

---

## 三、原来缺的技术点，现在的状态清单

### 第 1 类：该补的（已补）

| 技术点 | 状态 |
|--------|------|
| 真·检索质量评测（Recall@k/MRR/NDCG + 带标注评测集） | ✅ 已补 |
| 分块（Chunking） | ✅ 补了可配置 chunker（当前默认整篇） |
| 重排（Reranker） | ✅ 补了接口 + 关键词精排 + cross-encoder 接入点 |

### 第 2 类：知道就行、当前规模不必写代码（认知清单，面试会问）

| 技术点 | 现在的诚实回答 | 什么时候才需要做 |
|--------|--------------|----------------|
| Query 改写 / HyDE / 多查询扩展 | 没做，直接拿原 query 检索 | 用户查询是口语/模糊/多意图时；知识库规模大、检索漂移明显时 |
| 检索结果上下文管理 | 固定 `top_k=5`，按相关性排序塞进 prompt | 文档变长、检索结果总量超 prompt 预算时，需要「重排 + 截断 + 摘要」策略 |
| Embedding 批量/持久化缓存 | 内存缓存（同进程内）；跨进程/重启不缓存 | 知识库构建频繁、多实例部署时换 Redis/磁盘缓存 |
| 增量更新 | 已做（内容未变跳过） | 已满足 |
| RRF 的 k=60 | 补了敏感性实验，可验证是否稳健 | 如果实验显示 k 敏感，再调 |

**面试话术模板（被问「RAG 你做到什么程度」）：**

> 我的 RAG 管线是「分块 → 非对称 embedding（query/document 分开编码）→
> 向量 + BM25 + RRF 混合检索 → 可选精排」的两阶段架构。召回层用双塔模型保证快，
> 精排层预留了 cross-encoder 接口。当前知识库 23 篇、每篇一个独立知识点，
> 所以整篇成块、不需要 cross-encoder 精排——这是规模匹配的选择，不是能力缺失。
> 我用自建的 24 条评测集（含语义改写、近义干扰、知识库外负例）做了 Recall@k /
> MRR / NDCG 评测，对比了纯向量、混合检索、混合+精排三种配置，
> 用数据证明了混合检索和精排各自补上了什么短板。

---

## 四、简历上该怎么写（诚实版本）

- ✅ 可以写：「自建 24 条带标注评测集（含近义干扰、多文档、知识库外负例），用 Recall@k/MRR/NDCG 对比三种检索配置」
- ✅ 可以写：「分块/重排分层——超长文档滑动窗口切块，重排层验证了词面精排在近义干扰场景有害、改用 cross-encoder 接口预留」
- ❌ 不要写：「命中率 100% / MRR 100%」——指标饱和是「评测集不够难」的信号，不是卖点，会被问穿
- ❌ 不要写 precision@5（结构性低，且不好解释）
- ❌ 不要写离线代理 embedding 的结果——那是验证流程用的，不是语义检索质量

---

## 五、和旧评测体系的关系

- `evaluation/deterministic_metrics.py`（工程可靠性三指标）：**保留**，它测的是「管线对不对」，
  和这里「检索准不准」是互补的两层，不冲突。
- `evaluation/rag_test_cases.py`（5 条必然命中题）：可被 `rag/eval/eval_cases.py` 的 direct 类覆盖，
  建议后续归档，避免两套口径混淆。
