import os
import requests
from bs4 import BeautifulSoup
import json
from playwright.sync_api import sync_playwright

# --- تنظیمات ---
URL_MOMTAZ = "https://www.momtaznews.com/%D8%A2%D8%AE%D8%B1%DB%8C%D9%86-%D9%88%D8%B6%D8%B9%DB%8C%D8%AA-%D8%AA%D8%B1%D8%A7%D9%81%DB%8C%DA%A9-%D8%AC%D8%A7%D8%AF%D9%87-%D9%87%D8%A7/"
URL_141 = "https://141.ir/news/obstruction-list"
URL_141_STATE = "https://141.ir/news/latest-roads-state"
URL_141_POLICE = "https://141.ir/news/police-traffic-restrictions"
URL_141_WORKSHOPS = "https://api.141.ir/api/road_workshops/bbox"

DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK")

STATUS_FILE_MOMTAZ = "last_status.json"
STATUS_FILE_141 = "obstruction_status.json"
STATUS_FILE_141_STATE = "roads_state_141.json"
STATUS_FILE_141_POLICE = "police_restrictions_141.json"
STATUS_FILE_141_WORKSHOPS = "workshops_141.json"

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

# --- بخش ۱۴۱: انسدادها (فقط موارد جدید، بدون لینک) ---
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

    new_ids = set()
    all_current = {}

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

        uid = f"{province}::{description}"
        new_ids.add(uid)
        all_current[uid] = {
            "date": date_str,
            "province": province,
            "description": description,
            "reason": reason,
            "direction": direction
        }

    old_ids = set()
    if os.path.exists(STATUS_FILE_141):
        with open(STATUS_FILE_141, "r", encoding="utf-8") as f:
            try:
                data = json.load(f)
                old_ids = set(data.get("ids", []))
            except:
                old_ids = set()

    new_items_ids = new_ids - old_ids
    if not new_items_ids:
        print("ℹ️ (۱۴۱) هیچ مورد جدیدی اضافه نشده است.")
    else:
        print(f"🆕 (۱۴۱) {len(new_items_ids)} مورد جدید اضافه شده:")
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

    with open(STATUS_FILE_141, "w", encoding="utf-8") as f:
        json.dump({"ids": list(new_ids)}, f, ensure_ascii=False, indent=2)
    print("✅ (۱۴۱) فایل وضعیت انسدادها به‌روزرسانی شد.")

