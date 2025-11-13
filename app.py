from flask import Flask, request, jsonify, render_template_string, send_file
import os, random, string, io
from captcha.image import ImageCaptcha

import json, uuid
CLIENTS_FILE = "client_configs.json"

def load_clients():
    if os.path.exists(CLIENTS_FILE):
        with open(CLIENTS_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_clients(data):# app.py
import os
import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
import re
import uuid
import io
import random
import string
from email.message import EmailMessage
from email.mime.text import MIMEText
from datetime import datetime
from flask import (
    Flask, request, jsonify, render_template_string,
    session, redirect, url_for, send_file
)
from PIL import Image, ImageDraw, ImageFont

api_key = os.getenv("BREVO_API_KEY")
import os
print("BREVO_API_KEY:", os.getenv("BREVO_API_KEY"))



# ---------------- CONFIG ----------------
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey123")

# Environment-configurable values
FREE_LIMIT = int(os.environ.get("FREE_LIMIT", "100"))
DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "sagar@123")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", os.environ.get("EMAIL_USER", "sagarms121415@gmail.com"))

        # app password or SMTP password

# In-memory stores (persisting to DB is recommended later)
api_keys = {}       # free API keys: {key: {"email", "count", "emailed", "last_reset"}}
pro_requests = []   # list of pro requests for logging / admin
captcha_store = {}  # { "value": "ABC12", "time": iso }

# ---------------- UTILITIES ----------------
EMAIL_REGEX = re.compile(r"[^@]+@[^@]+\.[^@]+")

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


from email.message import EmailMessage
import os



def send_email_brevo(to_email, subject, html_content):
    """
    Sends an HTML email using Brevo (Sendinblue) Transactional API.
    """
    configuration = sib_api_v3_sdk.Configuration()
    configuration.api_key['api-key'] = os.getenv("BREVO_API_KEY")

    api_instance = sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

    sender = {"name": "QuickCaptcha Team", "email": "sagarms121415@gmail.com"}  # can replace with your verified sender

    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=[{"email": to_email}],
        html_content=html_content,
        subject=subject,
        sender=sender
    )

    try:
        api_response = api_instance.send_transac_email(send_smtp_email)
        print(f"✅ Email sent successfully to {to_email} via Brevo.")
        return True
    except ApiException as e:
        print(f"❌ Error sending email via Brevo: {e}")
        return False



def build_free_key_email(email, key):
    # HTML email content advertising Pro plans and contact
    content = f"""
    <p>Hello {email},</p>
    <p>Here is your QuickCaptcha <strong>Free API key</strong>:</p>
    <pre style="background:#f6f8fa;padding:10px;border-radius:6px;">{key}</pre>
    <p><strong>Limit:</strong> {FREE_LIMIT} requests per month.</p>

    <hr>

    <h3>Interested in QuickCaptcha Pro?</h3>
    <p>Upgrade and get higher limits, priority support, custom styling and branding removal.</p>

    <ul>
      <li><strong>Lite</strong> — ₹100 / $1.5 — minimal customization (color/background/logo)</li>
      <li><strong>Starter</strong> — ₹199 / $3 — 1,000 requests / month</li>
      <li><strong>Growth</strong> — ₹599 / $8 — 5,000 requests / month</li>
      <li><strong>Business</strong> — ₹1,499 / $18 — 20,000+ requests / month</li>
      <li><strong>Enterprise</strong> — Custom — 20,000+ / month (contact for quote)</li>
    </ul>

    <p>To upgrade, reply to this email or visit the dashboard:<br>
    <a href="{request_host_or_site()}">{request_host_or_site()}</a></p>

    <p>Contact: <a href="mailto:{ADMIN_EMAIL}">{ADMIN_EMAIL}</a></p>

    <p>— QuickCaptcha Team</p>
    """
    return content

