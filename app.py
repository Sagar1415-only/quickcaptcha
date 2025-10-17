import os
import uuid
import re
from datetime import datetime
from flask import Flask, request, jsonify, render_template_string, session, redirect, url_for

# ---------------- CONFIG ----------------
app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY", "supersecretkey")

FREE_LIMIT = 50
DASHBOARD_PASSWORD = "admin123"
ADMIN_EMAIL = "sagarms121415@gmail.com"
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


def send_email(to, subject, message):
    """Simulate email sending by printing to logs."""
    print(f"\n============================")
    print(f"📧 TO: {to}")
    print(f"SUBJECT: {subject}")
    print(f"MESSAGE:\n{message}")
    print(f"============================\n")


# ---------------- ROUTES ----------------
@app.route("/generate-free-key", methods=["POST"])
def generate_free_key():
    email = (request.json.get("email") or "").strip().lower()
    if not email:
        return jsonify({"error": "Email required"}), 400
    key = str(uuid.uuid4())
    api_keys[key] = {"email": email, "count": 0, "emailed": False, "last_reset": datetime.now().isoformat()}
    reset_monthly_limits()

    # Send Free API key email
    send_email(
        email,
        "🎉 Your QuickCaptcha Free API Key",
        f"""Hello {email},

Here is your free API key:
{key}

Limit: {FREE_LIMIT} requests per month.

Enjoy using QuickCaptcha!

---
⚡ Need higher limits or business features?

Upgrade to **QuickCaptcha Pro** — get more requests, faster delivery, and premium support.

Choose your preferred monthly plan:

• Lite — ₹100 / $1.5 — Limited customization (color/background only)  
• Starter — 1,000 requests — ₹199 / $3  
• Growth — 5,000 requests — ₹599 / $8  
• Business — 20,000+ requests — ₹1,499 / $18  

💡 The bigger the plan, the more value for your project.

To upgrade:
👉 Visit: https://quickcaptcha.onrender.com  
📩 Or email: {ADMIN_EMAIL}

— QuickCaptcha Team
"""
    )

    return jsonify({"api_key": key, "free_limit": FREE_LIMIT})


