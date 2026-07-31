# ql-wecom-service

青龙面板 x 企业微信回调桥接服务，通过企业微信自建应用直接管理和操作青龙面板。

## 功能

- **消息指令**：在企业微信中发送文本指令，查询/执行/管理青龙面板的任务、变量、订阅、脚本
- **应用菜单**：启动后自动创建底部固定菜单，点击即可操作（任务列表、执行/停止任务、设置变量等）
- **回调加密**：支持企业微信明文模式和安全加解密模式

## 架构

```
企业微信 App → 回调 URL → Nginx 反代 → ql-wecom-service → 青龙面板 API
                                            ↕
                                     ghcr.io 容器镜像
```

## 快速部署

### 1. 创建企业微信应用

企业微信管理后台 → 应用管理 → 创建自建应用，记录以下信息：

| 配置项 | 获取位置 |
|--------|---------|
| CorpID | 我的企业 → 企业信息 |
| AgentID | 应用管理 → 自建应用 |
| Secret | 应用管理 → 自建应用 → 应用密钥 |

设置接收消息 → API 接收：
- URL：`https://你的域名/wecom/callback`
- Token：自定义字符串（如 `random_token_123`）
- EncodingAESKey：随机生成（明文模式可跳过）
- 加密模式：推荐明文模式（NORMAL），简单部署用 Nginx + TLS 即可

### 2. 配置文件

```bash
cp .env.example .env
vim .env
```

必填项：

```ini
# 企业微信
WE_COM_CORP_ID=wwb124c7b08d2b3aff
WE_COM_AGENT_ID=1000009
WE_COM_CORP_SECRET=你的应用密钥
WE_COM_ENCODING_AES_KEY=你的AESKey（明文模式留空）
WE_COM_ENCRYPT_MODE=NORMAL
CALLBACK_HOST=https://你的域名
CALLBACK_TOKEN=random_token_123

# 青龙面板 - 容器内必须用宿主机 IP（Docker 网桥网关）
QL_BASE_URL=http://172.20.0.1:5700
QL_TOKEN=你的青龙Token
```

> ⚠️ `QL_BASE_URL` 在容器内**不能写 localhost**，容器内的 localhost 指向自身。需填写宿主机 Docker 网桥网关 IP。查看方法：
> ```bash
> docker network inspect bridge --format '{{range .IPAM.Config}}{{.Gateway}}{{end}}'
> ```
> 通常为 `172.17.0.1` 或 `172.20.0.1`。

### 3. 启动服务

```bash
docker compose up -d
docker compose logs -f
```

看到 `✅ 应用菜单创建成功` 即为部署完成。在企业微信打开应用即可看到底部菜单。

## 指令大全

### 文本指令

发送 `ql` 前缀的消息（前缀可在 `.env` 中修改 `BOT_PREFIX`）：

```
任务         查看任务列表
执行 签到    运行指定任务
停止 签到    停止正在运行的任务
日志 签到    查看任务最新日志
状态 签到    查看任务详情（状态、定时、上次执行时间）
禁用任务 签到 禁用任务
启用任务 签到 启用任务
删除任务 签到 删除任务

变量         查看环境变量列表（值自动脱敏）
设变量 NAME=VALUE 备注   创建环境变量
查看变量 1   查看变量详情
删变量 1     删除变量
禁用变量 1   禁用变量
启用变量 1   启用变量

订阅         查看订阅列表
运行订阅 网易云 运行指定订阅

脚本         查看脚本列表
系统         查看青龙系统信息
通知 标题=内容 发送青龙通知
```

### 菜单

启动后自动创建底部菜单，点击即可触发对应操作：

| 常用查询 | 任务操作 | 更多设置 |
|---------|---------|---------|
| 任务列表 | 执行任务 | 设置变量 |
| 变量列表 | 停止任务 | 发送通知 |
| 订阅列表 | 查看日志 | 删除任务 |
| 脚本列表 | 查看状态 | 使用帮助 |
| 系统信息 | 禁用/启用 | |

## Nginx 反代（推荐）

生产环境建议前置 Nginx + Let's Encrypt SSL：

```nginx
server {
    listen 443 ssl http2;
    server_name 你的域名;

    ssl_certificate     /etc/letsencrypt/live/你的域名/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/你的域名/privkey.pem;

    location /wecom/callback {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## 开发

```bash
# 本地运行（不依赖 Docker）
pip install -r requirements.txt
cp .env.example .env
vim .env  # QL_BASE_URL 写 localhost 即可
python run.py

# 或使用 Docker
docker compose up -d
```

## 项目结构

```
ql-wecom-service/
├── app.py              # FastAPI 主服务：回调处理、消息发送、菜单初始化
├── commands.py         # 指令解析与青龙操作逻辑
├── menu.py             # 企业微信菜单定义、创建与点击事件处理
├── ql_client.py        # 青龙面板 OpenAPI 客户端封装
├── settings.py         # 环境变量配置解析
├── run.py              # 本地开发入口
├── vl/__init__.py      # 企业微信消息加解密工具 (WXBizMsgCrypt)
├── Dockerfile          # 容器构建
├── docker-compose.yml  # 容器编排
├── .env.example        # 配置模板
└── requirements.txt    # Python 依赖
```

## License

MIT
