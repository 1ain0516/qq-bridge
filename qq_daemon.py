#!/c/Program Files/Python314/python
"""
QQ 消息守护进程 — 单实例，只负责实时接收消息写入队列
发送由 Claude Code（我）通过 qq_send.py 处理
"""
import json, os, sys, time, struct, socket, base64, atexit, subprocess, urllib.request, uuid

from local_config import TARGET_QQ

DATA_DIR = os.path.expanduser('~/qq-bridge/napcat_data')
EVENTS_FILE = os.path.join(DATA_DIR, 'events.jsonl')
QUEUE_FILE = os.path.join(DATA_DIR, 'queue.jsonl')
CURSOR_FILE = os.path.join(DATA_DIR, 'cursor.txt')
PID_FILE = os.path.join(DATA_DIR, 'daemon.pid')
DOWNLOADS_DIR = os.path.join(DATA_DIR, 'downloads')
WS_HOST = '127.0.0.1'
WS_PORT = 3001

os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(DOWNLOADS_DIR, exist_ok=True)

# === 日志轮转（daemon.log > 1MB 时归档）===
LOG_FILE = os.path.join(DATA_DIR, 'daemon.log')
try:
    if os.path.exists(LOG_FILE) and os.path.getsize(LOG_FILE) > 1024 * 1024:
        os.rename(LOG_FILE, LOG_FILE + '.old')
except PermissionError:
    pass  # 文件被旧进程占用，跳过轮转
# events.jsonl 同样轮转
try:
    if os.path.exists(EVENTS_FILE) and os.path.getsize(EVENTS_FILE) > 1024 * 1024:
        os.rename(EVENTS_FILE, EVENTS_FILE + '.old')
except PermissionError:
    pass
# queue.jsonl 超过 1MB 时轮转，同时重置游标
try:
    if os.path.exists(QUEUE_FILE) and os.path.getsize(QUEUE_FILE) > 1024 * 1024:
        os.rename(QUEUE_FILE, QUEUE_FILE + '.old')
        with open(CURSOR_FILE, 'w') as _f:
            _f.write('0')
except PermissionError:
    pass

# === 清理 downloads/ 中超过 24h 的旧文件 ===
now = time.time()
for fname in os.listdir(DOWNLOADS_DIR):
    fpath = os.path.join(DOWNLOADS_DIR, fname)
    if os.path.isfile(fpath) and now - os.path.getmtime(fpath) > 86400:
        try: os.remove(fpath)
        except: pass

# === 单例锁 ===
def check_singleton():
    if os.path.exists(PID_FILE):
        try:
            with open(PID_FILE, 'r') as f:
                old_pid = int(f.read().strip())
            result = subprocess.run(['powershell', '-Command',
                f'Get-Process -Id {old_pid} -ErrorAction SilentlyContinue | Select-Object -ExpandProperty Id'],
                capture_output=True, text=True, timeout=5)
            if result.stdout.strip():
                print(f'Another daemon running (PID {old_pid}), exiting.')
                sys.exit(0)
        except (ValueError, FileNotFoundError):
            pass
    with open(PID_FILE, 'w') as f:
        f.write(str(os.getpid()))

def cleanup_pid():
    try:
        if os.path.exists(PID_FILE):
            with open(PID_FILE, 'r') as f:
                pid = int(f.read().strip())
            if pid == os.getpid():
                os.remove(PID_FILE)
    except: pass

atexit.register(cleanup_pid)
check_singleton()

# === WebSocket ===
def ws_connect():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(60)
    sock.connect((WS_HOST, WS_PORT))
    key = base64.b64encode(os.urandom(16)).decode()
    req = (f'GET / HTTP/1.1\r\nHost: {WS_HOST}:{WS_PORT}\r\n'
           f'Upgrade: websocket\r\nConnection: Upgrade\r\n'
           f'Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n')
    sock.sendall(req.encode())
    resp = b''
    while b'\r\n\r\n' not in resp:
        c = sock.recv(4096)
        if not c: raise Exception('handshake failed')
        resp += c
    if b'101' not in resp[:128]:
        raise Exception(f'bad handshake: {resp[:200]}')
    return sock

