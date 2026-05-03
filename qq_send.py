#!/c/Program Files/Python314/python
import json, sys, urllib.request, urllib.error
from local_config import TARGET_QQ

NAPCAT_URL = "http://localhost:3001"

def send_message(text):
    payload = json.dumps({"user_id": TARGET_QQ, "message": text}).encode('utf-8')
    req = urllib.request.Request(
        f"{NAPCAT_URL}/send_msg", data=payload,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return json.loads(resp.read().decode('utf-8'))
    except urllib.error.HTTPError as e:
        return {"error": e.code, "body": e.read().decode()}
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: qq_send.py <message>")
        sys.exit(1)
    if sys.argv[1] == "--file" and len(sys.argv) > 2:
        with open(sys.argv[2], 'r', encoding='utf-8') as f:
            text = f.read().strip()
    else:
        text = " ".join(sys.argv[1:])
    result = send_message(text)
    print(json.dumps(result, ensure_ascii=False, indent=2))
