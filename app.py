from flask import Flask, send_file, request, jsonify, render_template_string
import os
import random, string
from captcha.image import ImageCaptcha
import io

app = Flask(__name__)

CAPTCHA_STORE = {}

# Complete HTML + CSS + JS frontend in one file
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
            background: linear-gradient(to right, #4facfe, #00f2fe);
            display: flex;
            justify-content: center;
            align-items: center;
            height: 100vh;
            margin: 0;
        }
        .container {
            background: white;
            color: #333;
            padding: 40px;
            border-radius: 15px;
            box-shadow: 0 8px 20px rgba(0, 0, 0, 0.15);
            text-align: center;
            width: 320px;
        }
        h1 {
            color: #4facfe;
            margin-bottom: 10px;
        }
        p {
            color: #555;
            margin-bottom: 20px;
        }
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
        button:hover {
            background-color: #00c3ff;
        }
        img {
            margin-top: 20px;
            border-radius: 8px;
            border: 1px solid #ccc;
        }
        input {
            padding: 8px;
            border-radius: 6px;
            border: 1px solid #ccc;
            width: 160px;
            margin-right: 5px;
        }
        .message {
            margin-top: 15px;
            font-weight: bold;
        }
        footer {
            margin-top: 25px;
            font-size: 13px;
            color: #666;
        }
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
            document.getElementById("captchaDiv").innerHTML = `<img src="${url}" alt="CAPTCHA" width="200" height="70">`;
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
        document.getElementById("message").style.color = data.success ? "green" : "red";
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
    text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    image = ImageCaptcha()
    data = io.BytesIO()
    image.write(text, data)
    data.seek(0)

    captcha_id = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    CAPTCHA_STORE[captcha_id] = text

    response = send_file(data, mimetype='image/png')
    response.headers["X-Captcha-ID"] = captcha_id
    return response

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
