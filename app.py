from flask import Flask, request, jsonify, render_template, send_file, redirect, url_for, session
import os, random, string, io, uuid, requests
from captcha.image import ImageCaptcha
from datetime import datetime

# ---------------- CONFIG ----------------
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey123")
FREE_LIMIT = 100
ADMIN_EMAIL = "sagarms121415@gmail.com"
DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "sagar@123")
BREVO_API_KEY = os.environ.get("BREVO_API_KEY")  # Brevo API key
EMAIL_USER = os.environ.get("EMAIL_USER")  # Verified sender email in Brevo

# Store API usage and captchas in memory
api_keys = {}  # { api_key: {email, count, emailed} }
CAPTCHA_STORE = {}

# ---------------- EMAIL FUNCTION USING BREVO API ----------------
def send_email(to_email, subject, body):
    if not BREVO_API_KEY:
        print("⚠️ BREVO_API_KEY not set in environment.")
        return False
    if not EMAIL_USER:
        print("⚠️ EMAIL_USER not set in environment.")
        return False

    url = "https://api.brevo.com/v3/smtp/email"
    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "api-key": BREVO_API_KEY
    }
    payload = {
        "sender": {"name": "QuickCaptcha", "email": EMAIL_USER},
        "to": [{"email": to_email}],
        "subject": subject,
        "htmlContent": f"<html><body><p>{body.replace(chr(10), '<br>')}</p></body></html>"
    }

    try:
        response = requests.post(url, json=payload, headers=headers)
        print(f"📧 Sending email to {to_email}, status {response.status_code}")
        return response.status_code in [200, 201, 202]
    except Exception as e:
        print("❌ Brevo email exception:", e)
        return False

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

    if send_email(
        email,
        "Your QuickCaptcha API Key",
        f"Hello {email},\n\nYour free API key is:\n\n{key}\n\nLimit: {FREE_LIMIT} requests.\n\nThank you for using QuickCaptcha!"
    ):
        api_keys[key]["emailed"] = True

    send_email(
        ADMIN_EMAIL,
        "🔔 New QuickCaptcha API Registration",
        f"A new API key was generated.\n\nUser: {email}\nAPI Key: {key}\nTime: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
    )

    return jsonify({"api_key": key, "free_limit": FREE_LIMIT})

# ---------------- CAPTCHA ----------------
@app.route("/captcha")
def captcha():
    text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    image = ImageCaptcha()
    data = io.BytesIO()
    image.write(text, data)
    data.seek(0)
    CAPTCHA_STORE["current"] = text
    return send_file(data, mimetype="image/png")

@app.route("/verify", methods=["POST"])
def verify():
    user_input = request.form.get("captcha", "").strip().upper()
    correct = CAPTCHA_STORE.get("current", "")
    message, color = ("✅ CAPTCHA Verified Successfully!", "#2ecc71") if user_input == correct else ("❌ Incorrect CAPTCHA. Try Again!", "#e74c3c")
    return render_template("index.html", message=message, color=color)

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
        else:
            return "❌ Wrong password", 403

    if not session.get("dashboard_access"):
        return """
        <form method="POST" style='margin-top:100px;text-align:center;'>
            <input type="password" name="password" placeholder="Enter dashboard password" required>
            <button type="submit">Login</button>
        </form>
        """

    return render_template("dashboard.html", api_keys=api_keys, free_limit=FREE_LIMIT)

@app.route("/logout")
def logout():
    session.pop("dashboard_access", None)
    return redirect(url_for("dashboard"))

@app.route("/refresh-data")
def refresh_data():
    return jsonify({"api_keys": api_keys})

# ---------------- ROOT ----------------
@app.route("/")
def home():
    return render_template("index.html")

# ---------------- RUN SERVER ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
