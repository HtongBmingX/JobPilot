# API 设计（v0.9.3）

> 所有端点均已落地，以下为当前真实接口。
> 鉴权：除 `/`、`/status`、`/auth/*` 外，所有端点需 `Authorization: Bearer <access_token>`。
> 限流：Agent 端点（`/agent/*`）每 IP 每分钟最多 20 次请求。

---

## 健康检查

`GET /` → `{"message": "JobPilot Backend Running!"}`

---

## 鉴权

### 注册

`POST /auth/register`

```json
{ "username": "zhangsan", "password": "123456" }
```

返回：`{ "id": 1, "username": "zhangsan", "created_at": "..." }`

### 登录

`POST /auth/login`

```json
{ "username": "zhangsan", "password": "123456" }
```

返回：`{ "access_token": "...", "refresh_token": "...", "token_type": "bearer" }`
- access_token 30 分钟有效
- refresh_token 7 天有效

### 刷新 Token

`POST /auth/refresh`

```json
{ "refresh_token": "..." }
```

返回：新的 access_token + refresh_token

---

## 系统状态

`GET /status`（公开，不鉴权）

```json
{ "redis_connected": true, "agent_mode": "react" }
```

---

## 手写版 Agent

### 同步端点

`POST /agent/run`

```json
{
  "query": "分析我的简历",
  "resume": "简历原文（可选）",
  "jd": "岗位 JD 原文（可选）",
  "session_id": "可选，提供则跨请求保留 Memory 上下文"
}
```

返回：`{ "answer": "基于真实分析结果生成的最终答案" }`

### 流式端点（SSE）

`POST /agent/run/stream`

请求体同上。事件类型：
- `step_start` — 开始执行某步骤（resume/jd/match/search/interview），含 thought
- `step_done` — 步骤完成
- `synthesize_chunk` — 最终答案的文本片段
- `done` — 全部完成
- `error` — 出错（含 message）

---

## LangChain 版 Agent

`POST /agent/langchain/run`（同步）
`POST /agent/langchain/stream`（SSE 流式）

请求体、返回格式同手写版。`session_id` 映射为 LangGraph 的 `thread_id`。

---

## 文件摄入

`POST /upload`

请求：`multipart/form-data`，字段名 `file`（PDF / DOCX）

返回：`{ "filename": "简历.pdf", "text": "解析出的纯文本" }`

扫描版/图片型 PDF（无文本层）返回 `422`，提示上传可编辑 PDF 或粘贴文字。

---

## 投递看板

| 端点 | 方法 | 说明 |
|------|------|------|
| `/applications` | POST | 创建投递记录 |
| `/applications` | GET | 列表（可选 `?status=applied` 筛选） |
| `/applications/{id}` | PUT | 更新（状态/备注等，字段可选） |
| `/applications/{id}` | DELETE | 删除 |

创建请求体：
```json
{
  "company": "字节跳动",
  "position": "后端开发",
  "jd_text": "岗位描述（可选）",
  "match_score": "85%",
  "match_summary": "匹配分析摘要（可选）",
  "applied_at": "2026-08-17",
  "notes": "备注（可选）"
}
```

`status` 枚举：`applied` / `screening` / `interviewing` / `offered` / `rejected`

---

## 简历库（多简历管理）

| 端点 | 方法 | 说明 |
|------|------|------|
| `/resumes` | POST | 创建简历 |
| `/resumes` | GET | 列表（默认简历排前） |
| `/resumes/{id}` | PUT | 更新（可设为默认） |
| `/resumes/{id}` | DELETE | 删除 |

创建请求体：
```json
{ "name": "后端开发版", "content": "简历全文", "is_default": false }
```

---

## 用户画像（跨会话长期记忆）

| 端点 | 方法 | 说明 |
|------|------|------|
| `/profile` | GET | 获取画像（不存在则创建空画像） |
| `/profile` | PUT | 更新画像 |

更新请求体：
```json
{
  "tech_stack": "Python, FastAPI, Redis",
  "target_role": "后端开发工程师",
  "target_companies": "字节跳动, 腾讯",
  "education": "本科 / 软件工程",
  "experience_summary": "2 段后端实习"
}
```

---

## 错误响应格式

```json
{
  "error": "ERROR_CODE",
  "message": "人类可读的错误描述",
  "detail": "同 message（兼容前端读取）"
}
```

| 错误码 | HTTP | 含义 |
|--------|------|------|
| LLM_SERVICE_ERROR | 502 | LLM API 调用失败 |
| LLM_RESPONSE_ERROR | 502 | LLM 返回格式不可解析 |
| AGENT_EXECUTION_ERROR | 500 | Agent 执行异常 |
| VALIDATION_ERROR | 400 | 输入参数验证失败 |
| FILE_INGEST_ERROR | 400 | 文件解析失败 |
| INTERNAL_ERROR | 500 | 未知异常（不暴露内部细节） |

---

## 限流

Agent 端点（`/agent/*`）每 IP 每分钟最多 20 次请求，超限返回 `429`。
Redis 不可用时限流自动放行。

---

## 跨域（CORS）

开发环境 Vite proxy 绕开跨域（前端请求同域，Vite 转发到 `:8000`）。
生产环境 Nginx 反向代理统一域名，CORS 中间件放行前端来源。
