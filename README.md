# ql-wecom-service

青龙面板 x 企业微信智能机器人。通过企业微信智能机器人「API 模式 → 长连接」接收消息，直接管理和操作青龙面板。

**不需要公网 IP、端口映射、回调 URL 或 Nginx 反向代理。**

## 功能

- **机器人指令**：在企业微信单聊或群聊中 @机器人，查询/执行/管理青龙面板的任务、变量、订阅、脚本、依赖、日志
- **长连接**：WebSocket 主动连接企业微信，自动心跳、断线重连
- **消息去重**：按 `msgid` 去重，避免重复执行
- **长消息分片**：任务列表、日志等超长回复自动拆分发送
- **用户白名单**：可通过 `allowed_users` 限制哪些用户可以使用
- **欢迎语**：用户首次进入机器人会话时自动回复使用提示

## 架构

```
企业微信智能机器人
        ↕  WebSocket 长连接（wss://openws.work.weixin.qq.com）
青龙容器内 python3 -m jbot
        ↓
青龙 OpenAPI :5700
```

插件由青龙面板的 `ql bot` 命令安装和托管：代码放在 `/ql/data/jbot`，配置放在 `/ql/data/config/bot.json`。`ql bot` 用 `nohup` 启动进程，容器重启后不会自动恢复；需要开启青龙的 `AutoStartBot` 或在启动脚本中再次执行 `ql bot`。

## 快速开始

### 1. 创建企业微信智能机器人

企业微信管理后台 → **管理工具 → 智能机器人 → 创建机器人**：

- 选择 **手动创建**
- 选择 **API 模式**
- 连接方式选择 **长连接（无需域名/IP）**
- 记录页面中的 **BotID** 和 **Secret**

> API 模式只能选择一种连接方式：长连接或设置接收消息回调地址。选择长连接后，不需要配置 URL、Token、EncodingAESKey。

### 2. 创建青龙 OpenAPI 应用

青龙面板 → **系统设置 → 应用设置 → 创建应用**，记录 `Client ID` / `Client Secret`。

建议只授予机器人需要的权限，或直接使用管理员应用。

### 3. 安装插件

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

如果只想临时安装：

```bash
export BotRepoUrl=https://github.com/hanlihanshaobo/ql-wecom-service
ql bot
```

> `ql bot` 会读取 `BotRepoUrl` 的 `main` 分支，使用仓库中的 `jbot/requirements.txt` 和 `config/bot.json`，安装依赖后以 `python3 -m jbot` 启动。
>
> 安装本插件后，如果不再设置 `BotRepoUrl` 直接执行 `ql bot`，会重新安装青龙默认的 Telegram Bot 并覆盖本插件。请把 `BotRepoUrl` 写入容器的持久化环境变量（如 docker-compose 的 `environment` 或青龙 `config.sh`），不要只在当前 shell `export`。
>
> 如果 `/ql/data/config/bot.json` 已存在（例如默认 Telegram Bot 或旧版自建应用配置），`ql bot` 不会覆盖。请先备份并删除该文件，再执行安装以生成本插件的配置模板。

### 4. 修改配置

首次安装会生成 `/ql/data/config/bot.json`。此时配置模板为空，机器人会提示未配置并退出；填好配置后执行第 5 步重启即可。

```bash
vi /ql/data/config/bot.json
```

```json
{
  "wecom_bot": {
    "bot_id": "你的BotID",
    "secret": "你的Secret",
    "ws_url": "wss://openws.work.weixin.qq.com",
    "heartbeat_interval": 30,
    "max_reconnect_attempts": -1,
    "welcome_message": "发送「帮助」查看可用指令"
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

- `wecom_bot.bot_id` / `secret`：企业微信智能机器人页面获取
- `wecom_bot.heartbeat_interval`：心跳间隔（秒），默认 30
- `wecom_bot.max_reconnect_attempts`：最大重连次数，`-1` 表示无限重连
- `qinglong.base_url`：插件和青龙面板在同一个容器，保持 `http://127.0.0.1:5700` 即可
- `bot.prefix`：指令前缀，留空表示直接发送 `任务`；填 `ql` 后 `ql 任务` 和 `任务` 都可以
- `bot.allowed_users`：可选，企业微信 UserID 列表；留空允许所有人，填写后仅这些用户可执行指令
- `custom_script_filename` + `custom_script_path`：配置后发送 `自定义脚本` 可一键运行指定脚本

### 5. 重启并验证

```bash
export BotRepoUrl=https://github.com/hanlihanshaobo/ql-wecom-service
ql bot
```

> `ql bot` 可能复用 `$QL_DATA_DIR/repo/diybot` 的旧克隆。更新代码时先删除该目录，或进入目录执行 `git pull`，再执行 `ql bot`。

查看日志：

```bash
tail -f /ql/data/log/bot/nohup.log
```

看到以下日志即为连接成功：

```text
✅ 企业微信智能机器人认证成功
```

### 6. 使用机器人

- **单聊**：在企业微信中打开机器人会话，直接发送 `任务`、`帮助` 等指令
- **群聊**：把机器人拉进群，发送 `@机器人 任务`；代码会自动去掉 @ 前缀

首次进入会话会收到欢迎语，发送 `帮助` 查看全部指令。

## 指令大全

### 任务

```
任务 / 任务列表
执行 1
停止 1
日志 1
状态 1
禁用任务 1
启用任务 1
删除任务 1
修改定时 1 0 8 * * *
运行中任务
```

任务名可以用序号代替，序号与 `任务` 列表一致。

### 环境变量

