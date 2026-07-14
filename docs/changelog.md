# Changelog

## v0.1.0（当前版本）

### 新增

#### 基础设施

- 新增项目配置管理（Pydantic Settings）
- 新增日志模块（Logger）
- 新增 PromptManager
- 支持 Prompt 模板缓存
- 支持 Prompt 模板渲染
- 新增 LLMService
- 支持 DeepSeek API 调用
- 新增 ChatResult 数据模型

---

#### 业务模块

新增 ResumeService

支持：

- 简历分析（Analyze）
- 简历评分（Score）
- 简历优化（Optimize）
- 简历总结（Summarize）

新增 JDService

支持：

- 岗位分析（Analyze）

新增 MatchService

支持：

- 简历与岗位匹配
- 匹配度分析
- 差距分析
- 风险分析
- 面试建议
- 投递建议

---

#### 架构升级

新增 BaseService

所有 AI Service 统一继承 BaseService。

统一封装：

- PromptManager
- LLMService
- _chat()

减少重复代码，提高可维护性。

---

#### 测试

新增：

- test_resume_service.py
- test_jd_service.py
- test_match_service.py

所有测试通过。