import logging


logger = logging.getLogger("JobPilot")  # Create the application logger.
logger.setLevel(logging.INFO)
#debug适合开发阶段，全打印；
#info知道程序干了什么，但不会看到一堆debug
#error只有出错才知道，一般用于生产环境

console_handler = logging.StreamHandler()
formatter = logging.Formatter(
    fmt="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)