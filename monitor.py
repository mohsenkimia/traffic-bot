from playwright.sync_api import sync_playwright
import hashlib
import os
import requests
import re

URL = "https://141.ir/news/latest-roads-state"
WEBHOOK = os.environ["DISCORD_WEBHOOK"]
STATE_FILE = "last_status.txt"

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto(URL, wait_until="networkidle", timeout=90000)
    text = page.locator("body").inner_text()
    browser.close()

match = re.search(
    r"آخرین وضعیت جوی ترافیکی محورهای شمالی(.*?)(آخرین وضعیت جوی ترافیکی سایر محورها|آخرین وضعیت جوی ترافیکی سایر محور ها)",
    text,
    re.S,
)

if not match:
    raise Exception("بخش محورهای شمالی پیدا نشد")

status = match.group(1).strip()
new_hash = hashlib.sha256(status.encode("utf-8")).hexdigest()
old_hash = ""

if os.path.exists(STATE_FILE):
    with open(STATE_FILE, "r", encoding="utf-8") as f:
        old_hash = f.read().strip()

if new_hash != old_hash:
    message = f"""🚨 **آخرین وضعیت جوی ترافیکی محورهای شمالی تغییر کرد**

{status}

🔗 {URL}
"""
    requests.post(
        WEBHOOK,
        json={"content": message},
        timeout=30,
    )
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        f.write(new_hash)
    print("Changes detected and sent to Discord.")
else:
    print("No changes.")
