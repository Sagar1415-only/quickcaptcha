from flask import Flask, request, jsonify, render_template_string, send_file, redirect, url_for, session
import os, random, string, io, uuid, requests
from captcha.image import ImageCaptcha
from datetime import datetime

# ---------------- CONFIG ----------------
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey123")
FREE_LIMIT = 100
ADMIN_EMAIL = "sagarms121415@gmail.com"
DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "sagar@123")
BREVO_API_KEY = os.environ.get("BREVO_API_KEY")
EMAIL_USER = os.environ.get("EMAIL_USER")

api_keys = {}       # free API keys
pro_api_keys = {}   # pro API keys
CAPTCHA_STORE = {}  # current captcha

# ---------------- EMAIL FUNCTION ----------------
def send_email(to_email, subject, body):
    if not BREVO_API_KEY or not EMAIL_USER:
        print("⚠️ Email not configured properly")
        return False
    url = "https://api.brevo.com/v3/smtp/email"
    headers = {"accept": "application/json","content-type": "application/json","api-key": BREVO_API_KEY}
    payload = {
        "sender": {"name": "QuickCaptcha", "email": EMAIL_USER},
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": f"<html><body><p>{body.replace(chr(10), '<br>')}</p></body></html>"
    }
    try:
        res = requests.post(url, json=payload, headers=headers)
        return res.status_code in [200,201,202]
    except Exception as e:
        print("❌ Email exception:", e)
        return False

# ---------------- CAPTCHA ----------------
@app.route("/captcha")
def captcha():
    text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    CAPTCHA_STORE["current"] = text
    image = ImageCaptcha()
    data = io.BytesIO()
    image.write(text, data)
    data.seek(0)
    return send_file(data, mimetype="image/png")

# ---------------- ROOT ----------------
@app.route("/")
def home():
    return render_template_string(HTML_TEMPLATE)

# ---------------- VERIFY ----------------
@app.route("/verify", methods=["POST"])
def verify():
    user_input = request.form.get("captcha", "").strip().upper()
    correct = CAPTCHA_STORE.get("current", "")
    message, color = ("✅ CAPTCHA Verified Successfully!", "#2ecc71") if user_input == correct else ("❌ Incorrect CAPTCHA. Try Again!", "#e74c3c")
    return render_template_string(HTML_TEMPLATE, message=message, color=color)

# ---------------- GENERATE FREE API KEY ----------------
@app.route("/generate-free-key", methods=["POST"])
def generate_key():
    email = request.json.get("email", "").strip().lower()
    if not email:
        return jsonify({"error": "Email required"}), 400
    for k, v in api_keys.items():
        if v["email"] == email:
            return jsonify({"api_key": k, "free_limit": FREE_LIMIT})

    key = str(uuid.uuid4())
    api_keys[key] = {"email": email, "count": 0, "emailed": False}

    if send_email(email, "Your QuickCaptcha API Key", f"Hello {email},\n\nYour free API key is:\n\n{key}\n\nLimit: {FREE_LIMIT} requests.\n\nThank you!"):
        api_keys[key]["emailed"] = True

    send_email(ADMIN_EMAIL, "🔔 New QuickCaptcha API Registration", f"New API key generated for {email}\nKey: {key}\nTime: {datetime.now()}")

    return jsonify({"api_key": key, "free_limit": FREE_LIMIT})

# ---------------- GENERATE PRO API KEY ----------------
@app.route("/generate-pro-key", methods=["POST"])
def generate_pro_key():
    if not session.get("dashboard_access"):
        return jsonify({"error":"Unauthorized"}), 403
    data = request.json
    email = data.get("email")
    limit = int(data.get("limit", 1000))
    key = str(uuid.uuid4())
    pro_api_keys[key] = {"email": email, "count": 0, "limit": limit, "paid": True}

    # Send Pro-specific email
    if send_email(email, "Your QuickCaptcha Pro API Key",
        f"Hello {email},\n\nYour Pro API key is:\n\n{key}\n\nLimit: {limit} requests/month.\n\n🎯 Features: Custom styling, higher limits, priority support.\n\nThank you for choosing QuickCaptcha!"):
        print(f"✅ Pro key email sent to {email}")

    return jsonify({"api_key": key, "limit": limit})

