"""
Plan schema 单测（断言式）

Plan 是 Planner 输出的数据模型，测默认值和 model_dump 的序列化行为。
"""

from backend.app.schemas.plan import Plan


def test_plan_default_action_input_empty():
    plan = Plan(thought="分析简历", action="resume")
    assert plan.action_input == {}


def test_plan_model_dump():
    plan = Plan(
        thought="做匹配",
        action="match",
        action_input={"resume_analysis": "x", "jd_analysis": "y"},
    )
    dumped = plan.model_dump()
    assert dumped["action"] == "match"
    assert dumped["action_input"]["resume_analysis"] == "x"


def test_plan_validate_from_json_string():
    """Plan.model_validate 能接受 dict（模拟 Planner 解析 JSON 后的结果）"""
    plan = Plan.model_validate({"thought": "t", "action": "finish", "action_input": {}})
    assert plan.action == "finish"
    assert plan.thought == "t"
