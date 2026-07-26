import os
import requests
from bs4 import BeautifulSoup
import json

URL = "https://www.momtaznews.com/%D8%A2%D8%AE%D8%B1%DB%8C%D9%86-%D9%88%D8%B6%D8%B9%DB%8C%D8%AA-%D8%B1%D8%A7%D9%87%E2%80%8C%D9%87%D8%A7%DB%8C-%DA%A9%D8%B4%D9%88%D8%B1/"
DISCORD_WEBHOOK = os.environ.get("DISCORD_WEBHOOK")  # از environment variable می‌خواند

def send_discord_message(content: str):
    """ارسال پیام به دیسکورد از طریق وب‌هوک"""
    if not DISCORD_WEBHOOK:
        print("⚠️ هشدار: DISCORD_WEBHOOK تنظیم نشده است. پیامی ارسال نمی‌شود.")
        return

    data = {"content": content}
    headers = {"Content-Type": "application/json"}
    try:
        resp = requests.post(DISCORD_WEBHOOK, data=json.dumps(data), headers=headers)
        if resp.status_code == 204:
            print("✅ پیام با موفقیت به دیسکورد ارسال شد.")
        else:
            print(f"❌ خطا در ارسال پیام به دیسکورد: {resp.status_code} {resp.text}")
    except Exception as e:
        print(f"❌ خطا در اتصال به دیسکورد: {e}")

def get_traffic_info():
    headers = {"User-Agent": "Mozilla/5.0 (compatible; TrafficBot/1.0)"}
    resp = requests.get(URL, headers=headers, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    content_div = soup.find("div", class_="post-single-content")
    if not content_div:
        msg = "⚠️ نتوانستیم محتوای خبر را پیدا کنیم."
        print(msg)
        send_discord_message(msg)
        return

    # حذف بخش‌های اضافی (همانند قبل)
    related_div = content_div.find("div", id="crp_related")
    if related_div:
        related_div.decompose()

    for p in content_div.find_all("p"):
        if "پرشین خودرو" in p.get_text():
            p.decompose()
            break

    full_text = content_div.get_text(separator="\n", strip=True)

    # استخراج محورهای مسدود
    blocked = "اطلاعات محورهای مسدود یافت نشد."
    restricted = "اطلاعات ممنوعیت تردد یافت نشد."

    if "محورهای مسدود" in full_text:
        start = full_text.find("محورهای مسدود")
        end = full_text.find("ممنوعیت تردد", start)
        if end == -1:
            end = len(full_text)
        blocked = full_text[start:end].strip()

    if "ممنوعیت تردد" in full_text:
        start = full_text.find("ممنوعیت تردد")
        restricted = full_text[start:].strip()

    # ساخت پیام نهایی برای دیسکورد (حداکثر ۲۰۰۰ کاراکتر مجاز است، ما خلاصه می‌کنیم)
    message = (
        "🚧 **محورهای مسدود:**\n"
        f"{blocked}\n\n"
        "⛔ **ممنوعیت تردد:**\n"
        f"{restricted}"
    )

    # اگر پیام خیلی طولانی باشد، می‌توان آن را برش داد یا به صورت فایل فرستاد
    if len(message) > 2000:
        message = message[:1900] + "\n... (متن کامل در لاگ اکشن موجود است)"

    # چاپ در لاگ
    print(message)
    # ارسال به دیسکورد
    send_discord_message(message)

if __name__ == "__main__":
    get_traffic_info()
