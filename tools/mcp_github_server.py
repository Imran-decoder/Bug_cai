import requests
import os
import sys
import json
from dotenv import load_dotenv

load_dotenv()
GITHUB_TOKEN = os.getenv("GITHUB_ACCESS_TOKEN")

def search_repos(query):
    headers = {"Authorization": f"Bearer {GITHUB_TOKEN}"} if GITHUB_TOKEN else {}
    url = f"https://api.github.com/search/repositories?q={query}"
    return requests.get(url, headers=headers).json()

def handle_request(req):
    if req.get("method") == "search_repos":
        q = req.get("params", {}).get("query", "langchain")
        return search_repos(q)
    return {"error": "unknown method"}

def main():
    for line in sys.stdin:
        req = json.loads(line)
        res = handle_request(req)
        sys.stdout.write(json.dumps(res) + "\n")
        sys.stdout.flush()

if __name__ == "__main__":
    main()
