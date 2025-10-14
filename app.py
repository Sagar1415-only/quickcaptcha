from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for
import os, random, string, io, uuid, requests, base64
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

# Store API usage and captchas in memory
api_keys = {}  # { api_key: {email, count, emailed} }
CAPTCHA_STORE = {}

# ---------------- EMAIL FUNCTION ----------------
def send_email(to_email, subject, body):
    if not BREVO_API_KEY or not EMAIL_USER:
        print("⚠️ Email not configured properly")
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
        res = requests.post(url, json=payload, headers=headers)
        return res.status_code in [200, 201, 202]
    except Exception as e:
        print("❌ Email exception:", e)
        return False
        #......................Pro........................
# Store Pro API keys
pro_api_keys = {}  # { api_key: {email, count, limit, paid} }
@app.route("/generate-pro-key", methods=["POST"])
def generate_pro_key():
    if not session.get("dashboard_access"):
        return jsonify({"error": "Unauthorized"}), 403
    email = request.json.get("email", "").strip().lower()
    limit = request.json.get("limit", 1000)
    key = str(uuid.uuid4())
    pro_api_keys[key] = {"email": email, "count": 0, "limit": limit, "paid": True}

    send_email(email, "Your QuickCaptcha Pro API Key",
               f"Hello {email},\n\nYour Pro API key is:\n\n{key}\n\nLimit: {limit} requests.\n\nThank you for upgrading!")

    return jsonify({"api_key": key, "limit": limit})


# ---------------- GENERATE CAPTCHA ----------------
def generate_captcha():
    text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    image = ImageCaptcha(width=280, height=90)
    data = io.BytesIO()
    image.write(text, data)
    data.seek(0)
    img_base64 = base64.b64encode(data.read()).decode('utf-8')
    CAPTCHA_STORE["current"] = text
    return f"data:image/png;base64,{img_base64}"

# ---------------- ROOT / CAPTCHA PAGE ----------------
@app.route("/")
def home():
    captcha_text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    CAPTCHA_STORE["current"] = captcha_text
    captcha_img = f"/captcha?{uuid.uuid4().hex}"  # force reload
    return render_template_string(HTML_TEMPLATE, captcha_img=captcha_img)
@app.route("/refresh-captcha")
def refresh_captcha():
    text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    CAPTCHA_STORE["current"] = text
    captcha_img = f"/captcha?{uuid.uuid4().hex}"
    return jsonify({"captcha_img": captcha_img})




@app.route("/verify", methods=["POST"])
def verify():
    user_input = request.form.get("captcha", "").strip().upper()
    correct = CAPTCHA_STORE.get("current", "")
    message, color = ("✅ CAPTCHA Verified Successfully!", "#2ecc71") if user_input == correct else ("❌ Incorrect CAPTCHA. Try Again!", "#e74c3c")
    captcha_img = generate_captcha()
    return render_template_string(HTML_TEMPLATE, captcha_img=captcha_img, message=message, color=color)

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

    if send_email(email, "Your QuickCaptcha API Key",
                  f"Hello {email},\n\nYour free API key is:\n\n{key}\n\nLimit: {FREE_LIMIT} requests.\n\nThank you!"):
        api_keys[key]["emailed"] = True

    send_email(ADMIN_EMAIL, "🔔 New QuickCaptcha API Registration",
               f"New API key generated for {email}\nKey: {key}\nTime: {datetime.now()}")

    return jsonify({"api_key": key, "free_limit": FREE_LIMIT})

# ---------------- API VERIFY ----------------
@app.route("/api/verify", methods=["POST"])
def api_verify():
    api_key = request.headers.get("x-api-key") or request.json.get("api_key")
    if not api_key:
        return jsonify({"error": "API key required"}), 401

    key_rec = api_keys.get(api_key)
    if key_rec:  # Free key
        if key_rec["count"] >= FREE_LIMIT:
            return jsonify({"error": "Free limit reached"}), 403
        captcha_input = (request.json.get("captcha_input") or "").strip().upper()
        if not captcha_input:
            return jsonify({"error": "captcha_input required"}), 400
        correct = CAPTCHA_STORE.get("current", "")
        key_rec["count"] += 1
        success = captcha_input == correct
        return jsonify({"success": success, "remaining": FREE_LIMIT - key_rec["count"], "message": "Verified" if success else "Incorrect captcha"})

    key_rec = pro_api_keys.get(api_key)
    if key_rec:  # Pro key
        if key_rec["count"] >= key_rec["limit"]:
            return jsonify({"error": "Pro limit reached"}), 403
        captcha_input = (request.json.get("captcha_input") or "").strip().upper()
        if not captcha_input:
            return jsonify({"error": "captcha_input required"}), 400
        correct = CAPTCHA_STORE.get("current", "")
        key_rec["count"] += 1
        success = captcha_input == correct
        return jsonify({"success": success, "remaining": key_rec["limit"] - key_rec["count"], "message": "Verified" if success else "Incorrect captcha"})

    return jsonify({"error": "Invalid API key"}), 403


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