def build_pro_request_user_email(email, plan, price, description):
    content = f"""
    <p>Hello {email},</p>
    <p>Thanks for requesting QuickCaptcha <strong>Pro</strong>.</p>
    <p><strong>Plan:</strong> {plan} — ₹{price}</p>
    <p><strong>Description provided:</strong><br>{(description or '—')}</p>

    <p><strong>Next steps:</strong><br>
    1) Pay 50% upfront to the payment link sent to your email (or reply to coordinate payment).<br>
    2) Once we receive 50% payment, development starts. Remaining 50% after completion.</p>

    <p>We will contact you shortly with payment details and timeline.</p>

    <p>Contact: <a href="mailto:{ADMIN_EMAIL}">{ADMIN_EMAIL}</a></p>
    <p>— QuickCaptcha Pro Team</p>
    """
    return content

def build_pro_request_admin_email(email, plan, price, description):
    content = f"""
    <p>New Pro request received:</p>
    <ul>
      <li><strong>User:</strong> {email}</li>
      <li><strong>Plan:</strong> {plan}</li>
      <li><strong>Price:</strong> ₹{price}</li>
      <li><strong>Description:</strong><br>{(description or '—')}</li>
      <li><strong>Time:</strong> {datetime.utcnow().isoformat()}</li>
    </ul>
    <p>Action: send payment link for 50% and await confirmation.</p>
    """
    return content

def request_host_or_site():
    # returns configured host for links; try environment var first
    return os.environ.get("PUBLIC_URL", "https://quickcaptcha.onrender.com")

# ---------------- CAPTCHA ----------------
def generate_captcha_text(length=5):
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))

def generate_captcha_image_bytes(text):
    # simple PIL image with text
    img = Image.new("RGB", (220, 72), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)

    try:
        # try to use a truetype if available
        font = ImageFont.truetype("DejaVuSans.ttf", 36)
    except Exception:
        font = ImageFont.load_default()

    # center text
    w, h = draw.textsize(text, font=font)
    x = (img.width - w) // 2
    y = (img.height - h) // 2
    draw.text((x, y), text, fill=(20, 20, 20), font=font)

    # add some noise lines
    for _ in range(2):
        x1 = random.randint(0, img.width)
        y1 = random.randint(0, img.height)
        x2 = random.randint(0, img.width)
        y2 = random.randint(0, img.height)
        draw.line((x1, y1, x2, y2), fill=(200, 200, 200))

    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf

@app.route("/captcha")
def captcha():
    # create and store captcha value and time
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
    # expiry 5 minutes
    try:
        created = datetime.fromisoformat(captcha_store.get("time"))
    except Exception:
        created = datetime.utcnow()
    if (datetime.utcnow() - created).total_seconds() > 60 * 5:
        return jsonify({"success": False, "message": "CAPTCHA expired. Refresh."})
    success = user_input == correct
    if success:
        # clear captcha after success
        captcha_store.pop("value", None)
        captcha_store.pop("time", None)
    return jsonify({"success": success, "message": "Verified" if success else "Incorrect captcha"})

# ---------------- FREE KEY ----------------
import re
EMAIL_REGEX = re.compile(r"^[\w\.-]+@[\w\.-]+\.\w+$")

