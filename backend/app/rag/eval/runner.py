"""
RAG 检索质量评测执行器

跑三种检索配置的对比（这是要写进简历/README 的那条曲线）：
1. vector        —— 纯向量检索（bi-encoder 余弦相似度）
2. hybrid        —— 向量 + BM25 + RRF 混合检索（当前生产配置）
3. hybrid+rerank —— 混合检索召回 top_n 后再精排

外加一个 RRF 参数敏感性实验（k=10/30/60/100），回答「k=60 是不是拍脑袋」。

两种运行方式：

1. 离线（默认，无需任何 API key）：
   python -m backend.app.rag.eval.runner
   用哈希 n-gram 代理 embedding，只验证「评测流程本身能跑通 + 输出结构正确」，
   以及展示「关键词题/近义干扰题」这类靠词面就能区分的行为。
   ⚠️ 代理 embedding 是词面的，不是语义的——「语义改写题」的增益必须用真实
   embedding 才能体现。离线结果不能写进简历。

2. 真实（需要 DASHSCOPE_API_KEY + 已构建知识库）：
   python -m backend.app.rag.build_knowledge_base    # 先建库
   python -m backend.app.rag.eval.runner --real      # 再评测
   这才是简历上那条「纯向量 → 混合检索 → 精排」命中率曲线的真实数据来源。
"""

import argparse
import hashlib
import math
import re

from backend.app.rag.chunker import TextChunker, normalize_chunk_id
from backend.app.rag.knowledge_docs import KNOWLEDGE_DOCS
from backend.app.rag.reranker import KeywordReranker
from backend.app.rag.rag_pipeline import RAGPipeline
from backend.app.rag.vector_store import VectorStore
from backend.app.rag.hybrid_searcher import HybridSearcher
from backend.app.rag.eval.metrics import (
    METRIC_FUNCS,
    aggregate,
    recall_at_k,
    mrr,
)
from backend.app.rag.eval.eval_cases import get_eval_cases


# ============================================================
#  离线代理 embedding（哈希 n-gram 特征向量）
# ============================================================

class HashEmbedding:
    """
    离线评测用的确定性代理 embedding。

    原理：把文本切成语义近似单元（英文词、中文单字、中英 bigram），
    用 md5 哈希到固定维度桶，累加后 L2 归一化。这是经典的 hashing trick。

    诚实声明：这是「词面」代理，不是「语义」模型。它能区分词面不同的文档，
    但「同义改写」（如「情境任务行动结果」vs「STAR」）它区分不了——
    那需要真实 embedding 的语义能力。所以离线结果只用于验证流程，不写简历。
    """

    def __init__(self, dim: int = 512):
        self.dim = dim
        self.available = True  # 模拟「已配置」，让 RAGPipeline.available 为 True

    def _grams(self, text: str) -> list[str]:
        t = (text or "").lower()
        # 英文词 + 中文单字
        tokens = re.findall(r"[a-zA-Z]+|[一-鿿]", t)
        grams = list(tokens)
        # 英文词内 bigram（捕捉字母组合，如 redis → re/ed/di/is/s）
        for w in re.findall(r"[a-zA-Z]+", t):
            grams.extend(w[i:i + 2] for i in range(len(w) - 1))
        # 中文相邻 bigram（捕捉词组，如 缓存 → 缓/存/缓存）
        cjk = re.findall(r"[一-鿿]", t)
        grams.extend(cjk[i] + cjk[i + 1] for i in range(len(cjk) - 1))
        return grams

    def _embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        for g in self._grams(text):
            h = int(hashlib.md5(g.encode("utf-8")).hexdigest(), 16) % self.dim
            vec[h] += 1.0
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]

    def embed_query(self, query: str) -> list[float] | None:
        if not query or not query.strip():
            return None
        return self._embed(query)

    def embed_document(self, document: str) -> list[float] | None:
        if not document or not document.strip():
            return None
        return self._embed(document)


# ============================================================
#  构建管线
# ============================================================

