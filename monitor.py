import os, hashlib, smtplib
from email.mime.text import MIMEText
from playwright.sync_api import sync_playwright

URL = "https://appointment.bmeia.gv.at/?Office=Kairo"
TO_EMAIL = os.environ["TO_EMAIL"]
FROM_EMAIL = os.environ["FROM_EMAIL"]
APP_PASSWORD = os.environ["GMAIL_APP_PASSWORD"]
STATE_FILE = "last_signature.txt"

UNAVAILABLE = [
    "no appointments available", "no appointment available",
    "no free appointments", "keine termine verfügbar",
    "keine termine verfugbar", "keine freien termine"
]
POSITIVE = [
    "available", "select appointment", "choose appointment",
    "book appointment", "termin auswählen", "termin auswahlen",
    "freie termine", "verfügbare termine", "verfugbare termine"
]

def send_alert():
    msg = MIMEText(
        "تم اكتشاف مؤشر على وجود موعد متاح في نظام مواعيد النمسا بالقاهرة.\n\n"
        f"الرابط: {URL}\n\n"
        "افتح الموقع وتحقق يدويًا من الموعد قبل الحجز.",
        "plain", "utf-8")
    msg["Subject"] = "موعد محتمل متاح - سفارة النمسا بالقاهرة"
    msg["From"] = FROM_EMAIL
    msg["To"] = TO_EMAIL
    with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=30) as smtp:
        smtp.login(FROM_EMAIL, APP_PASSWORD)
        smtp.send_message(msg)

def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(URL, wait_until="domcontentloaded", timeout=60000)
        page.wait_for_timeout(5000)
        body = page.locator("body").inner_text(timeout=30000)
        low = body.lower()

        if any(x in low for x in UNAVAILABLE):
            print("NO_APPOINTMENT")
            browser.close()
            return

        found = any(x in low for x in POSITIVE)
        if not found:
            for el in page.locator("button, a, input, select").all():
                try:
                    if not el.is_visible() or el.is_disabled():
                        continue
                    label = (el.inner_text() or el.get_attribute("value") or "").strip().lower()
                    if any(k in label for k in ["appointment","termin","available","book","select"]):
                        found = True
                        break
                except Exception:
                    pass

        if found:
            sig = hashlib.sha256(body.encode("utf-8")).hexdigest()
            old = open(STATE_FILE, encoding="utf-8").read().strip() if os.path.exists(STATE_FILE) else ""
            if sig != old:
                send_alert()
                with open(STATE_FILE, "w", encoding="utf-8") as f:
                    f.write(sig)
                print("ALERT_SENT")
            else:
                print("DUPLICATE_SUPPRESSED")
        else:
            print("NO_APPOINTMENT")
        browser.close()

if __name__ == "__main__":
    main()