#.....pro email...
@app.route("/request-pro-api", methods=["POST"])
def request_pro_api():
    data = request.json
    email = data.get("email")
    limit = int(data.get("limit", 1000))
    if not email:
        return jsonify({"error":"Email required"}),400

    # Send greeting email to user
    send_email(email, "Welcome to QuickCaptcha Pro!",
        f"Hello {email},\n\nThank you for choosing QuickCaptcha Pro!\nPlease reply with your requirements.\nContact: {ADMIN_EMAIL}\n\nLimit requested: {limit}")

    # Notify admin
    send_email(ADMIN_EMAIL, "New Pro API Request",
        f"User {email} requested Pro API.\nLimit: {limit}\nTime: {datetime.now()}")

    return jsonify({"status":"ok"})



# ---------------- API VERIFY ----------------
@app.route("/api/verify", methods=["POST"])
def api_verify():
    api_key = request.headers.get("x-api-key") or request.json.get("api_key")
    if not api_key:
        return jsonify({"error": "API key required"}), 401
    key_rec = api_keys.get(api_key)
    if not key_rec:
        return jsonify({"error": "Invalid API key"}), 403
    if key_rec["count"] >= FREE_LIMIT:
        return jsonify({"error": "Free limit reached"}), 403
    captcha_input = (request.json.get("captcha_input") or "").strip().upper()
    if not captcha_input:
        return jsonify({"error": "captcha_input required"}), 400
    correct = CAPTCHA_STORE.get("current", "")
    key_rec["count"] += 1
    success = captcha_input == correct
    return jsonify({"success": success, "remaining": FREE_LIMIT - key_rec["count"], "message": "Verified" if success else "Incorrect captcha"})

# ---------------- DASHBOARD ----------------
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if request.method == "POST":
        pwd = request.form.get("password")
        if pwd == DASHBOARD_PASSWORD:
            session["dashboard_access"] = True
            return redirect(url_for("dashboard"))
        return "❌ Wrong password", 403
    if not session.get("dashboard_access"):
        return """<form method="POST" style='margin-top:100px;text-align:center;'>
                  <input type="password" name="password" placeholder="Enter dashboard password" required>
                  <button type="submit">Login</button></form>"""
    return render_template_string(DASHBOARD_HTML, api_keys=api_keys, free_limit=FREE_LIMIT)

@app.route("/logout")
def logout():
    session.pop("dashboard_access", None)
    return redirect(url_for("dashboard"))

@app.route("/refresh-data")
def refresh_data():
    return jsonify({"api_keys": api_keys})

# ---------------- HTML TEMPLATE ----------------

