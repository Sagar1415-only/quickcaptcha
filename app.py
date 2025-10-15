from flask import Flask, request, jsonify, render_template_string, send_file, redirect, url_for, session
import os, random, string, io, uuid, smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from captcha.image import ImageCaptcha
from datetime import datetime, timedelta, timezone

# ---------------- CONFIG ----------------
app = Flask(__name__)
app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "None"
app.config["SESSION_TYPE"] = "filesystem"
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey123")

FREE_LIMIT = 100
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "sagarms121415@gmail.com")
DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "sagar@123")
EMAIL_USER = os.environ.get("EMAIL_USER")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD")  # Gmail App Password

api_keys = {}  # free API keys
pro_requests = []  # store pro requests

# ---------------- EMAIL FUNCTION ----------------
def send_email(to_email, subject, body):
    if not EMAIL_USER or not EMAIL_PASSWORD:
        print("⚠️ Email not configured")
        return False
    try:
        msg = MIMEMultipart()
        msg["From"] = EMAIL_USER
        msg["To"] = to_email
        msg["Subject"] = subject
        msg.attach(MIMEText(body, "html"))

        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(EMAIL_USER, EMAIL_PASSWORD)
            server.sendmail(EMAIL_USER, to_email, msg.as_string())
        print(f"📧 Email sent to {to_email}")
        return True
    except Exception as e:
        print("❌ Email failed:", e)
        return False

# ---------------- CAPTCHA ----------------
@app.route("/captcha")
def captcha():
    text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    session['captcha'] = text
    session['captcha_time'] = datetime.now().isoformat()
    session['captcha_attempts'] = 0
    image = ImageCaptcha()
    data = io.BytesIO()
    image.write(text, data)
    data.seek(0)
    return send_file(data, mimetype="image/png")

# ---------------- ROOT ----------------
@app.route("/")
def home():
    return render_template_string(HTML_TEMPLATE, message="")

# ---------------- VERIFY CAPTCHA ----------------
@app.route("/verify-captcha", methods=["POST"])
def verify_captcha():
    data = request.get_json() or {}
    user_input = (data.get("user_input") or "").strip().upper()
    correct = session.get("captcha", "")
    captcha_time_str = session.get("captcha_time")
    message = ""

    if not correct:
        return jsonify({"success": False, "message": "Captcha not found. Refresh to try again."})

    try:
        captcha_time = datetime.fromisoformat(captcha_time_str)
    except:
        captcha_time = datetime.now()

    if datetime.now(timezone.utc).replace(tzinfo=None) - captcha_time > timedelta(minutes=5):
        return jsonify({"success": False, "message": "Captcha expired. Refresh to try again."})

    attempts = session.get("captcha_attempts", 0) + 1
    session["captcha_attempts"] = attempts
    if attempts > 5:
        return jsonify({"success": False, "message": "Too many attempts. Please refresh captcha."})

    success = user_input == correct
    if success:
        session.pop("captcha", None)
        session.pop("captcha_time", None)
        session.pop("captcha_attempts", None)

    print(f"[CAPTCHA LOG] {datetime.now()} | IP: {request.remote_addr} | Input: {user_input} | Correct: {correct} | Success: {success}")

    return jsonify({"success": success, "message": "✅ Verified successfully!" if success else "❌ Incorrect captcha. Try again!"})

# ---------------- FREE API ----------------
@app.route("/generate-free-key", methods=["POST"])
def generate_free_key():
    email = (request.json.get("email") or "").strip().lower()
    if not email: return jsonify({"error": "Email required"}), 400

    for key, val in api_keys.items():
        if val["email"] == email:
            return jsonify({"api_key": key, "free_limit": FREE_LIMIT})

    key = str(uuid.uuid4())
    api_keys[key] = {"email": email, "count": 0, "emailed": False}

    body = f"Hello {email},<br>Your free API key:<br><b>{key}</b><br>Limit: {FREE_LIMIT} requests."
    send_email(email, "🎉 QuickCaptcha Free API Key", body)
    send_email(ADMIN_EMAIL, "🆕 New Free API Registration", f"User: {email}<br>Key: {key}<br>Time: {datetime.now()}")

    return jsonify({"api_key": key, "free_limit": FREE_LIMIT})

# ---------------- PRO REQUEST ----------------
@app.route("/request-pro-api", methods=["POST"])
def request_pro_api():
    data = request.json or {}
    email = (data.get("email") or "").strip().lower()
    limit = int(data.get("limit", 1000))
    if not email: return jsonify({"error": "Email required"}), 400

    body_user = f"Hello {email},<br>Thanks for requesting QuickCaptcha Pro API.<br>Requested limit: {limit}<br>We will contact you soon."
    body_admin = f"User {email} requested Pro API.<br>Limit: {limit}<br>Time: {datetime.now()}"

    send_email(email, "💼 QuickCaptcha Pro Request", body_user)
    send_email(ADMIN_EMAIL, "📩 New Pro API Request", body_admin)
    pro_requests.append({"email": email, "limit": limit, "time": datetime.now()})
    print(f"[ADMIN LOG] Pro API request received from {email}")
    return jsonify({"status": "ok"})