@app.route("/generate-free-key", methods=["POST"])
def generate_free_key():
    reset_monthly_limits()
    data = request.get_json() or {}
    email = (data.get("email") or "").strip().lower()
    if not email or not EMAIL_REGEX.match(email):
        return jsonify({"error": "Valid email required"}), 400

    # Reuse a key for same email (preserve monthly reset logic)
    for k, v in api_keys.items():
        if v.get("email") == email:
            return jsonify({"api_key": k, "free_limit": FREE_LIMIT})

    # Generate new API key
    key = str(uuid.uuid4())
    api_keys[key] = {
        "email": email,
        "count": 0,
        "emailed": False,
        "last_reset": datetime.utcnow().isoformat()
    }

    # Send email to user with plan advertising
    user_html = f"""
    <h3>🎉 Your QuickCaptcha Free API Key</h3>
    <p>Email: {email}</p>
    <p>API Key: <strong>{key}</strong></p>
    <p>Limit: {FREE_LIMIT} requests per month</p>
    <p>Try our Pro Plans for higher limits, customization, and priority support!</p>
    <ul>
        <li>₹100 — Limited customization</li>
        <li>₹199 — Starter</li>
        <li>₹599 — Growth</li>
        <li>₹1499 — Business</li>
    </ul>
    <p>Enjoy testing QuickCaptcha!</p>
    """
    sent_user = send_email_brevo(email, "🎉 Your QuickCaptcha Free API Key", user_html)

    # Notify admin
    admin_html = f"""
    <p>User <strong>{email}</strong> generated a free API key: <code>{key}</code></p>
    <p>Time: {datetime.utcnow().isoformat()}</p>
    """
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

    # log it
    pro_requests.append({
        "email": email,
        "plan": plan,
        "price": price,
        "description": description,
        "time": datetime.utcnow().isoformat()
    })

    # send user email with next steps (50% payment)
    user_html = f"""
    <h3>💼 QuickCaptcha Pro Request: {plan}</h3>
    <p>Hello {email},</p>
    <p>Thank you for choosing the <strong>{plan}</strong> plan (₹{price}).</p>
    <p>Your description / requirements:</p>
    <blockquote>{description}</blockquote>
    <p>Please proceed with 50% advance payment to confirm your plan. Once received, we will start the service and notify you.</p>
    <p>Pro Plans Overview:</p>
    <ul>
        <li>₹100 — Limited customization (message & logo)</li>
        <li>₹199 — Starter</li>
        <li>₹599 — Growth</li>
        <li>₹1499 — Business</li>
    </ul>
    <p>Contact us for support: <a href="mailto:{ADMIN_EMAIL}">{ADMIN_EMAIL}</a></p>
    """
    send_email_brevo(email, f"💼 QuickCaptcha Pro Request: {plan}", user_html)

    # notify admin
    admin_html = f"""
    <h3>📩 New Pro API Request</h3>
    <p>User: <strong>{email}</strong></p>
    <p>Plan: {plan} — ₹{price}</p>
    <p>Description:</p>
    <blockquote>{description}</blockquote>
    <p>Time: {datetime.utcnow().isoformat()}</p>
    """
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

    # notify admin upon payment
    admin_html = f"""
    <h3>✅ 50% Payment Received</h3>
    <p>User: {email}</p>
    <p>Plan: {plan}</p>
    <p>Amount Paid: ₹{paid_amount}</p>
    <p>Note: {note}</p>
    <p>Time: {datetime.utcnow().isoformat()}</p>
    """
    send_email_brevo(ADMIN_EMAIL, f"✅ Payment Received — {email}", admin_html)

    # send receipt/confirmation to user
    user_html = f"""
    <h3>💳 Payment Confirmation — QuickCaptcha Pro</h3>
    <p>Hello {email},</p>
    <p>We have received your payment of ₹{paid_amount} for the <strong>{plan}</strong> plan.</p>
    <p>We will start your service and notify you once it is completed.</p>
    <p>If you have any questions, contact us at <a href="mailto:{ADMIN_EMAIL}">{ADMIN_EMAIL}</a></p>
    """
    send_email_brevo(email, "💳 Payment Received — QuickCaptcha Pro", user_html)

    return jsonify({"status": "ok"})


# ---------------- DASHBOARD ----------------
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    reset_monthly_limits()
    if request.method == "POST":
        pwd = request.form.get("password")
        if pwd == DASHBOARD_PASSWORD:
            session["dashboard_access"] = True
            return redirect(url_for("dashboard"))
        return "❌ Wrong password", 403

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

