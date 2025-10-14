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
    session['captcha'] = text
    session['captcha_time'] = datetime.now()
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
@app.route("/verify-captcha", methods=["POST"])
def verify_captcha():
    data = request.get_json()
    user_input = data.get("user_input", "").strip().upper()
    correct = session.get("captcha", "")
    captcha_time = session.get("captcha_time")
    from datetime import timedelta

    # Check expiry
    if captcha_time and datetime.now() - captcha_time > timedelta(minutes=5):
        return jsonify({"success": False, "message": "CAPTCHA expired. Refresh to try again."})

    # Increment attempts
    attempts = session.get("captcha_attempts", 0) + 1
    session["captcha_attempts"] = attempts
    if attempts > 5:
        return jsonify({"success": False, "message": "Too many attempts. Refresh CAPTCHA."})

    success = user_input == correct

    # Clear after success
    if success:
        session.pop("captcha", None)
        session.pop("captcha_time", None)
        session.pop("captcha_attempts", None)

    # Logging
    print(f"[CAPTCHA LOG] {datetime.now()} | IP: {request.remote_addr} | Input: {user_input} | Success: {success}")

    return jsonify({"success": success})

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
        print(f"[ADMIN LOG] Email sent to: {email}")

    send_email(ADMIN_EMAIL, "🔔 New QuickCaptcha API Registration", f"New API key generated for {email}\nKey: {key}\nTime: {datetime.now()}")
    print(f"[ADMIN LOG] Admin notified for new registration: {email}")
    return jsonify({"api_key": key, "free_limit": FREE_LIMIT})

# ---------------- GENERATE PRO API KEY ----------------
@app.route("/generate-pro-key", methods=["POST"])
def generate_pro_key():
    if not session.get("dashboard_access"):
        return jsonify({"error": "Unauthorized"}), 403

    data = request.json or {}
    email = (data.get("email") or "").strip().lower()
    limit = int(data.get("limit", 1000))

    if not email:
        return jsonify({"error": "Email required"}), 400

    # Generate key
    key = str(uuid.uuid4())
    pro_api_keys[key] = {"email": email, "count": 0, "limit": limit, "paid": True, "emailed": False}

    # Send email
    if send_email(email, "Your QuickCaptcha Pro API Key",
        f"Hello {email},\n\nYour Pro API key is:\n\n{key}\nLimit: {limit} requests/month.\n\nThank you!"):
        pro_api_keys[key]["emailed"] = True

    print(f"[ADMIN LOG] Pro key generated for {email}")
    return jsonify({"api_key": key, "limit": limit})


# ---------------- PRO REQUEST ----------------
@app.route("/request-pro-api", methods=["POST"])
def request_pro_api():
    data = request.json or {}
    email = (data.get("email") or "").strip().lower()
    limit = int(data.get("limit", 1000))

    if not email:
        return jsonify({"error": "Email required"}), 400

    # Notify user
    send_email(email, "QuickCaptcha Pro Request Received",
        f"Hello {email},\n\nThank you for your interest in QuickCaptcha Pro.\nWe will review your request and contact you soon.\nRequested limit: {limit}")

    # Notify admin
    send_email(ADMIN_EMAIL, "New Pro API Request",
        f"User {email} requested Pro API access.\nLimit: {limit}\nTime: {datetime.now()}")

    print(f"[ADMIN LOG] Admin notified for Pro request by {email}")
    return jsonify({"status": "ok"})