def build_offline_pipeline() -> RAGPipeline:
    """离线管线：代理 embedding + 内存向量库 + 关键词重排。"""
    p = RAGPipeline(chunker=TextChunker(), reranker=KeywordReranker(), rerank_top_n=20)
    p.embedding = HashEmbedding()
    p.vector_store = VectorStore()  # 内存模式，不落盘
    p.searcher = HybridSearcher(p.vector_store)
    for d in KNOWLEDGE_DOCS:
        p.index(d["id"], f"{d['title']}\n{d['text']}")
    return p


def build_real_pipeline() -> RAGPipeline:
    """真实管线：千问 embedding + 持久化向量库（需先 build_knowledge_base）。"""
    return RAGPipeline()


# ============================================================
#  评测核心
# ============================================================

def _dedupe(ids: list[str]) -> list[str]:
    """去重（保序）。同一文档多个 chunk 命中时，只保留第一次出现的排名。"""
    seen, out = set(), []
    for i in ids:
        if i not in seen:
            seen.add(i)
            out.append(i)
    return out


def evaluate(pipeline: RAGPipeline, mode: str, top_k: int = 5) -> dict:
    """对单种检索配置跑全部用例，返回各指标均值 + 负例行为 + 按类别 recall。"""
    cases = get_eval_cases()
    per_metric: dict[str, list] = {name: [] for name in METRIC_FUNCS}
    neg_sims: list[float] = []
    neg_nonempty = 0
    # 按类别统计 recall@1 和 mrr（区分「哪些题有区分度」——这两个才是
    # 「正确文档排第几」的核心指标；recall@5 在少量文档下易饱和，不统计）
    per_category: dict[str, dict] = {}

    for case in cases:
        results = pipeline.search(case["question"], top_k=top_k, mode=mode)
        retrieved = _dedupe([normalize_chunk_id(r["id"]) for r in results])
        expected = [normalize_chunk_id(i) for i in case["expected_doc_ids"]]

        if expected:
            r1 = recall_at_k(retrieved, expected, 1)
            m = mrr(retrieved, expected)
            for name, fn in METRIC_FUNCS.items():
                per_metric[name].append(fn(retrieved, expected))
            cat = case.get("category", "other")
            bucket = per_category.setdefault(cat, {"recall1": [], "mrr": []})
            bucket["recall1"].append(r1 if r1 is not None else 0.0)
            bucket["mrr"].append(m if m is not None else 0.0)
        else:
            # 负例：理想行为是「知识库没有相关内容」，不该强行召回。
            # 用 vector 模式取 top-1 的原始余弦相似度衡量「离知识库有多近」——越低越好。
            vec_res = pipeline.search(case["question"], top_k=1, mode="vector")
            if vec_res:
                neg_sims.append(float(vec_res[0]["score"]))
                neg_nonempty += 1

    agg = {name: aggregate(vals) for name, vals in per_metric.items()}
    agg["negative_avg_top1_sim"] = (sum(neg_sims) / len(neg_sims)) if neg_sims else 0.0
    agg["negative_retrieved_nonempty"] = neg_nonempty  # 负例里非空检索的条数
    agg["by_category"] = {
        cat: {
            "recall1": round(sum(v["recall1"]) / len(v["recall1"]), 4) if v["recall1"] else 0.0,
            "mrr": round(sum(v["mrr"]) / len(v["mrr"]), 4) if v["mrr"] else 0.0,
        }
        for cat, v in per_category.items()
    }
    return agg


def run(pipeline: RAGPipeline, top_k: int = 5) -> dict:
    """跑三种配置 + k 敏感性 + 拒答阈值校准，返回完整报告 dict。"""
    modes = ["vector", "hybrid", "hybrid+rerank"]
    report = {m: evaluate(pipeline, m, top_k) for m in modes}
    report["rrf_sensitivity"] = rrf_sensitivity(pipeline)
    report["threshold_calibration"] = threshold_calibration(pipeline)
    report["top_k"] = top_k
    report["n_cases"] = len(get_eval_cases())
    return report


