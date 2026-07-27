import os
import requests
from bs4 import BeautifulSoup
import json
from playwright.sync_api import sync_playwright

# --- تنظیمات ---
URL_MOMTAZ = "https://www.momtaznews.com/..."
URL_141 = "https://141.ir/news/obstruction-list"
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK")
STATUS_FILE_MOMTAZ = "last_status.json"
STATUS_FILE_141 = "obstruction_status.json"

# --- ابزار ارسال پیام ---
def send_discord_message(content: str):
    # (همان تابع قبلی، بدون تغییر)
    pass

# --- بخش ممتاز نیوز (بدون تغییر) ---
def get_traffic_info_momtaz():
    # (همان کد قبلی)
    pass

# --- بخش ۱۴۱ با Playwright ---
def get_obstructions_141():
    print("🔄 (۱۴۱) در حال بارگذاری صفحه با مرورگر...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(URL_141, wait_until="domcontentloaded", timeout=120000)
            # صبر کن تا حداقل یک ردیف ظاهر شود
            page.wait_for_selector("div.grid.grid-cols-8.items-center.gap-4.py-6.text-center", timeout=30000)
            html = page.content()
        except Exception as e:
            print(f"⚠️ (۱۴۱) خطا در بارگذاری: {e}")
            browser.close()
            return
        browser.close()

    soup = BeautifulSoup(html, "html.parser")
    rows = soup.select("div.grid.grid-cols-8.items-center.gap-4.py-6.text-center")
    if not rows:
        print("⚠️ (۱۴۱) هیچ ردیف انسدادی پیدا نشد.")
        return

    obstructions = []
    for row in rows:
        p_tags = row.find_all("p")
        if len(p_tags) < 5:
            continue
        date_spans = p_tags[0].find_all("span")
        if len(date_spans) >= 2:
            date_str = date_spans[0].text.strip() + " " + date_spans[1].text.strip()
        else:
            date_str = p_tags[0].text.strip()

        province = p_tags[1].text.strip()
        description = p_tags[2].text.strip()
        reason = p_tags[3].text.strip()
        direction_p = p_tags[4]
        direction_span = direction_p.find("span")
        direction = direction_span.text.strip() if direction_span else direction_p.text.strip()

        obstructions.append(
            f"• استان: {province}\n"
            f"  تاریخ: {date_str}\n"
            f"  مسیر: {description}\n"
            f"  علت: {reason}\n"
            f"  جهت: {direction}"
        )

    if not obstructions:
        print("⚠️ (۱۴۱) لیست انسدادها خالی است.")
        return

    new_content = "\u200F**🚧 انسدادهای جاده‌ای (سایت ۱۴۱):**\n" + "\n\n".join(obstructions)

    old_content = ""
    if os.path.exists(STATUS_FILE_141):
        with open(STATUS_FILE_141, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                old_content = data.get("content", "")
            except:
                old_content = ""

    if new_content == old_content:
        print("ℹ️ (۱۴۱) تغییری در لیست انسدادها ایجاد نشده.")
    else:
        print("🔄 (۱۴۱) تغییر در لیست انسدادها شناسایی شد.")
        send_discord_message(new_content)
        with open(STATUS_FILE_141, "w", encoding="utf-8") as f:
            json.dump({"content": new_content}, f, ensure_ascii=False, indent=2)
        print("✅ (۱۴۱) فایل وضعیت انسدادها به‌روزرسانی شد.")

# --- اجرای اصلی ---
if __name__ == "__main__":
    get_traffic_info_momtaz()
    get_obstructions_141()