# ---------------- HTML TEMPLATES ----------------
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>QuickCaptcha</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<style>
body{margin:0;font-family:sans-serif;background:#f0f4f7;display:flex;flex-direction:column;align-items:center;justify-content:center;height:100vh;}
.captcha-box{background:#fff;padding:30px;border-radius:12px;box-shadow:0 6px 18px rgba(0,0,0,0.1);text-align:center;width:350px;margin-bottom:20px;}
h1{color:#2c3e50;margin-bottom:20px;}
img{border:1px solid #ddd;border-radius:8px;margin-bottom:15px;width:100%;max-width:260px;}
input[type=text],input[type=email]{width:100%;padding:10px;margin-bottom:15px;border-radius:6px;border:1px solid #ccc;}
input:focus{border-color:#3498db;box-shadow:0 0 5px rgba(52,152,219,0.4);outline:none;}
button{width:100%;padding:10px;border-radius:6px;border:none;background:#3498db;color:#fff;cursor:pointer;}
button:hover{background:#2980b9;}
.refresh{color:#3498db;text-decoration:none;margin-top:10px;display:block;}
.refresh:hover{color:#21618c;}
#tryFreeBtn{margin-top:15px;background:#ff7f50;color:#fff;padding:10px 20px;border-radius:8px;}
#tryFreeBtn:hover{background:#ff6347;}
#copyKeyBtn{display:none;margin-top:10px;background:#3498db;color:#fff;border:none;padding:8px 15px;border-radius:6px;cursor:pointer;}
#copyKeyBtn:hover{background:#2980b9;}
#apiKeyDisplay.success{color:#2ecc71;font-weight:600;word-break:break-all;margin-top:10px;}
#apiKeyDisplay.error{color:#e74c3c;font-weight:600;word-break:break-all;margin-top:10px;}
.modal{display:none;position:fixed;z-index:1000;left:0;top:0;width:100%;height:100%;overflow:auto;background-color:rgba(0,0,0,0.5);}
.modal-content{background:#fff;margin:10% auto;padding:20px;border-radius:8px;width:300px;text-align:center;}
.close{float:right;font-size:28px;font-weight:bold;color:#aaa;cursor:pointer;}
.close:hover{color:#000;}
</style>
</head>
<body>
<div class="captcha-box">
<h1>QuickCaptcha</h1>
<form method="POST" action="/verify">
<img src="{{ captcha_img }}" alt="CAPTCHA" id="captcha-image">
<a href="#" class="refresh" onclick="refreshCaptcha(event)">🔄 Refresh CAPTCHA</a>
<input type="text" name="captcha" placeholder="Enter CAPTCHA" required>
<button type="submit">Verify</button>
</form>
{% if message %}
<p style="color:{{color}}">{{ message }}</p>
{% endif %}
</div>

<button id="tryFreeBtn">Try it Free</button>
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

<script>
function refreshCaptcha(e){
    e.preventDefault();
    fetch('/refresh-captcha').then(r => r.json()).then(d => {
        document.getElementById('captcha-image').src = d.captcha_img;
    });
}

const modal = document.getElementById("signupModal"),
      tryBtn = document.getElementById("tryFreeBtn"),
      closeSpan = document.getElementsByClassName("close")[0],
      getKeyBtn = document.getElementById("getKeyBtn"),
      emailInput = document.getElementById("emailInput"),
      apiKeyDisplay = document.getElementById("apiKeyDisplay"),
      copyKeyBtn = document.getElementById("copyKeyBtn");

tryBtn.onclick = () => modal.style.display = "block";
closeSpan.onclick = () => modal.style.display = "none";
window.onclick = e => { if(e.target == modal) modal.style.display = "none"; }

getKeyBtn.onclick = async () => {
    const email = emailInput.value.trim();
    if(!email){
        apiKeyDisplay.className="error"; apiKeyDisplay.textContent="❌ Enter your email"; copyKeyBtn.style.display="none"; return;
    }
    try{
        const res = await fetch("/generate-free-key",{
            method:"POST",
            headers:{"Content-Type":"application/json"},
            body:JSON.stringify({email})
        });
        const data = await res.json();
        if(data.api_key){
            apiKeyDisplay.className="success";
            apiKeyDisplay.textContent = `✅ Your API Key: ${data.api_key} (Limit: ${data.free_limit})`;
            copyKeyBtn.style.display="inline-block"; copyKeyBtn.textContent="Copy Key";
        } else if(data.error){
            apiKeyDisplay.className="error";
            apiKeyDisplay.textContent = `❌ Error: ${data.error}`;
            copyKeyBtn.style.display="none";
        }
    } catch(err){
        apiKeyDisplay.className="error";
        apiKeyDisplay.textContent = "❌ Error generating API key.";
        copyKeyBtn.style.display="none";
    }
};

copyKeyBtn.onclick = () => {
    const keyText = apiKeyDisplay.textContent.split(":")[1]?.split("(")[0].trim();
    if(keyText){
        navigator.clipboard.writeText(keyText);
        copyKeyBtn.textContent="Copied!";
        setTimeout(()=>{copyKeyBtn.textContent="Copy Key";},2000);
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
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)