# --- بخش ۱۴۱: وضعیت راه‌ها (شمالی و سایر) ---
def get_latest_roads_state_141():
    print("🔄 (۱۴۱-State) در حال بارگذاری صفحه با مرورگر...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(URL_141_STATE, wait_until="domcontentloaded", timeout=120000)
            page.wait_for_selector("div.sticky.top-20", timeout=30000)
        except Exception as e:
            print(f"⚠️ (۱۴۱-State) خطا در بارگذاری صفحه: {e}")
            browser.close()
            return

        try:
            content_div_1 = page.wait_for_selector("div.flex-1 > div.bg-buttons", timeout=10000)
            north_html = content_div_1.inner_html()
        except:
            print("⚠️ (۱۴۱-State) تب اول پیدا نشد.")
            browser.close()
            return

        try:
            page.click("text=آخرین وضعیت جوی ترافیکی سایر محور ها")
            page.wait_for_timeout(2000)
            content_div_2 = page.wait_for_selector("div.flex-1 > div.bg-buttons", timeout=10000)
            other_html = content_div_2.inner_html()
        except:
            print("⚠️ (۱۴۱-State) تب دوم پیدا نشد یا کلیک ناموفق بود.")
            browser.close()
            return

        browser.close()

    def extract_text_from_html(html):
        soup = BeautifulSoup(html, "html.parser")
        lines = []
        for p in soup.find_all("p", class_="MsoNormal"):
            line = p.get_text(strip=True)
            if line:
                lines.append(line)
        return "\n".join(lines) if lines else "اطلاعات موجود نیست."

    north_text = extract_text_from_html(north_html)
    other_text = extract_text_from_html(other_html)

    new_sections = {
        "آخرین وضعیت جوی ترافیکی محورهای شمالی": f"**آخرین وضعیت جوی ترافیکی محورهای شمالی:**\n{north_text}",
        "آخرین وضعیت جوی ترافیکی سایر محورها": f"**آخرین وضعیت جوی ترافیکی سایر محورها:**\n{other_text}"
    }

    old_sections = {}
    if os.path.exists(STATUS_FILE_141_STATE):
        with open(STATUS_FILE_141_STATE, "r", encoding="utf-8") as f:
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
            print(f"🔄 (۱۴۱-State) تغییر در بخش «{title}»")
            send_discord_message(message)

    if not changed:
        print("ℹ️ (۱۴۱-State) تغییری در وضعیت راه‌ها ایجاد نشده.")
    else:
        with open(STATUS_FILE_141_STATE, "w", encoding="utf-8") as f:
            json.dump(new_sections, f, ensure_ascii=False, indent=2)
        print("✅ (۱۴۱-State) فایل وضعیت به‌روزرسانی شد.")

# --- بخش ۱۴۱: محدودیت‌های تردد پلیس ---
def get_police_restrictions_141():
    print("🔄 (۱۴۱-Police) در حال بارگذاری صفحه با مرورگر...")
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        try:
            page.goto(URL_141_POLICE, wait_until="domcontentloaded", timeout=120000)
            page.wait_for_selector("div.flex-1 > div.bg-buttons", timeout=30000)
        except Exception as e:
            print(f"⚠️ (۱۴۱-Police) خطا در بارگذاری: {e}")
            browser.close()
            return

        try:
            content_div = page.wait_for_selector("div.flex-1 > div.bg-buttons", timeout=10000)
            main_html = content_div.inner_html()
        except:
            print("⚠️ (۱۴۱-Police) محتوای محدودیت‌ها پیدا نشد.")
            browser.close()
            return

        second_html = ""
        try:
            page.click("text=محدودیت تردد وسایل نقلیه")
            page.wait_for_timeout(2000)
            second_div = page.wait_for_selector("div.flex-1 > div.bg-buttons", timeout=10000)
            second_html = second_div.inner_html()
        except:
            pass

        browser.close()

    def extract_text(html):
        soup = BeautifulSoup(html, "html.parser")
        lines = []
        for p in soup.find_all("p", class_="MsoNormal"):
            line = p.get_text(strip=True)
            if line:
                lines.append(line)
        return "\n".join(lines) if lines else "اطلاعات موجود نیست."

    main_text = extract_text(main_html)
    second_text = extract_text(second_html) if second_html else ""

    sections = {}
    if main_text:
        sections["محدودیت‌های تردد (اصلی)"] = f"**محدودیت‌های تردد (پلیس راه):**\n{main_text}"
    if second_text:
        sections["سایر محدودیت‌ها"] = f"**سایر محدودیت‌ها:**\n{second_text}"

    if not sections:
        print("⚠️ (۱۴۱-Police) متنی برای محدودیت‌ها استخراج نشد.")
        return

    old_sections = {}
    if os.path.exists(STATUS_FILE_141_POLICE):
        with open(STATUS_FILE_141_POLICE, "r", encoding="utf-8") as f:
            try:
                old_sections = json.load(f)
            except:
                old_sections = {}

    changed = False
    for title, text in sections.items():
        old_text = old_sections.get(title, "")
        if text != old_text:
            changed = True
            message = "\u200F" + text
            print(f"🔄 (۱۴۱-Police) تغییر در بخش «{title}»")
            send_discord_message(message)

    if not changed:
        print("ℹ️ (۱۴۱-Police) تغییری در محدودیت‌ها ایجاد نشده.")
    else:
        with open(STATUS_FILE_141_POLICE, "w", encoding="utf-8") as f:
            json.dump(sections, f, ensure_ascii=False, indent=2)
        print("✅ (۱۴۱-Police) فایل وضعیت به‌روزرسانی شد.")

# --- بخش ۱۴۱: کارگاه‌های جاده‌ای (API با تقسیم‌بندی) ---
def get_workshops_141():
    print("🔄 (۱۴۱-Workshops) دریافت لیست کارگاه‌ها...")
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; TrafficBot/1.0)",
        "Accept": "application/json, text/plain, */*",
        "Origin": "https://141.ir",
        "Referer": "https://141.ir/",
    }

    # ۴ ناحیه برای پوشش کل ایران با zoom=8
    regions = [
        {"min_lon": "44", "min_lat": "32", "max_lon": "50", "max_lat": "40", "zoom": "8"},  # شمال غرب
        {"min_lon": "50", "min_lat": "32", "max_lon": "64", "max_lat": "40", "zoom": "8"},  # شمال شرق
        {"min_lon": "44", "min_lat": "25", "max_lon": "50", "max_lat": "32", "zoom": "8"},  # جنوب غرب
        {"min_lon": "50", "min_lat": "25", "max_lon": "64", "max_lat": "32", "zoom": "8"},  # جنوب شرق
    ]

    all_ids = set()
    all_current = {}

    for i, region in enumerate(regions, 1):
        try:
            resp = requests.post(URL_141_WORKSHOPS, headers=headers, data=region, timeout=30)
            resp.raise_for_status()
            data = resp.json()
        except Exception as e:
            print(f"⚠️ (۱۴۱-Workshops) خطا در ناحیه {i}: {e}")
            continue

        items = data.get("data", [])
        for item in items:
            uid = str(item["id"])
            if uid in all_ids:
                continue   # تکراری نگیریم
            all_ids.add(uid)
            meta = item["meta"]
            start_time = meta["start_time"]
            end_time = meta["end_time"]
            all_current[uid] = {
                "title": meta["title"],
                "province": meta["province_fa"],
                "start_date": meta["start_date"],
                "end_date": meta["end_date"],
                "start_time": f"{start_time[:2]}:{start_time[2:]}",
                "end_time": f"{end_time[:2]}:{end_time[2:]}",
                "status": meta["passing_situation_fa"],
                "operation": meta["operation_type_fa"]
            }

    if not all_current:
        print("⚠️ (۱۴۱-Workshops) هیچ کارگاهی دریافت نشد.")
        return

    old_ids = set()
    if os.path.exists(STATUS_FILE_141_WORKSHOPS):
        with open(STATUS_FILE_141_WORKSHOPS, "r", encoding="utf-8") as f:
            try:
                old_data = json.load(f)
                old_ids = set(old_data.get("ids", []))
            except:
                old_ids = set()

    added = all_ids - old_ids
    if not added:
        print("ℹ️ (۱۴۱-Workshops) هیچ کارگاه جدیدی اضافه نشده.")
    else:
        print(f"🆕 (۱۴۱-Workshops) {len(added)} کارگاه جدید:")
        messages = []
        for uid in added:
            w = all_current[uid]
            msg = (
                f"• استان: {w['province']}\n"
                f"  تاریخ: {w['start_date']} تا {w['end_date']}\n"
                f"  ساعت: {w['start_time']} تا {w['end_time']}\n"
                f"  وضعیت: {w['status']}\n"
                f"  عملیات: {w['operation']}\n"
                f"  مسیر: {w['title']}"
            )
            messages.append(msg)
        full = "\u200F**🛠️ کارگاه جاده‌ای تازه:**\n" + "\n\n".join(messages)
        send_discord_message(full)

    with open(STATUS_FILE_141_WORKSHOPS, "w", encoding="utf-8") as f:
        json.dump({"ids": list(all_ids)}, f, ensure_ascii=False, indent=2)
    print("✅ (۱۴۱-Workshops) فایل وضعیت به‌روزرسانی شد.")

