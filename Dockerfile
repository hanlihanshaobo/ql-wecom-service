FROM python:3.11-slim

WORKDIR /app

# 安装依赖
# pycryptodome 在 linux/arm/v7 无预编译 wheel，需临时安装 gcc 等编译工具链，
# 编译完成后立即卸载清理，保持镜像精简
COPY requirements.txt .
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential python3-dev \
    && pip install --no-cache-dir -r requirements.txt \
    && apt-get purge -y build-essential python3-dev \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

# 复制源码
COPY . .

EXPOSE 3000

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "3000"]
