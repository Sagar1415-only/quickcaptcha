from flask import Flask, request, jsonify, render_template, send_file, redirect, url_for, session
import os, random, string, io, uuid, requests
from captcha.image import ImageCaptcha
from datetime import datetime

# ---------------- CONFIG ----------------
app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey123")
FREE_LIMIT = 100
ADMIN_EMAIL = "sagarms121415@gmail.com"
DASHBOARD_PASSWORD = os.environ.get("DASHBOARD_PASSWORD", "sagar@123")
BREVO_API_KEY = os.environ.get("BREVO_API_KEY")  # Brevo API key
EMAIL_USER = os.environ.get("EMAIL_USER")  # Verified sender email in Brevo

# Store API usage and captchas in memory
api_keys = {}  # { api_key: {email, count, emailed} }
CAPTCHA_STORE = {}

# ---------------- EMAIL FUNCTION ----------------
def send_email(to_email, subject, body):
    if not BREVO_API_KEY or not EMAIL_USER:
        print("⚠️ Email credentials not set")
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
        return response.status_code in [200, 201, 202]
    except Exception as e:
        print("Email error:", e)
        return False

# ---------------- ROUTES ----------------

@app.route("/")
def index():
    return render_template("index.html")

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
    user_input = request.form.get("captcha_input", "").strip().upper()
    correct = CAPTCHA_STORE.get("current", "")
    success = user_input == correct
    message = "✅ CAPTCHA Verified Successfully!" if success else "❌ Incorrect CAPTCHA. Try Again!"
    color = "#2ecc71" if success else "#e74c3c"
    return render_template("index.html", message=message, color=color)

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
    if send_email(email, "Your QuickCaptcha API Key", f"Hello {email},\n\nYour free API key is: {key}\nLimit: {FREE_LIMIT}"):
        api_keys[key]["emailed"] = True
    send_email(ADMIN_EMAIL, "New API Registration", f"User: {email}\nAPI Key: {key}\nTime: {datetime.now()}")
    return jsonify({"api_key": key, "free_limit": FREE_LIMIT})

@app.route("/subscribe", methods=["POST"])
def subscribe():
    email = request.form.get("email", "").strip().lower()
    if email:
        with open("subscribers.csv", "a") as f:
            f.write(f"{email},{datetime.now().isoformat()}\n")
    return redirect("/")

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

# ---------------- RUN ----------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 10000))
    app.run(host="0.0.0.0", port=port)


HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="description" content="QuickCaptcha — Lightweight, privacy-first CAPTCHA API for developers. Easy integration, REST endpoints, free tier, and admin dashboard.">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>QuickCaptcha — Lightweight CAPTCHA API</title>
<link rel="icon" href="/free_trial/assets/favicon.ico" />
<style>
body { font-family:'Segoe UI', sans-serif; margin:0; padding:0; background: linear-gradient(to right,#4facfe,#00f2fe); display:flex; flex-direction:column; align-items:center; min-height:100vh;}
header { text-align:center; color:white; margin-top:30px;}
header h1 { font-size:2.5rem; margin-bottom:10px;}
header p { font-size:1.1rem; margin-bottom:20px;}
.container { background:white; padding:30px; border-radius:12px; box-shadow:0 6px 18px rgba(0,0,0,0.1); margin:20px; text-align:center; width:320px; max-width:90%;}
button { padding:10px 20px; border:none; border-radius:8px; cursor:pointer; background:#4facfe; color:white; font-weight:bold; transition:.3s; margin:5px;}
button:hover { background:#00c3ff;}
input { padding:8px; border-radius:6px; border:1px solid #ccc; width:160px; margin:5px 0;}
img { margin:15px 0; border-radius:6px; border:1px solid #ccc;}
.message { margin-top:10px; font-weight:bold;}
footer { margin-top:20px; font-size:13px; color:#eee; text-align:center;}
a { color:#4facfe; text-decoration:none; font-weight:bold;}
.modal { display:none; position:fixed; z-index:1000; left:0; top:0; width:100%; height:100%; overflow:auto; background-color:rgba(0,0,0,0.5);}
.modal-content { background:#fff; margin:10% auto; padding:20px; border-radius:8px; width:300px; text-align:center;}
.close { float:right; font-size:28px; font-weight:bold; color:#aaa; cursor:pointer;}
.close:hover { color:#000;}
#copyKeyBtn { display:none; margin-top:10px; padding:8px 15px; background:#3498db; color:white; border:none; border-radius:6px; cursor:pointer;}
#copyKeyBtn:hover { background:#2980b9;}
#apiKeyDisplay.success { color:#2ecc71; font-weight:600; word-break:break-all; margin-top:10px;}
#apiKeyDisplay.error { color:#e74c3c; font-weight:600; word-break:break-all; margin-top:10px;}
body{font-family:'Segoe UI',sans-serif;margin:0;padding:0;background:linear-gradient(to right,#4facfe,#00f2fe);display:flex;flex-direction:column;align-items:center;min-height:100vh;}
header{text-align:center;color:white;margin-top:20px;}
.logo{border-radius:8px;}
h1{font-size:2.4rem;margin:8px 0;}
.tagline{font-size:1.05rem;margin-bottom:8px;color:#eef7ff;}
.container{background:white;padding:24px;border-radius:12px;box-shadow:0 6px 18px rgba(0,0,0,0.08);margin:16px;text-align:center;width:340px;max-width:92%;}
button{padding:10px 18px;border:none;border-radius:8px;cursor:pointer;background:#4facfe;color:white;font-weight:bold;transition:.18s;margin:6px;}
button:hover{background:#00c3ff;}
input{padding:8px;border-radius:6px;border:1px solid #ccc;width:170px;margin:6px 0;}
img{margin:14px 0;border-radius:8px;border:1px solid #eee;}
.message{margin-top:10px;font-weight:600;}
footer{margin-top:18px;font-size:13px;color:#eef7ff;text-align:center;margin-bottom:18px;}
.modal{display:none;position:fixed;z-index:1000;left:0;top:0;width:100%;height:100%;overflow:auto;background-color:rgba(0,0,0,0.45);}
.modal-content{background:#fff;margin:8% auto;padding:18px;border-radius:8px;width:320px;text-align:center;}
.close{float:right;font-size:22px;color:#aaa;cursor:pointer;}
.small{font-size:13px;color:#666;margin-top:8px;}
.stripe-disabled{opacity:0.5;pointer-events:none;}
</style>
</head>
<body>
<header>
<img src="/free_trial/assets/sagar1.png" width="72" class="logo"><br>
<h1>QuickCaptcha</h1>
<p>Lightweight, privacy-first CAPTCHA API — free tier available.</p>
<a href="#demo"><button>Try Demo</button></a>
<a href="#pricing"><button>Subscribe</button></a>
<div class="tagline">Lightweight, privacy-first CAPTCHA API — easy integration, free tier, admin dashboard.</div>
</header>

<!-- Demo -->
<div class="container" id="demo">
<h2>Live CAPTCHA Demo</h2>
<p class="small">Click generate, type the letters, verify.</p>
<button onclick="generateCaptcha()">Generate CAPTCHA</button>
<div id="captchaDiv"></div>
<div id="verifyDiv" style="display:none;">
<input type="text" id="captchaInput" placeholder="Enter CAPTCHA">
<button onclick="verifyCaptcha()">Verify</button>
</div>
<div class="message" id="message"></div>
<div class="message" id="message">{{ message }}</div>
</div>

<!-- Features + Demo GIF -->
<div class="container">
<h2>Features</h2>
<h3 style="margin-top:0">Features</h3>
<ul style="text-align:left;">
<li>Simple REST API verification</li>
<li>Self-hostable & privacy-friendly</li>
<li>Customizable appearance & language</li>
<li>Free tier with API key generation</li>
<li>Admin dashboard to track usage</li>
<li>Simple REST API for CAPTCHA verification</li>
<li>Privacy-friendly — no tracking</li>
<li>Self-hostable or API-as-a-Service</li>
<li>Customizable language, theme, and size</li>
<li>Free tier + Admin dashboard</li>
</ul>
<img src="/free_trial/assets/sagar2.gif" alt="Demo" width="260">
</div>

<!-- Pricing / Subscribe -->
<div class="container" id="pricing">
<h2>Pricing Preview</h2>
<p>Free Tier: 1,000 monthly requests — always free.</p>
<p>Starter & Pro plans coming soon — subscribe for updates!</p>
<form action="/subscribe" method="post">
<input type="email" name="email" placeholder="Enter your email" required>
<h3 style="margin-top:0">Pricing Preview</h3>
<p>Free Tier: {{ free_limit if free_limit else "1000" }} monthly requests — always free.</p>
<p class="small">Starter & Pro launching soon — subscribe for updates.</p>
<form action="/subscribe" method="post" style="margin-top:8px;">
<input type="email" name="email" placeholder="Your email" required>
<button type="submit">Subscribe</button>
</form>
<div style="margin-top:12px;">
<button id="openKeyModalBtn">Get Free API Key</button>
<button id="stripeStarterBtn">Buy Starter</button>
<button id="stripeProBtn">Buy Pro</button>
</div>
</div>

<footer>© 2025 QuickCaptcha API • <a href="https://github.com/your/repo" target="_blank">GitHub Source</a></footer>
<footer>© 2025 QuickCaptcha • <a href="https://github.com/your/repo" target="_blank" style="color:#fff">GitHub</a></footer>

<!-- Modal: Generate Free Key -->
<div id="keyModal" class="modal">
<div class="modal-content">
<span class="close" id="closeKeyModal">&times;</span>
<h3>Get Free API Key</h3>
<input type="email" id="modalEmail" placeholder="Your email">
<button id="generateKeyBtn">Generate Key</button>
<p id="apiKeyDisplay" class="small"></p>
<button id="copyKeyBtn" style="display:none">Copy Key</button>
</div>
</div>

<script>
let captchaId = "";
function generateCaptcha() {
    fetch("/captcha").then(r=>r.blob()).then(blob=>{
        const url = URL.createObjectURL(blob);
        document.getElementById("captchaDiv").innerHTML = `<img src="${url}" width="200" height="70">`;
        document.getElementById("verifyDiv").style.display = "block";
        document.getElementById("message").innerText = "";
    });
// --- CAPTCHA demo logic (unchanged behavior) ---
function generateCaptcha(){
  fetch("/captcha").then(r=>r.blob()).then(b=>{
    const u = URL.createObjectURL(b);
    document.getElementById("captchaDiv").innerHTML = `<img src="${u}" width="220" height="70">`;
    document.getElementById("verifyDiv").style.display = "block";
    document.getElementById("message").innerText = "";
  });
}
function verifyCaptcha() {
    const userInput = document.getElementById("captchaInput").value;
    fetch("/verify", { method:"POST", headers:{"Content-Type":"application/x-www-form-urlencoded"}, body:`captcha=${userInput}` })
    .then(r=>r.text()).then(html=>{
        document.getElementById("message").innerText = html;
function verifyCaptcha(){
  const user = document.getElementById("captchaInput").value;
  fetch("/verify", { method:"POST", headers:{"Content-Type":"application/x-www-form-urlencoded"}, body:`captcha=${encodeURIComponent(user)}` })
  .then(r=>r.text()).then(html=>{
    // simple parse to show success/fail — server returns whole HTML, but contains emojis
    if(html.includes("✅")) {
      document.getElementById("message").innerText="✅ CAPTCHA verified!";
    } else if(html.includes("❌")) {
      document.getElementById("message").innerText="❌ Incorrect CAPTCHA.";
    } else {
      document.getElementById("message").innerText="Verification result received.";
    }
  });
}

// --- Modal for Generate Free API Key ---
const keyModal = document.getElementById("keyModal");
document.getElementById("openKeyModalBtn").onclick = ()=> keyModal.style.display = "block";
document.getElementById("closeKeyModal").onclick = ()=> keyModal.style.display = "none";
window.onclick = (e)=> { if(e.target == keyModal) keyModal.style.display = "none"; };

document.getElementById("generateKeyBtn").onclick = async ()=>{
  const email = document.getElementById("modalEmail").value.trim();
  const disp = document.getElementById("apiKeyDisplay");
  if(!email){ disp.innerText = "Enter an email"; disp.style.color = "red"; return; }
  disp.innerText = "Generating...";
  try{
    const res = await fetch("/generate-free-key", {
      method: "POST", headers: {"Content-Type":"application/json"}, body: JSON.stringify({email})
    });
    const data = await res.json();
    if(data.api_key){ disp.innerText = `✅ Your API Key: ${data.api_key} (limit: ${data.free_limit})`; disp.style.color="green";
      const copyBtn = document.getElementById("copyKeyBtn"); copyBtn.style.display="inline-block";
      copyBtn.onclick = ()=>{ navigator.clipboard.writeText(data.api_key); copyBtn.innerText="Copied!"; setTimeout(()=>copyBtn.innerText="Copy Key",2000); };
    } else { disp.innerText = `❌ Error: ${data.error||"unknown"}`; disp.style.color="red"; }
  }catch(err){ disp.innerText = "❌ Network error"; disp.style.color="red"; }
};

// --- Stripe starter/pro buttons (invoke /create-checkout-session) ---
async function startStripe(plan){
  const url = "/create-checkout-session";
  try{
    const res = await fetch(url, { method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({plan})});
    const data = await res.json();
    if(data.url) { window.location = data.url; }
    else if(data.id && data.url){ window.location = data.url; }
    else { alert("Stripe not configured or error: " + (data.error||"unknown")); }
  }catch(e){ alert("Stripe error: " + e.message); }
}
document.getElementById("stripeStarterBtn").onclick = ()=> startStripe("starter");
document.getElementById("stripeProBtn").onclick = ()=> startStripe("pro");

// If Stripe is not configured, gray out the buttons
fetch("/stripe-status").catch(()=>{}); // harmless
</script>
</body>
</html>
"""

# ---------------- DASHBOARD HTML ----------------
DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta charset="utf-8">
<title>QuickCaptcha Dashboard</title>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
body{background:#f4f6f9;font-family:sans-serif;margin:0;padding:0;}
.container{max-width:900px;margin:50px auto;background:#fff;padding:30px;border-radius:12px;box-shadow:0 6px 18px rgba(0,0,0,0.1);}
body{font-family:sans-serif;background:#f4f6f9;margin:0;padding:0;}
.container{max-width:1000px;margin:30px auto;background:#fff;padding:20px;border-radius:8px;box-shadow:0 6px 18px rgba(0,0,0,0.08);}
h1{text-align:center;color:#2c3e50;}
table{width:100%;border-collapse:collapse;margin-top:20px;}
th,td{border:1px solid #ddd;padding:10px;text-align:center;}
table{width:100%;border-collapse:collapse;margin-top:12px;}
th,td{border:1px solid #ddd;padding:10px;text-align:left;}
th{background:#3498db;color:#fff;}
tr:nth-child(even){background:#f2f2f2;}
button{padding:10px 20px;border:none;border-radius:6px;background:#2980b9;color:#fff;cursor:pointer;margin:10px 0;}
button:hover{background:#21618c;}
.rowcenter{text-align:center;}
.small{font-size:13px;color:#666;}
</style>
</head>
<body>
<div class="container">
<h1>QuickCaptcha Dashboard</h1>
<button onclick="loadData()">Retrieve Data</button>
<table id="apiTable">
<h1>QuickCaptcha Admin</h1>
<p class="small">API Key summary</p>
<table>
<tr><th>Email</th><th>API Key</th><th>Used</th><th>Remaining</th></tr>
{% for k,v in api_keys.items() %}
<tr>
<td>{{v['email']}}</td>
<td>{{k}}</td>
<td>{{v['count']}}</td>
<td>{{free_limit - v['count']}}</td>
<td>{{ v['email'] }}</td>
<td style="word-break:break-all">{{ k }}</td>
<td>{{ v['count'] }}</td>
<td>{{ free_limit - v['count'] }}</td>
</tr>
{% endfor %}
</table>
<br><center><a href="/logout">Logout</a></center>

<h2 style="margin-top:22px">Usage (last 7 days)</h2>
<table>
<tr><th>Date</th><th>Total Requests</th></tr>
{% for row in analytics %}
<tr><td>{{ row.date }}</td><td>{{ row.total }}</td></tr>
{% endfor %}
</table>

<br><div class="rowcenter"><a href="/logout">Logout</a></div>
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
    app.run(host="0.0.0.0", port=port, debug=True)