```
变量 / 变量列表 [关键词]
设变量 NAME=VALUE 备注
查看变量 1
删变量 1
禁用变量 1
启用变量 1
```

环境变量值会自动脱敏显示。

### 订阅

```
订阅 / 订阅列表
创建订阅 https://github.com/user/repo 别名
运行订阅 网易云
停止订阅 网易云
禁用订阅 网易云
启用订阅 网易云
订阅日志 网易云
```

### 脚本

```
脚本 / 脚本列表
脚本详情 x.py
运行脚本 x.py
停止脚本 x.py
删除脚本 x.py
重命名脚本 a.py b.py
自定义脚本
```

### 系统 / 依赖 / 配置 / 日志

```
系统
系统配置
系统日志
清系统日志
检查更新
更新系统
重载系统
导出数据
通知 标题=内容

依赖 / 依赖列表
依赖详情 1
安装依赖 名称 1
删依赖 1
重装依赖 1

配置 / 配置列表
查看配置 config.sh

日志列表
日志详情 x.log
删除日志 x.log
```

### 命令管理

```
运行命令 ql repo https://github.com/user/repo
停止命令 12345
```

## Docker 独立部署（可选）

不使用青龙插件、单独跑一个容器时，也可以直接使用长连接模式。

```bash
cp .env.example .env
vim .env
```

必填：

```ini
WECOM_BOT_ID=你的BotID
WECOM_BOT_SECRET=你的Secret

# 青龙面板 - 容器内必须用宿主机 IP（Docker 网桥网关）
QL_BASE_URL=http://172.20.0.1:5700
QL_CLIENT_ID=你的青龙ClientID
QL_CLIENT_SECRET=你的青龙ClientSecret
```

启动：

```bash
docker compose up -d
docker compose logs -f
```

> `QL_BASE_URL` 在容器内**不能写 localhost**，容器内的 localhost 指向自身。需填写宿主机 Docker 网桥网关 IP。查看方法：
> ```bash
> docker network inspect bridge --format '{{range .IPAM.Config}}{{.Gateway}}{{end}}'
> ```
> 通常为 `172.17.0.1` 或 `172.20.0.1`。

Docker 模式不需要暴露任何端口。

## 当前分支手动安装

如果功能分支尚未合并到 `main`，可以把仓库复制到青龙容器后执行安装脚本：

```bash
# 在宿主机仓库目录执行
docker cp . qinglong:/tmp/ql-wecom-service
docker exec -it qinglong bash /tmp/ql-wecom-service/scripts/install-ql-bot.sh
```

脚本会复制 `jbot` 到 `/ql/data/jbot`、安装依赖、保留已有配置并重启机器人。已有配置如果不是智能机器人格式（例如旧版 Telegram 或自建应用 `bot.json`），脚本不会自动覆盖，请手动替换为 `config/bot.json` 的内容。

## 开发

```bash
pip install -r requirements.txt
cp .env.example .env
vim .env  # 填 WECOM_BOT_ID / WECOM_BOT_SECRET / QL_*

python run.py
```

或：

```bash
python -m jbot
```

## 项目结构

```
ql-wecom-service/
├── jbot/                    # 青龙机器人插件核心（python3 -m jbot）
│   ├── __main__.py          # 插件入口
│   ├── bot_ws.py            # 智能机器人 WebSocket 长连接
│   ├── config.py            # bot.json + 环境变量配置
│   ├── commands.py          # 指令解析与青龙操作
│   ├── ql_client.py         # 青龙 OpenAPI 客户端
│   ├── text.py              # 长文本分片
│   ├── requirements.txt     # 插件依赖
│   └── ...                  # 旧版自建应用回调代码（不再作为默认入口）
├── config/bot.json          # 青龙机器人插件配置模板
├── scripts/install-ql-bot.sh # 当前分支手动安装脚本
├── app.py                   # 旧版自建应用回调入口（可选）
├── run.py                   # 本地开发入口（长连接）
├── Dockerfile               # Docker 镜像（长连接模式）
├── docker-compose.yml
├── .env.example
├── LICENSE
└── requirements.txt
```

## 常见问题

**Q：企业微信群机器人 webhook 能用吗？**

群机器人 webhook 只能单向推送消息，不能接收指令。本项目使用**企业微信智能机器人**的 API 模式（长连接），不是群机器人 webhook，也不是自建应用回调。

**Q：需要公网 IP 或域名吗？**

不需要。长连接由你的服务器主动连接企业微信，适合家庭内网、没有公网 IP 的青龙面板。

**Q：同一机器人可以同时开多个连接吗？**

不可以。每个智能机器人同一时间只能保持一个有效长连接。新连接会踢掉旧连接，旧连接会收到 `disconnected_event` 并停止重连。请只运行一个 `python -m jbot` 实例。

**Q：群聊里 @机器人 没反应？**

确认机器人已加入该群，并且消息以 `@机器人名` 开头。单聊不需要 @。

**Q：`allowed_users` 填什么？**

填企业微信的 `userid`。如果机器人创建者不是企业超级管理员，回调中的 `from.userid` 可能是加密 ID；可以先留空，在日志中查看实际值再填入。

**Q：`ql bot` 启动后立刻退出？**

查看 `/ql/data/log/bot/nohup.log`。常见原因：

- `wecom_bot.bot_id` / `secret` 未填或填错
- 依赖安装失败
- 同一机器人已有其他长连接实例

**Q：修改配置后如何生效？**

重新执行 `ql bot`，或使用 `scripts/install-ql-bot.sh` 重启。仅修改 `bot.json` 不会自动热加载。

## License

MIT
