import logging
from pathlib import Path

# 创建日志目录
log_dir = Path("logs")
log_dir.mkdir(exist_ok=True)

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