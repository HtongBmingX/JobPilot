# ===================================================================
# 阶段 1：构建阶段 — npm install + npm run build
# ===================================================================
FROM node:20-alpine AS builder

WORKDIR /app

# 先复制 package 文件（利用 Docker 层缓存）
COPY frontend/package.json frontend/package-lock.json* ./

# 安装依赖
RUN npm install

# 复制前端源码 + Vite 配置 + index.html
COPY frontend/ .

# 构建生产版本 → dist/ 目录
RUN npm run build

# ===================================================================
# 阶段 2：运行阶段 — nginx 托管静态文件
# ===================================================================
FROM nginx:alpine AS runner

# 把构建产物复制到 nginx 的静态文件目录
COPY --from=builder /app/dist /usr/share/nginx/html

# 用自定义 nginx 配置替换默认配置
COPY frontend/nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
