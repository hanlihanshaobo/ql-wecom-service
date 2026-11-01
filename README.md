# ql-wecom-service

青龙面板 x 企业微信机器人。通过企业微信自建应用直接管理和操作青龙面板。

支持两种部署方式：

- **青龙面板机器人插件（推荐）**：作为青龙自带的 Bot 运行，`python3 -m jbot` 常驻在青龙容器内，不需要额外的业务容器（仍需 Nginx/反代把公网回调转发到插件端口）
- **Docker 独立服务**：单独运行 `ql-wecom-service` 容器，适合已有独立服务的用户

## 功能

- **机器人指令**：在企业微信中发送文本指令，查询/执行/管理青龙面板的任务、变量、订阅、脚本、依赖、日志
- **应用菜单**：启动后自动创建底部固定菜单，点击即可操作
- **回调加密**：支持企业微信明文模式和安全加解密模式
- **消息去重**：按 `MsgId` 去重，避免企业微信超时重试导致脚本重复执行
- **长消息分片**：任务列表、日志等超长回复自动拆分发送

## 架构

### 青龙机器人插件模式

```
企业微信 App → 回调 URL → Nginx/反代 → 青龙容器 :3000
                                           ↓
                                   python3 -m jbot（本插件）
                                           ↓
                                   青龙 OpenAPI :5700
```

插件由青龙面板的 `ql bot` 命令安装和托管：代码放在 `/ql/data/jbot`，配置放在 `/ql/data/config/bot.json`。`ql bot` 用 `nohup` 启动进程，容器重启后不会自动恢复；需要开启青龙的 `AutoStartBot` 或在启动脚本中再次执行 `ql bot`。

### Docker 独立服务模式

```
企业微信 App → 回调 URL → Nginx 反代 → ql-wecom-service 容器 → 青龙面板 API
                                            ↕
                                     ghcr.io 容器镜像
```

## 方式一：青龙面板机器人插件（推荐）

### 1. 前置条件

- 青龙面板需要支持 `ql bot` 命令（较新版本，Python 3.9+）
- 青龙面板已创建 OpenAPI 应用：**系统设置 → 应用设置 → 创建应用**，记录 `Client ID` / `Client Secret`
- 企业微信已创建自建应用，并记录 `CorpID`、`AgentID`、`Secret`
- 青龙容器所在服务器的公网 IP 已加入企业微信应用 → **企业可信 IP**

### 2. 安装插件

推荐把配置写入青龙的持久化配置 `/ql/data/config/config.sh`，这样容器重启后 `AutoStartBot` 仍能拉起本插件：

```bash
docker exec -it qinglong bash

# 编辑青龙配置，加入：
#   AutoStartBot="true"
#   BotRepoUrl="https://github.com/hanlihanshaobo/ql-wecom-service"
vi /ql/data/config/config.sh

# 立即安装并启动
ql bot
```

如果只想临时安装，也可以在当前 shell 执行：

```bash
export BotRepoUrl=https://github.com/hanlihanshaobo/ql-wecom-service
ql bot
```

> `ql bot` 会读取 `BotRepoUrl` 的 `main` 分支，使用仓库中的 `jbot/requirements.txt` 和 `config/bot.json`，安装依赖后以 `python3 -m jbot` 启动。
>
> 安装本插件后，如果不再设置 `BotRepoUrl` 直接执行 `ql bot`，会重新安装青龙默认的 Telegram Bot 并覆盖本插件。请把 `BotRepoUrl` 写入容器的持久化环境变量（如 docker-compose 的 `environment` 或青龙 `config.sh`），不要只在当前 shell `export`。
>
> 如果之前安装过青龙默认 Telegram Bot，`/ql/data/config/bot.json` 已存在，`ql bot` 不会覆盖。请先备份并删除该文件，再执行安装以生成本插件的配置模板。

### 3. 修改配置

首次安装会生成 `/ql/data/config/bot.json`。编辑并填入企业微信和青龙配置：

```bash
vi /ql/data/config/bot.json
```

```json
{
  "wecom": {
    "corp_id": "你的CorpID",
    "agent_id": "你的AgentID",
    "corp_secret": "你的应用Secret",
    "encoding_aes_key": "你的EncodingAESKey",
    "encrypt_mode": "SAFETY"
  },
  "callback": {
    "host": "0.0.0.0",
    "port": 3000,
    "path": "/wecom/callback",
    "token": "你的回调Token",
    "secret": "",
    "public_url": "https://你的域名"
  },
  "qinglong": {
    "base_url": "http://127.0.0.1:5700",
    "client_id": "你的青龙ClientID",
    "client_secret": "你的青龙ClientSecret",
    "host": ""
  },
  "bot": {
    "prefix": "",
    "name": "QinglongBot",
    "allowed_users": [],
    "custom_script_filename": "",
    "custom_script_path": "",
    "custom_script_button_name": "执行自定义脚本"
  }
}
```

