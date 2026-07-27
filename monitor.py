import os
import requests
from bs4 import BeautifulSoup
import json
from playwright.sync_api import sync_playwright

# --- تنظیمات ---
URL_MOMTAZ = "https://www.momtaznews.com/%D8%A2%D8%AE%D8%B1%DB%8C%D9%86-%D9%88%D8%B6%D8%B9%DB%8C%D8%AA-%D8%AA%D8%B1%D8%A7%D9%81%DB%8C%DA%A9-%D8%AC%D8%A7%D8%AF%D9%87-%D9%87%D8%A7/"
URL_141 = "https://141.ir/news/obstruction-list"
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK")
STATUS_FILE_MOMTAZ = "last_status.json"
STATUS_FILE_141 = "obstruction_status.json"

# --- ابزار ارسال پیام به دیسکورد (تکه‌تکه) ---
def send_discord_message(content: str):
    if not DISCORD_WEBHOOK:
        print("⚠️ DISCORD_WEBHOOK not set.")
        return
    max_len = 1950
    while len(content) > 0:
        if len(content) <= max_len:
            chunk = content
            content = ""
        else:
            split_at = content.rfind("\n", 0, max_len)
            if split_at == -1:
                split_at = max_len
            chunk = content[:split_at]
            content = content[split_at:].lstrip()
        data = {"content": chunk}
        headers = {"Content-Type": "application/json"}
        try:
            resp = requests.post(DISCORD_WEBHOOK, data=json.dumps(data), headers=headers)
            if resp.status_code == 204:
                print(f"✅ قطعه ارسال شد ({len(chunk)} کاراکتر)")
            else:
                print(f"❌ خطا در ارسال: {resp.status_code} {resp.text}")
                break
        except Exception as e:
            print(f"❌ خطای اتصال: {e}")
            break

# --- بخش ممتاز نیوز ---
def get_traffic_info_momtaz():
    headers = {"User-Agent": "Mozilla/5.0 (compatible; TrafficBot/1.0)"}
    resp = requests.get(URL_MOMTAZ, headers=headers, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    content_div = soup.find("div", class_="post-single-content")
    if not content_div:
        print("⚠️ (ممتاز نیوز) محتوای خبر پیدا نشد.")
        return

    crp = content_div.find("div", id="crp_related")
    if crp:
        crp.decompose()

    road_boxes = content_div.find_all("div", class_="road-box")
    if not road_boxes:
        print("⚠️ (ممتاز نیوز) هیچ جعبه اطلاعات راه پیدا نشد.")
        return

    new_sections = {}
    for box in road_boxes:
        h3 = box.find("h3")
        if not h3:
            continue
        raw_title = h3.get_text(strip=True)
        clean_title = raw_title.split("(بروزرسانی:")[0].strip()
        p = box.find("p")
        if p:
            lines = [line.strip() for line in p.get_text(separator="\n").splitlines() if line.strip()]
            content = "\n".join(lines)
        else:
            content = "اطلاعات موجود نیست."
        new_sections[clean_title] = f"**{clean_title}:**\n{content}"

    old_sections = {}
    if os.path.exists(STATUS_FILE_MOMTAZ):
        with open(STATUS_FILE_MOMTAZ, "r", encoding="utf-8") as f:
            try:
                old_sections = json.load(f)
            except:
                old_sections = {}

    changed = False
    for title, text in new_sections.items():
        old_text = old_sections.get(title, "")
        if text != old_text:
            changed = True
            message = "\u200F" + text
            print(f"🔄 (ممتاز نیوز) تغییر در بخش «{title}»")
            send_discord_message(message)

    if not changed:
        print("ℹ️ (ممتاز نیوز) تغییری در هیچ یک از بخش‌ها ایجاد نشده.")
    else:
        with open(STATUS_FILE_MOMTAZ, "w", encoding="utf-8") as f:
            json.dump(new_sections, f, ensure_ascii=False, indent=2)
        print("✅ (ممتاز نیوز) فایل وضعیت به‌روزرسانی شد.")

# --- بخش ۱۴۱ (با Playwright) ---
def get_obstructions_141():
    print("🔄 (۱۴۱) در حال بارگذاری صفحه با مرورگر...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(URL_141, wait_until="domcontentloaded", timeout=120000)
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

    # مجموعه شناسه‌های جدید (استان + مسیر)
    new_ids = set()
    # اطلاعات کامل ردیف‌ها برای ساخت پیام در صورت جدید بودن
    all_current = {}   # id -> dict with details

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

        # شناسه یکتا: ترکیب استان + مسیر (می‌توان تاریخ را هم اضافه کرد ولی معمولاً مسیر ثابت است)
        uid = f"{province}::{description}"
        new_ids.add(uid)
        all_current[uid] = {
            "date": date_str,
            "province": province,
            "description": description,
            "reason": reason,
            "direction": direction
        }

    # خواندن شناسه‌های قبلی از فایل
    old_ids = set()
    if os.path.exists(STATUS_FILE_141):
        with open(STATUS_FILE_141, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                old_ids = set(data.get("ids", []))
            except:
                old_ids = set()

    # پیدا کردن شناسه‌های جدید
    new_items_ids = new_ids - old_ids
    if not new_items_ids:
        print("ℹ️ (۱۴۱) هیچ مورد جدیدی اضافه نشده است.")
    else:
        print(f"🆕 (۱۴۱) {len(new_items_ids)} مورد جدید اضافه شده:")
        # ساخت پیام با موارد جدید
        new_messages = []
        for uid in new_items_ids:
            info = all_current[uid]
            new_messages.append(
                f"• استان: {info['province']}\n"
                f"  تاریخ: {info['date']}\n"
                f"  مسیر: {info['description']}\n"
                f"  علت: {info['reason']}\n"
                f"  جهت: {info['direction']}"
            )
        full_message = "\u200F**🚧 انسدادهای جدید (سایت ۱۴۱):**\n" + "\n\n".join(new_messages)
        send_discord_message(full_message)

    # ذخیره مجموعه جدید
    with open(STATUS_FILE_141, "w", encoding="utf-8") as f:
        json.dump({"ids": list(new_ids)}, f, ensure_ascii=False, indent=2)
    print("✅ (۱۴۱) فایل وضعیت انسدادها به‌روزرسانی شد.")

# --- اجرای اصلی ---
if __name__ == "__main__":
    get_traffic_info_momtaz()
    get_obstructions_141()
