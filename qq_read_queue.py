#!/c/Program Files/Python314/python
"""游标式队列读取 — 无竞态，只返回未处理的新消息"""
import json, os, sys

DATA_DIR = os.path.expanduser('~/qq-bridge/napcat_data')
QUEUE_FILE = os.path.join(DATA_DIR, 'queue.jsonl')
CURSOR_FILE = os.path.join(DATA_DIR, 'cursor.txt')


def get_new_messages():
    cursor = 0
    if os.path.exists(CURSOR_FILE):
        with open(CURSOR_FILE, 'r') as f:
            cursor = int(f.read().strip())

    if not os.path.exists(QUEUE_FILE):
        return []

    file_size = os.path.getsize(QUEUE_FILE)

    if cursor > file_size:
        cursor = 0

    if file_size <= cursor:
        return []

    # 必须用二进制模式读取，seek 才能按字节偏移
    with open(QUEUE_FILE, 'rb') as f:
        f.seek(cursor)
        raw = f.read()
        # 如果游标在行中间（之前 bug 导致），跳到下一行开头
        if cursor > 0 and not raw.startswith(b'{'):
            first_nl = raw.find(b'\n')
            if first_nl >= 0:
                raw = raw[first_nl + 1:]
                cursor = cursor + first_nl + 1
                with open(CURSOR_FILE, 'w') as cf:
                    cf.write(str(cursor))

    text = raw.decode('utf-8', errors='replace')
    lines = text.split('\n')

    messages = []
    bytes_consumed = 0
    bad_lines = 0
    for i, line in enumerate(lines):
        line_bytes = line.encode('utf-8')
        if not line.strip():
            if i == len(lines) - 1:
                break  # split('\n') 末尾空串，不计字节
            bytes_consumed += len(line_bytes) + 1  # +1 换行符
            continue
        try:
            msg = json.loads(line)
            messages.append(msg)
            bytes_consumed += len(line_bytes) + 1
            bad_lines = 0
        except json.JSONDecodeError:
            bad_lines += 1
            if bad_lines > 5:
                break  # 连续多行损坏，可能 daemon 正在写入
            bytes_consumed += len(line_bytes) + 1  # 跳过坏行

    new_cursor = cursor + bytes_consumed
    with open(CURSOR_FILE, 'w') as f:
        f.write(str(new_cursor))

    # 文件超过 1MB 且已处理超过一半时，截断旧数据
    if file_size > 1024 * 1024 and new_cursor > file_size // 2:
        with open(QUEUE_FILE, 'rb') as f:
            remaining = f.read()
        remaining = remaining[new_cursor:]
        with open(QUEUE_FILE, 'wb') as f:
            f.write(remaining)
        with open(CURSOR_FILE, 'w') as f:
            f.write('0')

    return messages


if __name__ == '__main__':
    msgs = get_new_messages()
    if msgs:
        print(json.dumps(msgs, ensure_ascii=False))
