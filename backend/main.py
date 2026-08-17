from fastapi import FastAPI, Depends, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from pathlib import Path
from backend.app.core.logger import logger
from backend.app.core.exceptions import ValidationError, LLMServiceError
from backend.app.core.error_handlers import register_error_handlers
from backend.app.core.rate_limit import rate_limit
from backend.app.core.database import Base, engine, get_db
from backend.app.core.auth import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    get_current_user,
    TokenResponse,
)
from backend.app.schemas.user import UserRegisterRequest, UserLoginRequest, UserResponse
from backend.app.schemas.application import ApplicationCreateRequest, ApplicationUpdateRequest, ApplicationResponse
from backend.app.schemas.resume_library import ResumeCreateRequest, ResumeUpdateRequest, ResumeResponse
from backend.app.schemas.user_profile import UserProfileUpdateRequest, UserProfileResponse
from backend.app.repositories.user_repo import UserRepository
from backend.app.repositories.application_repo import ApplicationRepository
from backend.app.repositories.resume_repo import ResumeRepository
from backend.app.repositories.user_profile_repo import UserProfileRepository
from backend.app.models.user import User
from backend.app.models.application import Application
from backend.app.models.resume import Resume
from backend.app.models.user_profile import UserProfile
from backend.app.agent.jobpilot_agent import JobPilotAgent
from backend.app.tools.registry import ToolRegistry
from backend.app.tools.resume_tool import ResumeTool
from backend.app.tools.jd_tool import JDTool
from backend.app.tools.match_tool import MatchTool
from backend.app.tools.interview_tool import InterviewTool
from backend.app.tools.ingest_tool import IngestTool
from backend.app.tools.search_tool import SearchTool
from backend.app.schemas.status import SystemStatus
from backend.app.core.redis_client import get_client as get_redis_client
from sqlalchemy.orm import Session
import json

app = FastAPI()

# CORS — 必须先于路由和异常处理器注册
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://127.0.0.1:5173", "http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 全局异常处理器 — 在 CORS 之后注册，避免拦截 OPTIONS 请求
register_error_handlers(app)

# ================================================================
# 数据库初始化 — 启动时自动创建表（开发友好，生产用 Alembic migration）
# ================================================================
Base.metadata.create_all(bind=engine)

registry = ToolRegistry()
registry.register(ResumeTool())
registry.register(JDTool())
registry.register(MatchTool())
registry.register(InterviewTool())
registry.register(SearchTool())
agent = JobPilotAgent(registry)

# 让所有 Tool 的 Service 共享 agent 的 LLMService 实例
# 这样 LLMService 的 token 计数器会累计所有 Tool 调用
shared_llm = agent.llm
for name in registry.list_tools():
    tool = registry.get(name)
    if hasattr(tool, 'service') and hasattr(tool.service, 'llm'):
        tool.service.llm = shared_llm

# LangChain Agent — 懒加载，用到才 import
# 避免启动时就加载 langgraph，减少冷启动时间和依赖耦合
_langchain_agent = None

def _get_langchain_agent():
    """懒加载 LangChain Agent，首次调用时才 import langgraph 等依赖"""
    global _langchain_agent
    if _langchain_agent is None:
        from backend.app.langchain_agent.agent import LangChainAgent
        _langchain_agent = LangChainAgent()
    return _langchain_agent


@app.get("/")
def root():
    return {"message": "JobPilot Backend Running!"}


# ================================================================
#  鉴权路由（JWT + bcrypt）
# ================================================================

@app.post("/auth/register", response_model=UserResponse, status_code=201)
def auth_register(req: UserRegisterRequest, db: Session = Depends(get_db)):
    """
    用户注册。

    request body:
        {"username": "zhangsan", "password": "123456"}

    密码用 bcrypt 哈希后存储，不存明文。
    用户名重复返回 409 Conflict。
    """
    user_repo = UserRepository(db)

    # 检查用户名是否已存在
    if user_repo.get_by_username(req.username):
        raise HTTPException(status_code=409, detail="用户名已存在")

    user = user_repo.create(
        username=req.username,
        hashed_password=hash_password(req.password),
    )
    logger.info(f"新用户注册：{user.username}")
    return user