说明：

- `qinglong.base_url`：插件和青龙面板在同一个容器，保持 `http://127.0.0.1:5700` 即可
- `callback.port`：插件监听端口，默认 `3000`。需要把该端口暴露给反向代理
- `callback.secret`：明文模式下的附加校验参数。设置后回调 URL 需写成 `https://你的域名/wecom/callback?secret=你的密钥`；使用 `SAFETY` 加密模式时可留空
- `bot.prefix`：指令前缀，留空表示直接发送 `任务`；填 `ql` 后 `ql 任务` 和 `任务` 都可以
- `bot.allowed_users`：可选，企业微信 UserID 列表；留空允许所有人，填写后仅这些用户可执行指令
- 自定义脚本：`custom_script_filename` + `custom_script_path` 配置后，菜单按钮始终存在；未配置时点击会提示补充配置

### 4. 暴露回调端口

青龙容器默认只映射了 `5700`。任选一种方式让企业微信能访问 `3000`：

**方式 A：重新创建容器时增加端口映射**

```bash
-p 3000:3000
```

**方式 B：Nginx 直接代理到容器 IP（无需发布 3000）**

```nginx
location /wecom/callback {
    proxy_pass http://青龙容器IP:3000;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
}
```

企业微信后台 → 应用 → **接收消息 → API 接收**：

- URL：`https://你的域名/wecom/callback`
- Token：与 `callback.token` 一致
- EncodingAESKey：与 `wecom.encoding_aes_key` 一致
- 加密模式：推荐 `SAFETY`（需填写 EncodingAESKey）；如果使用明文 `NORMAL`，请务必设置 `callback.secret`

### 5. 重启并验证

修改配置后重新执行：

```bash
export BotRepoUrl=https://github.com/hanlihanshaobo/ql-wecom-service
ql bot
```

> `ql bot` 可能复用 `$QL_DATA_DIR/repo/diybot` 的旧克隆。更新代码时先删除该目录，或进入目录执行 `git pull`，再执行 `ql bot`。

验证：

```bash
curl http://127.0.0.1:3000/health
tail -f /ql/data/log/bot/nohup.log
```

看到 `✅ 企业微信应用菜单创建成功` 后，在企业微信打开应用，直接发送 `任务` 或点击底部菜单即可。

### 6. 当前分支手动安装

如果功能分支尚未合并到 `main`，可以把仓库复制到青龙容器后执行安装脚本：

```bash
# 在宿主机仓库目录执行
docker cp . qinglong:/tmp/ql-wecom-service
docker exec -it qinglong bash /tmp/ql-wecom-service/scripts/install-ql-bot.sh
```

脚本会复制 `jbot` 到 `/ql/data/jbot`、安装依赖、保留已有配置并重启机器人。已有配置如果是旧版 Telegram `bot.json`，脚本不会自动覆盖，请手动替换为 `config/bot.json` 的内容。

## 方式二：Docker 独立部署

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
- EncodingAESKey：随机生成（使用 SAFETY 加密模式时必填）
- 加密模式：推荐 `SAFETY`；如使用明文 `NORMAL`，请设置 `CALLBACK_SECRET` 并在回调 URL 后追加 `?secret=...`

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
WE_COM_ENCODING_AES_KEY=你的EncodingAESKey
WE_COM_ENCRYPT_MODE=SAFETY
CALLBACK_HOST=https://你的域名
CALLBACK_TOKEN=你的回调Token
CALLBACK_SECRET=

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

看到 `✅ 企业微信应用菜单创建成功` 即为部署完成。在企业微信打开应用即可看到底部菜单。

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
修改定时 1 0 8 * * *   修改任务定时
运行中任务       查看正在运行的任务

变量             查看环境变量列表（值自动脱敏）
设变量 NAME=VALUE 备注   创建环境变量
查看变量 1       查看变量详情
删变量 1         删除变量
禁用变量 1       禁用变量
启用变量 1       启用变量

订阅             查看订阅列表
创建订阅 URL 别名 添加订阅源
运行订阅 网易云   运行指定订阅
停止订阅 网易云   停止订阅
订阅日志 网易云   查看订阅日志