def rrf_sensitivity(pipeline: RAGPipeline, ks=(10, 30, 60, 100)) -> dict:
    """RRF 参数敏感性：同一组非负例用例，换 k 看 recall@5 / mrr 变化。

    说明：RRF 的 k 控制「排名带来的分数差异」——k 越小，排名越靠前贡献越大，
    越「激进地相信第一名」；k 越大越「平滑」。业界默认 60，这里验证它是否稳健。
    """
    non_neg = [c for c in get_eval_cases() if c["expected_doc_ids"]]
    out = {}
    for k in ks:
        searcher = HybridSearcher(pipeline.vector_store, rrf_k=k)
        recalls1, mrrs = [], []
        for case in non_neg:
            qv = pipeline.embedding.embed_query(case["question"])
            if qv is None:
                continue
            res = searcher.search(case["question"], qv, top_k=5)
            ids = _dedupe([normalize_chunk_id(r["id"]) for r in res])
            exp = [normalize_chunk_id(i) for i in case["expected_doc_ids"]]
            recalls1.append(recall_at_k(ids, exp, 1))
            mrrs.append(mrr(ids, exp))
        out[str(k)] = {
            "recall@1": aggregate(recalls1),
            "mrr": aggregate(mrrs),
        }
    return out


def threshold_calibration(pipeline: RAGPipeline, thresholds=(0.30, 0.35, 0.40, 0.45, 0.50)) -> dict:
    """
    拒答阈值校准：验证「阈值挡知识库外问题」这个设计决策。

    方法：对正例（有 ground truth）和负例（知识库外）分别取 top-1 向量余弦相似度，
    在不同阈值下统计：
    - 误拒率：正例里相似度 < 阈值 的比例（真实问题被错误挡掉，越低越好）
    - 漏挡率：负例里相似度 >= 阈值 的比例（知识库外问题被放进来，越低越好）

    好的阈值在两者之间取平衡——误拒率和漏挡率都低，说明正负例的相似度分布分得开。
    """
    cases = get_eval_cases()
    pos_sims, neg_sims = [], []
    for case in cases:
        sim = pipeline.top1_vector_similarity(case["question"])
        if sim is None:
            continue
        if case["expected_doc_ids"]:
            pos_sims.append(sim)
        else:
            neg_sims.append(sim)

    if not pos_sims or not neg_sims:
        return {}

    out = {}
    for t in thresholds:
        # 误拒：正例 top1 相似度低于阈值 → 会被错误拒答
        false_reject = sum(1 for s in pos_sims if s < t) / len(pos_sims)
        # 漏挡：负例 top1 相似度不低于阈值 → 会被错误放行
        false_pass = sum(1 for s in neg_sims if s >= t) / len(neg_sims)
        out[str(t)] = {
            "误拒率": round(false_reject, 4),
            "漏挡率": round(false_pass, 4),
        }
    return out


# ============================================================
#  报告输出
# ============================================================

def _pct(x: float) -> str:
    return f"{x * 100:.1f}%"


