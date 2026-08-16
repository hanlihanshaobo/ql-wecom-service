# ql-wecom-service

青龙面板 x 企业微信回调桥接服务，通过企业微信自建应用直接管理和操作青龙面板。

## 功能

- **消息指令**：在企业微信中发送文本指令，查询/执行/管理青龙面板的任务、变量、订阅、脚本
- **应用菜单**：启动后自动创建底部固定菜单，点击即可操作（任务/订阅/脚本/依赖/变量操作、日志/命令管理、查看配置等）
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

设置开发者 → 企业可信 IP → 添加 VPS 公网 IP

设置接收消息 → API 接收：
- URL：`https://你的域名/wecom/callback`
- Token：自定义字符串（如 `random_token_123`）
- EncodingAESKey：随机生成（明文模式可跳过）
- 加密模式：推荐明文模式（NORMAL），有 Nginx + TLS 即可

### 2. 配置文件

```bash
cp .env.example .env
vim .env
```

必填项：

```ini
# 企业微信
WE_COM_CORP_ID=你的CorpID
WE_COM_AGENT_ID=你的AgentID
WE_COM_CORP_SECRET=你的应用Secret
WE_COM_ENCODING_AES_KEY=你的EncodingAESKey（明文模式留空）
WE_COM_ENCRYPT_MODE=NORMAL
CALLBACK_HOST=https://你的域名
CALLBACK_TOKEN=你的回调Token

# 青龙面板 - 容器内必须用宿主机 IP（Docker 网桥网关）
QL_BASE_URL=http://172.20.0.1:5700
QL_CLIENT_ID=你的青龙ClientID
QL_CLIENT_SECRET=你的青龙ClientSecret

# 自定义脚本（可选）：点击菜单按钮一键运行指定脚本
CUSTOM_SCRIPT_FILENAME=my_script.py
CUSTOM_SCRIPT_PATH=scripts   # 脚本所在子目录，根目录则留空
CUSTOM_SCRIPT_BUTTON_NAME=论坛签到   # 菜单按钮显示的文字
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

在企业微信中直接发送以下指令（无需前缀，直接匹配关键词）：

```
任务             查看任务列表
执行 1           按序号运行任务（也支持任务名）
停止 1           按序号停止任务
日志 1           查看任务最新日志
状态 1           查看任务详情（状态、定时、上次执行时间）
禁用任务 1       禁用任务
启用任务 1       启用任务
删除任务 1       删除任务
运行中任务       查看正在运行的任务
修改定时 1 0 8 * * *   修改任务定时（cron表达式）

变量             查看环境变量列表（值自动脱敏）
设变量 NAME=VALUE 备注   创建环境变量
查看变量 1       查看变量详情
删变量 1         删除变量
禁用变量 1       禁用变量
启用变量 1       启用变量

订阅             查看订阅列表
创建订阅 https://github.com/user/repo 别名   添加订阅源
运行订阅 网易云   运行指定订阅

脚本             查看脚本列表
系统             查看青龙系统信息
通知 标题=内容   发送青龙通知

依赖             查看依赖列表
配置             查看配置文件列表

命令             查看命令列表
新建命令 名称 ql repo https://xxx   创建命令
命令详情 1       查看命令详情
运行命令 1       运行命令
删命令 1         删除命令
```

### 菜单

启动后自动创建底部菜单，点击即可触发对应操作：

| 任务 | 资源 | 系统 |
|------|------|------|
| 任务操作 | 订阅操作 | 系统操作 |
| 运行中任务 | 脚本操作 | 日志管理 |
|          | 依赖操作 | 命令操作 |
|          | 变量操作 | 查看配置 |
|          | 自定义脚本 | 使用帮助 |

> 自定义脚本：通过 `.env` 配置 `CUSTOM_SCRIPT_FILENAME` 和 `CUSTOM_SCRIPT_PATH` 指定青龙中的脚本，点击按钮即可一键执行。菜单名通过 `CUSTOM_SCRIPT_BUTTON_NAME` 自定义。

按资源类型分类：**任务**（任务操作/运行中任务）、**资源**（订阅/脚本/依赖/变量/自定义脚本）、**系统**（系统操作/日志管理/命令操作/配置/帮助）。点击带"操作"的按钮后，会先显示对应列表，并附上全部操作指令提示，只需回复如 `执行 1`、`日志 1`、`禁用任务 1`、`修改定时 1 0 8 * * *`、`创建订阅 <仓库URL>`、`新建命令 <名称> <内容>`、`删变量 3`、`日志详情 <文件名>` 即可操作，无需输入完整名称。

## Nginx 反代（推荐）

生产环境建议前置 Nginx + Let's Encrypt SSL：

```nginx
server {
    listen 443 ssl http2;
    server_name 你的域名;

    ssl_certificate     /etc/letsencrypt/live/你的域名/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/你的域名/privkey.pem;

    # 企业微信回调
    location /wecom/callback {
        proxy_pass http://127.0.0.1:3000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # 代理企业微信 API（解决家庭网络 IP 不在白名单的问题） 可选
    location /cgi-bin/ {
        proxy_pass https://qyapi.weixin.qq.com;
        proxy_ssl_server_name on;
        proxy_set_header Host qyapi.weixin.qq.com;
    }
}
```

### 解决青龙通知 60020 错误（家庭网络场景）

如果青龙面板部署在家庭内网（动态 IP），无法加入企业微信可信 IP 白名单，通知会报错：

```
{"errcode":60020,"errmsg":"not allow to access from your ip"}
```

**解决方案**：利用 VPS 固定 IP 做代理中转。

1. 确保 VPS 的 IP 已加入企业微信应用 → **企业可信 IP**
2. Nginx 配置已包含上述 `/cgi-bin/` 代理（见上方配置）
3. 青龙面板通知设置中填写：

```
weWorkOrigin = https://你的域名
```

> 原理：青龙通知请求 → VPS Nginx（固定 IP，白名单内）→ 企微 API，绕过家庭动态 IP 限制。

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