@app.route("/request-pro-payment", methods=["POST"])
def request_pro_payment():
    data = request.get_json()
    email = (data.get("email") or "").strip().lower()
    plan = data.get("plan")
    price = data.get("price")
    description = data.get("description", "")

    # Email validation
    if not re.match(r"[^@]+@[^@]+\.[^@]+", email):
        return jsonify({"error": "Invalid email format"}), 400

    # Log the request
    print(f"[ADMIN LOG] Pro API request received from {email}")

    # Send confirmation emails
    send_email(
        email,
        f"💼 QuickCaptcha Pro Plan Request Received — {plan}",
        f"""Hello {email},

Thank you for your interest in QuickCaptcha Pro!

Your selected plan: **{plan}**  
Price: ₹{price}  

Your project description:
{description}

Available customization options:
🎨 Background, logo, and color adjustments.

Current plans:
• Lite — ₹100 / $1.5 — Limited customization (color/background)  
• Starter — ₹199 / $3 — 1,000 requests/month  
• Growth — ₹599 / $8 — 5,000 requests/month  
• Business — ₹1,499 / $18 — 20,000+ requests/month  

Next Step:
💰 Please pay 50% upfront (₹{round(price/2,2)}) to proceed with customization and activation.  
The remaining 50% is due upon completion.

Once payment is done, you'll receive setup confirmation and credentials within 24 hours.

Best regards,  
— QuickCaptcha Pro Team
📩 {ADMIN_EMAIL}
"""
    )

    # Notify admin (you)
    send_email(
        ADMIN_EMAIL,
        f"📩 New Pro Plan Request — {plan}",
        f"""User: {email}
Plan: {plan}
Price: ₹{price}
Description: {description}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Payment pending (50% upfront).  
After payment confirmation, send setup response to user.
"""
    )

    return jsonify({"status": "ok"})


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
.small{font-size:13px;color:#6b7280;margin-top:6px}

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
     <p class="muted">For startups and businesses — higher limits, priority support, and custom styling.</p>

     <!-- Pro Plans Table -->
     <div class="table-wrap" style="margin-top:12px">
       <table class="pro-table" aria-label="Pro Plans">
         <thead>
           <tr><th>Plan</th><th>Limit</th><th>Price</th><th>Action</th></tr>
         </thead>
         <tbody>
           <tr>
             <td>Lite</td>
             <td>Limited customization (color/bg only)</td>
             <td>₹100 / $1.5</td>
             <td><button class="btn selectProBtn" data-plan="Lite" data-price="100">Select</button></td>
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
let selectedPlan=null,selectedPrice=0;

// select plan
document.querySelectorAll(".selectProBtn").forEach(btn=>{
 btn.addEventListener("click",()=>{
   selectedPlan=btn.getAttribute("data-plan");
   selectedPrice=parseFloat(btn.getAttribute("data-price"));
   document.getElementById("proPayBtn").disabled=false;
   document.getElementById("proStatus").style.color="";
   document.getElementById("proStatus").textContent=`Selected: ${selectedPlan} — ₹${selectedPrice}`;
 });
});

// payment
document.getElementById("proPayBtn").addEventListener("click",async()=>{
 const email=document.getElementById("proEmail").value.trim();
 const desc=document.getElementById("proDescription").value.trim();
 const status=document.getElementById("proStatus");

 if(!email){status.textContent="⚠️ Enter your email";return;}
 if(!/^[^@]+@[^@]+\\.[^@]+$/.test(email)){status.textContent="⚠️ Enter a valid email address";return;}
 if(!selectedPlan){status.textContent="⚠️ Select a plan";return;}
 if(!desc){status.textContent="⚠️ Describe your requirements";return;}

 try{
   const res=await fetch("/request-pro-payment",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({email,plan:selectedPlan,price:selectedPrice,description:desc})});
   const data=await res.json();
   if(data.status==="ok"){
     status.style.color="var(--success)";
     status.textContent="✅ Request submitted! Check your email for payment link.";
   }else{
     status.style.color="var(--danger)";
     status.textContent="❌ "+(data.error||"Error submitting request");
   }
 }catch(e){
   status.style.color="var(--danger)";
   status.textContent="⚠️ Request failed";
 }
});
</script>
</body></html>
"""

DASHBOARD_HTML = """<!DOCTYPE html>
<html lang="en"><head><meta charset="UTF-8"><title>Dashboard</title>
<style>
body{background:#f6f7fb;font-family:Inter,system-ui;font-size:14px;color:#0f172a;text-align:center;padding:24px}
.container{max-width:900px;margin:0 auto;background:#fff;padding:20px;border-radius:10px;box-shadow:0 8px 30px rgba(2,6,23,0.1)}
table{width:100%;border-collapse:collapse;margin-top:20px}
th,td{border:1px solid #e6e7ee;padding:8px 10px;text-align:left;font-size:13px}
th{background:#eef2ff}
</style></head>
<body>
<div class="container">
<h2>Admin Dashboard</h2>
<p>Total Keys: {{api_keys|length}}</p>
<table>
<tr><th>Email</th><th>Key</th><th>Usage</th><th>Last Reset</th></tr>
{% for k,v in api_keys.items() %}
<tr>
<td>{{v.email}}</td>
<td>{{k}}</td>
<td>{{v.count}} / {{free_limit}}</td>
<td>{{v.last_reset}}</td>
</tr>
{% endfor %}
</table>
<a href='/logout'>Logout</a>
</div></body></html>"""

@app.route("/")
def home():
    return render_template_string(HTML_TEMPLATE, FREE_LIMIT=FREE_LIMIT)

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=10000)
