"""
RAG 检索质量评测指标（纯函数、确定性、可复现）

与 evaluation/deterministic_metrics.py 的区别：
- 那个测的是「工程可靠性」：状态机有没有路由到 search、search 有没有返回非空、
  回答有没有带来源标注。这三个是代码行为，100% 可复现，但**测不出检索质量**。
- 这里测的是「检索质量」：命中的文档对不对、正确文档排在第几位。
  这才是 RAG 的核心——召回了对的文档，生成才有据可依。

四个指标（信息检索领域标准）：

1. Recall@k —— 召回率：正确文档里，有多少被召回到了前 k 个结果。
   回答「找没找到」。k 太小会漏，k 太大上下文噪音多。
   公式：|检索到的相关文档| / |全部相关文档|

2. Precision@k —— 精确率：前 k 个结果里，有多少是真正相关的。
   回答「找得准不准」。k 太大精确率会下降（塞进无关文档）。

3. MRR —— 平均倒数排名：只关心「第一个正确文档排在第几位」。
   适合「用户只看第一个答案」的场景（如问答、搜索框联想）。
   公式：1 / 第一个正确结果的排名，没命中记 0。

4. NDCG@k —— 归一化折损累计增益：不仅看「找没找到」，还看「正确文档排得靠不靠前」。
   排名越靠前贡献越大（用 log 折损），对「排序质量」敏感。
   适合「多个正确文档、顺序重要」的场景（如推荐、多文档综述）。

为什么这几个而不是 LLM 打分？
- 检索评测的 ground truth 是「哪篇文档该被命中」，这是确定性的、可人工标注的。
- LLM 打分的 faithfulness 噪声大（同一个回答两次判定可能不同），不适合做检索层的
  ground truth。检索层用确定性指标，生成层才考虑用 LLM 判定。

设计约定：
- 单条用例的 negative（知识库外问题）没有 expected_doc_ids，返回 None 跳过该指标。
- 所有函数对空输入、k 越界都有防御，评测执行器不用额外判空。
"""

import math
from typing import Sequence


def _norm_ids(retrieved: Sequence[str]) -> list[str]:
    """把检索结果里的文档 id 统一成字符串列表（结果可能是 dict 或 str）。"""
    ids = []
    for item in retrieved:
        if isinstance(item, dict):
            ids.append(str(item.get("id", "")))
        else:
            ids.append(str(item))
    return ids


def recall_at_k(retrieved: Sequence[str], expected: Sequence[str], k: int) -> float | None:
    """
    Recall@k：正确文档被召回的比例。

    :param retrieved: 检索结果中的文档 id（按排序，可能含 dict）
    :param expected: 标注的正确文档 id
    :param k: 只看前 k 个结果
    :return: 0.0~1.0；expected 为空（negative 用例）返回 None
    """
    if not expected:
        return None
    got = set(_norm_ids(retrieved[:k]))
    want = set(str(x) for x in expected)
    return len(got & want) / len(want)


def precision_at_k(retrieved: Sequence[str], expected: Sequence[str], k: int) -> float | None:
    """
    Precision@k：前 k 个结果里正确的比例。

    :return: 0.0~1.0；expected 为空返回 None；retrieved 为空返回 0.0
    """
    if not expected:
        return None
    got = _norm_ids(retrieved[:k])
    if not got:
        return 0.0
    want = set(str(x) for x in expected)
    return len([g for g in got if g in want]) / len(got)


def mrr(retrieved: Sequence[str], expected: Sequence[str]) -> float | None:
    """
    MRR：第一个正确文档的排名倒数。

    只关心「第一个正确答案在第几位」。排名从 1 开始。
    """
    if not expected:
        return None
    want = set(str(x) for x in expected)
    for rank, item in enumerate(retrieved, start=1):
        rid = item.get("id") if isinstance(item, dict) else item
        if str(rid) in want:
            return 1.0 / rank
    return 0.0


def ndcg_at_k(retrieved: Sequence[str], expected: Sequence[str], k: int) -> float | None:
    """
    NDCG@k：归一化折损累计增益。

    对「正确文档排得靠前」敏感——排名越靠前贡献越大。
    DCG 用 1/log2(rank+1) 折损；IDCG 是理想排序（正确文档全部排最前面）的 DCG。
    """
    if not expected:
        return None
    want = set(str(x) for x in expected)
    got = _norm_ids(retrieved[:k])

    dcg = 0.0
    for i, gid in enumerate(got, start=1):
        if gid in want:
            dcg += 1.0 / math.log2(i + 1)

    # 理想排序：所有正确文档依次排在最前面（相关性按 1 计）
    n = min(len(want), k)
    idcg = sum(1.0 / math.log2(i + 1) for i in range(1, n + 1))
    if idcg == 0:
        return 0.0
    return dcg / idcg


def aggregate(values: Sequence[float | None], default: float = 0.0) -> float:
    """
    聚合一条指标在全部用例上的得分。

    约定：None（negative 用例，无 ground truth）不参与平均，
    但也没有提供证据——评测报告里要单独统计 negative 的命中行为，
    用「负例漏判率」衡量（见 eval_runner）。

    :param default: 若全部为 None（理论上不该发生），返回该默认值
    """
    valid = [v for v in values if v is not None]
    if not valid:
        return default
    return sum(valid) / len(valid)


# 所有对外暴露的指标名，供 eval_runner 反射调用
METRIC_FUNCS = {
    "recall@5": lambda r, e: recall_at_k(r, e, 5),
    "recall@3": lambda r, e: recall_at_k(r, e, 3),
    "precision@5": lambda r, e: precision_at_k(r, e, 5),
    "mrr": mrr,
    "ndcg@5": lambda r, e: ndcg_at_k(r, e, 5),
}
