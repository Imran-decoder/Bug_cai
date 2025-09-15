#!/usr/bin/env python3
"""
selenium_test.py
Usage:
    python selenium_test.py --url https://example.com --out results.json --proxy http://127.0.0.1:8080
"""
import argparse
import json
import time
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager

def run_test(url: str, out: str = "selenium_result.json", proxy: str | None = None, headless: bool = True, timeout: int = 30):
    result = {
        "url": url,
        "success": False,
        "error": None,
        "title": None,
        "screenshot": None,
        "page_source": None,
        "timestamp": time.time(),
    }

    opts = Options()
    if headless:
        opts.add_argument("--headless=new")        # headless chrome
        opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    # accept insecure certs (useful when proxying through ZAP)
    opts.set_capability("acceptInsecureCerts", True)

    if proxy:
        opts.add_argument(f"--proxy-server={proxy}")

    # create driver
    driver = None
    try:
        driver = webdriver.Chrome(ChromeDriverManager().install(), options=opts)
        driver.set_page_load_timeout(timeout)
        driver.get(url)
        time.sleep(1.0)  # allow some JS to run
        result["title"] = driver.title

        # screenshot
        screenshot_path = out.replace(".json", ".png")
        driver.save_screenshot(screenshot_path)
        result["screenshot"] = os.path.abspath(screenshot_path)

        # page source
        page_src_path = out.replace(".json", ".html")
        with open(page_src_path, "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        result["page_source"] = os.path.abspath(page_src_path)

        result["success"] = True
    except Exception as e:
        result["error"] = str(e)
    finally:
        if driver:
            try:
                driver.quit()
            except Exception:
                pass

    with open(out, "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2)

    return result

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--url", required=True, help="Target URL to test")
    parser.add_argument("--out", default="selenium_result.json")
    parser.add_argument("--proxy", default=None, help="HTTP proxy (e.g. http://127.0.0.1:8080)")
    parser.add_argument("--headless", action="store_true")
    parser.add_argument("--timeout", type=int, default=30)
    args = parser.parse_args()
    res = run_test(args.url, out=args.out, proxy=args.proxy, headless=args.headless, timeout=args.timeout)
    print(json.dumps(res, indent=2))
