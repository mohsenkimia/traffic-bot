import os
import requests
from bs4 import BeautifulSoup
import json

URL = "https://www.momtaznews.com/%D8%A2%D8%AE%D8%B1%DB%8C%D9%86-%D9%88%D8%B6%D8%B9%DB%8C%D8%AA-%D8%AA%D8%B1%D8%A7%D9%81%DB%8C%DA%A9-%D8%AC%D8%A7%D8%AF%D9%87-%D9%87%D8%A7/"
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK")
STATUS_FILE = "last_status.json"   # تغییر به json

def send_discord_message(content: str):
    if not DISCORD_WEBHOOK:
        print("⚠️ DISCORD_WEBHOOK not set.")
        return
    # اگر طول پیام بیش از ۲۰۰۰ کاراکتر بود، تکه‌تکه می‌فرستیم
    max_len = 1950  # کمی کمتر از ۲۰۰۰ برای احتیاط
    while len(content) > 0:
        if len(content) <= max_len:
            chunk = content
            content = ""
        else:
            # برش در نزدیکترین خط جدید
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

def get_traffic_info():
    headers = {"User-Agent": "Mozilla/5.0 (compatible; TrafficBot/1.0)"}
    resp = requests.get(URL, headers=headers, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    content_div = soup.find("div", class_="post-single-content")
    if not content_div:
        print("⚠️ محتوای خبر پیدا نشد.")
        return

    # حذف بخش‌های نامربوط
    crp = content_div.find("div", id="crp_related")
    if crp:
        crp.decompose()

    road_boxes = content_div.find_all("div", class_="road-box")
    if not road_boxes:
        print("⚠️ هیچ جعبه اطلاعات راه پیدا نشد.")
        return

    # دیکشنری جدید از وضعیت فعلی: کلید = عنوان (بدون "بروزرسانی: ...")، مقدار = متن بولت‌دار
    new_sections = {}
    for box in road_boxes:
        h3 = box.find("h3")
        if not h3:
            continue
        # جدا کردن عنوان اصلی از بروزرسانی
        raw_title = h3.get_text(strip=True)
        # حذف بخش "(بروزرسانی: ...)" برای کلید
        clean_title = raw_title.split("(بروزرسانی:")[0].strip()
        # محتوا
        p = box.find("p")
        if p:
            lines = [line.strip() for line in p.get_text(separator="\n").splitlines() if line.strip()]
            content = "\n".join(lines)
        else:
            content = "اطلاعات موجود نیست."
        new_sections[clean_title] = f"**{clean_title}:**\n{content}"

    # خواندن وضعیت قبلی
    old_sections = {}
    if os.path.exists(STATUS_FILE):
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            try:
                old_sections = json.load(f)
            except:
                old_sections = {}

    # پیدا کردن بخش‌های تغییرکرده
    changed = False
    for title, text in new_sections.items():
        old_text = old_sections.get(title, "")
        if text != old_text:
            changed = True
            # ارسال پیام راست‌چین
            message = "\u200F" + text
            print(f"🔄 تغییر در بخش «{title}»")
            send_discord_message(message)

    if not changed:
        print("ℹ️ تغییری در هیچ یک از بخش‌ها ایجاد نشده. پیامی ارسال نمی‌شود.")
    else:
        # ذخیره وضعیت جدید
        with open(STATUS_FILE, "w", encoding="utf-8") as f:
            json.dump(new_sections, f, ensure_ascii=False, indent=2)
        print("✅ فایل وضعیت به‌روزرسانی شد.")

if __name__ == "__main__":
    get_traffic_info()
