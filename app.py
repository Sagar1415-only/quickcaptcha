# app.py
import os
import re
import uuid
import io
import random
import string
from datetime import datetime
from flask import (
    Flask, request, jsonify, render_template_string,
    session, redirect, url_for, send_file
)
from PIL import Image, ImageDraw, ImageFont
from email.message import EmailMessage
import brevolib

# ---------------- CONFIG ----------------
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey123")

FREE_LIMIT = int(os.environ.get("FREE_LIMIT", "100"))
DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "sagar@123")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", os.environ.get("EMAIL_USER", "sagarms121415@gmail.com"))

# brevo (Gmail) config
brevo_SERVER = os.environ.get("brevo_SERVER", "brevo.gmail.com")
brevo_PORT = int(os.environ.get("brevo_PORT", "587"))
EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASS = os.environ.get("EMAIL_PASS")

# in-memory storage
api_keys = {}
pro_requests = []
captcha_store = {}

EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")

# ---------------- UTILITIES ----------------
def reset_monthly_limits():
    now = datetime.utcnow()
    for key, val in api_keys.items():
        try:
            last_reset = datetime.fromisoformat(val.get("last_reset"))
        except Exception:
            last_reset = now
        if (now.year, now.month) != (last_reset.year, last_reset.month):
            val["count"] = 0
            val["last_reset"] = now.isoformat()
            print(f"[RESET] Free API key {key} reset for new month.")

import smtplib
from email.message import EmailMessage
import ssl

def send_email_brevo(to_email, subject, html_body):
    if not EMAIL_USER or not EMAIL_PASS:
        print("⚠️ Email credentials not configured. Printing email instead.")
        print(f"To: {to_email}\nSubject: {subject}\n{html_body}")
        return False

    try:
        msg = EmailMessage()
        msg["From"] = EMAIL_USER
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.set_content(html_body, subtype="html")

        context = ssl.create_default_context()
        with smtplib.SMTP(brevo_SERVER, brevo_PORT) as server:
            server.ehlo()
            server.starttls(context=context)
            server.login(EMAIL_USER, EMAIL_PASS)
            server.send_message(msg)

        print(f"📧 Sent email to {to_email}")
        return True
    except Exception as e:
        print("❌ Email send error:", e)
        return False


def request_host_or_site():
    return os.environ.get("PUBLIC_URL", "https://quickcaptcha.onrender.com")

def build_free_key_email(email, key):
    content = f"""
    <p>Hello {email},</p>
    <p>Here is your QuickCaptcha <strong>Free API key</strong>:</p>
    <pre style="background:#f6f8fa;padding:10px;border-radius:6px;">{key}</pre>
    <p><strong>Limit:</strong> {FREE_LIMIT} requests per month.</p>
    <hr>
    <h3>Interested in QuickCaptcha Pro?</h3>
    <p>Upgrade for higher limits and customization.</p>
    <ul>
      <li>Lite — ₹100 / $1.5 — minimal customization</li>
      <li>Starter — ₹199 / $3 — 1,000 requests</li>
      <li>Growth — ₹599 / $8 — 5,000 requests</li>
      <li>Business — ₹1,499 / $18 — 20,000+ requests</li>
      <li>Enterprise — Custom</li>
    </ul>
    <p>Dashboard: <a href="{request_host_or_site()}">{request_host_or_site()}</a></p>
    <p>Contact: <a href="mailto:{ADMIN_EMAIL}">{ADMIN_EMAIL}</a></p>
    <p>— QuickCaptcha Team</p>
    """
    return content

# ---------------- CAPTCHA ----------------
def generate_captcha_text(length=5):
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))