# ---------------- DASHBOARD ----------------
@app.route("/dashboard", methods=["GET","POST"])
def dashboard():
    if request.method == "POST":
        if request.form.get("password") == DASHBOARD_PASSWORD:
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

# ---------------- HTML TEMPLATE ----------------
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>QuickCaptcha</title>
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600&display=swap" rel="stylesheet">
<style>
body{font-family:'Poppins',sans-serif;background:#eef2f3;text-align:center;padding:40px;margin:0;}
h1{color:#007bff;margin-bottom:10px;}
.container{display:flex;justify-content:center;gap:40px;flex-wrap:wrap;}
.card{background:white;padding:25px;border-radius:16px;box-shadow:0 4px 20px rgba(0,0,0,0.1);width:320px;}
.captcha-verify{margin-top:15px;display:flex;justify-content:center;gap:10px;flex-wrap:wrap;}
.captcha-verify input{padding:8px;border-radius:6px;border:1px solid #ccc;width:120px;}
.captcha-verify button{padding:8px 12px;background:#007bff;color:white;border:none;border-radius:6px;cursor:pointer;}
.captcha-verify button:hover{background:#0056b3;}
#message{margin-top:10px;font-weight:600;}
button:hover{opacity:0.9;}
</style>
</head>
<body>

<h1>QuickCaptcha</h1>
<p>Secure, Simple & Reliable Captcha Verification</p>

<div class="container">
  <div class="card">
    <h2>Free Plan</h2>
    <p>For testing & small-scale apps</p>
    <img id="captcha-image" src="/captcha" alt="Captcha" style="width:240px;border:1px solid #ddd;border-radius:8px;">
    <div class="captcha-verify">
      <input type="text" id="captchaInput" placeholder="Enter Captcha">
      <button onclick="verifyCaptcha()">Verify</button>
      <button onclick="refreshCaptcha()">🔄 Refresh</button>
    </div>
    <div id="message"></div>
    <br>
    <input type="email" id="emailInput" placeholder="Enter your email" style="padding:8px;width:80%;margin-bottom:5px;">
    <button onclick="generateFreeKey()">Generate Free API Key</button>
    <p id="apiKeyDisplay"></p>
  </div>
</div>

<script>
function refreshCaptcha(){
  document.getElementById("captcha-image").src="/captcha?"+new Date().getTime();
}
async function verifyCaptcha(){
  const input=document.getElementById("captchaInput").value.trim();
  if(!input){document.getElementById("message").textContent="Enter captcha!";return;}
  const res=await fetch("/verify-captcha",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({user_input:input})});
  const data=await res.json();
  document.getElementById("message").textContent=data.message;
  if(!data.success){refreshCaptcha();}
}
async function generateFreeKey(){
  const email=document.getElementById("emailInput").value.trim();
  if(!email){document.getElementById("apiKeyDisplay").textContent="Enter email!";return;}
  const res=await fetch("/generate-free-key",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({email})});
  const data=await res.json();
  if(data.api_key){document.getElementById("apiKeyDisplay").textContent="✅ Your API Key: "+data.api_key;}
  else{document.getElementById("apiKeyDisplay").textContent="❌ "+(data.error||"Error");}
}
</script>
</body>
</html>
"""

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>Dashboard</title>
<style>
body{background:#f6f7fb;font-family:Poppins,sans-serif;text-align:center;}
table{margin:auto;border-collapse:collapse;width:90%;margin-bottom:20px;}
th,td{border:1px solid #ddd;padding:8px;}th{background:#007bff;color:#fff;}
tr:nth-child(even){background:#f2f2f2;}
h2{color:#007bff;}
</style></head><body>
<h2>QuickCaptcha Dashboard</h2>

<h3>Free API Keys</h3>
<table><tr><th>Email</th><th>API Key</th><th>Used</th><th>Remaining</th></tr>
{% for k,v in api_keys.items() %}
<tr><td>{{v['email']}}</td><td>{{k}}</td><td>{{v['count']}}</td><td>{{free_limit - v['count']}}</td></tr>
{% endfor %}
</table>

<h3>Pro API Requests</h3>
<table><tr><th>Email</th><th>Limit</th><th>Request Time</th></tr>
{% for req in pro_requests %}
<tr><td>{{req.email}}</td><td>{{req.limit}}</td><td>{{req.time}}</td></tr>
{% endfor %}
</table>

<a href="/logout">Logout</a>
</body></html>"""

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
