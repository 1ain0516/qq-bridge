import socket, base64, struct, json, os, sys, time

DATA_DIR = '/app/data'
EVENTS_FILE = os.path.join(DATA_DIR, 'events.jsonl')
WS_HOST = '127.0.0.1'
WS_PORT = 3001
WS_PATH = '/'
os.makedirs(DATA_DIR, exist_ok=True)

def ws_connect(host, port, path='/'):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(30)
    sock.connect((host, port))
    key = base64.b64encode(os.urandom(16)).decode()
    req = (f'GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\n'
           f'Upgrade: websocket\r\nConnection: Upgrade\r\n'
           f'Sec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n')
    sock.sendall(req.encode())
    resp = b''
    while b'\r\n\r\n' not in resp:
        c = sock.recv(4096)
        if not c: raise Exception('Closed during handshake')
        resp += c
    if b'101' not in resp[:128]:
        raise Exception(f'Handshake failed: {resp[:200].decode(errors="ignore")}')
    return sock

def ws_recv(sock):
    d = sock.recv(2)
    if len(d) < 2: return None
    opcode, length = d[0] & 0x0F, d[1] & 0x7F
    if length == 126: length = struct.unpack('>H', sock.recv(2))[0]
    elif length == 127: length = struct.unpack('>Q', sock.recv(8))[0]
    payload = b''
    while len(payload) < length:
        c = sock.recv(length - len(payload))
        if not c: return None
        payload += c
    if opcode == 0x8: return None
    if opcode in (0x9, 0xA): return ''
    if opcode == 0x1:
        try:
            return payload.decode('utf-8')
        except UnicodeDecodeError:
            return payload.decode('gbk')
    if opcode == 0x2:
        try:
            return payload.decode('utf-8')
        except UnicodeDecodeError:
            return payload.decode('gbk')
    return ''

def write_event(data):
    try:
        ev = json.loads(data)
        with open(EVENTS_FILE, 'a', encoding='utf-8') as f:
            f.write(json.dumps(ev) + '\n')
    except: pass

print('[Relay] WS connecting to NapCat...')
sys.stdout.flush()
while True:
    try:
        sock = ws_connect(WS_HOST, WS_PORT, WS_PATH)
        print('[Relay] Connected')
        sys.stdout.flush()
        while True:
            msg = ws_recv(sock)
            if msg is None:
                print('[Relay] Disconnected, reconnecting...')
                sys.stdout.flush()
                break
            if msg: write_event(msg)
    except Exception as e:
        print(f'[Relay] Error: {e}, retry 5s...')
        sys.stdout.flush()
        try: sock.close()
        except: pass
    time.sleep(5)