def generate_captcha_image_bytes(text):
    img = Image.new("RGB", (220, 72), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    try:
        font = ImageFont.truetype("DejaVuSans.ttf", 36)
    except Exception:
        font = ImageFont.load_default()
    w, h = draw.textsize(text, font=font)
    draw.text(((img.width - w)//2, (img.height - h)//2), text, fill=(20,20,20), font=font)
    for _ in range(2):
        draw.line((random.randint(0,img.width), random.randint(0,img.height),
                   random.randint(0,img.width), random.randint(0,img.height)), fill=(200,200,200))
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

@app.route("/captcha")
def captcha():
    text = generate_captcha_text()
    captcha_store["value"] = text
    captcha_store["time"] = datetime.utcnow().isoformat()
    buf = generate_captcha_image_bytes(text)
    return send_file(buf, mimetype="image/png")

@app.route("/verify-captcha", methods=["POST"])
def verify_captcha():
    req = request.get_json() or {}
    user_input = (req.get("user_input") or "").strip().upper()
    correct = (captcha_store.get("value") or "").upper()
    if not correct:
        return jsonify({"success": False, "message": "No captcha generated. Refresh."})
    try:
        created = datetime.fromisoformat(captcha_store.get("time"))
    except Exception:
        created = datetime.utcnow()
    if (datetime.utcnow() - created).total_seconds() > 60*5:
        return jsonify({"success": False, "message": "CAPTCHA expired. Refresh."})
    success = user_input == correct
    if success:
        captcha_store.pop("value", None)
        captcha_store.pop("time", None)
    return jsonify({"success": success, "message": "Verified" if success else "Incorrect captcha"})

# ---------------- FREE KEY ----------------
@app.route("/generate-free-key", methods=["POST"])
def generate_free_key():
    reset_monthly_limits()
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    if not email or not EMAIL_REGEX.match(email):
        return jsonify({"error": "Valid email required"}), 400

    for k, v in api_keys.items():
        if v.get("email") == email:
            return jsonify({"api_key": k, "free_limit": FREE_LIMIT})

    key = str(uuid.uuid4())
    api_keys[key] = {
        "email": email,
        "count": 0,
        "emailed": False,
        "last_reset": datetime.utcnow().isoformat()
    }

    user_html = build_free_key_email(email, key)
    sent_user = send_email_brevo(email, "🎉 Your QuickCaptcha Free API Key", user_html)
    admin_html = f"<p>User <strong>{email}</strong> generated a free API key: <code>{key}</code></p><p>Time: {datetime.utcnow().isoformat()}</p>"
    sent_admin = send_email_brevo(ADMIN_EMAIL, f"🔔 New Free API Key for {email}", admin_html)
    api_keys[key]["emailed"] = bool(sent_user)
    return jsonify({"api_key": key, "free_limit": FREE_LIMIT})

# ---------------- PRO REQUEST & PAYMENT ----------------
@app.route("/request-pro-payment", methods=["POST"])
def request_pro_payment():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    plan = data.get("plan") or ""
    price = float(data.get("price") or 0)
    description = data.get("description") or ""
    if not email or not EMAIL_REGEX.match(email):
        return jsonify({"error": "Valid email required"}), 400
    if not plan or price <= 0:
        return jsonify({"error": "Valid plan & price required"}), 400

    pro_requests.append({"email": email,"plan": plan,"price": price,"description": description,"time": datetime.utcnow().isoformat()})

    user_html = f"""
    <h3>💼 QuickCaptcha Pro Request: {plan}</h3>
    <p>Hello {email},</p>
    <p>Thank you for choosing the <strong>{plan}</strong> plan (₹{price}).</p>
    <p>Description: {description or '—'}</p>
    <p>Please proceed with 50% advance payment. Development starts after receipt.</p>
    <p>Contact: <a href="mailto:{ADMIN_EMAIL}">{ADMIN_EMAIL}</a></p>
    """
    send_email_brevo(email, f"💼 QuickCaptcha Pro Request: {plan}", user_html)

    admin_html = f"<h3>📩 New Pro API Request</h3><p>User: {email}</p><p>Plan: {plan} — ₹{price}</p><p>Description: {description}</p><p>Time: {datetime.utcnow().isoformat()}</p>"
    send_email_brevo(ADMIN_EMAIL, f"📩 New Pro API Request — {plan}", admin_html)

    return jsonify({"status": "ok"})

@app.route("/confirm-pro-payment", methods=["POST"])
def confirm_pro_payment():
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    plan = data.get("plan") or ""
    paid_amount = float(data.get("amount") or 0.0)
    note = data.get("note") or ""
    if not email or not EMAIL_REGEX.match(email):
        return jsonify({"error": "Valid email required"}), 400

    admin_html = f"<h3>✅ 50% Payment Received</h3><p>User: {email}</p><p>Plan: {plan}</p><p>Amount Paid: ₹{paid_amount}</p><p>Note: {note}</p><p>Time: {datetime.utcnow().isoformat()}</p>"
    send_email_brevo(ADMIN_EMAIL, f"✅ Payment Received — {email}", admin_html)

    user_html = f"<h3>💳 Payment Confirmation — QuickCaptcha Pro</h3><p>Hello {email},</p><p>Received ₹{paid_amount} for <strong>{plan}</strong> plan.</p><p>Contact: <a href='mailto:{ADMIN_EMAIL}'>{ADMIN_EMAIL}</a></p>"
    send_email_brevo(email, "💳 Payment Received — QuickCaptcha Pro", user_html)

    return jsonify({"status": "ok"})

# ---------------- DASHBOARD ----------------
@app.route("/dashboard", methods=["GET","POST"])
def dashboard():
    reset_monthly_limits()
    if request.method=="POST":
        pwd = request.form.get("password")
        if pwd == DASHBOARD_PASSWORD:
            session["dashboard_access"] = True
            return redirect(url_for("dashboard"))
        return "❌ Wrong password",403
    if not session.get("dashboard_access"):
        return """<form method='POST' style='margin-top:100px;text-align:center;'>
                    <input type='password' name='password' placeholder='Enter password'>
                    <button type='submit'>Login</button>
                  </form>"""
    return render_template_string(DASHBOARD_HTML, api_keys=api_keys, free_limit=FREE_LIMIT, pro_requests=pro_requests)

@app.route("/logout")
def logout():
    session.pop("dashboard_access", None)
    return redirect(url_for("dashboard"))

@app.route("/refresh-data")
def refresh_data():
    reset_monthly_limits()
    return jsonify({"api_keys": api_keys, "pro_requests": pro_requests})

# ---------------- HOME ----------------
@app.route("/")
def home():
    return render_template_string(HTML_TEMPLATE, free_limit=FREE_LIMIT)

# ---------------- RUN ----------------
if __name__=="__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT",10000)), debug=True)
