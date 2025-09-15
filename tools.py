import json
import warnings
import os
from typing import Any, Dict, List

warnings.filterwarnings("ignore", category=RuntimeWarning, module="langchain_community.utilities.duckduckgo_search")
from langchain_community.tools import WikipediaQueryRun, DuckDuckGoSearchRun
from langchain_community.utilities import WikipediaAPIWrapper
from langchain.tools import Tool
from datetime import datetime
from langgraph.types import Command, interrupt
from ddgs import DDGS
import subprocess
from langchain.tools import tool


@tool
def terminal_tool(command: str) -> str:
    """Execute a shell command in the local terminal and return the output."""
    try:
        result = subprocess.run(
            command,
            shell=True,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )
        return result.stdout.strip() or result.stderr.strip()
    except subprocess.CalledProcessError as e:
        return f"Error executing command: {e.stderr.strip()}"


#
# @tool
# def run_codeql(query: str, db_path: str = "my-database") -> str:
#     """
#     Runs a CodeQL query against a given database.
#     Assumes CodeQL CLI is installed and database is already created.
#     """
#     try:
#         result = subprocess.run(
#             ["codeql", "query", "run", query, "--database", db_path],
#             capture_output=True,
#             text=True,
#             check=True
#         )
#         return result.stdout
#     except subprocess.CalledProcessError as e:
#         return f"Error running CodeQL: {e.stderr}"
#
#
# codeql_tool = Tool(
#     name="codeql_query",
#     func=run_codeql,
#     description=(
#         "Run a CodeQL query against the codebase database. "
#         "Input should be the path to a .ql query file."
#     ),
# )


@tool
def human_assistant(query: str) -> str:
    """Tool that asks the human a question and waits for their answer."""
    try:
        human_resp = interrupt({"query": query})
    except Exception:
        # fallback for local testing without LangGraph
        human_resp = input(f"[Human Assistant] {query}\nYour answer: ")

    if isinstance(human_resp, dict):
        if "data" in human_resp:
            return str(human_resp["data"])
        else:
            return str(human_resp)
    return str(human_resp)


def save_to_txt(data: str, filename: str = "research_output.txt"):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    formatted_text = f"--- Research Output ---\nTimestamp: {timestamp}\n\n{data}\n\n"

    with open(filename, "a", encoding="utf-8") as f:
        f.write(formatted_text)

    return f"Data successfully saved to {filename}"


save_tool = Tool(
    name="save_text_to_file",
    func=save_to_txt,
    description="Saves structured research data to a text file.",
)


def duckduckgo_search(query: str) -> str:
    with DDGS() as ddgs:
        results = [r["body"] for r in ddgs.text(query, max_results=5)]
        return "\n".join(results)


search_tool = Tool(
    name="search",
    func=duckduckgo_search,
    description="Search the web for information",
)

api_wrapper = WikipediaAPIWrapper(top_k_results=1, doc_content_chars_max=100)
wiki_tool = WikipediaQueryRun(api_wrapper=api_wrapper)


# --------helper----

def _run(cmd: List[str], timeout: int = 180) -> Dict[str, Any]:
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        out = (res.stdout or "").strip()
        err = (res.stderr or "").strip()
        if res.returncode != 0:
            return {"ok": False, "error": err or f"exit={res.returncode}"}
        return {"ok": True, "data": out if out else err}
    except FileNotFoundError:
        return {"ok": False, "error": f"command not found: {cmd[0]}"}
    except subprocess.TimeoutExpired:
        return {"ok": False, "error": "timeout"}
    except Exception as e:
        return {"ok": False, "error": str(e)}


def _exists_dir(path: str) -> bool:
    return os.path.isdir(path)


def _json_or_text(s: str) -> Any:
    try:
        return json.loads(s)
    except:
        return s


def _wrap_json(res: Dict[str, Any]) -> Dict[str, Any]:
    if not res["ok"]:
        return res
    return {"ok": True, "data": _json_or_text(res["data"])}


# -----static tool ----

@tool
def scan_semgrep(path: str, rules: str = "p/ci") -> Dict[str, Any]:
    """Run Semgrep static analysis on a given path."""
    if not _exists_dir(path):
        return {"ok": False, "error": f"not a directory: {path}"}
    cmd = ["semgrep", "--config", rules, path, "--json", "--quiet"]
    return _wrap_json(_run(cmd))


@tool
def scan_bandit(path):
    """RUn scan bandit"""
    cmd = ["bandit", "-r", path, "-f", "json", "-q"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    return {"ok": True, "data": res.stdout}


@tool
def scan_pip_audit(path):
    """Run pip audit"""
    cmd = ["pip-audit", "-r", os.path.join(path, "requirements.txt"), "-f", "json"]
    res = subprocess.run(cmd, capture_output=True, text=True)
    return {"ok": True, "data": res.stdout}


@tool
def scan_trufflehog(path: str) -> Dict[str, Any]:
    """Run TruffleHog secrets scan (supports v2 and v3)."""
    if not _exists_dir(path):
        return {"ok": False, "error": f"not a directory: {path}"}

    # Check if .git exists
    if os.path.isdir(os.path.join(path, ".git")):
        cmd = ["trufflehog", path, "--json"]  # works in both v2 and v3
    else:
        # Try v3 filesystem mode
        cmd = ["trufflehog", "filesystem", path, "--json"]

    r = _run(cmd, timeout=300)
    if not r["ok"]:
        return r

    lines = [ln for ln in r["data"].splitlines() if ln.strip()]
    parsed = []
    for ln in lines:
        try:
            parsed.append(json.loads(ln))
        except:
            parsed.append({"raw": ln})
    return {"ok": True, "data": parsed}
