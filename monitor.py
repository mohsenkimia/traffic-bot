import requests
from bs4 import BeautifulSoup
import re

URL = "https://www.momtaznews.com/%D8%A2%D8%AE%D8%B1%DB%8C%D9%86-%D9%88%D8%B6%D8%B9%DB%8C%D8%AA-%D8%B1%D8%A7%D9%87%E2%80%8C%D9%87%D8%A7%DB%8C-%DA%A9%D8%B4%D9%88%D8%B1/"

def get_traffic_info():
    headers = {
        "User-Agent": "Mozilla/5.0 (compatible; TrafficBot/1.0)"
    }
    resp = requests.get(URL, headers=headers, timeout=30)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")

    # محتوای اصلی خبر داخل div با این کلاس‌ها قرار دارد
    content_div = soup.find("div", class_="post-single-content")
    if not content_div:
        print("⚠️ نتوانستیم محتوای خبر را پیدا کنیم.")
        return

    # تمام متن داخل آن div را بگیریم
    full_text = content_div.get_text(separator="\n", strip=True)

    # جدا کردن بخش "محورهای مسدود" و "ممنوعیت تردد"
    # با استفاده از عبارت‌های کلیدی
    blocked_section = ""
    restricted_section = ""

    if "محورهای مسدود" in full_text:
        # از "محورهای مسدود" تا "ممنوعیت تردد" یا انتها
        start = full_text.find("محورهای مسدود")
        end = full_text.find("ممنوعیت تردد", start)
        if end == -1:
            end = len(full_text)
        blocked_section = full_text[start:end].strip()
    else:
        blocked_section = "اطلاعات محورهای مسدود یافت نشد."

    if "ممنوعیت تردد" in full_text:
        start = full_text.find("ممنوعیت تردد")
        # معمولاً تا انتهای div
        restricted_section = full_text[start:].strip()
    else:
        restricted_section = "اطلاعات ممنوعیت تردد یافت نشد."

    # نمایش خروجی (می‌توانید فرمت دلخواه را تغییر دهید)
    print("🚧 محورهای مسدود:\n" + blocked_section)
    print("\n" + "="*50)
    print("⛔ ممنوعیت تردد:\n" + restricted_section)

if __name__ == "__main__":
    get_traffic_info()