脚本             查看脚本列表
脚本详情 x.py    查看脚本详情
运行脚本 x.py    运行脚本
停止脚本 x.py    停止脚本
删除脚本 x.py    删除脚本
重命名脚本 a.py b.py  重命名脚本

系统             查看青龙系统信息
系统配置         查看系统配置
系统日志         查看系统日志
通知 标题=内容   发送青龙通知
检查更新 / 更新系统 / 重载系统 / 导出数据

依赖             查看依赖列表
安装依赖 名称 1  安装依赖（0=NodeJs 1=Python3 2=Linux）
删依赖 1         删除依赖
重装依赖 1       重装依赖

配置             查看配置文件列表
查看配置 config.sh   查看配置内容

日志列表         查看日志文件列表
日志详情 x.log   查看日志内容
删除日志 x.log   删除日志

运行命令 ql repo https://github.com/user/repo   执行 shell 命令
停止命令 12345   停止命令
```

### 菜单

启动后自动创建底部菜单，点击即可触发对应操作：

| 任务 | 资源 | 系统 |
|------|------|------|
| 任务操作 | 订阅操作 | 系统操作 |
| 运行中任务 | 脚本操作 | 日志管理 |
| | 依赖操作 | 命令操作 |
| | 变量操作 | 查看配置 |
| | 自定义脚本 | 使用帮助 |

> 自定义脚本：通过配置 `custom_script_filename` 和 `custom_script_path` 指定青龙中的脚本，点击按钮即可一键执行。菜单名通过 `custom_script_button_name` 自定义。

点击任务操作类按钮后，任务列表会带序号显示，只需回复 `执行 1` 即可操作对应任务，无需输入完整任务名。

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
        # 独立服务模式：127.0.0.1:3000
        # 青龙插件模式：青龙容器IP:3000
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
2. Nginx 配置已包含上述 `/cgi-bin/` 代理
3. 青龙面板通知设置中填写：

```
weWorkOrigin = https://你的域名
```

> 原理：青龙通知请求 → VPS Nginx（固定 IP，白名单内）→ 企微 API，绕过家庭动态 IP 限制。

## 开发

```bash
# 独立服务模式
pip install -r requirements.txt
cp .env.example .env
vim .env  # QL_BASE_URL 写 localhost 即可
python run.py

# 青龙插件模式（模拟青龙运行环境）
cd /path/to/ql/data
python3 -m jbot

# 或使用 Docker
docker compose up -d
```

## 项目结构

```
ql-wecom-service/
├── jbot/                    # 青龙机器人插件核心（python3 -m jbot）
│   ├── __main__.py          # 插件入口
│   ├── config.py            # bot.json + 环境变量配置
│   ├── server.py            # FastAPI 回调服务
│   ├── wecom.py             # 企业微信 API 客户端
│   ├── commands.py          # 指令解析与青龙操作
│   ├── menu.py              # 企业微信菜单定义与点击处理
│   ├── ql_client.py         # 青龙 OpenAPI 客户端
│   ├── crypto.py            # 企业微信消息加解密
│   └── requirements.txt     # 插件依赖
├── config/bot.json          # 青龙机器人插件配置模板
├── scripts/install-ql-bot.sh # 当前分支手动安装脚本
├── app.py                   # Docker 独立部署入口（兼容旧用法）
├── run.py                   # 本地开发入口
├── Dockerfile
├── docker-compose.yml
├── .env.example
├── LICENSE
└── requirements.txt
```

## 常见问题

**Q：企业微信群机器人（webhook）能用吗？**

群机器人 webhook 只能单向推送消息，不能接收指令。本项目的“用机器人调用”使用企业微信自建应用的回调，必须配置 `CorpID`、`AgentID`、`Secret` 和回调 URL。

**Q：明文模式（NORMAL）能用吗？**

企业微信自建应用回调通常是加密的（`msg_signature` + `<Encrypt>`），服务端会自动识别并解密，建议直接配置 `SAFETY` + `EncodingAESKey`。`NORMAL` 仅用于兼容非加密回调；使用 `NORMAL` 时请设置 `callback.secret` / `CALLBACK_SECRET`，否则任何能访问回调 URL 的人都可以调用机器人。

**Q：`ql bot` 启动后立刻退出？**

查看 `/ql/data/log/bot/nohup.log`。常见原因：端口被占用、依赖未安装成功、`config/bot.json` 路径或权限错误。`config/bot.json` 不是合法 JSON 时不会退出，而是回退到默认值并记录错误日志。

**Q：修改配置后如何生效？**

重新执行 `ql bot`，或使用 `scripts/install-ql-bot.sh` 重启。仅修改 `bot.json` 不会自动热加载。

## License

MIT
