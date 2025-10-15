from flask import Flask, request, jsonify, render_template_string, send_file, redirect, url_for, session
import os, random, string, io, uuid, requests
from captcha.image import ImageCaptcha
from datetime import datetime, timedelta

# ---------------- CONFIG ----------------
app = Flask(__name__)
app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "None"
app.config["SESSION_TYPE"] = "filesystem"  # ensures persistence across requests
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey123")
FREE_LIMIT = 100
ADMIN_EMAIL = "sagarms121415@gmail.com"
DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "sagar@123")
BREVO_API_KEY = os.environ.get("BREVO_API_KEY")
EMAIL_USER = os.environ.get("EMAIL_USER")

api_keys = {}       # free API keys
pro_api_keys = {}   # pro API keys

# ---------------- EMAIL FUNCTION ----------------
def send_email(to_email, subject, body):
    if not BREVO_API_KEY or not EMAIL_USER:
        print("⚠️ Email not configured properly.")
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
        print(f"📧 Email sent to {to_email} ({res.status_code})")
        return res.status_code in [200, 201, 202]
    except Exception as e:
        print("❌ Email exception:", e)
        return False

# ---------------- CAPTCHA GENERATION ----------------
@app.route("/captcha")
def captcha():
    from datetime import datetime
    text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    session['captcha'] = text
    session['captcha_time'] = datetime.now().isoformat()  # store as string
    session['captcha_attempts'] = 0  # reset
    image = ImageCaptcha()
    data = io.BytesIO()
    image.write(text, data)
    data.seek(0)
    return send_file(data, mimetype="image/png")


# ---------------- ROOT ----------------
@app.route("/")
def home():
    return render_template_string(HTML_TEMPLATE)

# ---------------- VERIFY CAPTCHA ----------------
@app.route("/verify-captcha", methods=["POST"])
def verify_captcha():
    from datetime import datetime, timedelta

    data = request.get_json() or {}
    user_input = (data.get("user_input") or "").strip().upper()
    correct = session.get("captcha", "")
    captcha_time_str = session.get("captcha_time")

    # if not generated
    if not correct:
        return jsonify({"success": False, "message": "Captcha not found. Refresh to try again."})

    # parse stored timestamp safely
    if captcha_time_str:
        try:
            captcha_time = datetime.fromisoformat(captcha_time_str)
        except:
            captcha_time = datetime.now()
    else:
        captcha_time = datetime.now()

    # expiry
    if datetime.now() - captcha_time > timedelta(minutes=5):
        return jsonify({"success": False, "message": "Captcha expired. Refresh to try again."})

    # too many attempts
    attempts = session.get("captcha_attempts", 0) + 1
    session["captcha_attempts"] = attempts
    if attempts > 5:
        return jsonify({"success": False, "message": "Too many attempts. Please refresh captcha."})

    # check correctness
    success = user_input == correct
    if success:
        session.pop("captcha", None)
        session.pop("captcha_time", None)
        session.pop("captcha_attempts", None)

    print(f"[CAPTCHA LOG] {datetime.now()} | IP: {request.remote_addr} | Input: {user_input} | Correct: {correct} | Success: {success}")

    return jsonify({
        "success": success,
        "message": "Verified successfully!" if success else "Incorrect captcha. Try again!"
    })


# ---------------- FREE API KEY ----------------
@app.route("/generate-free-key", methods=["POST"])
def generate_free_key():
    email = (request.json.get("email") or "").strip().lower()
    if not email:
        return jsonify({"error": "Email required"}), 400

    for key, val in api_keys.items():
        if val["email"] == email:
            return jsonify({"api_key": key, "free_limit": FREE_LIMIT})

    key = str(uuid.uuid4())
    api_keys[key] = {"email": email, "count": 0, "emailed": False}

    send_email(email, "🎉 Your QuickCaptcha Free API Key",
               f"Hello {email},\n\nHere is your free API key:\n\n{key}\nLimit: {FREE_LIMIT} requests.\n\nEnjoy using QuickCaptcha!")

    send_email(ADMIN_EMAIL, "🆕 New Free API Registration",
               f"User: {email}\nKey: {key}\nTime: {datetime.now()}")

    return jsonify({"api_key": key, "free_limit": FREE_LIMIT})

