"""RAG 检索质量评测包。

包含：
- metrics.py     —— Recall@k / Precision@k / MRR / NDCG@k 四个指标纯函数
- eval_cases.py  —— 24 条带标注 ground truth 的评测集
- runner.py      —— 评测执行器（多配置对比 + k 敏感性 + 负例行为 + 报告）
"""