# --- اجرای اصلی با کنترل از طریق Secrets ---
if __name__ == "__main__":
    if os.environ.get("ENABLE_MOMTAZ", "false").lower() == "true":
        get_traffic_info_momtaz()
    else:
        print("ℹ️ (ممتاز نیوز) غیرفعال است. (ENABLE_MOMTAZ=true)")

    if os.environ.get("ENABLE_141_OBSTRUCTIONS", "false").lower() == "true":
        get_obstructions_141()
    else:
        print("ℹ️ (۱۴۱ - انسدادها) غیرفعال است. (ENABLE_141_OBSTRUCTIONS=true)")

    if os.environ.get("ENABLE_141_STATE", "false").lower() == "true":
        get_latest_roads_state_141()
    else:
        print("ℹ️ (۱۴۱ - وضعیت راه‌ها) غیرفعال است. (ENABLE_141_STATE=true)")

    if os.environ.get("ENABLE_141_POLICE", "false").lower() == "true":
        get_police_restrictions_141()
    else:
        print("ℹ️ (۱۴۱ - محدودیت‌های پلیس) غیرفعال است. (ENABLE_141_POLICE=true)")

    if os.environ.get("ENABLE_141_WORKSHOPS", "false").lower() == "true":
        get_workshops_141()
    else:
        print("ℹ️ (۱۴۱ - کارگاه‌های جاده‌ای) غیرفعال است. (ENABLE_141_WORKSHOPS=true)")