# ---------------- PRO REQUEST ----------------
@app.route("/request-pro-api", methods=["POST"])
def request_pro_api():
    data = request.json or {}
    email = (data.get("email") or "").strip().lower()
    limit = int(data.get("limit", 1000))

    if not email:
        return jsonify({"error": "Email required"}), 400

    send_email(email, "💼 QuickCaptcha Pro Request Received",
               f"Hello {email},\n\nThank you for your interest in QuickCaptcha Pro.\nPlease reply with your specific requirements.\nRequested limit: {limit}\n\nContact: {ADMIN_EMAIL}")

    send_email(ADMIN_EMAIL, "📩 New Pro API Request",
               f"User {email} requested Pro API access.\nLimit: {limit}\nTime: {datetime.now()}")

    print(f"[ADMIN LOG] Pro API request received from {email}")
    return jsonify({"status": "ok"})

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
        return """<form method='POST' style='margin-top:100px;text-align:center;'>
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

# ---------------- HTML TEMPLATE ----------------
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>QuickCaptcha</title>
<style>
body {
  font-family: 'Poppins', sans-serif;
  background: linear-gradient(135deg, #f8faff, #eef2f3);
  text-align: center;
  padding: 40px;
}
.container {
  display: flex;
  justify-content: center;
  gap: 40px;
  flex-wrap: wrap;
}
.card {
  background: white;
  padding: 25px;
  border-radius: 16px;
  box-shadow: 0 4px 20px rgba(0,0,0,0.1);
  width: 300px;
}
.captcha-verify {
  margin-top: 15px;
}
.captcha-verify input {
  padding: 8px;
  border-radius: 6px;
  border: 1px solid #ccc;
}
.captcha-verify button {
  padding: 8px 12px;
  background: #007bff;
  color: white;
  border: none;
  border-radius: 6px;
  cursor: pointer;
}
button:hover { background: #0056b3; }
.modal {
  display: none; position: fixed; z-index: 999;
  left: 0; top: 0; width: 100%; height: 100%;
  background: rgba(0,0,0,0.4);
}
.modal-content {
  background: white; border-radius: 10px; padding: 20px;
  width: 90%; max-width: 400px; margin: 10% auto;
  text-align: center;
}
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
      <p id="captchaResult"></p>
    </div>
    <br>
    <button id="tryFreeBtn">Generate Free Key</button>
  </div>

  <div class="card">
    <h2>Pro Plan</h2>
    <p>For startups & commercial use</p>
    <button id="getProBtn">Explore Pro Plans</button>
  </div>
</div>

<!-- Modals -->
<div id="signupModal" class="modal">
  <div class="modal-content">
    <h2>Get Your Free API Key</h2>
    <input type="email" id="emailInput" placeholder="Enter your email">
    <button id="getKeyBtn">Generate Key</button>
    <p id="apiKeyDisplay"></p>
  </div>
</div>

<div id="proModal" class="modal">
  <div class="modal-content">
    <h2>Pro Packages</h2>
    <table border="1" style="width:100%;border-collapse:collapse;">
      <tr><th>Plan</th><th>Limit</th><th>Price</th></tr>
      <tr><td>Starter</td><td>1,000/mo</td><td>₹199 / $3</td></tr>
      <tr><td>Growth</td><td>5,000/mo</td><td>₹599 / $8</td></tr>
      <tr><td>Business</td><td>20,000+/mo</td><td>₹1499 / $18</td></tr>
    </table>
    <input type="email" id="proEmail" placeholder="Your Email">
    <input type="number" id="proLimit" placeholder="Limit (e.g. 5000)">
    <button id="requestProBtn">Request Access</button>
    <p id="proRequestStatus"></p>
  </div>
</div>

<script>
function refreshCaptcha(){
  const img = document.getElementById("captcha-image");
  img.src = "/captcha?"+new Date().getTime();
}

async function verifyCaptcha(){
  const input = document.getElementById("captchaInput").value.trim();
  const result = document.getElementById("captchaResult");
  if(!input){alert("Enter captcha");return;}
  try{
    const res = await fetch("/verify-captcha",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({user_input:input})});
    const data = await res.json();
    if(data.success){result.style.color="green";result.textContent="✅ Verified";}
    else{result.style.color="red";result.textContent="❌ "+data.message;refreshCaptcha();}
  }catch{result.style.color="orange";result.textContent="⚠️ Error verifying";}
}

document.getElementById("tryFreeBtn").onclick=()=>signupModal.style.display="block";
document.getElementById("getProBtn").onclick=()=>proModal.style.display="block";

document.getElementById("getKeyBtn").onclick=async()=>{
  const email=document.getElementById("emailInput").value.trim();
  const res=await fetch("/generate-free-key",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({email})});
  const data=await res.json();
  document.getElementById("apiKeyDisplay").textContent=data.api_key?"✅ "+data.api_key:"❌ "+(data.error||"Error");
};

document.getElementById("requestProBtn").onclick=async()=>{
  const email=document.getElementById("proEmail").value.trim();
  const limit=parseInt(document.getElementById("proLimit").value)||1000;
  const res=await fetch("/request-pro-api",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({email,limit})});
  const data=await res.json();
  document.getElementById("proRequestStatus").textContent=data.status==="ok"?"✅ Request Sent!":"❌ "+(data.error||"Error");
};
</script>
</body></html>
"""

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>Dashboard</title>
<style>
body{background:#f6f7fb;font-family:Poppins,sans-serif;text-align:center;}
table{margin:auto;border-collapse:collapse;width:80%;}
th,td{border:1px solid #ddd;padding:8px;}th{background:#007bff;color:#fff;}
tr:nth-child(even){background:#f2f2f2;}
</style></head><body>
<h2>QuickCaptcha Dashboard</h2>
<table><tr><th>Email</th><th>API Key</th><th>Used</th><th>Remaining</th></tr>
{% for k,v in api_keys.items() %}
<tr><td>{{v['email']}}</td><td>{{k}}</td><td>{{v['count']}}</td><td>{{free_limit - v['count']}}</td></tr>
{% endfor %}
</table><br><a href="/logout">Logout</a></body></html>"""

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
