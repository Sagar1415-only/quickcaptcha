import os
import uuid
import re
import io
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for, send_file
from PIL import Image, ImageDraw, ImageFont
import random
import string

# ---------------- CONFIG ----------------
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey")

FREE_LIMIT = 50
DASHBOARD_PASSWORD = "admin123"
ADMIN_EMAIL = "sagarms121415@gmail.com"
api_keys = {}  # Store API keys
captcha_store = {}

# ---------------- UTILITIES ----------------
def reset_monthly_limits():
    now = datetime.now()
    for key, val in api_keys.items():
        try:
            last_reset = datetime.fromisoformat(val.get("last_reset", now.isoformat()))
        except:
            last_reset = now
        if (now.year, now.month) != (last_reset.year, last_reset.month):
            val["count"] = 0
            val["last_reset"] = now.isoformat()
            print(f"[RESET] {key} reset for new month.")


def send_email(to, subject, message):
    """Simulate email sending (print to logs)"""
    print("\n============================")
    print(f"📧 TO: {to}")
    print(f"SUBJECT: {subject}")
    print(f"MESSAGE:\n{message}")
    print("============================\n")


def generate_captcha_text(length=5):
    return "".join(random.choices(string.ascii_uppercase + string.digits, k=length))


def generate_captcha_image(text):
    img = Image.new("RGB", (160, 60), color=(255, 255, 255))
    d = ImageDraw.Draw(img)
    font = ImageFont.load_default()
    d.text((30, 20), text, fill=(0, 0, 0), font=font)
    return img


# ---------------- ROUTES ----------------
@app.route("/captcha")
def captcha():
    text = generate_captcha_text()
    captcha_store["current"] = text
    img = generate_captcha_image(text)
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return send_file(buf, mimetype="image/png")


@app.route("/verify-captcha", methods=["POST"])
def verify_captcha():
    data = request.get_json()
    user_text = (data.get("text") or "").strip().upper()
    correct = captcha_store.get("current", "").upper()
    if user_text == correct and correct != "":
        return jsonify({"success": True})
    return jsonify({"success": False})


@app.route("/generate-free-key", methods=["POST"])
def generate_free_key():
    email = (request.json.get("email") or "").strip().lower()
    if not email:
        return jsonify({"error": "Email required"}), 400

    key = str(uuid.uuid4())
    api_keys[key] = {"email": email, "count": 0, "emailed": False, "last_reset": datetime.now().isoformat()}
    reset_monthly_limits()

    # Email message (user)
    message = f"""
🎉 Hello {email},

Here’s your *QuickCaptcha Free API Key*:

🔑 {key}

Limit: {FREE_LIMIT} requests/month.

---

💡 **Upgrade anytime!**

✅ Lite — ₹100 / $1.5 — Limited customization (color/bg only)  
✅ Starter — ₹199 / $3 — 1,000 requests/month  
✅ Growth — ₹599 / $8 — 5,000 requests/month  
✅ Business — ₹1,499 / $18 — 20,000+/month

To upgrade → reply to this email or visit https://quickcaptcha.onrender.com  
📩 Contact: {ADMIN_EMAIL}

— QuickCaptcha Team
"""

    # Send emails (to user + admin)
    send_email(email, "🎉 Your QuickCaptcha Free API Key", message)
    send_email(
        ADMIN_EMAIL,
        f"📩 New Free API Request — {email}",
        f"User {email} received free API key {key} on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
    )

    return jsonify({"api_key": key, "free_limit": FREE_LIMIT})


@app.route("/request-pro-payment", methods=["POST"])
def request_pro_payment():
    data = request.get_json()
    email = (data.get("email") or "").strip().lower()
    plan = data.get("plan")
    price = data.get("price")
    description = data.get("description", "")

    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return jsonify({"error": "Invalid email format"}), 400

    # User email content
    user_msg = f"""
Hello {email},

We’ve received your QuickCaptcha Pro plan request!

📦 Plan: {plan}  
💰 Price: ₹{price}  
📝 Description: {description}

Next Step:
Please pay 50% upfront (₹{round(price/2,2)}) to start customization.
Remaining 50% after project completion.

---

✨ Plans Overview ✨  
Lite — ₹100 / $1.5 — Limited customization (color/bg only)  
Starter — ₹199 / $3 — 1,000 requests/month  
Growth — ₹599 / $8 — 5,000 requests/month  
Business — ₹1,499 / $18 — 20,000+/month

Need more? Custom enterprise options available.

— QuickCaptcha Pro Team  
📩 {ADMIN_EMAIL}
"""

    # Admin alert
    admin_msg = f"""
New Pro Request Received:

User: {email}
Plan: {plan}
Price: ₹{price}
Description: {description}

Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
"""

    send_email(email, f"💼 QuickCaptcha Pro Plan Request — {plan}", user_msg)
    send_email(ADMIN_EMAIL, f"📩 Pro Plan Request — {plan}", admin_msg)

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
        return """
        <form method='POST' style='margin-top:100px;text-align:center;'>
            <input type='password' name='password' placeholder='Enter password'>
            <button type='submit'>Login</button>
        </form>"""

    return render_template_string(DASHBOARD_HTML, api_keys=api_keys, free_limit=FREE_LIMIT)


@app.route("/logout")
def logout():
    session.pop("dashboard_access", None)
    return redirect(url_for("dashboard"))

@app.route("/refresh-data")
def refresh_data():
    return jsonify({"api_keys": api_keys})

