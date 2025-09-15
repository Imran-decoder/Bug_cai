import os
import time
import json
import subprocess
import asyncio
from typing import Optional, Dict, Any

import httpx
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("zap_tools")

# Configuration via environment or hard-coded defaults
ZAP_HOST = os.environ.get("ZAP_HOST", "127.0.0.1")
ZAP_PORT = int(os.environ.get("ZAP_PORT", "8080"))
ZAP_API_KEY = os.environ.get("ZAP_API_KEY", "vd9q8hbq2ra4v2o8io0ancsc28")  # set if you configured an API key in ZAP
ZAP_BASE = f"http://{ZAP_HOST}:{ZAP_PORT}"
ZAP_PATH = os.environ.get("ZAP_PATH", "zap.sh")  # path to zap.sh or zap.bat on Windows
ZAP_STARTUP_WAIT = int(os.environ.get("ZAP_STARTUP_WAIT", "6"))  # seconds to wait after starting

# internal process holder (will contain subprocess.Popen)
_zap_proc: Optional[subprocess.Popen] = None
# add imports near top of file (if not already present)
import os
import time
import json
import asyncio
from typing import Optional, Dict, Any, List
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By

# ... existing code ...

# Helper: blocking selenium worker (run in thread)
def _selenium_exercise_worker(
    target_url: str,
    login_type: Optional[str],
    login_url: Optional[str],
    username: Optional[str],
    password: Optional[str],
    username_selector: Optional[str],
    password_selector: Optional[str],
    submit_selector: Optional[str],
    payloads: Optional[List[str]],
    out_prefix: str,
    proxy: Optional[str],
    headless: bool,
    page_timeout: int,
) -> Dict[str, Any]:
    """
    Blocking worker that uses Selenium to:
      - optionally do basic auth or form login
      - visit target_url and inject payloads into forms
      - save screenshot and page source
    Returns dict with paths and errors (if any).
    """
    res = {
        "target_url": target_url,
        "ok": False,
        "errors": [],
        "artifacts": {},
        "timestamp": time.time(),
        "payloads_tested": [],
    }

    opts = Options()
    if headless:
        # modern chrome uses `--headless=new`
        opts.add_argument("--headless=new")
        opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.set_capability("acceptInsecureCerts", True)

    if proxy:
        opts.add_argument(f"--proxy-server={proxy}")

    driver = None
    try:
        # install chromedriver via webdriver-manager
        driver_path = ChromeDriverManager().install()
        driver = webdriver.Chrome(driver_path, options=opts)
        driver.set_page_load_timeout(page_timeout)

        # Basic auth via URL if username/password provided and login_type == "basic"
        if login_type == "basic" and username and password:
            # construct basic auth URL
            # NOTE: this exposes credentials in shell history; use only in safe env
            parts = target_url.split("://", 1)
            if len(parts) == 2:
                proto, rest = parts
                login_target = f"{proto}://{username}:{password}@{rest}"
            else:
                login_target = target_url
            driver.get(login_target)
            time.sleep(1)

        # Form-based login
        elif login_type == "form" and login_url and username and password:
            driver.get(login_url)
            time.sleep(1)
            try:
                if username_selector:
                    uel = driver.find_element(By.CSS_SELECTOR, username_selector)
                    uel.clear(); uel.send_keys(username)
                if password_selector:
                    pel = driver.find_element(By.CSS_SELECTOR, password_selector)
                    pel.clear(); pel.send_keys(password)
                if submit_selector:
                    btn = driver.find_element(By.CSS_SELECTOR, submit_selector)
                    btn.click()
                else:
                    # try submit via form element
                    forms = driver.find_elements(By.TAG_NAME, "form")
                    if forms:
                        forms[0].submit()
                time.sleep(2)
            except Exception as e:
                res["errors"].append(f"form-login error: {e}")

        # If not logging in, just visit target
        driver.get(target_url)
        time.sleep(1)

        # Save landing screenshot and HTML
        screenshot_path = f"{out_prefix}.png"
        driver.save_screenshot(screenshot_path)
        res["artifacts"]["screenshot"] = os.path.abspath(screenshot_path)

        page_src_path = f"{out_prefix}.html"
        with open(page_src_path, "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        res["artifacts"]["page_source"] = os.path.abspath(page_src_path)

        # Find forms and test payloads
        forms = driver.find_elements(By.TAG_NAME, "form")
        payloads = payloads or ['<script>window.__xss=1</script>', '"><img src=x onerror=window.__xss2=1>']
        tested = []
        for p in payloads:
            # for each form try to fill text inputs and submit
            try:
                for form in forms:
                    inputs = form.find_elements(By.XPATH, ".//input[translate(@type,'ABCDEFGHIJKLMNOPQRSTUVWXYZ','abcdefghijklmnopqrstuvwxyz')='text' or not(@type)] | .//textarea")
                    if not inputs:
                        # try input[type=text/email/search]
                        inputs = form.find_elements(By.XPATH, ".//input[@type='text' or @type='search' or @type='email']")
                    # inject into first few inputs
                    for i_idx, inp in enumerate(inputs[:3]):
                        try:
                            inp.clear()
                            inp.send_keys(p)
                        except Exception:
                            pass
                    # submit the form
                    try:
                        form.submit()
                    except Exception:
                        # try to find submit button
                        try:
                            btn = form.find_element(By.CSS_SELECTOR, "button[type=submit], input[type=submit]")
                            btn.click()
                        except Exception:
                            pass
                    time.sleep(1)  # allow JS
                # after submissions, capture a small artifact
                snap_p = f"{out_prefix}_payload_{len(tested)}.png"
                driver.save_screenshot(snap_p)
                tested.append({"payload": p, "screenshot": os.path.abspath(snap_p)})
            except Exception as e:
                res["errors"].append(f"payload-test error for payload {p}: {e}")
        res["payloads_tested"] = tested

        # detect simple DOM-executed payload flags
        try:
            x1 = driver.execute_script("return window.__xss === 1 || window.__xss === true")
            x2 = driver.execute_script("return window.__xss2 === 1 || window.__xss2 === true")
            if x1 or x2:
                res["artifacts"]["dom_xss_detected"] = True
            else:
                res["artifacts"]["dom_xss_detected"] = False
        except Exception:
            res["artifacts"]["dom_xss_detected"] = False

        res["ok"] = True
    except Exception as e:
        res["errors"].append(str(e))
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

    # persist JSON
    out_json = f"{out_prefix}.json"
    try:
        with open(out_json, "w", encoding="utf-8") as f:
            json.dump(res, f, indent=2)
        res["artifacts"]["result_json"] = os.path.abspath(out_json)
    except Exception as e:
        res["errors"].append(f"write result json error: {e}")

    return res

# MCP tool (async) that orchestrates Selenium -> ZAP spider/scan -> report
@mcp.tool()
async def zap_selenium_exercise(
    target_url: str,
    login_type: Optional[str] = None,            # "basic" or "form" or None
    login_url: Optional[str] = None,             # for form login
    username: Optional[str] = None,
    password: Optional[str] = None,
    username_selector: Optional[str] = None,     # CSS selector for username input
    password_selector: Optional[str] = None,     # CSS selector for password input
    submit_selector: Optional[str] = None,       # CSS selector for submit button (optional)
    payloads: Optional[List[str]] = None,        # list of payloads to try
    out_prefix: str = "selenium_zap",
    headless: bool = True,
    page_timeout: int = 30,
    proxy_host: Optional[str] = None,
    run_spider: bool = True,
    run_active_scan: bool = True,
    active_scan_timeout: int = 300,
) -> str:
    """
    Orchestrate Selenium-driven interaction (handles Basic/Auth or form login and form payloads)
    then optionally run ZAP spider and active scan, export report.
    Returns a JSON string with summary and artifact paths.
    """
    # ensure ZAP is running
    ensure_res = await ensure_zap()
    # set proxy string
    proxy = proxy_host or f"http://{ZAP_HOST}:{ZAP_PORT}"

    # run blocking selenium work in thread (to avoid blocking event loop)
    loop = asyncio.get_running_loop()
    worker_res = await loop.run_in_executor(
        None,
        _selenium_exercise_worker,
        target_url,
        login_type,
        login_url,
        username,
        password,
        username_selector,
        password_selector,
        submit_selector,
        payloads,
        out_prefix,
        proxy,
        headless,
        page_timeout,
    )

    final = {"selenium": worker_res, "zap": {}}

    # run zap spider on target (if requested)
    if run_spider:
        try:
            spider_res = await zap_spider(target=target_url, max_children=5)
            final["zap"]["spider"] = spider_res
        except Exception as e:
            final["zap"]["spider_error"] = str(e)

    # run active scan
    if run_active_scan:
        try:
            active_res = await zap_active_scan(target=target_url, timeout_seconds=active_scan_timeout)
            final["zap"]["active_scan"] = active_res
        except Exception as e:
            final["zap"]["active_scan_error"] = str(e)

    # export report
    try:
        rpt = await zap_export_report(format_type="html", out_path=f"{out_prefix}_zap_report.html")
        final["zap"]["report"] = rpt
    except Exception as e:
        final["zap"]["report_error"] = str(e)

    # combine and return JSON string
    return json.dumps(final, default=str)


def safe_run(cmd: list[str], cwd: Optional[str] = None, timeout: int = 60) -> str:
    """Run a command safely and return stdout/stderr as string (never raise)."""
    try:
        p = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, timeout=timeout)
        out = (p.stdout or "").strip()
        err = (p.stderr or "").strip()
        if p.returncode != 0:
            return f"ERROR (code={p.returncode}): {err or out}"
        return out or err or "OK"
    except FileNotFoundError:
        return f"ERROR: command not found: {cmd[0]}"
    except subprocess.TimeoutExpired:
        return "ERROR: command timed out"
    except Exception as e:
        return f"ERROR: unexpected: {e}"


