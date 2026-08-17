from backend.app.prompts.prompt_manager import PromptManager
from backend.app.services.llm_service import LLMService
from backend.app.schemas.plan import Plan
from backend.app.core.exceptions import LLMResponseError, LLMServiceError
from backend.app.core.logger import logger
from backend.app.agent.agent_state import AgentStateMachine
import json
import re


class Planner:
    """
    Agent 的"大脑"：Planner。

    Phase 2 重构后，职责精简化：
    - 代码状态机（AgentStateMachine）决定「当前允许哪些 action」
    - Planner（LLM）从 allowed 中选一个，并提取 action_input
    - LLM 不再需要"理解状态机规则"，只需要"从有限选项中做选择 + 提取文本"

    这是 prompt 驱动状态机和代码状态机的分界线：
    旧：LLM 需要同时理解规则 + 做决策 → 不可靠
    新：代码管规则，LLM 管选择 → 各司其职
    """

    def __init__(self):
        self.prompt_manager = PromptManager()
        self.llm = LLMService()

    def think(
            self,
            query: str,
            tools: str,
            memory: str = "",
            conversation_history: str = "",
    ) -> Plan:
        logger.info("Planner: 进入思考阶段")

        # Step 1: 已经在 Agent 侧通过代码状态机（AgentStateMachine）过滤了
        # 允许的 action 列表，Planner 只负责从 allowed 中选择并提取参数。

        # Step 2: LLM 决策
        system_prompt = self.prompt_manager.get_prompt("system")
        user_prompt = self.prompt_manager.render_prompt(
            "planner",
            query=query,
            tools=tools,
            memory=memory,
            conversation_history=conversation_history,
        )

        result = self.llm.chat(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
        )
        logger.info(f"Planner: LLM 返回成功，耗时 {result.elapsed}s")

        data = self._extract_json(result.content)
        logger.info(f"Planner: 解析得到 action={data.get('action')}")

        plan = Plan.model_validate(data)
        return plan

    @staticmethod
    def _extract_json(text: str) -> dict:
        if not text or not text.strip():
            raise LLMResponseError("LLM 返回为空，无法解析 JSON")

        # 1) 先试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 2) 去掉 ```json ... ``` 包裹
        cleaned = re.sub(r"^```(?:json)?\s*", "", text.strip(),
                         flags=re.IGNORECASE)
        cleaned = re.sub(r"\s*```$", "", cleaned)
        try:
            return json.loads(cleaned)
        except json.JSONDecodeError:
            pass

        # 3) 从文本中抽取第一个 {...} 块（模型在 JSON 前后说了多余的话）
        match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
        if match:
            try:
                return json.loads(match.group(0))
            except json.JSONDecodeError:
                pass

        raise LLMResponseError(
            f"无法从 LLM 返回解析 JSON，原始返回前 200 字符：{text[:200]}"
        )