# ---------------- TEMPLATES ----------------
HTML_TEMPLATE = """
<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>QuickCaptcha</title>
  <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
  <style>
    :root{--bg:#f4f7fb;--card:#fff;--muted:#6b7280;--accent:#2563eb;--accent-dark:#1e40af;--success:#16a34a;--danger:#dc2626}
    body{font-family:Inter,system-ui,Arial;background:var(--bg);margin:0;color:#0f172a}
    .container{max-width:1100px;margin:36px auto;padding:20px}
    .header{display:flex;justify-content:space-between;align-items:center;margin-bottom:18px}
    .card{background:var(--card);border-radius:12px;padding:20px;box-shadow:0 8px 30px rgba(2,6,23,0.06);margin-bottom:20px}
    .grid{display:grid;grid-template-columns:1fr 420px;gap:20px}
    .captcha-img{width:220px;height:72px;border-radius:8px;border:1px solid #e6e7ee;display:block;margin-bottom:10px}
    .input, textarea{width:100%;padding:10px;border-radius:8px;border:1px solid #e6e7ee;margin-top:8px}
    .btn{background:var(--accent);color:#fff;padding:10px 12px;border-radius:8px;border:0;cursor:pointer;font-weight:600}
    .btn-ghost{background:transparent;border:1px solid #e6e7ee;color:#0f172a;padding:10px 12px;border-radius:8px}
    .small{font-size:13px;color:var(--muted)}
    table{width:100%;border-collapse:collapse;margin-top:12px}
    th,td{padding:10px;border:1px solid #eef2f6;text-align:left}
    thead th{background:linear-gradient(90deg,#eef2ff,#f8fbff)}
    .modal{display:none;position:fixed;inset:0;background:rgba(10,12,20,0.6);align-items:center;justify-content:center}
    .modal .box{background:#fff;padding:18px;border-radius:10px;max-width:420px;width:90%}
    .msg{margin-top:10px;font-weight:600}
    .msg.success{color:var(--success)}
    .msg.error{color:var(--danger)}
    @media (max-width:980px){ .grid{grid-template-columns:1fr} }
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <div>
        <h1 style="margin:0">QuickCaptcha</h1>
        <div class="small">Secure · Simple · Reliable</div>
      </div>
      <div class="small">Free limit: <strong>{{ free_limit }}</strong>/month</div>
    </div>

    <div class="grid">
      <div>
        <div class="card">
          <h2 style="margin-top:0">Free Plan — Demo</h2>
          <p class="small">Test the captcha & generate a free API key.</p>

          <img id="captchaImage" src="/captcha" class="captcha-img" alt="captcha">
          <div style="display:flex;gap:10px;align-items:center">
            <input id="captchaInput" class="input" placeholder="Enter captcha">
            <button id="verifyBtn" class="btn">Verify</button>
            <button id="refreshBtn" class="btn-ghost">🔄 Refresh</button>
          </div>
          <div id="verifyMessage" class="msg"></div>

          <hr style="margin:16px 0">
          <button id="openFreeModal" class="btn">Generate Free API Key</button>
        </div>

        <div class="card">
          <h2 style="margin-top:0">Pro Plans</h2>
          <p class="small">Choose one plan, describe requirements and request a quote / payment link.</p>

          <table>
            <thead><tr><th></th><th>Plan</th><th>Limit / Notes</th><th>Price</th></tr></thead>
            <tbody>
              <tr>
                <td><input type="radio" name="plan" value="Lite" data-price="100"></td>
                <td>Lite</td><td>Limited customization (color/background/logo)</td><td>₹100</td>
              </tr>
              <tr>
                <td><input type="radio" name="plan" value="Starter" data-price="199"></td>
                <td>Starter</td><td>1,000 requests / month</td><td>₹199</td>
              </tr>
              <tr>
                <td><input type="radio" name="plan" value="Growth" data-price="599"></td>
                <td>Growth</td><td>5,000 requests / month</td><td>₹599</td>
              </tr>
              <tr>
                <td><input type="radio" name="plan" value="Business" data-price="1499"></td>
                <td>Business</td><td>20,000+ requests / month</td><td>₹1499</td>
              </tr>
            </tbody>
          </table>

          <input id="proEmail" class="input" placeholder="Your business email">
          <textarea id="proDescription" class="input" rows="4" placeholder="Describe requirements, integrations, preferred timeline..."></textarea>
          <div style="display:flex;gap:10px;align-items:center;margin-top:10px">
            <button id="requestProBtn" class="btn">Request & Pay 50%</button>
            <div id="proStatus" class="small"></div>
          </div>
        </div>
      </div>

      <!-- right column -->
      <div>
        <div class="card">
          <h3 style="margin-top:0">Account / Admin</h3>
          <p class="small">Generate free keys, copy to clipboard, and get emailed details. Admin gets notified on pro requests & payments.</p>
          <div style="margin-top:8px">
            <button id="openDashboard" class="btn btn-ghost" onclick="window.location='/dashboard'">Open Dashboard</button>
          </div>
        </div>
      </div>
    </div>
  </div>

  <!-- Free key modal -->
  <div id="freeModal" class="modal" aria-hidden="true">
    <div class="box">
      <h3 style="margin-top:0">Get your free API key</h3>
      <p class="small">Enter your email and we will send your key right away.</p>
      <input id="freeEmail" class="input" placeholder="your@email.com">
      <div style="display:flex;gap:8px;margin-top:8px">
        <button id="generateKeyBtn" class="btn">Generate Key</button>
        <button id="closeFreeModal" class="btn btn-ghost">Close</button>
      </div>
      <p id="apiKeyDisplay" style="font-weight:600;word-break:break-all;margin-top:10px"></p>
      <button id="copyApiBtn" style="display:none;margin-top:8px;padding:8px 12px;border-radius:8px;background:#0f172a;color:#fff;border:0;cursor:pointer">📋 Copy API Key</button>
    </div>
  </div>

<script>
/* helper */
function isValidEmail(e){ return /^[^@]+@[^@]+\.[^@]+$/.test(e); }

/* Captcha verify & refresh */
document.getElementById('refreshBtn').addEventListener('click', () => {
  document.getElementById('captchaImage').src = '/captcha?'+Date.now();
});
document.getElementById('verifyBtn').addEventListener('click', async () => {
  const input = document.getElementById('captchaInput').value.trim();
  const msg = document.getElementById('verifyMessage');
  msg.className = 'msg';
  msg.textContent = '';
  if(!input){ msg.className='msg error'; msg.textContent='Enter captcha'; return; }
  try{
    const res = await fetch('/verify-captcha', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({user_input: input})});
    const data = await res.json();
    if(data.success){ msg.className='msg success'; msg.textContent='✅ Captcha verified'; }
    else { msg.className='msg error'; msg.textContent='❌ '+(data.message || 'Incorrect'); document.getElementById('captchaImage').src='/captcha?'+Date.now(); }
  }catch(err){ msg.className='msg error'; msg.textContent='⚠️ Error'; }
});

/* Free key modal open/close/generate/copy */
const freeModal = document.getElementById('freeModal');
document.getElementById('openFreeModal').addEventListener('click', ()=>{ freeModal.style.display='flex'; document.getElementById('apiKeyDisplay').textContent=''; document.getElementById('copyApiBtn').style.display='none'; });
document.getElementById('closeFreeModal').addEventListener('click', ()=>{ freeModal.style.display='none'; });
document.getElementById('generateKeyBtn').addEventListener('click', async ()=>{
  const email = document.getElementById('freeEmail').value.trim();
  const display = document.getElementById('apiKeyDisplay');
  const copyBtn = document.getElementById('copyApiBtn');
  display.textContent = ''; copyBtn.style.display='none';
  if(!isValidEmail(email)){ display.textContent = 'Enter a valid email'; return; }
  try{
    const res = await fetch('/generate-free-key', {method:'POST', headers:{'Content-Type':'application/json'}, body: JSON.stringify({email})});
    const data = await res.json();
    if(data.api_key){ display.innerHTML = '✅ ' + data.api_key; copyBtn.style.display='inline-block'; }
    else { display.textContent = '❌ ' + (data.error || 'Error generating'); }
  }catch(err){ display.textContent = '❌ Error'; }
});
document.getElementById('copyApiBtn').addEventListener('click', async ()=>{
  const txt = document.getElementById('apiKeyDisplay').textContent.replace('✅ ','').trim();
  if(!txt) return alert('No API key to copy'); try{ await navigator.clipboard.writeText(txt); alert('API Key copied'); }catch(e){ alert('Clipboard denied'); }
});

/* Pro request */
document.getElementById('requestProBtn').addEventListener('click', async ()=>{
  const email = document.getElementById('proEmail').value.trim();
  const desc = document.getElementById('proDescription').value.trim();
  const selected = document.querySelector('input[name="plan"]:checked');
  const status = document.getElementById('proStatus');
  status.textContent = ''; status.style.color = '';
  if(!email || !isValidEmail(email)){ status.textContent='⚠️ Enter a valid email'; status.style.color='var(--danger)'; return; }
  if(!selected){ status.textContent='⚠️ Select a plan'; status.style.color='var(--danger)'; return; }
  const plan = selected.value;
  const price = parseFloat(selected.dataset.price || selected.getAttribute('data-price') || 0) || selected.value==='Lite' ? 100 : parseFloat(selected.getAttribute('data-price') || 0);
  try{
    const res = await fetch('/request-pro-payment', {
      method:'POST',
      headers:{'Content-Type':'application/json'},
      body: JSON.stringify({ email, plan, price: selected.dataset.price || selected.getAttribute('data-price') || 0, description: desc })
    });
    const data = await res.json();
    if(data.status === 'ok'){ status.textContent = '✅ Request sent. Check your email for payment details.'; status.style.color='var(--success)'; }
    else { status.textContent = '❌ '+(data.error||'Request failed'); status.style.color='var(--danger)'; }
  }catch(err){ status.textContent = '❌ Error sending request'; status.style.color='var(--danger)'; }
});

/* close modal on outside click */
window.addEventListener('click', (e)=>{ if(e.target === freeModal) freeModal.style.display='none'; });

</script>
</body>
</html>
"""

