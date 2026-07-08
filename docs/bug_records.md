Bug001
标题：
ModuleNotFoundError

现象：
No module named app

原因：
直接运行 main.py

解决：
使用： uvicorn app.main:app --reload

经验：
FastAPI 项目不要直接运行 main.py

Bug002
标题：
Settings ValidationError

现象：
OPENAI_API_KEY missing

原因：
.env 未正确读取

解决：
检查工作目录

经验：
BaseSettings 读取 .env 与程序启动目录有关。