def ws_recv(sock):
    d = sock.recv(2)
    if len(d) < 2: return None
    op, l = d[0] & 0x0F, d[1] & 0x7F
    if l == 126: l = struct.unpack('>H', sock.recv(2))[0]
    elif l == 127: l = struct.unpack('>Q', sock.recv(8))[0]
    p = b''
    while len(p) < l:
        c = sock.recv(l - len(p))
        if not c: return None
        p += c
    if op == 0x8: return None
    if op in (0x9, 0xA): return ''
    if op in (0x1, 0x2):
        try:
            return p.decode('utf-8')
        except UnicodeDecodeError:
            return p.decode('gbk')
    return ''

# === 日志 ===
log = open(LOG_FILE, 'a', buffering=1, encoding='utf-8')
def log_msg(msg):
    log.write(f'[{time.strftime("%H:%M:%S")}] {msg}\n')

log_msg(f'=== Daemon started (PID {os.getpid()}) ===')

# === 主循环：只接收消息 ===
seen_ids = set()
while True:
    try:
        sock = ws_connect()
        connected_at = time.time()
        log_msg('WS connected')
        while True:
            msg = ws_recv(sock)
            if msg is None:
                log_msg('WS disconnected, reconnecting...')
                break
            if not msg: continue
            try:
                evt = json.loads(msg)
            except: continue
            if (evt.get('post_type') == 'message'
                    and evt.get('message_type') == 'private'
                    and evt.get('user_id') == TARGET_QQ):
                # 跳过重连后 NapCat 重推的旧事件
                if evt.get('time', 0) < connected_at - 5:
                    continue
                msg_id = evt.get('message_id', 0)
                if msg_id and msg_id in seen_ids: continue
                if msg_id:
                    seen_ids.add(msg_id)
                    if len(seen_ids) > 100: seen_ids.pop()
                # 提取文字
                texts = [s['data']['text'] for s in evt.get('message', []) if s.get('type') == 'text']
                text = texts[0] if texts else ''
                # 提取图片/文件并下载
                files = []
                for seg in evt.get('message', []):
                    seg_type = seg.get('type')
                    seg_data = seg.get('data', {})
                    if seg_type == 'image' and seg_data.get('url'):
                        ext = os.path.splitext(seg_data.get('file', 'image.png'))[1] or '.png'
                        fname = f"{uuid.uuid4().hex}{ext}"
                        fpath = os.path.join(DOWNLOADS_DIR, fname)
                        try:
                            urllib.request.urlretrieve(seg_data['url'], fpath)
                            files.append({'type': 'image', 'name': fname, 'path': fpath})
                            log_msg(f'<<< [图片] {fpath}')
                        except Exception as e:
                            log_msg(f'Download image error: {e}')
                    elif seg_type == 'file' and seg_data.get('url'):
                        ext = os.path.splitext(seg_data.get('name', 'file.bin'))[1] or '.bin'
                        fname = f"{uuid.uuid4().hex}{ext}"
                        fpath = os.path.join(DOWNLOADS_DIR, fname)
                        try:
                            urllib.request.urlretrieve(seg_data['url'], fpath)
                            files.append({'type': 'file', 'name': seg_data.get('name', fname), 'path': fpath})
                            log_msg(f'<<< [文件] {seg_data.get("name", fname)}')
                        except Exception as e:
                            log_msg(f'Download file error: {e}')
                if text or files:
                    log_msg(f'<<< {text}' if text else '<<< [非文字消息]')
                    entry = {'time': time.time(), 'text': text}
                    if files:
                        entry['files'] = files
                    with open(QUEUE_FILE, 'a', encoding='utf-8') as f:
                        f.write(json.dumps(entry, ensure_ascii=False) + '\n')
                    with open(os.path.join(DATA_DIR, 'latest_msg.txt'), 'w', encoding='utf-8') as f:
                        f.write(text + '\n')
            with open(EVENTS_FILE, 'a', encoding='utf-8') as f:
                f.write(msg + '\n')
    except Exception as e:
        log_msg(f'Error: {e}, retry 5s...')
        time.sleep(5)