DASHBOARD_HTML = """
<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>QuickCaptcha Dashboard</title>
  <style>
    body{font-family:Inter,system-ui;background:#f6f7fb;color:#0f172a;padding:24px}
    .box{max-width:1000px;margin:auto;background:#fff;padding:20px;border-radius:10px;box-shadow:0 8px 30px rgba(2,6,23,0.06)}
    table{width:100%;border-collapse:collapse}
    th,td{border:1px solid #eef2f6;padding:10px;text-align:left}
    thead th{background:#f1f8ff}
  </style>
</head>
<body>
  <div class="box">
    <h2>QuickCaptcha Dashboard</h2>
    <p>Free Limit: <strong>{{ free_limit }}</strong></p>
    <h3>API Keys</h3>
    <table>
      <thead><tr><th>Email</th><th>Key</th><th>Used</th><th>Last reset</th></tr></thead>
      <tbody>
      {% for k, v in api_keys.items() %}
        <tr>
          <td>{{ v.email }}</td>
          <td style="word-break:break-all">{{ k }}</td>
          <td>{{ v.count }}</td>
          <td>{{ v.last_reset }}</td>
        </tr>
      {% endfor %}
      </tbody>
    </table>

    <h3 style="margin-top:18px">Pro Requests</h3>
    <table>
      <thead><tr><th>User</th><th>Plan</th><th>Price</th><th>Desc</th><th>Time</th></tr></thead>
      <tbody>
      {% for r in pro_requests %}
        <tr>
          <td>{{ r.email }}</td>
          <td>{{ r.plan }}</td>
          <td>{{ r.price }}</td>
          <td style="max-width:300px;word-break:break-word">{{ r.description }}</td>
          <td>{{ r.time }}</td>
        </tr>
      {% endfor %}
      </tbody>
    </table>

    <form method="GET" action="/logout" style="margin-top:16px">
      <button type="submit">Logout</button>
    </form>
  </div>
</body>
</html>
"""

