# QQ Bot Bridge
（一位普通的大学生兴趣使然和大模型一起做的有关于Claude code qq robot的小拙作，希望能帮助到别人，也更希望会有人提出问题来改进）
通过 **NapCat + Claude Code** 实现与 QQ 聊天——你在 QQ 上发消息，Claude Code 用完整能力回复。

## 架构

```
                    +----------+       +-----------+       +----------+
  QQ 用户 ──消息──> |  NapCat  | ──WS──> | qq_daemon | ──写入─> | queue.jsonl |
                    | (Docker) | <──HTTP─ | (Python)  |       +----------+
                    +----------+       +-----------+            |
                         ^                                     |
                         |                              Claude Code 读取
                         |                              ┌────┴────┐
                         |                              │ 图片 →  │
                         |                              │ vision  │
                         |                              │ 代理识别 │
                         |                              └─────────┘
                         |                                     |
                         |                              +----------+
                         +──HTTP /send_msg <─────────────── | qq_send.py |
                                                        +----------+
```

- **NapCat** (Docker)：QQ 协议网关，通过 OneBot11 标准接口与 QQ 通信
- **qq_daemon.py**：守护进程，WebSocket 实时接收消息，下载图片/文件，写入队列
- **Claude Code**：读取队列，用完整 AI 能力生成回复；图片先通过视觉代理识别再处理
- **qq_send.py**：HTTP 调用 NapCat API 发送消息
- **Vision Proxy**（可选）：配合 `claude-webui` 的 `/vision/describe` 接口，让纯文本模型也能理解图片

## 前置条件

- [Docker](https://docs.docker.com/engine/install/)
- [Python 3.14+](https://www.python.org/downloads/)
- [Node.js](https://nodejs.org/)（用于 Claude Code CLI）
- [Claude Code](https://claude.ai/code)（`npm install -g @anthropic-ai/claude-code`）

## 快速开始

### 1. 配置 NapCat

复制示例配置并填写你的 QQ 号：

```bash
cp docker-compose.example.yml docker-compose.yml
# 编辑 docker-compose.yml，将 ACCOUNT 改为你的机器人 QQ 号
```

编辑 `config/onebot11.json` 配置 NapCat 网络参数（默认即可，HTTP + WebSocket 都在 3001 端口）。

### 2. 启动 NapCat

```bash
docker compose up -d
```

首次启动需扫码登录 QQ。

### 3. 启动守护进程

```bash
# 前台运行（调试用）
"/c/Program Files/Python314/python" qq_daemon.py

# 或使用批处理脚本后台运行
start_daemon.bat
```

守护进程会：
- WebSocket 连接 NapCat 的 3001 端口
- 实时接收私聊消息
- 自动下载图片/文件到 `napcat_data/downloads/`
- 写入 `napcat_data/queue.jsonl` 消息队列

### 4. 配置 Claude Code

在 `~/.claude/settings.json` 中添加权限：

```json
{
  "permissions": {
    "allow": [
      "Bash(*qq_send*)",
      "Bash(cat ~/qq-bridge/napcat_data/queue.jsonl *)"
    ]
  }
}
```

然后在 Claude Code 中输入 `claude code robot` 进入 QQ 机器人模式，或使用 `/loop 1m claude code robot` 自动轮询。

## 图片识别

机器人支持自动识别图片消息。当收到图片时：

1. 图片自动下载到 `napcat_data/downloads/`
2. Claude Code 调 `claude-webui` 的 `/vision/describe` 接口识别图片
3. 识别结果作为上下文交给主模型处理

需要配合 [claude-webui](https://github.com/1ain0516/claude-webui) 使用（视觉代理基于 DashScope qwen3.6-flash）。

## 文件结构

```
qq-bridge/
├── CLAUDE.md                # Claude Code 行为指令（QQ 机器人模式）
├── qq_daemon.py             # 守护进程（WebSocket 接收消息）
├── qq_send.py               # 发送消息脚本（HTTP 调用 NapCat API）
├── qq_send.sh               # qq_send.py 的 bash 快捷包装
├── qq_read_queue.py         # 游标式队列读取（无竞态）
├── qq_receive.py            # 简易队列读取（可选）
├── qq_health.py             # 一键健康检查
├── start_daemon.bat         # Windows 开机自启脚本
├── check_daemon.sh          # Linux daemon 自愈脚本
├── relay.py                 # Docker 容器内 WebSocket 中继（备用）
├── relay.mjs                # Docker 容器内 HTTP 中继（备用）
├── entrypoint-wrapper.sh    # Docker 入口包装（启动 relay.py）
├── docker-compose.yml       # NapCat Docker 配置（含 QQ 号）
├── docker-compose.example.yml  # Docker 示例配置（占位 QQ 号）
├── local_config.py          # 本地配置（TARGET_QQ 等）
├── local_config.example.py  # 配置示例
├── config/
│   └── onebot11.json        # NapCat 配置
├── napcat_data/             # 运行时数据（被 gitignore）
│   ├── queue.jsonl          # 消息队列
│   ├── cursor.txt           # 游标文件（已处理偏移量）
│   ├── conversation_context.md  # 对话上下文摘要
│   ├── daemon.log           # 守护进程日志
│   ├── daemon.pid           # 单例锁文件
│   ├── downloads/           # 图片/文件下载目录
│   └── events.jsonl         # 原始事件日志
└── .gitignore
```

## 消息格式

队列 `queue.jsonl` 每行一条消息：

```json
{"time": 1712345678.9, "text": "你好"}
{"time": 1712345680.0, "text": "发张图片", "files": [{"type": "image", "name": "abc.jpg", "path": "napcat_data/downloads/abc.jpg"}]}
```

## 常见问题

**Q：Windows 上启动后没有反应？**
A：确认 NapCat Docker 容器在运行，检查 `napcat_data/daemon.log` 日志。

**Q：消息乱码？**
A：确保使用 `qq_send.py`（Python 版）发送，不要用 shell 脚本直接拼接 JSON。

**Q：Claude Code 处理消息时总弹权限确认？**
A：在 `~/.claude/settings.json` 的 `permissions.allow` 中添加相关命令的规则。

**Q：收到重复回复？**
A：可能有多个守护进程在运行。用 PowerShell 杀掉所有 `qq_daemon` 进程再重启：
```powershell
Get-WmiObject Win32_Process -Filter "name like 'python%'" | Where-Object { $_.CommandLine -like '*qq_daemon*' } | ForEach-Object { $_.Terminate() }
```