# ---------------- FRONTEND ----------------
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>QuickCaptcha</title>
<style>
body{font-family:Inter,system-ui;background:#f4f7fb;color:#0f172a;margin:0}
.container{max-width:1100px;margin:36px auto;padding:20px}
.card{background:#fff;border-radius:12px;padding:20px;box-shadow:0 8px 30px rgba(2,6,23,0.06);margin-bottom:20px}
.table{width:100%;border-collapse:collapse;margin-top:12px}
th,td{padding:10px;border:1px solid #e6e7ee}
.btn{padding:10px 14px;border:none;border-radius:8px;background:#2563eb;color:white;cursor:pointer}
.btn:hover{background:#1e40af}
.input,textarea{width:100%;padding:8px;border:1px solid #e6e7ee;border-radius:6px;margin-top:6px}
.captcha-img{width:160px;height:60px;border:1px solid #e6e7ee;margin:10px 0;border-radius:8px}
</style>
</head>
<body>
<div class="container">

<div class="card">
<h2>Free Plan</h2>
<p>Try QuickCaptcha free — get a unique API key instantly.</p>
<img id="captchaImage" src="/captcha" class="captcha-img" alt="Captcha">
<input id="captchaInput" class="input" placeholder="Enter Captcha">
<button id="verifyBtn" class="btn">Verify Captcha</button>
<p id="verifyMsg"></p>
<hr>
<button id="openModal" class="btn">Generate Free API Key</button>
</div>

<div class="card">
<h2>Pro Plan</h2>
<p>Select one plan and describe your requirements.</p>
<table class="table">
<tr><th></th><th>Plan</th><th>Limit</th><th>Price</th></tr>
<tr><td><input type="radio" name="plan" value="Lite" data-price="100"></td><td>Lite</td><td>Limited customization</td><td>₹100 / $1.5</td></tr>
<tr><td><input type="radio" name="plan" value="Starter" data-price="199"></td><td>Starter</td><td>1,000</td><td>₹199 / $3</td></tr>
<tr><td><input type="radio" name="plan" value="Growth" data-price="599"></td><td>Growth</td><td>5,000</td><td>₹599 / $8</td></tr>
<tr><td><input type="radio" name="plan" value="Business" data-price="1499"></td><td>Business</td><td>20,000+</td><td>₹1499 / $18</td></tr>
</table>
<input id="proEmail" class="input" placeholder="Your business email">
<textarea id="proDesc" class="input" rows="3" placeholder="Describe your requirements"></textarea>
<button id="proPayBtn" class="btn">Submit Request</button>
<p id="proStatus"></p>
</div>

<!-- Modal -->
<div id="modal" style="display:none;position:fixed;inset:0;background:rgba(0,0,0,0.6);align-items:center;justify-content:center;">
<div style="background:#fff;padding:20px;border-radius:10px;max-width:400px;width:90%">
<h3>Get Your Free API Key</h3>
<input id="emailInput" class="input" placeholder="Enter your email">
<button id="getKey" class="btn" style="margin-top:8px">Generate Key</button>
<p id="apiKeyDisplay" style="word-break:break-all"></p>
<button id="closeModal" class="btn" style="margin-top:8px;background:#999">Close</button>
</div></div>

</div>
<script>
const modal=document.getElementById('modal');
document.getElementById('openModal').onclick=()=>modal.style.display='flex';
document.getElementById('closeModal').onclick=()=>modal.style.display='none';

document.getElementById('getKey').onclick=async()=>{
 let email=document.getElementById('emailInput').value.trim();
 if(!email){alert('Enter email');return;}
 let res=await fetch('/generate-free-key',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email})});
 let data=await res.json();
 if(data.api_key){document.getElementById('apiKeyDisplay').innerHTML='Your Key:<br>'+data.api_key;}
 else{alert(data.error||'Error');}
};

document.getElementById('verifyBtn').onclick=async()=>{
 let text=document.getElementById('captchaInput').value.trim();
 let res=await fetch('/verify-captcha',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({text})});
 let data=await res.json();
 document.getElementById('verifyMsg').innerText=data.success?'✅ Correct!':'❌ Try again';
 if(data.success){document.getElementById('captchaImage').src='/captcha?'+Date.now();}
};

document.getElementById('proPayBtn').onclick=async()=>{
 let email=document.getElementById('proEmail').value.trim();
 let desc=document.getElementById('proDesc').value.trim();
 let checked=document.querySelector('input[name="plan"]:checked');
 let status=document.getElementById('proStatus');
 if(!email){status.innerText='⚠️ Enter email';return;}
 if(!checked){status.innerText='⚠️ Select a plan';return;}
 let plan=checked.value,price=checked.dataset.price;
 let res=await fetch('/request-pro-payment',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({email,plan,price,description:desc})});
 let data=await res.json();
 status.innerText=data.status==='ok'?'✅ Request received, check your email!':'❌ '+(data.error||'Error');
};
</script>
</body></html>
"""

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>Dashboard</title>
<style>
body{background:#f6f7fb;font-family:Inter,system-ui;padding:24px}
table{width:100%;border-collapse:collapse}
th,td{border:1px solid #e6e7ee;padding:8px}
th{background:#eef2ff}
</style></head>
<body>
<h2>Admin Dashboard</h2>
<table>
<tr><th>Email</th><th>Key</th><th>Usage</th><th>Last Reset</th></tr>
{% for k,v in api_keys.items() %}
<tr><td>{{v.email}}</td><td>{{k}}</td><td>{{v.count}}/{{free_limit}}</td><td>{{v.last_reset}}</td></tr>
{% endfor %}
</table>
<a href='/logout'>Logout</a>
</body></html>"""

@app.route("/")
def home():
    return render_template_string(HTML_TEMPLATE, FREE_LIMIT=FREE_LIMIT)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=10000)
