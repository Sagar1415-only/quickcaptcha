from flask import Flask, send_file, request, jsonify, render_template_string
import os
import random, string
from captcha.image import ImageCaptcha
import io

app = Flask(__name__)

CAPTCHA_STORE = {}

# HTML template with simple CSS
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>QuickCaptcha Service</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: linear-gradient(to right, #4facfe, #00f2fe);
            text-align: center;
            padding: 50px;
            color: #fff;
        }
        h1 { margin-bottom: 30px; }
        button {
            padding: 10px 20px;
            font-size: 16px;
            margin: 10px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            background-color: #fff;
            color: #4facfe;
            font-weight: bold;
        }
        img { margin-top: 20px; }
        input { padding: 8px; border-radius: 5px; border: none; width: 150px; }
        .message { margin-top: 15px; font-weight: bold; }
    </style>
</head>
<body>
    <h1>QuickCaptcha Service</h1>
    <p>Click "Generate CAPTCHA" to get a CAPTCHA:</p>
    <button onclick="generateCaptcha()">Generate CAPTCHA</button>
    <div id="captchaDiv" style="margin-top:20px;"></div>
    <div id="verifyDiv" style="margin-top:20px; display:none;">
        <input type="text" id="captchaInput" placeholder="Enter CAPTCHA">
        <button onclick="verifyCaptcha()">Verify</button>
    </div>
    <div class="message" id="message"></div>

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
            document.getElementById("captchaDiv").innerHTML = `<img src="${url}" alt="CAPTCHA">`;
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
            return jsonify({"success": True, "message": "CAPTCHA verified!"})
        else:
            return jsonify({"success": False, "message": "Incorrect CAPTCHA!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
