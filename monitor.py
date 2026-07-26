import os
import requests
from bs4 import BeautifulSoup
import json

URL = "https://www.momtaznews.com/%D8%A2%D8%AE%D8%B1%DB%8C%D9%86-%D9%88%D8%B6%D8%B9%DB%8C%D8%AA-%D8%B1%D8%A7%D9%87%E2%80%8C%D9%87%D8%A7%DB%8C-%DA%A9%D8%B4%D9%88%D8%B1/"
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

    # حذف بخش‌های نامربوط
    related = content_div.find("div", id="crp_related")
    if related:
        related.decompose()
    for p in content_div.find_all("p"):
        if "پرشین خودرو" in p.get_text():
            p.decompose()
            break

    full_text = content_div.get_text(separator="\n", strip=True)

    # استخراج محورهای مسدود (فقط از "محورهای مسدود تا اطلاع ثانوی" به بعد)
    blocked = "اطلاعات محورهای مسدود یافت نشد."
    if "محورهای مسدود تا اطلاع ثانوی" in full_text:
        start = full_text.find("محورهای مسدود تا اطلاع ثانوی")
        end = full_text.find("ممنوعیت تردد", start)
        if end == -1:
            end = len(full_text)
        blocked = full_text[start:end].strip()
    elif "محورهای مسدود" in full_text:   # fallback
        start = full_text.find("محورهای مسدود")
        end = full_text.find("ممنوعیت تردد", start)
        if end == -1:
            end = len(full_text)
        blocked = full_text[start:end].strip()

    # استخراج ممنوعیت تردد (فقط از "ممنوعیت تردد به‌تفکیک" به بعد)
    restricted = "اطلاعات ممنوعیت تردد یافت نشد."
    if "ممنوعیت تردد به‌تفکیک" in full_text:
        start = full_text.find("ممنوعیت تردد به‌تفکیک")
        restricted = full_text[start:].strip()
    elif "ممنوعیت تردد" in full_text:   # fallback
        start = full_text.find("ممنوعیت تردد")
        restricted = full_text[start:].strip()

    # متن جدید برای ذخیره و مقایسه
    new_status = f"🚧 محورهای مسدود:\n{blocked}\n\n⛔ ممنوعیت تردد:\n{restricted}"

    # خواندن آخرین وضعیت از فایل
    old_status = ""
    if os.path.exists(STATUS_FILE):
        with open(STATUS_FILE, "r", encoding="utf-8") as f:
            old_status = f.read().strip()

    # مقایسه
    if new_status.strip() == old_status:
        print("ℹ️ تغییری در وضعیت راه‌ها ایجاد نشده. پیامی به دیسکورد ارسال نمی‌شود.")
        return

    # تغییر وجود دارد: ارسال به دیسکورد و به‌روزرسانی فایل
    print("🔄 تغییرات جدید شناسایی شد. ارسال به دیسکورد...")
    if len(new_status) > 2000:
        message_to_send = new_status[:1900] + "\n... (متن کامل در لاگ موجود است)"
    else:
        message_to_send = new_status
    send_discord_message(message_to_send)

    # ذخیره وضعیت جدید
    with open(STATUS_FILE, "w", encoding="utf-8") as f:
        f.write(new_status)
    print("✅ فایل وضعیت به‌روزرسانی شد.")

if __name__ == "__main__":
    get_traffic_info()
