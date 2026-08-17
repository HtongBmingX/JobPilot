"""
Context Recall（上下文召回）评测指标

定义：来源材料中的关键信息有没有在回答中被覆盖。

算法：
1. 用 LLM 从来源材料中提取关键信息点
2. 对每个关键信息点，检查它是否在回答中出现
3. Recall = 被覆盖的关键信息点数 / 总关键信息点数

面试要点：Recall 和 Faithfulness 是互补的——
Faithfulness 检查回答是否"多说了"（编造了不在来源中的内容），
Recall 检查回答是否"少说了"（遗漏了来源中的重要信息）。
两个指标一起才能完整评估回答质量。
"""

from backend.app.services.llm_service import LLMService


class ContextRecallMetric:
    def __init__(self, llm: LLMService = None):
        self.llm = llm or LLMService()

    def extract_key_points(self, sources: str) -> list[str]:
        """从来源材料中提取关键信息点"""
        prompt = f"""请从以下求职分析材料中，提取关键信息点。每行一条，用 - 开头。

来源材料：
{sources}

关键信息点："""

        result = self.llm.chat(
            system_prompt="你是一个擅长信息提取的助手。只输出关键点列表。",
            user_prompt=prompt,
        )
        points = []
        for line in result.content.split("\n"):
            stripped = line.strip()
            if stripped.startswith("- "):
                points.append(stripped[2:])
            elif stripped.startswith("-"):
                points.append(stripped[1:])
        return points

    def check_coverage(self, point: str, answer: str) -> bool:
        """检查关键信息点是否在回答中被覆盖"""
        prompt = f"""请判断以下关键信息点是否在回答中被提及或暗示。只回答 YES 或 NO。

信息点：{point}

回答：{answer[:2000]}

回答中是否包含或暗示了这条信息？"""

        result = self.llm.chat(
            system_prompt="你是一个擅长信息匹配的助手。只输出 YES 或 NO。",
            user_prompt=prompt,
        )
        return "YES" in result.content.upper()

    def score(self, answer: str, sources: str) -> dict:
        """
        计算 recall 分数。

        返回：
            score: 0.0-1.0 的召回分数
            covered: 被覆盖的信息点数
            total: 总信息点数
            points: [(point, is_covered), ...] 明细
        """
        points = self.extract_key_points(sources)
        if not points:
            return {"score": 1.0, "covered": 0, "total": 0, "points": []}

        details = []
        covered_count = 0
        for point in points:
            is_covered = self.check_coverage(point, answer)
            details.append({"point": point, "covered": is_covered})
            if is_covered:
                covered_count += 1

        return {
            "score": covered_count / len(points) if points else 1.0,
            "covered": covered_count,
            "total": len(points),
            "points": details,
        }