# ---------------- RUN ----------------
@app.route("/")
def home():
    return render_template_string(HTML_TEMPLATE, free_limit=FREE_LIMIT)

if __name__ == "__main__":
    # debug True for local development; set to False in production
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)), debug=True)
    with open(CLIENTS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

clients = load_clients()


app = Flask(__name__)

CAPTCHA_STORE = {}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>QuickCaptcha</title>
<style>
    body {
        margin: 0;
        font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
        background: linear-gradient(135deg, #dfe9f3 0%, #ffffff 100%);
        height: 100vh;
        display: flex;
        justify-content: center;
        align-items: center;
    }
    .captcha-box {
        background: #fff;
        border-radius: 12px;
        box-shadow: 0 6px 18px rgba(0, 0, 0, 0.1);
        padding: 35px 30px;
        text-align: center;
        width: 350px;
    }
    h1 {
        font-size: 1.7rem;
        color: #2c3e50;
        margin-bottom: 25px;
    }
    img {
        border: 1px solid #ddd;
        border-radius: 8px;
        margin-bottom: 15px;
        width: 100%;
        max-width: 260px;
        height: auto;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
    }
    input[type="text"] {
        width: 100%;
        padding: 10px;
        font-size: 1rem;
        border: 1px solid #ccc;
        border-radius: 6px;
        margin-bottom: 15px;
        transition: all 0.2s ease-in-out;
    }
    input[type="text"]:focus {
        border-color: #3498db;
        box-shadow: 0 0 5px rgba(52, 152, 219, 0.4);
        outline: none;
    }
    button {
        background-color: #3498db;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 10px 0;
        width: 100%;
        font-size: 1rem;
        font-weight: 500;
        cursor: pointer;
        transition: 0.2s ease-in-out;
    }
    button:hover {
        background-color: #2980b9;
    }
    .refresh {
        color: #3498db;
        font-size: 0.9rem;
        text-decoration: none;
        display: block;
        margin-top: 10px;
    }
    .refresh:hover {
        color: #21618c;
    }
    .message {
        margin-top: 15px;
        font-weight: 600;
        color: {{ color | default('#2c3e50') }};
    }
</style>
</head>
<body>
<div class="captcha-box">
    <h1>QuickCaptcha</h1>
    <form method="POST" action="/verify">
        <img src="/captcha" alt="CAPTCHA" id="captcha-image">
        <a href="#" class="refresh" onclick="refreshCaptcha(event)">🔄 Refresh CAPTCHA</a>
        <input type="text" name="captcha" placeholder="Enter CAPTCHA" required>
        <button type="submit">Verify</button>
    </form>
    {% if message %}
    <p class="message" style="color: {{ color }}">{{ message }}</p>
    {% endif %}
</div>

<script>
function refreshCaptcha(e) {
    e.preventDefault();
    document.getElementById("captcha-image").src = "/captcha?" + new Date().getTime();
}
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/captcha")
def captcha():
    text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    image = ImageCaptcha()
    data = io.BytesIO()
    image.write(text, data)
    data.seek(0)
    CAPTCHA_STORE['current'] = text
    return send_file(data, mimetype='image/png')

@app.route("/verify", methods=["POST"])
def verify():
    user_input = request.form.get("captcha", "").strip().upper()
    correct = CAPTCHA_STORE.get('current', "")

    if user_input == correct:
        message = "✅ CAPTCHA Verified Successfully!"
        color = "#2ecc71"
    else:
        message = "❌ Incorrect CAPTCHA. Try Again!"
        color = "#e74c3c"

    return render_template_string(HTML_TEMPLATE, message=message, color=color)
@app.route("/register_client", methods=["POST"])
def register_client():
    data = request.get_json()
    client_name = data.get("client_name", "UnnamedClient")

    clients = load_clients()
    client_id = str(uuid.uuid4())
    clients[client_id] = {
        "name": client_name,
        "logo": "default_logo.png",
        "theme": "light",
        "custom": {}
    }
    save_clients(clients)

    return jsonify({"client_id": client_id, "message": "Client registered successfully"})

@app.route("/client/<client_id>")
def client_page(client_id):
    clients = load_clients()
    client = clients.get(client_id)

    if not client:
        return "Invalid client ID", 404

    logo = client.get("logo", "default_logo.png")
    theme = client.get("theme", "light")

    bg_color = "#111" if theme == "dark" else "#ffffff"
    text_color = "#fff" if theme == "dark" else "#000"

    html = f"""
    <html>
    <head><title>{client['name']} - QuickCaptcha</title></head>
    <body style="background:{bg_color}; color:{text_color}; text-align:center;">
        <img src="{logo}" alt="Logo" style="width:100px;margin-top:30px;"><br>
        <h2>{client['name']} - CAPTCHA Demo</h2>
        <iframe src="/captcha" style="border:none;width:300px;height:150px;"></iframe>
    </body>
    </html>
    """
    return html



if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
