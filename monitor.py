import os
import requests
from bs4 import BeautifulSoup
import json

URL = "https://www.momtaznews.com/%D8%A2%D8%AE%D8%B1%DB%8C%D9%86-%D9%88%D8%B6%D8%B9%DB%8C%D8%AA-%D8%AA%D8%B1%D8%A7%D9%81%DB%8C%DA%A9-%D8%AC%D8%A7%D8%AF%D9%87-%D9%87%D8%A7/"
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK")
STATUS_FILE = "last_status.txt"

def send_discord_message(content: str):
    if not DISCORD_WEBHOOK:
        print("⚠️ DISCORD_WEBHOOK not set.")
        return
    data = {"content": content}
    headers = {"Content-Type": "application/json"}
    try:
        resp = requests.post(DISCORD_WEBHOOK, data=json.dumps(data), headers=headers)
        if resp.status_code == 204:
            print("✅ پیام به دیسکورد ارسال شد.")
        else:
            print(f"❌ خطا در ارسال: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"❌ خطای اتصال: {e}")

def get_traffic_info():
    headers = {"User-Agent": "Mozilla/5.0 (compatible; TrafficBot/1.0)"}
    resp = requests.get(URL, headers=headers, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    content_div = soup.find("div", class_="post-single-content")
    if not content_div:
        print("⚠️ محتوای خبر پیدا نشد.")
        return

    # حذف بخش‌های نامربوط (مطالب پیشنهادی و تبلیغات)
    crp = content_div.find("div", id="crp_related")
    if crp:
        crp.decompose()

    # پیدا کردن تمام جعبه‌های وضعیت راه‌ها
    road_boxes = content_div.find_all("div", class_="road-box")
    if not road_boxes:
        print("⚠️ هیچ جعبه اطلاعات راه پیدا نشد.")
        return

    sections = []
    for box in road_boxes:
        # عنوان (h3)
        h3 = box.find("h3")
        title = h3.get_text(strip=True) if h3 else "بدون عنوان"
        # محتوا (p) – ممکن است چند p باشد، اما معمولاً یکی است
        p = box.find("p")
        if p:
            # خط‌های داخل p رو جدا می‌کنیم و بولت می‌زنیم
            lines = [line.strip() for line in p.get_text(separator="\n").splitlines() if line.strip()]
            # هر خط رو با • نمایش می‌دهیم
            content = "\n".join(f"• {line}" for line in lines)
        else:
            content = "اطلاعات موجود نیست."
        sections.append(f"**{title}:**\n{content}")

    # ساخت پیام نهایی (راست‌چین با \u200F)
    new_status = "\u200F" + "\n\n".join(sections)

    # خواندن وضعیت قبلی
    old_status = ""
    if os.path.exists(STATUS_FILE):
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            old_status = f.read().strip()

    if new_status.strip() == old_status:
        print("ℹ️ تغییری در وضعیت راه‌ها ایجاد نشده. پیامی به دیسکورد ارسال نمی‌شود.")
        return

    print("🔄 تغییرات جدید شناسایی شد. ارسال به دیسکورد...")
    if len(new_status) > 2000:
        message_to_send = new_status[:1900] + "\n... (متن کامل در لاگ موجود است)"
    else:
        message_to_send = new_status

    send_discord_message(message_to_send)

    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        f.write(new_status)
    print("✅ فایل وضعیت به‌روزرسانی شد.")

if __name__ == "__main__":
    get_traffic_info()
