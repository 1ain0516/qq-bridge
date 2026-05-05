---
name: qq-robot
description: >
  QQ机器人消息处理模式。轮询队列中的新消息，处理图片/文件，
  发送回复，更新对话上下文。适用于 QQ Bot Bridge 项目。
user-invocable: true
allowed-tools: Read, Write, Bash
---

# QQ Robot 消息处理

处理 QQ 机器人消息队列：

0. **确保服务运行**：执行 `cmd /c "~/qq-bridge/start_daemon.bat"`（幂等安全）

1. **读取上下文**：如果 `~/qq-bridge/napcat_data/conversation_context.md` 存在，先读取

2. **读取新消息**：运行 `"/c/Program Files/Python314/python" ~/qq-bridge/qq_read_queue.py`

3. **如果队列为空**，不做任何操作，直接结束

4. **智能处理消息**：
   - 单条直接回复，多条判断是否同一话题
   - 图片消息（`type: "image"`）：调视觉代理识别
     ```bash
     PORT=$(cat ~/claude-webui/.port 2>/dev/null || echo 8088)
     curl -s -X POST "http://localhost:$PORT/vision/describe" \
       -F "file=@<路径>" -F "prompt=请详细描述这张图片"
     ```
   - 普通文件：直接读取处理

5. **发送回复**：`"/c/Program Files/Python314/python" ~/qq-bridge/qq_send.py "内容"`

6. **更新上下文**：写入 `conversation_context.md`（不超过2KB）

7. **清空** `latest_msg.txt`