# ---------------- VERIFY CAPTCHA INPUT ----------------
# ---------------- VERIFY CAPTCHA ----------------
# ---------------- VERIFY CAPTCHA ----------------
@app.route("/verify-captcha", methods=["POST"])
def verify_captcha():
    data = request.get_json() or {}
    user_input = (data.get("user_input") or "").strip().upper()
    correct = session.get("captcha", "")
    captcha_time = session.get("captcha_time")
    from datetime import timedelta, datetime

    # Check expiry
    if captcha_time and datetime.now() - captcha_time > timedelta(minutes=5):
        return jsonify({"success": False, "message": "CAPTCHA expired. Refresh to try again."})

    # Increment attempts
    attempts = session.get("captcha_attempts", 0) + 1
    session["captcha_attempts"] = attempts
    if attempts > 5:
        return jsonify({"success": False, "message": "Too many attempts. Refresh CAPTCHA."})

    # Verify
    success = user_input == correct

    # Clear session after success
    if success:
        session.pop("captcha", None)
        session.pop("captcha_time", None)
        session.pop("captcha_attempts", None)

    # Logging
    print(f"[CAPTCHA LOG] {datetime.now()} | IP: {request.remote_addr} | Input: {user_input} | Success: {success}")

    return jsonify({"success": success, "message": "Verified" if success else "Incorrect captcha"})



# ---------------- API VERIFY ----------------
# ---------------- API VERIFY ----------------
@app.route("/api/verify", methods=["POST"])
def api_verify():
    api_key = request.headers.get("x-api-key") or request.json.get("api_key")
    if not api_key:
        return jsonify({"error": "API key required"}), 401

    key_rec = api_keys.get(api_key) or pro_api_keys.get(api_key)
    if not key_rec:
        return jsonify({"error": "Invalid API key"}), 403

    # Check limit
    limit = key_rec.get("limit", FREE_LIMIT)
    if key_rec["count"] >= limit:
        return jsonify({"error": "API limit reached"}), 403

    captcha_input = (request.json.get("captcha_input") or "").strip().upper()
    if not captcha_input:
        return jsonify({"error": "captcha_input required"}), 400

    correct = session.get("captcha", "")
    captcha_time = session.get("captcha_time")
    from datetime import timedelta

    # Check expiry
    if captcha_time and datetime.now() - captcha_time > timedelta(minutes=5):
        success = False
        message = "CAPTCHA expired. Refresh to try again."
    else:
        success = captcha_input == correct
        message = "Verified" if success else "Incorrect captcha"

    # Increment count & clear captcha on success
    if success:
        session.pop("captcha", None)
        session.pop("captcha_time", None)
        session.pop("captcha_attempts", None)
    key_rec["count"] += 1

    # Logging
    print(f"[API LOG] {datetime.now()} | IP: {request.remote_addr} | Key: {api_key} | Input: {captcha_input} | Success: {success}")

    return jsonify({
        "success": success,
        "remaining": limit - key_rec["count"],
        "message": message
    })

# ---------------- DASHBOARD ----------------
@app.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if request.method == "POST":fapi 
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
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>QuickCaptcha</title>
<style>
.captcha-verify {
  margin-top: 12px;
  display: flex;
  align-items: center;
  gap: 10px;
  justify-content: center;
}
.captcha-verify input {
  padding: 8px;
  border-radius: 6px;
  border: 1px solid #ccc;
  width: 150px;
}
.captcha-verify button {
  padding: 8px 12px;
  border: none;
  background: #007bff;
  color: white;
  border-radius: 6px;
  cursor: pointer;
}
#captchaResult {
  font-weight: 600;
}

