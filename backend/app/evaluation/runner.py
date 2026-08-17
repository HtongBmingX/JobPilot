"""
评测执行器 — 批量跑评测用例，输出 Markdown 报告
"""

import time
from datetime import datetime
from pathlib import Path

from backend.app.evaluation.metrics.faithfulness import FaithfulnessMetric
from backend.app.evaluation.metrics.relevancy import AnswerRelevancyMetric
from backend.app.evaluation.metrics.recall import ContextRecallMetric
from backend.app.evaluation.test_cases import TEST_CASES
from backend.app.evaluation.rag_test_cases import get_rag_test_cases
from backend.app.agent.jobpilot_agent import JobPilotAgent
from backend.app.tools.registry import ToolRegistry
from backend.app.tools.resume_tool import ResumeTool
from backend.app.tools.jd_tool import JDTool
from backend.app.tools.match_tool import MatchTool
from backend.app.tools.interview_tool import InterviewTool
from backend.app.tools.search_tool import SearchTool
from backend.app.core.logger import logger


class EvaluationRunner:
    """
    评测执行器 — 对每个测试用例调用 Agent，计算三个指标，生成报告。

    支持两种模式：
    - run_all(): 基础能力评测（简历分析、匹配等）
    - run_rag(): RAG 知识库问答评测（faithfulness/recall 才有意义的场景）
    """

    def __init__(self):
        # 初始化 Agent（和 main.py 相同的 Tool 配置，含 SearchTool）
        registry = ToolRegistry()
        registry.register(ResumeTool())
        registry.register(JDTool())
        registry.register(MatchTool())
        registry.register(InterviewTool())
        registry.register(SearchTool())
        self.agent = JobPilotAgent(registry)

        # 初始化三个评测指标
        self.faithfulness = FaithfulnessMetric()
        self.relevancy = AnswerRelevancyMetric()
        self.recall = ContextRecallMetric()

    def run_single(self, case: dict) -> dict:
        """对单个用例执行 Agent 调用并评测（通用实现）"""
        logger.info(f"开始评测用例：{case['id']} — {case['name']}")

        # 执行 Agent：简历/JD 作为独立参数传入（和真实前端一致，不拼进 query）
        start = time.perf_counter()
        try:
            answer = self.agent.execute(
                query=case["question"],
                resume=case.get("resume") or None,
                jd=case.get("jd") or None,
            )
            elapsed = round(time.perf_counter() - start, 2)
        except Exception as e:
            logger.error(f"用例 {case['id']} Agent 执行失败：{e}")
            return {
                "id": case["id"],
                "name": case["name"],
                "error": str(e),
                "answer": "",
                "elapsed": 0,
                "faithfulness": None,
                "relevancy": None,
                "recall": None,
            }

        sources = case.get("sources", "")
        if not sources:
            sources = (case.get("resume", "") + "\n\n" + case.get("jd", "")).strip()

        # 计算三个指标
        try:
            faith_result = self.faithfulness.score(answer, sources) if sources else {"score": 1.0}
        except Exception as e:
            logger.warning(f"faithfulness 计算失败：{e}")
            faith_result = {"score": 0.0, "error": str(e)}

        try:
            relev_result = self.relevancy.score(case["question"], answer)
        except Exception as e:
            logger.warning(f"relevancy 计算失败：{e}")
            relev_result = {"score": 0.0, "error": str(e)}

        try:
            recall_result = self.recall.score(answer, sources) if sources else {"score": 1.0}
        except Exception as e:
            logger.warning(f"recall 计算失败：{e}")
            recall_result = {"score": 0.0, "error": str(e)}

        return {
            "id": case["id"],
            "name": case["name"],
            "answer": answer[:500] + ("..." if len(answer) > 500 else ""),
            "elapsed": elapsed,
            "faithfulness": faith_result,
            "relevancy": relev_result,
            "recall": recall_result,
        }

    def run_all(self) -> list[dict]:
        """批量运行所有基础用例"""
        results = []
        for case in TEST_CASES:
            result = self.run_single(case)
            results.append(result)
            logger.info(f"用例 {case['id']} 完成：faithfulness={result.get('faithfulness', {}).get('score', 'N/A')}, relevancy={result.get('relevancy', {}).get('score', 'N/A')}, recall={result.get('recall', {}).get('score', 'N/A')}")
        return results

    def run_rag(self) -> list[dict]:
        """
        批量运行 RAG 知识库问答用例。

        这是 faithfulness/recall 最有意义的评测场景——
        sources 是明确的知识库文档，可以真实衡量"回答是否忠于检索内容"。
        """
        from backend.app.rag.rag_pipeline import get_rag_pipeline
        pipeline = get_rag_pipeline()
        if not pipeline.available:
            logger.error("RAG 评测需要配置 DASHSCOPE_API_KEY 且知识库已构建")
            return []

        results = []
        for case in get_rag_test_cases():
            result = self.run_single(case)
            results.append(result)
            logger.info(f"RAG 用例 {case['id']} 完成：faithfulness={result.get('faithfulness', {}).get('score', 'N/A')}, recall={result.get('recall', {}).get('score', 'N/A')}")
        return results

    def generate_report(self, results: list[dict], output_path: str = None) -> str:
        """生成 Markdown 评测报告"""
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        lines = [
            "# JobPilot 评测报告",
            f"",
            f"> 生成时间：{now}",
            f"> 评测用例数：{len(results)}",
            f"",
            "---",
            f"",
            "## 总览",
            f"",
            "| 指标 | 平均分 | 最低分 | 最高分 |",
            "|------|--------|--------|--------|",
        ]

        # 计算统计
        # 计算统计（过滤掉带 error 的用例和分数为 None/NaN 的结果）
        faith_scores = [
            r.get("faithfulness", {}).get("score", 0)
            for r in results
            if r.get("faithfulness") and not r.get("error") and r.get("faithfulness", {}).get("score") is not None
        ]
        relev_scores = [
            r.get("relevancy", {}).get("score", 0)
            for r in results
            if r.get("relevancy") and not r.get("error") and r.get("relevancy", {}).get("score") is not None
        ]
        recall_scores = [
            r.get("recall", {}).get("score", 0)
            for r in results
            if r.get("recall") and not r.get("error") and r.get("recall", {}).get("score") is not None
        ]

        for name, scores in [("Faithfulness", faith_scores), ("Relevancy", relev_scores), ("Recall", recall_scores)]:
            if scores:
                lines.append(f"| {name} | {sum(scores)/len(scores):.2%} | {min(scores):.0%} | {max(scores):.0%} |")
            else:
                lines.append(f"| {name} | N/A | N/A | N/A |")

        lines.extend([
            "",
            "---",
            "",
            "## 逐用例详情",
            "",
        ])

        for r in results:
            lines.append(f"### {r['id']} — {r['name']}")
            lines.append(f"")
            lines.append(f"- **耗时**：{r.get('elapsed', 'N/A')} 秒")
            if r.get("error"):
                lines.append(f"- **⚠️ 错误**：{r['error']}")
            else:
                faith = r.get("faithfulness", {})
                relev = r.get("relevancy", {})
                rec = r.get("recall", {})
                lines.append(f"- **Faithfulness**：{faith.get('score', 0):.0%}（{faith.get('supported', '?')}/{faith.get('total', '?')} 条陈述被支持）")
                lines.append(f"- **Relevancy**：{relev.get('score', 0):.2%}")
                lines.append(f"- **Recall**：{rec.get('score', 0):.0%}（{rec.get('covered', '?')}/{rec.get('total', '?')} 条信息点被覆盖）")
            lines.append(f"")
            lines.append(f"<details><summary>Agent 回答（前 500 字）</summary>")
            lines.append(f"")
            lines.append(f"```")
            lines.append(r.get("answer", "（无回答）"))
            lines.append(f"```")
            lines.append(f"</details>")
            lines.append(f"")

        report = "\n".join(lines)

        if output_path:
            Path(output_path).write_text(report, encoding="utf-8")
            logger.info(f"评测报告已保存到：{output_path}")

        return report


def run():
    """命令行入口：基础能力评测"""
    runner = EvaluationRunner()
    results = runner.run_all()
    output = Path(__file__).resolve().parents[3] / "logs" / "evaluation_report.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    report = runner.generate_report(results, str(output))
    print(report)
    print(f"\n报告已保存到：{output}")


def run_rag():
    """命令行入口：RAG 知识库问答评测"""
    runner = EvaluationRunner()
    results = runner.run_rag()
    if not results:
        print("RAG 评测未执行：请确认已配置 DASHSCOPE_API_KEY 且已构建知识库")
        return
    output = Path(__file__).resolve().parents[3] / "logs" / "rag_evaluation_report.md"
    output.parent.mkdir(parents=True, exist_ok=True)
    report = runner.generate_report(results, str(output))
    print(report)
    print(f"\nRAG 评测报告已保存到：{output}")


if __name__ == "__main__":
    run()