@app.post("/auth/login", response_model=TokenResponse)
def auth_login(req: UserLoginRequest, db: Session = Depends(get_db)):
    """
    用户登录。

    request body:
        {"username": "zhangsan", "password": "123456"}

    返回 access_token（30分钟）和 refresh_token（7天）。
    用户名或密码错误返回 401。
    """
    user_repo = UserRepository(db)

    # 查用户是否存在
    user = user_repo.get_by_username(req.username)
    if not user:
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    # 验证密码
    if not verify_password(req.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="用户名或密码错误")

    logger.info(f"用户登录：{user.username}")
    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


class RefreshRequest(BaseModel):
    refresh_token: str


@app.post("/auth/refresh", response_model=TokenResponse)
def auth_refresh(body: RefreshRequest, db: Session = Depends(get_db)):
    """
    刷新 access_token。

    Body: {"refresh_token": "xxx"}

    用 refresh_token 换取新的 access_token。refresh_token 必须是
    有效的、未过期的、类型为 "refresh" 的 JWT。

    安全说明：refresh_token 通过请求体（Body）传递，而非查询参数，
    避免被代理、浏览器历史、服务器日志等中间环节记录泄露。
    """
    try:
        payload = decode_token(body.refresh_token)
    except Exception:
        raise HTTPException(status_code=401, detail="refresh_token 无效或已过期")

    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="请使用 refresh_token（而非 access_token）刷新")

    # 确认用户仍然存在
    user_repo = UserRepository(db)
    user = user_repo.get_by_id(int(payload["sub"]))
    if not user:
        raise HTTPException(status_code=401, detail="用户不存在")

    return TokenResponse(
        access_token=create_access_token(user.id),
        refresh_token=create_refresh_token(user.id),
    )


# ================================================================
#  系统状态路由
# ================================================================

@app.get("/status", response_model=SystemStatus)
def get_status():
    """返回当前系统状态快照 — 前端定时拉取渲染状态栏（公开接口，不鉴权）"""
    from backend.app.core.redis_client import get_client as _redis_get_client

    return SystemStatus(
        redis_connected=_redis_get_client() is not None,
        agent_mode="react",
    )


# ================================================================
#  投递看板路由
# ================================================================

