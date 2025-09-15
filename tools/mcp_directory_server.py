import os
import sys
import json

def list_files(path="."):
    return {"files": os.listdir(path)}

def handle_request(req):
    if req.get("method") == "list_files":
        return list_files(req.get("params", {}).get("path", "."))
    return {"error": "unknown method"}

def main():
    for line in sys.stdin:
        req = json.loads(line)
        res = handle_request(req)
        sys.stdout.write(json.dumps(res) + "\n")
        sys.stdout.flush()

if __name__ == "__main__":
    main()
