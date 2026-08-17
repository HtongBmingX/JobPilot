# ===================================================================
# 阶段 1：构建阶段 — 只做一件事：装 Python 依赖
# ===================================================================
FROM python:3.11-slim AS builder

# 设置工作目录
WORKDIR /app

# 先复制依赖文件（利用 Docker 层缓存 — 依赖不常变，代码常变）
COPY backend/requirements.txt .

# 安装依赖到临时目录 /install
# --no-cache-dir: 不缓存下载的包，减小体积
# --target: 安装到指定目录而不是系统 site-packages
RUN pip install --no-cache-dir --target=/install -r requirements.txt

# ===================================================================
# 阶段 2：运行阶段 — 只复制必要的运行时文件
# ===================================================================
FROM python:3.11-slim AS runner

# 安装 hiredis 所需的 C 编译器运行时（很小的库）
# 如果没有这个，import hiredis 会报 ImportError
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# 从构建阶段复制已安装的依赖
COPY --from=builder /install /usr/local/lib/python3.11/site-packages

# 复制后端源码
COPY backend/ ./backend/

# 暴露端口
EXPOSE 8000

# 启动命令：uvicorn 在容器内监听 0.0.0.0（所有网络接口）
# 如果只监听 127.0.0.1，宿主机无法访问容器内的服务
CMD ["python", "-m", "uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]