HTML_TEMPLATE = """<html lang="en">
<head><meta charset="UTF-8"><title>QuickCaptcha</title><style>
/* ... your existing CSS ... */
body { margin:0; font-family:sans-serif; background:#f9f9f9; }
.captcha-box { background:#fff; padding:30px; border-radius:12px; box-shadow:0 8px 24px rgba(0,0,0,0.1); width:360px; text-align:center; }
button { padding:10px 15px; border:none; border-radius:6px; cursor:pointer; font-weight:600; }
#tryFreeBtn, #getProBtn { margin-top:15px; background:#1abc9c; color:#fff; }
#tryFreeBtn:hover, #getProBtn:hover { background:#16a085; }
table { width:100%; border-collapse:collapse; }
th, td { border:1px solid #ddd; padding:10px; text-align:center; }
th { background:#3498db; color:#fff; }
.modal-content { background:#fff; padding:20px; border-radius:12px; max-width:400px; margin:10% auto; box-shadow:0 8px 24px rgba(0,0,0,0.15); }
</style></head>
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
<p style="color:{{color}}">{{ message }}</p>
{% endif %}
</div>

<button id="tryFreeBtn">Try it Free</button>
{% if session.get('dashboard_access') %}
<button id="getProBtn">Get Pro API Key</button>
{% endif %}

<div id="signupModal" class="modal">
<div class="modal-content">
<span class="close">&times;</span>
<h2>Get Your Free QuickCaptcha API Key</h2>
<input type="email" id="emailInput" placeholder="Enter your email" required>
<button id="getKeyBtn">Generate Free Key</button>
<p id="apiKeyDisplay"></p>
<button id="copyKeyBtn">Copy Key</button>
</div>
</div>
<div id="proModal" class="modal">
  <div class="modal-content">
    <h2>QuickCaptcha Pro Plans</h2>

    <table style="width:100%;margin-bottom:15px;text-align:left;">
      <tr><th>Plan</th><th>Limit</th><th>Price</th><th>Features</th></tr>
      <tr>
        <td>Starter</td>
        <td>1,000 / month</td>
        <td>₹900 / $9</td>
        <td>Custom styling, priority support</td>
      </tr>
      <tr>
        <td>Growth</td>
        <td>5,000 / month</td>
        <td>₹2,900 / $29</td>
        <td>All Starter features + branding removal, analytics</td>
      </tr>
      <tr>
        <td>Enterprise</td>
        <td>20,000+ / month</td>
        <td>₹9,900 / $99</td>
        <td>All Growth features + dedicated domain, unlimited analytics</td>
      </tr>
    </table>

    <input type="email" id="proEmail" placeholder="User Email" required>
    <input type="number" id="proLimit" placeholder="Limit (default 1000)" value="1000">
    <button id="requestProBtn">Request Pro Access</button>
    <p id="proRequestStatus"></p>
  </div>
</div>

<script>
const proBtn = document.getElementById("getProBtn");
if (proBtn) {
    const proModal = document.getElementById("proModal");
    proBtn.onclick = () => proModal.style.display = "block";

    // Disable X close
    const closePro = proModal.getElementsByClassName("close")[0];
    if (closePro) closePro.style.display = "none";

    window.onclick = e => { if (e.target == proModal) proModal.style.display = "block"; }

    // Request Pro API
    document.getElementById("requestProBtn").onclick = async () => {
        const email = document.getElementById("proEmail").value.trim();
        const limit = parseInt(document.getElementById("proLimit").value) || 1000;
        if (!email) { alert("Enter your email"); return; }

        try {
            const res = await fetch("/request-pro-api", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify({ email, limit })
            });
            const data = await res.json();
            if (data.status === "ok") {
                document.getElementById("proRequestStatus").textContent = 
                    "✅ Request sent! Check your email for next steps.";
            } else {
                document.getElementById("proRequestStatus").textContent = 
                    `❌ Error: ${data.error || 'Unknown error'}`;
            }
        } catch (err) {
            document.getElementById("proRequestStatus").textContent = "❌ Error sending request.";
        }
    };
}
</script>
</body></html>
"""

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>QuickCaptcha Dashboard</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
body{background:#f4f6f9;font-family:sans-serif;margin:0;padding:0;}
.container{max-width:900px;margin:50px auto;background:#fff;padding:30px;border-radius:12px;box-shadow:0 6px 18px rgba(0,0,0,0.1);}
h1{text-align:center;color:#2c3e50;}
table{width:100%;border-collapse:collapse;margin-top:20px;}
th,td{border:1px solid #ddd;padding:10px;text-align:center;}
th{background:#3498db;color:#fff;}
tr:nth-child(even){background:#f2f2f2;}
button{padding:10px 20px;border:none;border-radius:6px;background:#2980b9;color:#fff;cursor:pointer;margin:10px 0;}
button:hover{background:#21618c;}
</style>
</head>
<body>
<div class="container">
<h1>QuickCaptcha Dashboard</h1>
<button onclick="loadData()">Retrieve Data</button>
<table id="apiTable">
<tr><th>Email</th><th>API Key</th><th>Used</th><th>Remaining</th></tr>
{% for k,v in api_keys.items() %}
<tr>
<td>{{v['email']}}</td>
<td>{{k}}</td>
<td>{{v['count']}}</td>
<td>{{free_limit - v['count']}}</td>
</tr>
{% endfor %}
</table>
<br><center><a href="/logout">Logout</a></center>
</div>
<script>
const FREE_LIMIT = {{ free_limit }};
async function loadData(){
    const res = await fetch('/refresh-data');
    const data = await res.json();
    const table = document.getElementById('apiTable');
    table.innerHTML='<tr><th>Email</th><th>API Key</th><th>Used</th><th>Remaining</th></tr>';
    for(const [key,val] of Object.entries(data.api_keys)){
        const row = table.insertRow();
        row.insertCell(0).innerText = val.email;
        row.insertCell(1).innerText = key;
        row.insertCell(2).innerText = val.count;
        row.insertCell(3).innerText = FREE_LIMIT - val.count;
    }
}
</script>
</body>
</html>
"""  # Keep your existing dashboard

# ---------------- RUN SERVER ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
