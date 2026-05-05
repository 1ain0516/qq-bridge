# QQ Bot Bridge (qq-bridge)

QQ机器人桥接项目，NapCat + qq_daemon.py + Claude Code 实现通过QQ与Claude对话。

## 架构

```
NapCat(QQ网关, OneBot11协议) --WebSocket--> qq_daemon.py --写入--> queue.jsonl
                                                                     |
                                                    Claude Code 读取并回复
                                                                     |
                                                    回复通过 qq_send.py (curl) 发送
```

## 技能：QQ机器人模式

QQ机器人消息处理已集成为 **`/qq-robot`** 技能。

- 手动执行：输入 `/qq-robot`
- 自动轮询：`/loop 1m /qq-robot`

## 文件路径

| 文件 | 说明 |
|------|------|
| `~/qq-bridge/napcat_data/queue.jsonl` | 消息队列，每行 `{"time":..., "text":"...", "files":[...]}` |
| `~/qq-bridge/napcat_data/latest_msg.txt` | 最新一条消息（调试用） |
| `~/qq-bridge/napcat_data/downloads/` | 图片/文件下载目录 |
| `~/qq-bridge/napcat_data/daemon.log` | 守护进程日志 |
| `~/qq-bridge/napcat_data/daemon.pid` | 单例锁文件 |
| `~/qq-bridge/qq_send.py` | 发送消息脚本 |
| `~/qq-bridge/qq_daemon.py` | 守护进程（实时接收WebSocket，写入队列） |
| `~/qq-bridge/qq_read_queue.py` | 游标式队列读取（无竞态） |
| `~/qq-bridge/qq_health.py` | 一键健康检查 |
| `~/qq-bridge/napcat_data/cursor.txt` | 游标文件，记录已处理的字节偏移 |
| `~/qq-bridge/napcat_data/conversation_context.md` | 对话上下文摘要（持久化记忆） |
| `~/qq-bridge/start_daemon.bat` | 开机自启脚本 |

## daemon 管理

- daemon 通过 PID 文件锁确保单例运行
- 收到消息实时写入 `queue.jsonl`
- 图片/文件自动下载到 `downloads/`（自动清理超过 24h 的旧文件）
- 日志超过 1MB 自动轮转（daemon.log.old）
- 启动：`start_daemon.bat` 或 `"/c/Program Files/Python314/python" ~/qq-bridge/qq_daemon.py &`
- 重启：先杀所有 `qq_daemon` 进程再启动（`start_daemon.bat` 会自动处理）
- 健康检查：`"/c/Program Files/Python314/python" ~/qq-bridge/qq_health.py`

## 发送消息

```bash
"/c/Program Files/Python314/python" ~/qq-bridge/qq_send.py "消息内容"
```

建议在 `~/.claude/settings.json` 中添加 `Bash(*qq-bridge*)` 免批准权限以避免重复弹窗。

## 关键配置

- 目标QQ: 在 `local_config.py` 中设置 `TARGET_QQ`
- 机器人QQ: 在 `docker-compose.yml` 中设置 `ACCOUNT`
- 机器人密码: 在 `docker-compose.yml` 中设置 `NAPCAT_QUICK_PASSWORD`（可选）
- NapCat端口: 127.0.0.1:3001
- Python路径: `/c/Program Files/Python314/python.exe`
- claude路径: `/c/Users/你的用户名/AppData/Roaming/npm/claude`
