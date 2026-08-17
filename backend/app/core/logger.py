import logging
from pathlib import Path

# 锚定日志目录到 backend/logs/，避免因启动位置(CWD)不同导致日志散落
# logger.py 位于 backend/app/core/，故 backend 目录为 parents[2]
BACKEND_DIR = Path(__file__).resolve().parents[2]
log_dir = BACKEND_DIR / "logs"
log_dir.mkdir(parents=True, exist_ok=True)

# 创建 Logger
logger = logging.getLogger("JobPilot")
logger.setLevel(logging.INFO)

# 防止重复添加 Handler
if not logger.handlers:

    formatter = logging.Formatter(
        fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    # 控制台
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    # 文件
    file_handler = logging.FileHandler(
        log_dir / "jobpilot.log",
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)