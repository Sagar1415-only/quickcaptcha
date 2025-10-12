from flask import Flask, request, jsonify, render_template_string
import os
import random, string
from captcha.image import ImageCaptcha
import io
import base64

app = Flask(__name__)

CAPTCHA_STORE = {}

# Complete HTML + CSS + JS frontend
HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>QuickCaptcha</title>
    <style>
        body {
            font-family: 'Poppins', 'Segoe UI', sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            height: 100vh;
            margin: 0;
            display: flex;
            justify-content: center;
            align-items: center;
            color: #333;
        }

        .container {
            background: #ffffff;
            padding: 45px 35px;
            border-radius: 16px;
            box-shadow: 0 12px 30px rgba(0,0,0,0.2);
            text-align: center;
            width: 340px;
            transition: 0.4s ease;
        }

        h1 {
            font-size: 28px;
            margin-bottom: 8px;
            color: #5a67d8;
        }

        p {
            font-size: 14px;
            color: #666;
            margin-bottom: 25px;
        }

        button {
            background: linear-gradient(90deg, #667eea, #764ba2);
            border: none;
            color: white;
            font-size: 15px;
            font-weight: 600;
            padding: 10px 24px;
            border-radius: 8px;
            cursor: pointer;
            transition: 0.3s;
        }

        button:hover {
            transform: scale(1.05);
            background: linear-gradient(90deg, #5a67d8, #6b46c1);
        }

        input {
            padding: 8px;
            border-radius: 6px;
            border: 1px solid #ccc;
            width: 160px;
            margin-right: 8px;
            text-align: center;
            font-weight: 500;
        }

        img {
            margin-top: 20px;
            border-radius: 8px;
            border: 1px solid #ddd;
            box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        }

        .message {
            margin-top: 18px;
            font-weight: bold;
            font-size: 14px;
        }

        footer {
            margin-top: 25px;
            font-size: 13px;
            color: #888;
        }

        .fade-in {
            animation: fadeIn 0.4s ease-in;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
    </style>
</head>
<body>
    <div class="container fade-in">
        <h1>QuickCaptcha</h1>
        <p>Simple, secure, and fast CAPTCHA verification</p>
        <button onclick="generateCaptcha()">Generate CAPTCHA</button>
        <div id="captchaDiv"></div>
        <div id="verifyDiv" style="display:none; margin-top:15px;">
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
        .then(response => {
            captchaId = response.headers.get("X-Captcha-ID");
            return response.blob();
        })
        .then(blob => {
            const url = URL.createObjectURL(blob);
            document.getElementById("captchaDiv").innerHTML = 
                `<img src="${url}" alt="CAPTCHA" width="200" height="70">`;
            document.getElementById("verifyDiv").style.display = "block";
            document.getElementById("message").innerText = "";
        });
}

function verifyCaptcha() {
    const userInput = document.getElementById("captchaInput").value;
    fetch("/verify", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({captcha_id: captchaId, user_input: userInput})
    })
    .then(res => res.json())
    .then(data => {
        document.getElementById("message").innerText = data.message;
        document.getElementById("message").style.color = data.success ? "#38a169" : "#e53e3e";
        if(data.success) {
            document.getElementById("verifyDiv").style.display = "none";
            document.getElementById("captchaDiv").innerHTML = "";
        }
    });
}
</script>
</body>
</html>
"""


@app.route("/")
def home():
    return render_template_string(HTML_TEMPLATE)

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

    return jsonify({"captcha_id": captcha_id, "image": img_base64})

@app.route("/verify", methods=["POST"])
def verify():
    try:
        data = request.get_json(force=True)
        captcha_id = data.get("captcha_id")
        user_input = data.get("user_input", "").upper()

        if captcha_id not in CAPTCHA_STORE:
            return jsonify({"success": False, "message": "Invalid CAPTCHA ID!"}), 400

        if CAPTCHA_STORE[captcha_id] == user_input:
            del CAPTCHA_STORE[captcha_id]
            return jsonify({"success": True, "message": "✅ CAPTCHA verified!"})
        else:
            return jsonify({"success": False, "message": "❌ Incorrect CAPTCHA!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
