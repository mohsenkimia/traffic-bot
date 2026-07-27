import os
import requests
from bs4 import BeautifulSoup
import json

# --- تنظیمات ---
URL_MOMTAZ = "https://www.momtaznews.com/%D8%A2%D8%AE%D8%B1%DB%8C%D9%86-%D9%88%D8%B6%D8%B9%DB%8C%D8%AA-%D8%AA%D8%B1%D8%A7%D9%81%DB%8C%DA%A9-%D8%AC%D8%A7%D8%AF%D9%87-%D9%87%D8%A7/"
URL_141 = "https://141.ir/news/obstruction-list"
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK")
STATUS_FILE_MOMTAZ = "last_status.json"       # وضعیت ممتاز نیوز
STATUS_FILE_141 = "obstruction_status.json"   # وضعیت انسدادهای ۱۴۱

# --- ابزار ارسال پیام به دیسکورد (تکه‌تکه اگر طولانی باشد) ---
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

# --- بخش ۱: مانیتورینگ ممتاز نیوز (دقیقاً مثل قبل) ---
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

# --- بخش ۲: مانیتورینگ انسدادهای سایت ۱۴۱ ---
def get_obstructions_141():
    headers = {"User-Agent": "Mozilla/5.0 (compatible; TrafficBot/1.0)"}
    try:
        resp = requests.get(URL_141, headers=headers, timeout=30)
        resp.raise_for_status()
    except Exception as e:
        print(f"⚠️ (۱۴۱) خطا در دریافت صفحه: {e}")
        return

    soup = BeautifulSoup(resp.text, "html.parser")
    # پیدا کردن تمام ردیف‌های جدول (div با کلاس‌های grid grid-cols-8 ...)
    rows = soup.select("div.grid.grid-cols-8.items-center.gap-4.py-6.text-center")
    if not rows:
        print("⚠️ (۱۴۱) هیچ ردیف انسدادی پیدا نشد.")
        return

    obstructions = []
    for row in rows:
        # استخراج تگ‌های p داخل هر ردیف (به ترتیب)
        p_tags = row.find_all("p")
        if len(p_tags) < 5:
            continue  # ردیف معیوب

        # تاریخ و ساعت
        date_p = p_tags[0]
        spans = date_p.find_all("span")
        if len(spans) >= 2:
            date_str = spans[0].text.strip() + " " + spans[1].text.strip()
        else:
            date_str = date_p.text.strip()

        province = p_tags[1].text.strip()
        description = p_tags[2].text.strip()
        reason = p_tags[3].text.strip()
        # جهت (ممکن است داخل span باشد)
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
