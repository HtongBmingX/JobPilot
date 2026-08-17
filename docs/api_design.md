# API 设计（v0.6.0）

> 所有端点均已落地，以下为当前真实接口。
> 限流：所有 Agent 端点每 IP 每分钟最多 20 次请求

---

## 健康检查

`GET /`

返回：`{"message": "JobPilot Backend Running!"}`

---

## 手写版 Agent

### 同步端点

`POST /agent/run`

请求体：
```json
{
  "query": "根据我的简历和这个 JD，给出面试准备建议",
  "resume": "简历原文（可选）",
  "jd": "岗位 JD 原文（可选）",
  "session_id": "可选，提供则跨请求保留 Memory 上下文"
}
```

返回：
```json
{ "answer": "基于 Memory 真实分析结果生成的最终答案" }
```

### 流式端点（SSE）

`POST /agent/run/stream`

请求体：同上

事件类型：
- `step_start` — 开始执行某个步骤（resume/jd/match），含 thought
- `step_done` — 步骤完成
- `synthesize_chunk` — 最终答案的文本片段
- `done` — 全部完成
- `error` — 出错（含 message）

---

## LangChain 版 Agent

### 同步端点

`POST /agent/langchain/run`

请求体：同手写版（query/resume/jd/session_id）

返回：`{ "answer": "..." }`

说明：`session_id` 映射为 LangGraph 的 `thread_id`，支持跨请求上下文保持。

### 流式端点（SSE）

`POST /agent/langchain/stream`

请求体：同上

事件类型：同手写版（step_start / step_done / synthesize_chunk / done / error）

---

## 文件摄入

`POST /upload`

请求：`multipart/form-data`，字段名 `file`（PDF / DOCX）

返回：
```json
{ "filename": "简历.pdf", "text": "解析出的纯文本" }
```

说明：内部调用 `IngestTool`（PyMuPDF / python-docx），是上传预处理，不经过 Agent 循环。

支持的文件类型：`.pdf`、`.docx`。其他格式返回 `400 FILE_INGEST_ERROR`。

---

## 错误响应格式

所有错误统一返回：

```json
{
  "error": "LLM_SERVICE_ERROR | LLM_RESPONSE_ERROR | AGENT_EXECUTION_ERROR | VALIDATION_ERROR | FILE_INGEST_ERROR",
  "message": "人类可读的错误描述"
}
```

HTTP 状态码：
| 错误码 | HTTP | 含义 |
|--------|------|------|
| LLM_SERVICE_ERROR | 502 | LLM API 调用失败 |
| LLM_RESPONSE_ERROR | 502 | LLM 返回格式不可解析 |
| AGENT_EXECUTION_ERROR | 500 | Agent 执行异常 |
| VALIDATION_ERROR | 400 | 输入参数验证失败 |
| FILE_INGEST_ERROR | 400 | 文件解析失败 |

---

## 限流

所有 Agent 端点（`/agent/*`）每 IP 每分钟最多 20 次请求。
超限返回 `429 Too Many Requests`：
```json
{ "detail": "请求过于频繁，请 60 秒后重试" }
```

Redis 不可用时限流自动放行。

---

## 跨域（CORS）

开发环境下 Vite proxy 已绕开跨域（前端请求同域，Vite 转发到 `:8000`）。

生产环境下 CORS 中间件放行：
```
Access-Control-Allow-Origin: http://127.0.0.1:5173
Access-Control-Allow-Origin: http://localhost:5173
```

生产部署时需替换为真实前端域名。