def print_report(report: dict) -> None:
    modes = ["vector", "hybrid", "hybrid+rerank"]
    # 主表指标：recall@1 和 mrr 是「正确文档排第几」的核心指标（区分度在这里）。
    # 不放 recall@5（小文档库下易饱和、全是 100%，没有区分度），也不放 precision（结构性低）
    metric_names = ["recall@1", "mrr", "ndcg@5"]

    print("\n" + "=" * 64)
    print(f"RAG 检索质量评测报告（top_k={report['top_k']}，共 {report['n_cases']} 条用例）")
    print("=" * 64)

    header = "| 配置 | " + " | ".join(metric_names) + " | 负例top1相似度 |"
    print(header)
    print("|" + "---|" * (len(metric_names) + 2))

    for mode in modes:
        r = report[mode]
        cells = [mode] + [_pct(r[n]) for n in metric_names] + [f"{r['negative_avg_top1_sim']:.3f}"]
        print("| " + " | ".join(cells) + " |")

    print("\n说明：")
    print("- recall@1 / mrr 是「正确文档排第几」的核心指标，区分度在这两个；")
    print("- 负例 top1 相似度越低越好（知识库外问题不该召回高相似文档）；")
    print("- 注意：当前 KeywordReranker 是「词面精排」，在近义干扰题上可能让 mrr 变差——")
    print("  因为近义干扰题正是「词面指向错误文档」，词面精排会强化这个错误。")
    print("  真正纠正它需要 cross-encoder 语义精排。这是重排层「词面 vs 语义」的经典权衡。")

    # 按类别 recall@1 + mrr（区分度视图：看「哪些题难」和「混合检索救回了哪些」）
    categories = sorted({c for m in modes for c in report[m].get("by_category", {})})
    if categories:
        print("\n按类别 recall@1 / mrr（区分度视图）：")
        print("| 类别 | " + " | ".join(f"{m}(r@1/mrr)" for m in modes) + " |")
        print("|---|" + "---|" * len(modes))
        for cat in categories:
            cells = []
            for m in modes:
                b = report[m].get("by_category", {}).get(cat, {})
                cells.append(f"{_pct(b.get('recall1', 0.0))}/{_pct(b.get('mrr', 0.0))}")
            print("| " + cat + " | " + " | ".join(cells) + " |")
        print("→ recall@1 / mrr 是「正确文档排第几」的核心指标，区分度在这里；")
        print("  hybrid 的 recall@1/mrr 超过 vector，才是「混合检索有价值」的真实证据。")

    # RRF 敏感性
    sens = report.get("rrf_sensitivity", {})
    if sens:
        print("\nRRF 参数敏感性（hybrid 模式，换 k）：")
        print("| k | recall@1 | mrr |")
        print("|---|---|---|")
        for k in ["10", "30", "60", "100"]:
            if k in sens:
                print(f"| {k} | {_pct(sens[k]['recall@1'])} | {_pct(sens[k]['mrr'])} |")
        print("→ 若各 k 分数接近，说明 k=60 稳健、不是拍脑袋；若差异大，说明需要调参。")

    # 拒答阈值校准
    calib = report.get("threshold_calibration", {})
    if calib:
        print("\n拒答阈值校准（不同阈值下的误拒率/漏挡率）：")
        print("| 阈值 | 误拒率(正例被挡) | 漏挡率(负例被放行) |")
        print("|---|---|---|")
        for t in sorted(calib.keys(), key=lambda x: float(x)):
            c = calib[t]
            print(f"| {t} | {_pct(c['误拒率'])} | {_pct(c['漏挡率'])} |")
        print("→ 误拒率=真实问题被错误拒绝的比例，漏挡率=知识库外问题被错误放行的比例，都要低；")
        print("  理想情况正负例相似度分布分得开，能找到一个阈值让两者都接近 0。")


def per_case_detail(pipeline: RAGPipeline, top_k: int = 5) -> list[dict]:
    """
    逐题明细：每条用例在三种配置下的 top-k 结果（归一化后的 doc_id）。

    用途：把「hybrid+rerank 的 mrr 变差」这类聚合结论，落到具体哪一题、哪篇文档
    被顶了上来——让面试时能指着某一题讲清楚「为什么词面重排在这里帮了倒忙」。
    """
    modes = ["vector", "hybrid", "hybrid+rerank"]
    cases = get_eval_cases()
    detail = []
    for case in cases:
        row = {
            "id": case["id"],
            "category": case["category"],
            "question": case["question"],
            "expected": [normalize_chunk_id(i) for i in case["expected_doc_ids"]],
        }
        for mode in modes:
            results = pipeline.search(case["question"], top_k=top_k, mode=mode)
            row[mode] = _dedupe([normalize_chunk_id(r["id"]) for r in results])
        detail.append(row)
    return detail


def print_detail(detail: list[dict]) -> None:
    """打印逐题明细（只对有 ground truth 的用例，负例另说）。"""
    print("\n" + "=" * 64)
    print("逐题明细（top-5，已归一化去重）")
    print("=" * 64)
    for row in detail:
        if not row["expected"]:
            continue
        print(f"\n[{row['id']}] ({row['category']}) {row['question']}")
        print(f"  期望命中: {row['expected']}")
        print(f"  vector       : {row['vector']}")
        print(f"  hybrid       : {row['hybrid']}")
        print(f"  hybrid+rerank: {row['hybrid+rerank']}")


