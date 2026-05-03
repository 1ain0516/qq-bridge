#!/c/Program Files/Python314/python
import json, os, sys

QUEUE_FILE = os.path.expanduser("~/qq-bridge/napcat_data/queue.jsonl")
TARGET_QQ = 0  # 改为你的QQ号

def read_queue(clear=True):
    """读取 queue.jsonl 中所有消息，可选清空队列"""
    if not os.path.exists(QUEUE_FILE):
        return []
    msgs = []
    with open(QUEUE_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                ev = json.loads(line)
                msgs.append(ev)
            except json.JSONDecodeError:
                continue
    if clear:
        open(QUEUE_FILE, 'w').close()  # 清空队列
    return msgs

if __name__ == "__main__":
    no_clear = "--no-clear" in sys.argv
    msgs = read_queue(clear=not no_clear)
    for m in msgs:
        print(json.dumps(m, ensure_ascii=False))
