# Day01

完成：
- 初始化 FastAPI
- 创建项目目录
- 创建虚拟环境
- 配置 requirements.txt
- 创建 .env
- 实现 Settings 配置中心
- FastAPI 成功读取配置

学习：
- BaseSettings
- SettingsConfigDict
- Working Directory
- Python Package
- uvicorn 启动方式
问题：
1. app 模块导入失败
2. .env 未读取

答案：
1. FastAPI 是 ASGI 应用，应该由 Uvicorn 等 ASGI Server 启动。使用 uvicorn app.main:app --reload 可以正确加载应用对象，并保证模块导入路径正确。
2. 项目目录结构优化

下一步：
实现 LLMService

# Day 02

完成内容
- 实现 LLMService
- 封装 OpenAI Client
- 实现 chat() 接口
- 添加异常处理

学到的知识
- Service Layer
- 单一职责原则
- 封装
- API 调用流程
- try...except

问题
1. 为什么封装 LLMService？
2. 为什么 chat() 返回 str？
3. 为什么不直接传 messages？

答案：
1. 封装 LLMService 主要是为了降低业务层和具体大模型 SDK 之间的耦合。如果业务代码直接依赖 OpenAI SDK，那么未来切换模型供应商或者 SDK 接口变化时，需要修改大量业务代码。通过 Service 层进行封装，可以提供一个稳定的调用接口，同时把模型初始化、异常处理、重试、日志记录等公共逻辑集中管理，提高代码的可维护性和扩展性。
2. 隐藏底层实现细节。降低业务代码和第三方 SDK 的耦合，同时如果未来更换模型供应商，只需要修改 Service 层即可。
3. messages 属于底层模型调用协议，而不是业务概念。封装 system_prompt 和 user_prompt，可以让业务层关注任务本身，同时由 LLMService 负责转换成模型需要的消息格式。如果加入 PromptManager、多轮对话、Memory 等模块，也可以保持接口稳定。

# Day03
完成内容
- 学习 Python logging 模块
- 理解 Logger、Handler、Formatter 的职责
- 完成企业级日志系统
- 成功输出第一条项目日志

今日收获
1. Logger 不负责输出，只负责管理日志。
2. Handler 负责将日志输出到不同目标。
3. Formatter 负责定义日志格式。
4. 一个 Logger 可以拥有多个 Handler。
5. 一个 Handler 通常对应一个 Formatter。

# Day4：PromptManager 模块开发

# 完成内容

1. PromptManager 初始化
2. 实现 get_prompt()，完成 Prompt 文件读取功能。
3. 实现 render_prompt()，新增 Prompt 渲染功能。

今日收获：
1. pathlib定位项目资源目录。 相比字符串路径更加稳定，可跨平台运行。
2. Prompt Cache 学习缓存思想。
3. PromptManager 遵循了单一职责原则（SRP）。