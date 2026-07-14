# JobPilot Architecture

## 整体架构

                PromptManager
                      │
                      ▼
                BaseService
                      │
      ┌───────────────┼───────────────┐
      ▼               ▼               ▼
 ResumeService   JDService    MatchService
      │               │               │
      └───────────────┼───────────────┘
                      ▼
                 LLMService
                      ▼
                 DeepSeek API

---

## 设计原则

1. 单一职责原则（SRP）

ResumeService
仅负责简历相关业务。

JDService
仅负责岗位相关业务。

MatchService
仅负责匹配分析。

---

2. DRY（Don't Repeat Yourself）

公共逻辑统一放入 BaseService。

---

3. Prompt 与业务解耦

所有 Prompt 使用 Markdown 模板管理。

避免业务代码中出现 Prompt 字符串。

---

4. 数据模型统一

所有请求与返回使用 Pydantic Schema。

统一接口输入输出。

---

## 下一阶段

Memory

Workflow

Tool

Agent

React Frontend

FastAPI API