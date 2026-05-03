#!/c/Program Files/Python314/python
"""一键健康检查 — daemon、NapCat、队列状态"""
import json, os, subprocess, urllib.request
from local_config import TARGET_QQ

DATA_DIR = os.path.expanduser('~/qq-bridge/napcat_data')
PID_FILE = os.path.join(DATA_DIR, 'daemon.pid')
LOG_FILE = os.path.join(DATA_DIR, 'daemon.log')
QUEUE_FILE = os.path.join(DATA_DIR, 'queue.jsonl')
CURSOR_FILE = os.path.join(DATA_DIR, 'cursor.txt')
WS_HOST = '127.0.0.1'
WS_PORT = 3001

def check(ok, msg):
    icon = "[OK]" if ok else "[FAIL]"
    print(f"  {icon} {msg}")

print("=== QQ Bot Health Check ===\n")

# 1. Daemon 进程
print("1. Daemon:")
if os.path.exists(PID_FILE):
    with open(PID_FILE) as f:
        pid = f.read().strip()
    result = subprocess.run(
        ['powershell', '-Command', f'Get-Process -Id {pid} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id'],
        capture_output=True, text=True, timeout=5
    )
    alive = result.stdout.strip() != ''
    check(alive, f"PID {pid} — {'运行中' if alive else '已死亡（PID 文件残留）'}")
else:
    check(False, "PID 文件不存在（daemon 未启动）")

# 2. 最近心跳
print("2. NapCat 连接状态:")
try:
    with open(LOG_FILE, 'r', encoding='utf-8', errors='replace') as f:
        lines = f.readlines()
    # 找最近的心跳或消息
    recent = [l for l in lines if 'heartbeat' in l.lower() or 'WS connected' in l or '<<<' in l]
    if recent:
        last = recent[-1].strip()
        check(True, f"最近活动: {last}")
    else:
        check(False, "日志中无活动记录")
except FileNotFoundError:
    check(False, "日志文件不存在")

# 3. NapCat HTTP 接口
print("3. NapCat API:")
try:
    req = urllib.request.Request("http://127.0.0.1:3001/get_status", method='GET')
    with urllib.request.urlopen(req, timeout=5) as resp:
        status = json.loads(resp.read().decode('utf-8'))
        online = status.get('data', {}).get('online', False)
        check(online, f"HTTP 可达，QQ {'在线' if online else '离线'}")
except Exception as e:
    check(False, f"HTTP 不可达: {e}")

# 4. 队列状态
print("4. 队列:")
queue_exists = os.path.exists(QUEUE_FILE)
cursor = 0
file_size = 0
if queue_exists:
    file_size = os.path.getsize(QUEUE_FILE)
    if os.path.exists(CURSOR_FILE):
        with open(CURSOR_FILE) as f:
            cursor = int(f.read().strip())
    pending = max(0, file_size - cursor)
    check(pending == 0, f"队列 {file_size} bytes，未处理 {pending} bytes")
else:
    check(True, "队列文件不存在（尚无消息）")

# 5. 发消息测试
print("5. 发送测试:")
try:
    payload = json.dumps({"user_id": TARGET_QQ, "message": "[健康检查] 服务正常"}).encode('utf-8')
    req = urllib.request.Request(
        "http://127.0.0.1:3001/send_msg", data=payload,
        headers={"Content-Type": "application/json"}
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        result = json.loads(resp.read().decode('utf-8'))
        check(result.get('retcode') == 0, f"retcode={result.get('retcode')}")
except Exception as e:
    check(False, f"发送失败: {e}")

print()
