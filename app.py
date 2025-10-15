import os
import uuid
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for

# ---------------- CONFIG ----------------
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey")

FREE_LIMIT = 50
DASHBOARD_PASSWORD = "admin123"
api_keys = {}  # Store API keys

# ---------------- FUNCTIONS ----------------
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

# ---------------- ROUTES ----------------
@app.route("/generate-free-key", methods=["POST"])
def generate_free_key():
    email = (request.json.get("email") or "").strip().lower()
    if not email:
        return jsonify({"error": "Email required"}), 400
    key = str(uuid.uuid4())
    api_keys[key] = {"email": email, "count": 0, "emailed": False, "last_reset": datetime.now().isoformat()}
    reset_monthly_limits()

    # Placeholder for sending email
    print(f"[EMAIL] Sending free API key to {email}: {key}")

    return jsonify({"api_key": key, "free_limit": FREE_LIMIT})


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

# ---------------- HTML TEMPLATE ----------------
HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>QuickCaptcha</title>
<link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;600;700&display=swap" rel="stylesheet">
<style>
:root{
 --bg:#f4f7fb; --card:#ffffff; --muted:#6b7280; --accent:#2563eb; --accent-dark:#1e40af;
 --success:#16a34a; --danger:#dc2626;
}
*{box-sizing:border-box}
body{margin:0;font-family:Inter,system-ui,Segoe UI,Roboto,'Helvetica Neue',Arial;background:var(--bg);color:#0f172a}
.container{max-width:1100px;margin:36px auto;padding:20px}
.header{display:flex;align-items:center;justify-content:space-between;gap:16px;margin-bottom:18px}
.title{display:flex;flex-direction:column}
.title h1{margin:0;font-size:20px}
.title p{margin:2px 0 0;color:var(--muted);font-size:13px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:20px}
.card{background:var(--card);border-radius:12px;padding:20px;box-shadow:0 8px 30px rgba(2,6,23,0.06);overflow:hidden}
.card h2{margin:0 0 8px;font-size:18px}
.card p.muted{color:var(--muted);margin:0 0 12px;font-size:13px}
.captcha-wrap{display:flex;flex-direction:column;align-items:center;gap:12px}
.captcha-img{width:260px;max-width:100%;border-radius:8px;border:1px solid #e6e7ee;box-shadow:0 6px 18px rgba(16,24,40,0.04)}
.controls{display:flex;gap:10px;align-items:center}
.input{padding:10px;border-radius:8px;border:1px solid #e6e7ee;min-width:140px}
.btn{background:var(--accent);color:#fff;padding:9px 12px;border-radius:8px;border:0;cursor:pointer;font-weight:600}
.btn:hover{background:var(--accent-dark)}
.btn-ghost{background:transparent;border:1px solid #e6e7ee;color:#0f172a}
.msg{margin-top:8px;font-weight:600}
.msg.success{color:var(--success)}
.msg.error{color:var(--danger)}
.small{font-size:13px;color:var(--muted);margin-top:6px}

/* Pro table */
.table-wrap{overflow:auto;border-radius:8px;border:1px solid #eef2f6}
.pro-table{width:100%;border-collapse:collapse;font-size:14px}
.pro-table thead th{background:linear-gradient(90deg,#eef2ff,#f8fbff);text-align:left;padding:12px 16px;font-weight:600;color:#0f172a}
.pro-table tbody td{padding:12px 16px;border-top:1px solid #f1f5f9;background:#fff}
.pro-table tbody tr:nth-child(even) td{background:#fbfdff}
.pro-cta{display:flex;gap:10px;align-items:center;margin-top:12px;flex-wrap:wrap}
.form-input{padding:10px;border-radius:8px;border:1px solid #e6e7ee;width:100%}
.form-row{display:flex;gap:8px}
.pro-card .label{font-size:13px;color:var(--muted);margin-bottom:6px}

/* responsive tweaks */
@media (max-width:520px){
 .controls{flex-direction:column}
 .form-row{flex-direction:column}
}
</style>
</head>
<body>
<div class="container">
 <div class="header">
   <div class="title">
     <h1>QuickCaptcha</h1>
     <p>Secure · Simple · Reliable</p>
   </div>
   <div style="text-align:right">
     <small style="color:var(--muted)">Limit (Free): <strong>{{FREE_LIMIT}}</strong></small>
   </div>
 </div>

 <div class="grid">
   <!-- Free Plan / Captcha Card -->
   <div class="card">
     <h2>Free Plan</h2>
     <p class="muted">For testing and small projects — generate a free API key and try the captcha demo.</p>

     <div class="captcha-wrap">
       <img id="captcha-image" class="captcha-img" src="/captcha" alt="captcha">
       <div class="controls">
         <input id="captchaInput" class="input" placeholder="Enter Captcha">
         <button id="verifyBtn" class="btn">Verify</button>
         <button id="refreshBtn" class="btn btn-ghost" title="Refresh Captcha">🔄 Refresh</button>
       </div>

       <div id="verifyMessage" class="msg small" aria-live="polite"></div>

       <div style="width:100%;margin-top:14px">
         <button id="openFreeModal" class="btn" style="width:100%">Generate Free API Key</button>
       </div>
     </div>
   </div>

   <!-- Pro Plan Card -->
   <div class="card pro-card">
     <h2>Pro Plan</h2>
     <p class="muted">For startups and businesses — higher limits, priority support, custom styling.</p>

     <!-- Pro Plans Table -->
     <div class="table-wrap" style="margin-top:12px">
       <table class="pro-table" aria-label="Pro Plans">
         <thead>
           <tr>
             <th>Plan</th>
             <th>Limit</th>
             <th>Price</th>
             <th>Action</th>
           </tr>
         </thead>
         <tbody>
           <tr>
             <td>Basic</td>
             <td>Minimal customization (background/logo)</td>
             <td>₹100 / $1.5</td>
             <td><button class="btn selectProBtn" data-plan="Basic" data-price="100">Select</button></td>
           </tr>
           <tr>
             <td>Starter</td>
             <td>1,000 / month</td>
             <td>₹199 / $3</td>
             <td><button class="btn selectProBtn" data-plan="Starter" data-price="199">Select</button></td>
           </tr>
           <tr>
             <td>Growth</td>
             <td>5,000 / month</td>
             <td>₹599 / $8</td>
             <td><button class="btn selectProBtn" data-plan="Growth" data-price="599">Select</button></td>
           </tr>
           <tr>
             <td>Business</td>
             <td>20,000+ / month</td>
             <td>₹1499 / $18</td>
             <td><button class="btn selectProBtn" data-plan="Business" data-price="1499">Select</button></td>
           </tr>
         </tbody>
       </table>
     </div>

     <!-- Request Form + Description + Payment -->
     <div style="margin-top:16px">
       <div class="label">Your Email</div>
       <input id="proEmail" class="form-input" placeholder="Your business email">
       
       <div class="label" style="margin-top:8px;">Describe your requirements</div>
       <textarea id="proDescription" class="form-input" placeholder="Describe what you need..." rows="4"></textarea>
       
       <div class="pro-cta" style="margin-top:8px;">
         <button id="proPayBtn" class="btn" disabled>Pay 50% & Submit Request</button>
         <div id="proStatus" class="small" aria-live="polite"></div>
       </div>
     </div>
   </div>
 </div>

 <!-- Free API Key modal -->
 <div id="freeModal" style="display:none;position:fixed;inset:0;background:rgba(10,12,20,0.6);align-items:center;justify-content:center;">
   <div style="background:#fff;border-radius:10px;padding:20px;max-width:420px;margin:auto;box-shadow:0 8px 30px rgba(2,6,23,0.12);">
     <h3 style="margin:0 0 8px">Get Your Free API Key</h3>
     <p style="margin:0 0 12px;color:#6b7280;font-size:13px">Enter your email to receive a free API key (limit {{FREE_LIMIT}} requests).</p>
     <input id="emailInput" type="email" placeholder="your@email.com" style="width:100%;padding:10px;border:1px solid #eef2f6;border-radius:8px;margin-bottom:10px">
     <div style="display:flex;gap:8px">
       <button id="getKeyBtnModal" class="btn" style="flex:1">Generate Key</button>
       <button id="closeModalBtn" class="btn btn-ghost" style="flex:1">Close</button>
     </div>
     <p id="apiKeyDisplay" style="font-weight:600;margin-top:10px;word-break:break-all"></p>
     <button id="copyApiBtn" style="display:none;margin-top:8px;padding:8px 12px;border-radius:8px;border:0;background:#0f172a;color:#fff;cursor:pointer">📋 Copy API Key</button>
   </div>
 </div>

<script>
let selectedPlan = null;
let selectedPrice = 0;

// Plan selection buttons
document.querySelectorAll(".selectProBtn").forEach(btn => {
  btn.addEventListener("click", () => {
    selectedPlan = btn.getAttribute("data-plan");
    selectedPrice = parseFloat(btn.getAttribute("data-price"));
    document.getElementById("proPayBtn").disabled = false;
    document.getElementById("proStatus").textContent = `Selected Plan: ${selectedPlan} — ₹${selectedPrice}`;
  });
});

// Payment button
document.getElementById("proPayBtn").addEventListener("click", async () => {
  const email = document.getElementById("proEmail").value.trim();
  const description = document.getElementById("proDescription").value.trim();
  const statusEl = document.getElementById("proStatus");
  statusEl.textContent = "";

  if (!email) { statusEl.textContent = "Enter your email"; return; }
  if (!selectedPlan) { statusEl.textContent = "Select a plan"; return; }
  if (!description) { statusEl.textContent = "Describe your requirements"; return; }

  try {
    const res = await fetch("/request-pro-payment", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ email, plan: selectedPlan, price: selectedPrice, description })
    });
    const data = await res.json();
    if (data.status === "ok") {
      statusEl.style.color = "var(--success)";
      statusEl.textContent = "✅ Request submitted! Payment link sent to your email.";
    } else {
      statusEl.style.color = "var(--danger)";
      statusEl.textContent = "❌ " + (data.error || "Request failed");
    }
  } catch (err) {
    statusEl.style.color = "var(--danger)";
    statusEl.textContent = "⚠️ Error sending request";
  }
});

// refresh captcha
function refreshCaptcha(){
 const img = document.getElementById("captcha-image");
 img.src = "/captcha?"+Date.now();
}
document.getElementById("refreshBtn").addEventListener("click", refreshCaptcha);

// captcha verify
document.getElementById("verifyBtn").addEventListener("click", async () => {
 const input = document.getElementById("captchaInput").value.trim();
 const messageEl = document.getElementById("verifyMessage");
 messageEl.textContent = "";
 if (!input) { messageEl.className="msg error"; messageEl.textContent="Enter captcha"; return; }
 try {
   const res = await fetch("/verify-captcha", {
     method: "POST",
     headers: {"Content-Type":"application/json"},
     body: JSON.stringify({user_input: input})
   });
   const data = await res.json();
   if (data.success) {
     messageEl.className = "msg success";
     messageEl.textContent = "✅ " + (data.message || "Verified successfully!");
   } else {
     messageEl.className = "msg error";
     messageEl.textContent = "❌ " + (data.message || "Incorrect captcha. Try again!");
     refreshCaptcha();
   }
 } catch (err) {
   messageEl.className = "msg";
   messageEl.textContent = "⚠️ Error verifying captcha";
 }
});

// Free API modal handling
const freeModal = document.getElementById("freeModal");
document.getElementById("openFreeModal").addEventListener("click", () => {
 freeModal.style.display = "flex";
 document.getElementById("apiKeyDisplay").textContent = "";
 document.getElementById("copyApiBtn").style.display = "none";
});
document.getElementById("closeModalBtn").addEventListener("click", () => { freeModal.style.display = "none"; });

// generate free key
document.getElementById("getKeyBtnModal").addEventListener("click", async () => {
 const email = (document.getElementById("emailInput").value || "").trim();
 const display = document.getElementById("apiKeyDisplay");
 const copyBtn = document.getElementById("copyApiBtn");
 if (!email) { display.textContent = "Enter email"; return; }
 try {
   const res = await fetch("/generate-free-key", {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({email})});
   const data = await res.json();
   if (data.api_key) {
     display.textContent = "✅ " + data.api_key;
     copyBtn.style.display = "inline-block";
   } else {
     display.textContent = "❌ " + (data.error || "Error generating key");
     copyBtn.style.display = "none";
   }
 } catch (err) {
   display.textContent = "❌ Error";
   copyBtn.style.display = "none";
 }
});

// copy api key
document.getElementById("copyApiBtn").addEventListener("click", async () => {
 const txt = document.getElementById("apiKeyDisplay").textContent.replace("✅ ","").trim();
 if (!txt) { alert("No API key to copy"); return; }
 try {
   await navigator.clipboard.writeText(txt);
   alert("✅ API Key copied to clipboard!");
 } catch (e) {
   alert("⚠️ Clipboard access denied.");
 }
});

// close modal on outside click
window.addEventListener("click", (e) => {
 if (e.target === freeModal) freeModal.style.display = "none";
});
</script>
</body>
</html>
"""

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>Dashboard</title>
<style>
body{background:#f6f7fb;font-family:Inter,system-ui;font-size:14px;color:#0f172a;text-align:center;padding:24px}
.container{max-width:900px;margin:0 auto;background:#fff;padding:20px;border-radius:10px;box-shadow:0 8px 30px rgba(2,6,23,0.06)}
table{margin:auto;border-collapse:collapse;width:100%}
th,td{border:1px solid #e6eef9;padding:10px;text-align:left}
th{background:#f1f8ff;color:#0f172a;font-weight:600}
tr:nth-child(even){background:#fbfdff}
a{color:#2563eb;text-decoration:none}
</style></head><body>
<div class="container">
<h2>QuickCaptcha Dashboard</h2>
<table><tr><th>Email</th><th>API Key</th><th>Used</th><th>Remaining</th></tr>
{% for k,v in api_keys.items() %}
<tr><td>{{v['email']}}</td><td style="word-break:break-all">{{k}}</td><td>{{v['count']}}</td><td>{{free_limit - v['count']}}</td></tr>
{% endfor %}
</table><br><a href="/logout">Logout</a>
</div>
</body></html>"""

# ---------------- RUN ----------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 10000)))
