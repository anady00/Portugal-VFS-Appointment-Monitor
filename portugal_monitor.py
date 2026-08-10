import os, hashlib, smtplib
from email.mime.text import MIMEText
from playwright.sync_api import sync_playwright

URL="https://visa.vfsglobal.com/egy/en/prt/application-detail"
TO_EMAIL=os.environ["TO_EMAIL"]; FROM_EMAIL=os.environ["FROM_EMAIL"]; APP_PASSWORD=os.environ["GMAIL_APP_PASSWORD"]
CHECKS=[
("Cairo","National Visa","Subordinated Work"),
("Alexandria","National Visa","Subordinated Work"),
("Cairo","Short Term Visa","Tourism"),
("Alexandria","Short Term Visa","Tourism")]

UNAVAILABLE=["no appointment slots are currently available","no appointments available","no appointment available","no free appointments"]

def mail(location,category,sub):
    m=MIMEText(f"تم اكتشاف مؤشر على وجود موعد متاح في VFS Portugal Egypt.\n\nالمركز: {location}\nالفئة: {category}\nالقسم: {sub}\n\nالرابط: {URL}\n\nتحقق يدويًا من الموعد قبل الحجز.","plain","utf-8")
    m["Subject"]=f"موعد محتمل - البرتغال - {location} - {sub}"; m["From"]=FROM_EMAIL; m["To"]=TO_EMAIL
    with smtplib.SMTP_SSL("smtp.gmail.com",465,timeout=30) as s:
        s.login(FROM_EMAIL,APP_PASSWORD); s.send_message(m)

def key(a,b,c): return hashlib.sha256(f"{a}|{b}|{c}".encode()).hexdigest()[:20]
def state_load():
    return set(open("alert_state.txt",encoding="utf8").read().split()) if os.path.exists("alert_state.txt") else set()
def state_save(s):
    open("alert_state.txt","w",encoding="utf8").write("\n".join(sorted(s)))

def select_value(page,value):
    x=page.get_by_text(value,exact=True)
    if x.count():
        try:
            if x.first.is_visible(): x.first.click(); page.wait_for_timeout(1200); return True
        except: pass
    for sel in page.locator("select").all():
        try:
            if sel.is_visible():
                try: sel.select_option(label=value); page.wait_for_timeout(1200); return True
                except: pass
        except: pass
    for combo in page.locator('[role="combobox"]').all():
        try:
            if combo.is_visible():
                combo.click(); page.wait_for_timeout(300)
                x=page.get_by_text(value,exact=True)
                if x.count() and x.first.is_visible(): x.first.click(); page.wait_for_timeout(1200); return True
        except: pass
    return False

def check(page,location,category,sub):
    page.goto(URL,wait_until="domcontentloaded",timeout=60000); page.wait_for_timeout(4000)
    center=f"Portugal Visa Application Center-{location}"
    ok=select_value(page,center) or select_value(page,location)
    ok=select_value(page,category) and ok
    ok=select_value(page,sub) and ok
    if not ok:
        print(f"SELECTION_FAILED | {location} | {category} | {sub}"); return False
    page.wait_for_timeout(2500)
    low=page.locator("body").inner_text(timeout=30000).lower()
    if any(x in low for x in UNAVAILABLE):
        print(f"NO_APPOINTMENT | {location} | {category} | {sub}"); return False
    positive=["available","select appointment","choose appointment","book appointment","free appointment","appointment date"]
    found=any(x in low for x in positive)
    print(("POTENTIAL_APPOINTMENT" if found else "NO_APPOINTMENT")+f" | {location} | {category} | {sub}")
    return found

def main():
    st=state_load()
    with sync_playwright() as p:
        b=p.chromium.launch(headless=True); page=b.new_page(viewport={"width":1440,"height":1000})
        for loc,cat,sub in CHECKS:
            try:
                found=check(page,loc,cat,sub); k=key(loc,cat,sub)
                if found and k not in st:
                    mail(loc,cat,sub); st.add(k); print("ALERT_SENT")
                elif found: print("DUPLICATE_SUPPRESSED")
                else: st.discard(k)
            except Exception as e: print(f"ERROR | {loc} | {cat} | {sub} | {type(e).__name__}: {e}")
        b.close()
    state_save(st)
if __name__=="__main__": main()
