"""
JobPilot 自定义异常体系

为什么需要自定义异常？
1. 区分错误类型：LLM 错误 vs 业务错误 vs 输入错误 — 不同错误需要不同处理
2. 统一错误格式：所有异常通过 FastAPI exception_handler 统一返回 JSON
3. 可追踪：每个异常带错误码和上下文，日志更精准
4. 面试价值：自定义异常体系是生产级项目的基本要求
"""


class JobPilotError(Exception):
    """JobPilot 基础异常"""
    def __init__(self, message: str, code: str = "INTERNAL_ERROR", status_code: int = 500):
        self.message = message
        self.code = code
        self.status_code = status_code
        super().__init__(message)


class LLMServiceError(JobPilotError):
    """LLM 服务异常：API 调用失败、超时、返回格式错误"""
    def __init__(self, message: str, original_error: Exception | None = None):
        detail = f"{message}（根因：{original_error}）" if original_error else message
        super().__init__(detail, code="LLM_SERVICE_ERROR", status_code=502)


class LLMResponseError(JobPilotError):
    """LLM 返回内容不可解析：JSON 格式错误、字段缺失"""
    def __init__(self, message: str):
        super().__init__(message, code="LLM_RESPONSE_ERROR", status_code=502)


class AgentExecutionError(JobPilotError):
    """Agent 执行异常：Tool 不存在、状态机异常、循环超限"""
    def __init__(self, message: str):
        super().__init__(message, code="AGENT_EXECUTION_ERROR", status_code=500)


class ValidationError(JobPilotError):
    """输入验证异常：缺少必要参数、文件格式不支持"""
    def __init__(self, message: str):
        super().__init__(message, code="VALIDATION_ERROR", status_code=400)


class FileIngestError(JobPilotError):
    """文件解析异常：PDF/DOCX 读取失败、文件损坏"""
    def __init__(self, message: str):
        super().__init__(message, code="FILE_INGEST_ERROR", status_code=400)