def write_markdown_report(report: dict, detail: list[dict], out_path: str, real: bool) -> None:
    """把完整评测报告（总表 + RRF 敏感性 + 逐题明细）写成 markdown 文件。"""
    modes = ["vector", "hybrid", "hybrid+rerank"]
    metric_names = ["recall@5", "precision@5", "mrr", "ndcg@5"]

    lines = []
    lines.append("# RAG 检索质量评测报告")
    lines.append("")
    lines.append(f"> 生成方式：`python -m backend.app.rag.eval.runner"
                 f"{' --real' if real else ''} --out {out_path}`")
    lines.append(f"> embedding：{'DashScope text-embedding-v3' if real else '哈希 n-gram 代理（词面，仅验证流程）'}")
    lines.append("")
    lines.append(f"top_k={report['top_k']}，共 {report['n_cases']} 条用例。")
    lines.append("")

    lines.append("## 总表")
    lines.append("")
    lines.append("| 配置 | " + " | ".join(metric_names) + " | 负例top1相似度 |")
    lines.append("|---|---|---|---|---|---|")
    for mode in modes:
        r = report[mode]
        cells = [mode] + [_pct(r[n]) for n in metric_names] + [f"{r['negative_avg_top1_sim']:.3f}"]
        lines.append("| " + " | ".join(cells) + " |")
    lines.append("")
    lines.append("- recall@5 / precision@5 / mrr / ndcg@5 只在有 ground truth 的用例上平均。")
    lines.append("- 负例 top1 相似度越低越好（知识库外问题不该召回高相似文档）。")
    lines.append("- hybrid+rerank 用 KeywordReranker（词面精排），近义干扰题上可能拉低 mrr——")
    lines.append("  这是「词面精排放大词面误导」的预期现象，真正纠正需要 cross-encoder 语义精排。")
    lines.append("")

    sens = report.get("rrf_sensitivity", {})
    if sens:
        lines.append("## RRF 参数敏感性（hybrid 模式）")
        lines.append("")
        lines.append("| k | recall@5 | mrr |")
        lines.append("|---|---|---|")
        for k in ["10", "30", "60", "100"]:
            if k in sens:
                lines.append(f"| {k} | {_pct(sens[k]['recall@5'])} | {_pct(sens[k]['mrr'])} |")
        lines.append("")

    lines.append("## 逐题明细（top-5，已归一化去重）")
    lines.append("")
    for row in detail:
        lines.append(f"### [{row['id']}] ({row['category']}) {row['question']}")
        lines.append("")
        lines.append(f"- 期望命中：`{row['expected']}`")
        lines.append(f"- vector：`{row['vector']}`")
        lines.append(f"- hybrid：`{row['hybrid']}`")
        lines.append(f"- hybrid+rerank：`{row['hybrid+rerank']}`")
        lines.append("")

    from pathlib import Path
    Path(out_path).parent.mkdir(parents=True, exist_ok=True)
    Path(out_path).write_text("\n".join(lines), encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description="RAG 检索质量评测")
    parser.add_argument("--real", action="store_true",
                        help="用真实 DashScope embedding（需先 build_knowledge_base）")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--detail", action="store_true",
                        help="输出逐题明细（每条用例在三种配置下的 top-5 结果）")
    parser.add_argument("--out", type=str, default=None,
                        help="把完整报告（含明细）写入指定 markdown 文件")
    args = parser.parse_args()

    if args.real:
        pipeline = build_real_pipeline()
        if not pipeline.available:
            print("❌ 未配置 DASHSCOPE_API_KEY，无法用真实 embedding 评测。")
            print("   请先配置 backend/.env 里的 DASHSCOPE_API_KEY，再运行：")
            print("   python -m backend.app.rag.build_knowledge_base")
            return
        print("✅ 使用真实 DashScope embedding 评测（请确保已构建知识库）")
    else:
        pipeline = build_offline_pipeline()
        print("⚠️  离线模式：使用哈希 n-gram 代理 embedding。")
        print("   只用于验证评测流程 + 展示词面可区分的行为，结果不代表真实语义检索质量。")
        print("   拿到真实数据请运行： python -m backend.app.rag.eval.runner --real")

    report = run(pipeline, top_k=args.top_k)
    print_report(report)

    if args.detail:
        detail = per_case_detail(pipeline, top_k=args.top_k)
        print_detail(detail)

    if args.out:
        detail = per_case_detail(pipeline, top_k=args.top_k)
        write_markdown_report(report, detail, args.out, real=args.real)
        print(f"\n✅ 完整报告已写入：{args.out}")


if __name__ == "__main__":
    main()
