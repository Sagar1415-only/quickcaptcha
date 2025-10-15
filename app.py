from flask import Flask, request, jsonify, render_template_string, send_file, redirect, url_for, session
import os, random, string, io, uuid, requests
from captcha.image import ImageCaptcha
from datetime import datetime, timedelta, timezone

# ---------------- RESET MONTHLY LIMITS ----------------
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
            print(f"[RESET] Free API key {key} reset for new month.")

# ---------------- CONFIG ----------------
app = Flask(__name__)
app.config["SESSION_COOKIE_SECURE"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "None"
app.config["SESSION_TYPE"] = "filesystem"
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
        "htmlContent": f"<html><body>{body}</body></html>"
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
    return render_template_string(HTML_TEMPLATE, FREE_LIMIT=FREE_LIMIT)

# ---------------- VERIFY CAPTCHA ----------------
@app.route("/verify-captcha", methods=["POST"])
def verify_captcha():
    data = request.get_json() or {}
    user_input = (data.get("user_input") or "").strip().upper()
    correct = session.get("captcha", "")
    captcha_time_str = session.get("captcha_time")

    if not correct:
        return jsonify({"success": False, "message": "Captcha not found. Refresh to try again."})

    captcha_time = datetime.now()
    if captcha_time_str:
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

    return jsonify({
        "success": success,
        "message": "Verified successfully!" if success else "Incorrect captcha. Try again!"
    })

# ---------------- FREE API KEY ----------------
reset_monthly_limits()
@app.route("/generate-free-key", methods=["POST"])
def generate_free_key():
    email = (request.json.get("email") or "").strip().lower()
    if not email:
        return jsonify({"error": "Email required"}), 400

    # Return existing key if user already registered
    for key, val in api_keys.items():
        if val["email"] == email:
            return jsonify({"api_key": key, "free_limit": FREE_LIMIT})

    # Generate new key
    key = str(uuid.uuid4())
    reset_monthly_limits()
    api_keys[key] = {"email": email, "count": 0, "emailed": False,"last_reset": datetime.now().isoformat()}

    # ---------------- SEND EMAILS ----------------
    # User email
    send_email(
        email,
        "🎉 Your QuickCaptcha Free API Key & Pro Plans",
        f"""
<div style="font-family: Arial; line-height:1.6; color:#333;">
<h2>🎉 Welcome to QuickCaptcha!</h2>
<p>Hello <b>{email}</b>,</p>
<p>Your <b>Free API Key</b>: <code>{key}</code></p>
<p><b>Limit:</b> {FREE_LIMIT} requests per month</p>
<p>Enjoy QuickCaptcha 🚀</p>
<hr>
<h3>💼 QuickCaptcha Pro Plans</h3>
<table style="width:100%; border-collapse:collapse;">
<tr><th>Plan</th><th>Limit</th><th>Price</th><th>Description</th></tr>
<tr><td>Mini</td><td>500 req/mo</td><td>₹100 / $1.5</td><td>Basic UI/logo customization. Pay 50% now, remaining 50% after completion.</td></tr>
<tr><td>Starter</td><td>1,000 req/mo</td><td>₹199 / $3</td><td>Standard support & customization</td></tr>
<tr><td>Growth</td><td>5,000 req/mo</td><td>₹499 / $6</td><td>Advanced features, priority support</td></tr>
<tr><td>Advanced</td><td>10,000 req/mo</td><td>₹899 / $11</td><td>Full customization, faster processing</td></tr>
<tr><td>Business</td><td>20,000 req/mo</td><td>₹1,499 / $18</td><td>Enterprise-level support & features</td></tr>
<tr><td>Enterprise</td><td>20,000+ req/mo</td><td>Custom Quote</td><td>Fully tailored solution</td></tr>
</table>
<div style="margin-top:10px;">
<a href='https://quickcaptcha.onrender.com' style='background:#007bff;color:white;padding:12px 25px;border-radius:8px;text-decoration:none;'>💼 Explore Pro Plans</a>
&nbsp;
<a href='mailto:{ADMIN_EMAIL}?subject=Upgrade to QuickCaptcha Pro&body=Hi, I want to upgrade. Email: {email}' style='background:#22c55e;color:white;padding:12px 25px;border-radius:8px;text-decoration:none;'>📩 Contact Admin</a>
</div>
</div>
"""
    )

    # Admin email
    send_email(
        ADMIN_EMAIL,
        "🆕 New Free API Registration",
        f"""
<div style="font-family: Arial; line-height:1.6; color:#333;">
<h2>New Free API Registration</h2>
<p><b>User Email:</b> {email}</p>
<p><b>API Key:</b> {key}</p>
<p><b>Free Limit:</b> {FREE_LIMIT}</p>
<p><b>Time:</b> {datetime.now()}</p>
</div>
"""
    )

    return jsonify({"api_key": key, "free_limit": FREE_LIMIT})

# ---------------- PRO REQUEST ----------------
@app.route("/request-pro-api", methods=["POST"])
def request_pro_api():
    data = request.json or {}
    email = (data.get("email") or "").strip().lower()
    limit = int(data.get("limit", 1000))
    if not email:
        return jsonify({"error": "Email required"}), 400

    # ---------------- SEND EMAIL TO USER ----------------
    send_email(
        email,
        "💼 QuickCaptcha Pro Request Received",
        f"""
<div style="font-family: Arial; line-height:1.6; color:#222;">
<h2>💼 QuickCaptcha Pro Request Received</h2>
<p>Hello <b>{email}</b>,</p>
<p>We offer flexible Pro plans. Please select your plan and describe your requirements:</p>
<p>50% advance payment required before development, remaining 50% after completion.</p>
<a href='mailto:{ADMIN_EMAIL}?subject=Pro Plan Request&body=I want the Mini plan (₹100 / 500 req)'>Choose Plan & Contact Admin</a>
</div>
"""
    )

    # ---------------- SEND EMAIL TO ADMIN ----------------
    send_email(
        ADMIN_EMAIL,
        "📩 New Pro Request",
        f"""
<div style="font-family: Arial; line-height:1.6; color:#222;">
<h2>New Pro API Request</h2>
<p><b>User Email:</b> {email}</p>
<p><b>Requested Limit:</b> {limit}</p>
<p><b>Time:</b> {datetime.now()}</p>
<p>Please contact user to proceed with payment and plan.</p>
</div>
"""
    )

    return jsonify({"success": True, "message": "Pro request received, admin will contact you."})

# ---------------- FRONTEND TEMPLATE ----------------
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head><title>QuickCaptcha</title></head>
<body style="font-family:Arial,sans-serif;background:#f8faff;padding:20px;">
<h1>QuickCaptcha</h1>
<p>Get your Free API Key ({FREE_LIMIT} req/mo)</p>
<form id="freeForm">
<input type="email" name="email" placeholder="Email" required>
<button type="submit">Get Free Key</button>
</form>

<h2>💼 Pro Plans</h2>
<table border="1" cellpadding="8" cellspacing="0">
<tr><th>Plan</th><th>Limit</th><th>Price</th><th>Description</th></tr>
<tr><td>Mini</td><td>500 req/mo</td><td>₹100 / $1.5</td><td>Basic UI & logo. 50% pay now, 50% after completion</td></tr>
<tr><td>Starter</td><td>1,000 req/mo</td><td>₹199 / $3</td><td>Standard support & customization</td></tr>
<tr><td>Growth</td><td>5,000 req/mo</td><td>₹499 / $6</td><td>Advanced features</td></tr>
<tr><td>Advanced</td><td>10,000 req/mo</td><td>₹899 / $11</td><td>Full customization</td></tr>
<tr><td>Business</td><td>20,000 req/mo</td><td>₹1,499 / $18</td><td>Enterprise support</td></tr>
<tr><td>Enterprise</td><td>20,000+ req/mo</td><td>Custom</td><td>Tailored solution</td></tr>
</table>

<h2>Request Pro API</h2>
<form id="proForm">
<input type="email" name="email" placeholder="Email" required>
<select name="limit">
<option value="500">Mini 500 req</option>
<option value="1000">Starter 1000 req</option>
<option value="5000">Growth 5000 req</option>
<option value="10000">Advanced 10000 req</option>
<option value="20000">Business 20000 req</option>
<option value="50000">Enterprise 50000+ req</option>
</select>
<button type="submit">Request Pro API</button>
</form>

<script>
document.getElementById("freeForm").onsubmit = async function(e){
    e.preventDefault();
    let email = e.target.email.value;
    let res = await fetch("/generate-free-key",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({email})});
    let data = await res.json();
    alert("Your API Key: "+data.api_key);
};
document.getElementById("proForm").onsubmit = async function(e){
    e.preventDefault();
    let email = e.target.email.value;
    let limit = e.target.limit.value;
    let res = await fetch("/request-pro-api",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({email,limit})});
    let data = await res.json();
    alert(data.message);
};
</script>
</body>
</html>
"""

# ---------------- RUN APP ----------------
if __name__ == "__main__":
    app.run(debug=True)
