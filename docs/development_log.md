Day01

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

遇到的问题：

1. app 模块导入失败
2. .env 未读取

解决：

1. FastAPI 是 ASGI 应用，应该由 Uvicorn 等 ASGI Server 启动。使用 uvicorn app.main:app --reload 可以正确加载应用对象，并保证模块导入路径正确。
2. 项目目录结构优化

下一步：

实现 LLMService