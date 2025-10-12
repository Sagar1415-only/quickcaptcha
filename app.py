from flask import Flask, request, jsonify, render_template_string
import os
import random, string
from captcha.image import ImageCaptcha
import io
import base64
import os

app = Flask(__name__)

CAPTCHA_STORE = {}

# Complete HTML + CSS + JS frontend with base64 embedded CAPTCHA
# Complete HTML + CSS + JS frontend
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QuickCaptcha Service</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(to right, #a16eff, #8a2be2);
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 2;
        }
        .container {
            background: white;
            color: #3b2a5a;
            padding: 50px;
            border-radius: 20px;
            box-shadow: 0 8px 20px rgba(0, 0, 0, 0.15);
            text-align: center;
            width: 330px;
        }
        h1 { color: 4facfe; margin-bottom: 10px; }
        p { color: #3b2a5a; margin-bottom: 20px; }
        button {
            padding: 10px 20px;
            font-size: 15px;
            margin: 10px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            background-color: #4facfe;
            color: white;
            font-weight: bold;
            transition: 0.3s;
        }
        button:hover { background-color: #00c3ff; }
        img { margin-top: 20px; border-radius: 8px; border: 1px solid #ccc; }
        input {
            padding: 8px;
            border-radius: 6px;
            border: 1px solid #ccc;
            width: 160px;
            margin-right: 5px;
        }
        .message { margin-top: 15px; font-weight: bold; }
        footer { margin-top: 25px; font-size: 13px; color: #2a1f3d; }
    </style>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>QuickCaptcha Service</title>
<style>
body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
       background: linear-gradient(to right, #4facfe, #00f2fe); 
       display:flex; justify-content:center; align-items:center; height:100vh; margin:0;}
.container { background:white; color:#333; padding:40px; border-radius:15px;
            box-shadow:0 8px 20px rgba(0,0,0,0.15); text-align:center; width:320px;}
h1 { color:#4facfe; margin-bottom:10px; }
p { color:#555; margin-bottom:20px; }
button { padding:10px 20px; font-size:15px; margin:10px; border:none; border-radius:8px;
         cursor:pointer; background-color:#4facfe; color:white; font-weight:bold; transition:0.3s; }
button:hover { background-color:#00c3ff; }
img { margin-top:20px; border-radius:8px; border:1px solid #ccc; }
input { padding:8px; border-radius:6px; border:1px solid #ccc; width:160px; margin-right:5px; }
.message { margin-top:15px; font-weight:bold; }
footer { margin-top:25px; font-size:13px; color:#666; }
</style>
</head>
<body>
<div class="container">
    <h1>QuickCaptcha</h1>
    <p>Generate and verify simple CAPTCHAs instantly.</p>
    <button onclick="generateCaptcha()">Generate CAPTCHA</button>
    <div id="captchaDiv"></div>
    <div id="verifyDiv" style="display:none;">
        <input type="text" id="captchaInput" placeholder="Enter CAPTCHA">
        <button onclick="verifyCaptcha()">Verify</button>
    </div>
    <div class="message" id="message"></div>
    <footer>© 2025 QuickCaptcha API</footer>
<h1>QuickCaptcha</h1>
<p>Generate and verify simple CAPTCHAs instantly.</p>
<button onclick="generateCaptcha()">Generate CAPTCHA</button>
<div id="captchaDiv"></div>
<div id="verifyDiv" style="display:none;">
<input type="text" id="captchaInput" placeholder="Enter CAPTCHA">
<button onclick="verifyCaptcha()">Verify</button>
</div>
<div class="message" id="message"></div>
<footer>© 2025 QuickCaptcha API</footer>
</div>

<script>
let captchaId = "";

function generateCaptcha() {
   fetch("/captcha")
        .then(res => res.json())
        .then(data => {
            captchaId = data.captcha_id;
            document.getElementById("captchaDiv").innerHTML =
                `<img src="data:image/png;base64,${data.image}" alt="CAPTCHA" width="200" height="70">`;
            document.getElementById("verifyDiv").style.display = "block";
            document.getElementById("message").innerText = "";
        });
    .then(res => res.json())
    .then(data => {
        captchaId = data.captcha_id;
        document.getElementById("captchaDiv").innerHTML = `<img src="data:image/png;base64,${data.image}" width="200" height="70" alt="CAPTCHA">`;
        document.getElementById("verifyDiv").style.display = "block";
        document.getElementById("message").innerText = "";
    });
}

function verifyCaptcha() {
@@ -120,34 +90,38 @@ def home():

@app.route("/captcha")
def generate_captcha():
    # Generate CAPTCHA text
text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
image = ImageCaptcha()
data = io.BytesIO()
image.write(text, data)
data.seek(0)

    # Encode image to base64
    img_base64 = base64.b64encode(data.read()).decode('utf-8')

captcha_id = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
CAPTCHA_STORE[captcha_id] = text

    # Convert image to base64
    img_base64 = base64.b64encode(data.getvalue()).decode('utf-8')

return jsonify({"captcha_id": captcha_id, "image": img_base64})

@app.route("/verify", methods=["POST"])
def verify():
    data = request.get_json()
    captcha_id = data.get("captcha_id")
    user_input = data.get("user_input", "").upper()
    try:
        data = request.get_json(force=True)
        captcha_id = data.get("captcha_id")
        user_input = data.get("user_input", "").upper()

        if captcha_id not in CAPTCHA_STORE:
            return jsonify({"success": False, "message": "Invalid CAPTCHA ID!"}), 400

    if captcha_id not in CAPTCHA_STORE:
        return jsonify({"success": False, "message": "Invalid CAPTCHA ID!"})
    
    if CAPTCHA_STORE[captcha_id] == user_input:
        del CAPTCHA_STORE[captcha_id]
        return jsonify({"success": True, "message": "✅ CAPTCHA verified!"})
    else:
        return jsonify({"success": False, "message": "❌ Incorrect CAPTCHA!"})
        if CAPTCHA_STORE[captcha_id] == user_input:
            del CAPTCHA_STORE[captcha_id]
            return jsonify({"success": True, "message": "✅ CAPTCHA verified!"})
        else:
            return jsonify({"success": False, "message": "❌ Incorrect CAPTCHA!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
port = int(os.environ.get("PORT", 5000))