body {
  margin:0; font-family:'Poppins', sans-serif;
  background:linear-gradient(135deg,#e3f2fd,#f8f9fa);
  display:flex; flex-direction:column; align-items:center; justify-content:center;
  min-height:100vh;
}
h1 { color:#2c3e50; margin-bottom:10px; }
.container {
  display:flex; gap:40px; flex-wrap:wrap; justify-content:center;
  margin-top:20px;
}
.card {
  background:#fff; padding:25px; border-radius:16px;
  box-shadow:0 8px 30px rgba(0,0,0,0.1);
  width:320px; text-align:center;
}
button {
  background:#007bff; color:#fff; border:none;
  border-radius:6px; padding:10px 20px; font-weight:600;
  cursor:pointer; transition:0.3s;
}
button:hover { background:#0056b3; }
.modal {
  display:none; position:fixed; z-index:999; left:0; top:0;
  width:100%; height:100%; background:rgba(0,0,0,0.4);
}
.modal-content {
  background:#fff; border-radius:12px; padding:25px;
  width:90%; max-width:400px; margin:10% auto;
  box-shadow:0 10px 25px rgba(0,0,0,0.2);
  text-align:center;
}
input {
  width:90%; padding:10px; margin:10px 0;
  border:1px solid #ccc; border-radius:6px;
}
.success { color:#2ecc71; }
.error { color:#e74c3c; }
table {
  width:100%; border-collapse:collapse; margin:10px 0;
}
th, td {
  border:1px solid #ddd; padding:8px; text-align:center;
}
th {
  background:#007bff; color:white;
}
</style>
</head>
<body>

<h1>QuickCaptcha</h1>
<p style="color:#555;">Secure. Simple. Smart Captcha Solution</p>

<div class="container">
  <div class="card">
    <h2>Free Plan</h2>
    <p>For developers and small projects</p>
    <p><b>Limit:</b> 100 requests</p>
    <div style="margin:10px 0;">
      <img id="captcha-image" src="/captcha" alt="captcha demo" style="max-width:240px;border-radius:8px;border:1px solid #e6e6e6;">
      <div><a href="#" onclick="refreshCaptcha(event)" style="color:#007bff;text-decoration:none;">🔄 Refresh CAPTCHA</a></div>
    </div>
    <div class="captcha-verify">
  <input type="text" id="captchaInput" placeholder="Enter Captcha">
  <button id="verifyCaptchaBtn">Verify</button>
  <p id="captchaResult"></p>
</div>

    <button id="tryFreeBtn">Generate Free Key</button>
  </div>

  <div class="card">
    <h2>Pro Plans</h2>
    <p>For startups & businesses needing more control</p>
    <button id="getProBtn">View Pro Packages</button>
  </div>
</div>

<!-- FREE MODAL -->
<div id="signupModal" class="modal">
  <div class="modal-content">
   <span class="close" style="float:right;cursor:pointer;font-size:18px;">&times;</span>
    <h2>Get Your Free QuickCaptcha API Key</h2>
    <input type="email" id="emailInput" placeholder="Enter your email" required>
    <button id="getKeyBtn">Generate Free Key</button>
    <p id="apiKeyDisplay"></p>
    <button id="copyKeyBtn" style="display:none;">Copy Key</button>
  </div>
</div>

<!-- PRO MODAL -->
<div id="proModal" class="modal">
  <div class="modal-content">
  <span class="close" style="float:right;cursor:pointer;font-size:18px;">&times;</span>
    <h2>QuickCaptcha Pro Packages</h2>
    <table>
      <tr><th>Plan</th><th>Limit</th><th>Price</th></tr>
      <tr><td>Starter</td><td>1,000/mo</td><td>₹199 / $3</td></tr>
      <tr><td>Growth</td><td>5,000/mo</td><td>₹599 / $8</td></tr>
      <tr><td>Business</td><td>20,000+/mo</td><td>₹1499 / $18</td></tr>
    </table>
    <p style="font-size:13px;color:#777;">Includes: Custom Styling • Branding Removal • Analytics • Priority Support</p>
    <input type="email" id="proEmail" placeholder="Your Email" required>
    <input type="number" id="proLimit" placeholder="Requested Limit (e.g. 5000)" value="1000">
    <button id="requestProBtn">Request Pro Access</button>
    <p id="proRequestStatus"></p>
  </div>
</div>

<script>
// Refresh Captcha
function refreshCaptcha(e){
  if(e) e.preventDefault();
  const img = document.getElementById("captcha-image");
  if(img) img.src = "/captcha?"+new Date().getTime();
}

// --- FREE PLAN MODAL ---
const freeModal = document.getElementById("signupModal");
const tryFreeBtn = document.getElementById("tryFreeBtn");
const freeClose = freeModal?.getElementsByClassName("close")[0];
const getKeyBtn = document.getElementById("getKeyBtn");
const emailInput = document.getElementById("emailInput");
const apiKeyDisplay = document.getElementById("apiKeyDisplay");
const copyKeyBtn = document.getElementById("copyKeyBtn");

if(tryFreeBtn) tryFreeBtn.onclick = () => freeModal.style.display = "block";
if(freeClose) freeClose.onclick = () => freeModal.style.display = "none";

if(getKeyBtn){
  getKeyBtn.onclick = async () => {
    const email = (emailInput?.value || "").trim();
    if(!email){ alert("Enter your email"); return; }
    try {
      const res = await fetch("/generate-free-key", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({email})
      });
      const data = await res.json();
      if(data.api_key){
        apiKeyDisplay.innerHTML = "✅ Your API Key: <b>" + data.api_key + "</b>";
        if(copyKeyBtn) copyKeyBtn.style.display = "inline-block";
      } else {
        apiKeyDisplay.textContent = "❌ " + (data.error || "Error generating key");
      }
    } catch(err){
      apiKeyDisplay.textContent = "❌ Error generating API key.";
    }
  };
}

if(copyKeyBtn){
  copyKeyBtn.onclick = () => {
    const txt = apiKeyDisplay.innerText.split(":")[1]?.trim();
    if(txt) {
      navigator.clipboard.writeText(txt);
      alert("API key copied to clipboard");
    }
  };
}

// --- PRO PLAN MODAL ---
const proModal = document.getElementById("proModal");
const getProBtn = document.getElementById("getProBtn");
const proClose = proModal?.getElementsByClassName("close")[0];
const requestProBtn = document.getElementById("requestProBtn");
const proEmail = document.getElementById("proEmail");
const proLimit = document.getElementById("proLimit");
const proStatus = document.getElementById("proRequestStatus");

if(getProBtn) getProBtn.onclick = () => proModal.style.display = "block";
if(proClose) proClose.onclick = () => proModal.style.display = "none";

if(requestProBtn){
  requestProBtn.onclick = async () => {
    const email = (proEmail?.value || "").trim();
    const limit = parseInt(proLimit?.value) || 1000;
    if(!email){ alert("Enter email"); return; }
    try {
      const res = await fetch("/request-pro-api", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({email, limit})
      });
      const data = await res.json();
      if(data.status === "ok"){
        proStatus.className = "success";
        proStatus.textContent = "✅ Request sent! Check your email for next steps.";
      } else {
        proStatus.className = "error";
        proStatus.textContent = "❌ " + (data.error || "Request failed");
      }
    } catch(err){
      proStatus.className = "error";
      proStatus.textContent = "❌ Request failed";
    }
  };
}

// unified outside click handler
window.onclick = function(e){
  if(e.target === freeModal) freeModal.style.display = "none";
  if(e.target === proModal) proModal.style.display = "none";
};
// --- CAPTCHA VERIFY ---
// --- CAPTCHA VERIFY ---
document.getElementById("verifyCaptchaBtn").onclick = async () => {
  const input = document.getElementById("captchaInput").value.trim();
  if (!input) { alert("Please enter captcha"); return; }

  const result = document.getElementById("captchaResult");
  result.textContent = "";
  
  try {
    const res = await fetch("/verify-captcha", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ user_input: input })
    });
    const data = await res.json();

    if (data.success) {
      result.style.color = "green";
      result.textContent = "✅ Captcha verified successfully!";
    } else {
      result.style.color = "red";
      result.textContent = "❌ " + (data.message || "Incorrect captcha. Try again!");
      refreshCaptcha();
    }
  } catch (err) {
    result.style.color = "orange";
    result.textContent = "⚠️ Error verifying captcha";
  }
};

</script>
</body>
</html>
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
"""

# ---------------- RUN SERVER ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
