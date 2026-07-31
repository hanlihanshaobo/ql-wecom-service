# 青龙面板 → 企业微信回调服务

通过企业微信应用消息远程管理青龙面板。

## 指令

| 指令 | 说明 |
|------|------|
| `帮助` | 查看帮助 |
| `任务` / `任务列表` | 查看所有任务 |
| `执行 <任务名>` | 运行指定任务 |
| `停止 <任务名>` | 停止运行中的任务 |
| `日志 <任务名>` | 查看任务最近日志 |
| `状态 <任务名>` | 查看任务详细信息 |
| `禁用任务 <任务名>` | 禁用任务 |
| `启用任务 <任务名>` | 启用任务 |
| `删除任务 <任务名>` | 删除任务 |
| `变量` / `变量列表` | 查看环境变量 |
| `变量 <关键词>` | 搜索环境变量 |
| `设变量 <名称>=<值>` | 创建环境变量 |
| `查看变量 <ID>` | 查看变量详情 |
| `删变量 <ID>` | 删除变量 |
| `禁用变量 <ID>` | 禁用变量 |
| `启用变量 <ID>` | 启用变量 |
| `订阅` / `订阅列表` | 查看订阅列表 |
| `运行订阅 <订阅名>` | 手动运行订阅 |
| `脚本` / `脚本列表` | 查看脚本列表 |
| `系统` | 查看青龙系统信息 |
| `通知 <标题>=<内容>` | 发送系统通知 |

---

## 部署

### 1. 拉取镜像

镜像由 GitHub Actions 自动构建推送到 ghcr.io：

```bash
echo "YOUR_GITHUB_TOKEN" | docker login ghcr.io -u YOUR_USERNAME --password-stdin
docker pull ghcr.io/YOUR_USERNAME/ql-wecom-service:latest
```

或本地构建：

```bash
git clone <本仓库>
cd ql-wecom-service
```

### 2. 配置

```bash
cp .env.example .env
vim .env   # 填入实际的配置信息
```

### 3. 启动

```bash
docker compose up -d
```

### 4. nginx 反代

```nginx
location /wecom/callback {
    proxy_pass http://127.0.0.1:3000/wecom/callback;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
}
```

### 5. 企微后台配置

| 项 | 值 |
|------|------|
| URL | `https://your.domain.com/wecom/callback` |
| Token | `.env` 中 `CALLBACK_TOKEN` |
| EncodingAESKey | `.env` 中 `WE_COM_ENCODING_AES_KEY` |

---

## GitHub Actions

push 到 `main` 自动构建 `linux/amd64` + `linux/arm64` 镜像，推送到 `ghcr.io`。

## 项目结构

| 文件 | 作用 |
|------|------|
| `app.py` | FastAPI 服务，企微回调接收 + 消息回复 |
| `commands.py` | 指令解析 |
| `ql_client.py` | 青龙面板 OpenAPI 客户端 |
| `vl/__init__.py` | 企微消息加解密 + XML 解析 |
| `settings.py` | 从 `.env` 加载配置 |
| `Dockerfile` | Docker 镜像 |
| `docker-compose.yml` | Docker Compose 编排 |
| `.github/workflows/docker-build.yml` | CI 自动构建推送 |