def _zap_api_params(additional: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    params = {}
    if ZAP_API_KEY:
        params["apikey"] = ZAP_API_KEY
    if additional:
        params.update(additional)
    return params


async def _is_zap_up(timeout: float = 2.0) -> bool:
    """Check ZAP core is reachable."""
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            r = await client.get(f"{ZAP_BASE}/JSON/core/view/version/", params=_zap_api_params())
            return r.status_code == 200 and "version" in r.json()
    except Exception:
        return False


@mcp.tool()
async def start_zap_daemon(cmd: Optional[str] = None, wait_seconds: Optional[int] = None) -> str:
    """
    Start ZAP in daemon mode. Returns process info or error string.
    cmd: optional command or path to zap.sh. Example: '/path/to/zap.sh -daemon -port 8080'
    wait_seconds: optional seconds to wait before reporting ZAP as ready.
    """
    global _zap_proc
    if await _is_zap_up():
        return "ZAP already running."

    zap_cmd = cmd or f"{ZAP_PATH} -daemon -port {ZAP_PORT}"
    if isinstance(zap_cmd, str):
        zap_cmd_list = zap_cmd.split()
    else:
        zap_cmd_list = zap_cmd

    try:
        # Start as background process, do not block server
        _zap_proc = subprocess.Popen(zap_cmd_list, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except FileNotFoundError:
        return f"ERROR: ZAP not found at path or command: {zap_cmd_list[0]}"
    except Exception as e:
        return f"ERROR: failed to start ZAP daemon: {e}"

    # Wait a moment for the daemon to come up (poll)
    wait = wait_seconds if wait_seconds is not None else ZAP_STARTUP_WAIT
    deadline = time.time() + wait
    while time.time() < deadline:
        if await _is_zap_up():
            return f"ZAP started (pid={_zap_proc.pid})."
        await asyncio.sleep(0.5)

    # Final check
    if await _is_zap_up():
        return f"ZAP started (pid={_zap_proc.pid})."
    return "ERROR: ZAP did not respond after startup wait."


@mcp.tool()
async def stop_zap() -> str:
    """Stop ZAP via API shutdown (preferred) then fallback to killing the process if needed."""
    global _zap_proc
    # try API shutdown
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{ZAP_BASE}/JSON/core/action/shutdown/", params=_zap_api_params())
            if r.status_code == 200:
                # give time for process termination
                await asyncio.sleep(1.0)
                if _zap_proc and _zap_proc.poll() is None:
                    _zap_proc.kill()
                return "ZAP shutdown via API."
            # otherwise continue to kill
    except Exception:
        pass

    # fallback: kill stored subprocess if present
    if _zap_proc:
        try:
            _zap_proc.kill()
            _zap_proc.wait(timeout=3)
            _zap_proc = None
            return "ZAP process killed."
        except Exception as e:
            return f"ERROR: failed to kill ZAP process: {e}"

    return "ZAP not running (no process tracked)."


@mcp.tool()
async def ensure_zap() -> str:
    """Ensure ZAP is running; start it if not. Returns status message."""
    if await _is_zap_up():
        return "ZAP is already running and reachable."
    return await start_zap_daemon()


@mcp.tool()
async def zap_spider(target: str, max_children: int = 5, context_name: Optional[str] = None) -> str:
    """
    Start ZAP spider (discovery). Returns a spider id or error string.
    context_name optional - if you use contexts configured in ZAP.
    """
    if not await _is_zap_up():
        return "ERROR: ZAP not running. Call ensure_zap or start_zap_daemon first."

    params = _zap_api_params({"url": target, "maxChildren": max_children})
    if context_name:
        params["contextName"] = context_name

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(f"{ZAP_BASE}/JSON/spider/action/scan/", params=params)
            j = resp.json()
            # response usually contains "scan" id
            return f"Spider started: {json.dumps(j)}"
    except Exception as e:
        return f"ERROR: zap_spider failed: {e}"


@mcp.tool()
async def zap_active_scan(target: str, recurse: bool = True, in_scope_only: bool = False,
                          scan_policy_name: Optional[str] = None, timeout_seconds: int = 600,
                          poll_interval: float = 2.0) -> str:
    """
    Start an active scan and wait (poll) for completion or timeout.
    Returns a summary (alerts count) or an error string.
    - target: target URL (must be authorized)
    - timeout_seconds: max wait time for the scan to finish
    """
    if not await _is_zap_up():
        return "ERROR: ZAP not running. Call ensure_zap or start_zap_daemon first."

    params = _zap_api_params(
        {"url": target, "recurse": "true" if recurse else "false", "inScopeOnly": "true" if in_scope_only else "false"})
    if scan_policy_name:
        params["scanPolicyName"] = scan_policy_name

    try:
        async with httpx.AsyncClient(timeout=30) as client:
            resp = await client.get(f"{ZAP_BASE}/JSON/ascan/action/scan/", params=params)
            start_info = resp.json()
            # start_info may contain scan id
            # Poll for progress
            scan_id = start_info.get("scan") or start_info.get("scanId") or ""
            deadline = time.time() + timeout_seconds
            last_pct = None
            while time.time() < deadline:
                status_r = await client.get(f"{ZAP_BASE}/JSON/ascan/view/status/",
                                            params=_zap_api_params({"scanId": scan_id}))
                status_j = status_r.json()
                # status_j usually has 'status' key with percent complete
                percent = status_j.get("status")
                # break if completed or 100
                if percent is None:
                    # no percent info, poll alerts instead
                    break
                try:
                    pct_int = int(percent)
                except Exception:
                    pct_int = None
                if pct_int is not None:
                    last_pct = pct_int
                    if pct_int >= 100:
                        break
                await asyncio.sleep(poll_interval)

            # When done or timed out, fetch alerts summary
            alerts_r = await client.get(f"{ZAP_BASE}/JSON/core/view/alerts/",
                                        params=_zap_api_params({"baseurl": target}))
            alerts = alerts_r.json()
            count = len(alerts.get("alerts", alerts)) if isinstance(alerts, dict) else (
                len(alerts) if isinstance(alerts, list) else 0)
            return json.dumps({
                "scan_id": scan_id,
                "last_progress_percent": last_pct,
                "alerts_count": count,
                "alerts_sample": alerts if count < 20 else alerts[:20],
            }, default=str)
    except Exception as e:
        return f"ERROR: zap_active_scan failed: {e}"


@mcp.tool()
async def zap_get_alerts(baseurl: Optional[str] = None, risk_filter: Optional[str] = None) -> str:
    """
    Get alerts. baseurl optional to restrict results. risk_filter optional (e.g., 'High').
    Returns JSON stringified alerts list or error message.
    """
    if not await _is_zap_up():
        return "ERROR: ZAP not running."

    params = _zap_api_params()
    if baseurl:
        params["baseurl"] = baseurl
    try:
        async with httpx.AsyncClient(timeout=20) as client:
            resp = await client.get(f"{ZAP_BASE}/JSON/core/view/alerts/", params=params)
            j = resp.json()
            alerts = j.get("alerts", j)
            if risk_filter:
                alerts = [a for a in alerts if a.get("risk") and risk_filter.lower() in a.get("risk", "").lower()]
            return json.dumps(alerts, default=str)
    except Exception as e:
        return f"ERROR: zap_get_alerts failed: {e}"


@mcp.tool()
async def zap_export_report(format_type: str = "json", out_path: Optional[str] = None) -> str:
    """
    Export full ZAP report in 'json' (default), 'xml', or 'html'.
    Returns path to saved file or error string.
    """
    if format_type not in ("json", "xml", "html"):
        return "ERROR: unsupported format. Use json|xml|html"

    if not await _is_zap_up():
        return "ERROR: ZAP not running."

    out_path = out_path or f"./zap_report.{format_type}"
    endpoint_map = {
        "json": f"{ZAP_BASE}/OTHER/core/other/jsonreport/",
        "xml": f"{ZAP_BASE}/OTHER/core/other/xmlreport/",
        "html": f"{ZAP_BASE}/OTHER/core/other/htmlreport/",
    }
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.get(endpoint_map[format_type], params=_zap_api_params())
            if r.status_code != 200:
                return f"ERROR: report endpoint returned {r.status_code}: {r.text}"
            with open(out_path, "wb") as f:
                f.write(r.content)
            return f"Report saved to {out_path}"
    except Exception as e:
        return f"ERROR: zap_export_report failed: {e}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