@app.post("/applications", response_model=ApplicationResponse, status_code=201)
def create_application(
    req: ApplicationCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建一条投递记录"""
    repo = ApplicationRepository(db)
    app = repo.create(
        user_id=current_user.id,
        company=req.company,
        position=req.position,
        jd_text=req.jd_text,
        match_score=req.match_score,
        match_summary=req.match_summary,
        applied_at=req.applied_at,
        notes=req.notes,
    )
    logger.info(f"用户 {current_user.username} 创建投递记录：{app.company} - {app.position}")
    return app


@app.get("/applications", response_model=list[ApplicationResponse])
def list_applications(
    status: str | None = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取当前用户的所有投递记录，可按状态筛选"""
    repo = ApplicationRepository(db)
    return repo.list_by_user(current_user.id, status=status)


@app.put("/applications/{app_id}", response_model=ApplicationResponse)
def update_application(
    app_id: int,
    req: ApplicationUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新投递记录——改状态、加备注等"""
    repo = ApplicationRepository(db)
    # 只传有值的字段
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    app = repo.update(app_id, current_user.id, **updates)
    if not app:
        raise HTTPException(status_code=404, detail="投递记录不存在")
    return app


@app.delete("/applications/{app_id}", status_code=204)
def delete_application(
    app_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除投递记录"""
    repo = ApplicationRepository(db)
    ok = repo.delete(app_id, current_user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="投递记录不存在")


# ================================================================
#  简历库路由（多简历管理）
# ================================================================

@app.post("/resumes", response_model=ResumeResponse, status_code=201)
def create_resume(
    req: ResumeCreateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """创建一份简历"""
    repo = ResumeRepository(db)
    if req.is_default:
        repo.clear_default(current_user.id)
    resume = repo.create(
        user_id=current_user.id,
        name=req.name,
        content=req.content,
        is_default=req.is_default,
    )
    logger.info(f"用户 {current_user.username} 创建简历：{resume.name}")
    return resume


@app.get("/resumes", response_model=list[ResumeResponse])
def list_resumes(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取用户的所有简历（默认简历排前面）"""
    repo = ResumeRepository(db)
    return repo.list_by_user(current_user.id)


@app.put("/resumes/{resume_id}", response_model=ResumeResponse)
def update_resume(
    resume_id: int,
    req: ResumeUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新简历"""
    repo = ResumeRepository(db)
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    # 设为默认时清除其他默认标记
    if updates.get("is_default"):
        repo.clear_default(current_user.id)
    resume = repo.update(resume_id, current_user.id, **updates)
    if not resume:
        raise HTTPException(status_code=404, detail="简历不存在")
    return resume


@app.delete("/resumes/{resume_id}", status_code=204)
def delete_resume(
    resume_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """删除简历"""
    repo = ResumeRepository(db)
    ok = repo.delete(resume_id, current_user.id)
    if not ok:
        raise HTTPException(status_code=404, detail="简历不存在")


# ================================================================
#  用户画像路由（跨会话长期记忆）
# ================================================================

@app.get("/profile", response_model=UserProfileResponse)
def get_profile(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """获取用户画像（不存在则创建空画像）"""
    repo = UserProfileRepository(db)
    return repo.get_or_create(current_user.id)


@app.put("/profile", response_model=UserProfileResponse)
def update_profile(
    req: UserProfileUpdateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """更新用户画像"""
    repo = UserProfileRepository(db)
    updates = {k: v for k, v in req.model_dump().items() if v is not None}
    profile = repo.update(current_user.id, **updates)
    logger.info(f"用户 {current_user.username} 更新画像：{updates.keys()}")
    return profile


class AgentRunRequest(BaseModel):
    query: str
    resume: str | None = None      # 可选：单独传简历原文
    jd: str | None = None          # 可选：单独传 JD 原文
    session_id: str | None = None  # 可选：跨请求保留记忆

class AgentRunResponse(BaseModel):
    answer: str


def _format_user_profile(profile: UserProfile | None) -> str | None:
    """把画像对象格式化成给 Agent 看的文本，画像为空时返回 None"""
    if not profile:
        return None
    parts = []
    if profile.target_role:
        parts.append(f"目标岗位：{profile.target_role}")
    if profile.tech_stack:
        parts.append(f"技术栈：{profile.tech_stack}")
    if profile.target_companies:
        parts.append(f"目标公司：{profile.target_companies}")
    if profile.education:
        parts.append(f"学历背景：{profile.education}")
    if profile.experience_summary:
        parts.append(f"经历摘要：{profile.experience_summary}")
    return "\n".join(parts) if parts else None


@app.post("/agent/run", response_model=AgentRunResponse)
def agent_run(
    req: AgentRunRequest,
    _rate: None = Depends(rate_limit(max_requests=20)),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    logger.info("收到 /agent/run 请求 | session_id=%s | user=%s", req.session_id, current_user.username)

    # 读用户画像（跨会话记忆）
    profile_repo = UserProfileRepository(db)
    user_profile = _format_user_profile(profile_repo.get_by_user(current_user.id))

    try:
        answer = agent.execute(
            query=req.query,
            resume=req.resume,
            jd=req.jd,
            session_id=req.session_id,
            user_profile=user_profile,
        )
        return AgentRunResponse(answer=answer)
    except LLMServiceError as e:
        logger.error(f"/agent/run LLM 异常：{e.message}")
        return JSONResponse(status_code=502, content={"error": e.code, "message": e.message})
    except Exception as e:
        logger.error(f"/agent/run 未捕获异常：{e}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": "server_error", "message": "服务器内部错误"})


# ================================================================
#  LangChain Agent 端点（Phase 4 — 与手写版并行）
# ================================================================

@app.post("/agent/langchain/run", response_model=AgentRunResponse)
def agent_langchain_run(
    req: AgentRunRequest,
    current_user: User = Depends(get_current_user),
):
    """LangChain 版 Agent 同步端点"""
    logger.info("收到 /agent/langchain/run 请求 | session_id=%s | user=%s", req.session_id, current_user.username)

    full_query = req.query
    if req.resume:
        full_query = f"简历内容：\n{req.resume}\n\n{full_query}"
    if req.jd:
        full_query = f"{full_query}\n\nJD内容：\n{req.jd}"

    thread_id = req.session_id or "default"
    try:
        answer = _get_langchain_agent().run(query=full_query, thread_id=thread_id)
        return AgentRunResponse(answer=answer)
    except Exception as e:
        logger.error(f"/agent/langchain/run 异常：{e}", exc_info=True)
        return JSONResponse(status_code=500, content={"error": str(e)})


@app.post("/agent/langchain/stream")
async def agent_langchain_stream(
    req: AgentRunRequest,
    current_user: User = Depends(get_current_user),
):
    """LangChain 版 Agent 流式端点"""
    logger.info("收到 /agent/langchain/stream 请求 | session_id=%s | user=%s", req.session_id, current_user.username)

    full_query = req.query
    if req.resume:
        full_query = f"简历内容：\n{req.resume}\n\n{full_query}"
    if req.jd:
        full_query = f"{full_query}\n\nJD内容：\n{req.jd}"

    thread_id = req.session_id or "default"

    def event_generator():
        try:
            for event in _get_langchain_agent().run_stream(
                query=full_query,
                thread_id=thread_id,
            ):
                sse_lines = []
                if event.get("event"):
                    sse_lines.append(f"event: {event['event']}")
                sse_lines.append(f"data: {json.dumps(event['data'], ensure_ascii=False)}")
                yield "\n".join(sse_lines) + "\n\n"
        except Exception as e:
            logger.error(f"[SSE-LangChain] 异常：{e}", exc_info=True)
            yield f"event: error\ndata: {json.dumps({'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/agent/run/stream")
async def agent_run_stream(
    req: AgentRunRequest,
    _rate: None = Depends(rate_limit(max_requests=20)),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    流式端点：通过 Server-Sent Events (SSE) 实时推送 Agent 执行过程。

    SSE 事件类型：
        step_start       — 开始执行某个步骤（resume/jd/match）
        step_done        — 步骤完成
        synthesize_chunk — 最终答案的一个文本片段
        done             — 全部完成
        error            — 出错（含错误信息）

    前端用 EventSource 或 fetch + ReadableStream 消费。

    设计决策：独立端点而非在 /agent/run 上加 ?stream=true 参数。
    因为响应格式完全不同（JSON vs text/event-stream），
    独立端点让路由层的职责更清晰——FastAPI 的依赖注入和文档生成也更直观。
    """
    logger.info("收到 /agent/run/stream 请求 | session_id=%s | user=%s", req.session_id, current_user.username)

    # 读用户画像（跨会话记忆）
    profile_repo = UserProfileRepository(db)
    user_profile = _format_user_profile(profile_repo.get_by_user(current_user.id))

    def event_generator():
        """
        SSE 事件生成器。

        把 JobPilotAgent.execute_stream 返回的事件字典序列化为
        SSE 格式：data: <JSON>\n\n

        try/except 保证即使 Agent 内部崩了，
        前端也能收到一个 error 事件而不是看到连接断开。
        """
        try:
            for event in agent.execute_stream(
                query=req.query,
                resume=req.resume,
                jd=req.jd,
                session_id=req.session_id,
                user_profile=user_profile,
            ):
                # SSE 格式：event + data，每条以 \n\n 结束
                sse_lines = []
                if event.get("event"):
                    sse_lines.append(f"event: {event['event']}")
                sse_lines.append(f"data: {json.dumps(event['data'], ensure_ascii=False)}")
                yield "\n".join(sse_lines) + "\n\n"
        except Exception as e:
            logger.error(f"[SSE] Agent 执行异常：{e}", exc_info=True)
            yield f"event: error\ndata: {json.dumps({'message': str(e)}, ensure_ascii=False)}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # 禁用 Nginx 缓冲（如果部署时有 Nginx 在前的准备）
        },
    )

@app.post("/upload")
async def upload(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
):
    import tempfile, os
    suffix = Path(file.filename).suffix
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=suffix) as tmp:
            tmp.write(await file.read())
            tmp_path = tmp.name
        text = IngestTool().run(tmp_path)   # 复用上面的工具

        # 扫描件检测：PDF 提取出空文本，大概率是扫描版/图片型 PDF（无文本层）
        if not text.strip():
            raise HTTPException(
                status_code=422,
                detail="这看起来是扫描版或图片型 PDF，无法直接提取文字。请上传可编辑的 PDF / DOCX，或直接把简历文字粘贴到输入框。",
            )
        return {"filename": file.filename, "text": text}
    finally:
        # 无论解析成功与否，都清理临时文件，避免磁盘残留
        if tmp_path and os.path.exists(tmp_path):
            os.unlink(tmp_path)