from flask import Flask, send_file, request, jsonify, render_template_string
import os
import random, string
from captcha.image import ImageCaptcha
import io
from datetime import datetime, timedelta

app = Flask(__name__)

CAPTCHA_STORE = {}
CAPTCHA_EXPIRY = timedelta(minutes=5)

def cleanup_captchas():
    now = datetime.utcnow()
    expired = [cid for cid, val in CAPTCHA_STORE.items() if val["time"] < now]
    for cid in expired:
        del CAPTCHA_STORE[cid]

# Simple HTML template for frontend
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>QuickCaptcha</title>
</head>
<body>
    <h1>QuickCaptcha Service</h1>
    <p>Click the button to generate a CAPTCHA:</p>
    <button onclick="getCaptcha()">Generate CAPTCHA</button>
    <div id="captcha-area" style="margin-top:20px;"></div>
    <div id="verify-area" style="margin-top:20px;"></div>
    
    <script>
        let currentCaptchaId = "";
        function getCaptcha() {
            fetch('/captcha')
            .then(response => {
                currentCaptchaId = response.headers.get('X-Captcha-ID');
                return response.blob();
            })
            .then(blob => {
                const url = URL.createObjectURL(blob);
                document.getElementById('captcha-area').innerHTML = 
                    '<img src="' + url + '"><br>' +
                    '<input type="text" id="captcha-input" placeholder="Enter CAPTCHA">' +
                    '<button onclick="verifyCaptcha()">Verify</button>';
                document.getElementById('verify-area').innerHTML = '';
            });
        }

        function verifyCaptcha() {
            const userInput = document.getElementById('captcha-input').value;
            fetch('/verify', {
                method: 'POST',
                headers: {'Content-Type': 'application/json'},
                body: JSON.stringify({captcha_id: currentCaptchaId, user_input: userInput})
            })
            .then(res => res.json())
            .then(data => {
                document.getElementById('verify-area').innerText = data.message;
            });
        }
    </script>
</body>
</html>
"""

@app.route("/")
def home():
    cleanup_captchas()
    return render_template_string(HTML_TEMPLATE)

@app.route("/captcha")
def generate_captcha():
    cleanup_captchas()
    text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    image = ImageCaptcha()
    data = io.BytesIO()
    image.write(text, data)
    data.seek(0)
    captcha_id = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    CAPTCHA_STORE[captcha_id] = {"text": text, "time": datetime.utcnow()}
    response = send_file(data, mimetype='image/png')
    response.headers["X-Captcha-ID"] = captcha_id
    return response

@app.route("/verify", methods=["POST"])
def verify():
    try:
        cleanup_captchas()
        data = request.get_json(force=True)
        captcha_id = data.get("captcha_id")
        user_input = data.get("user_input", "").upper()

        if captcha_id not in CAPTCHA_STORE:
            return jsonify({"success": False, "message": "Invalid or expired CAPTCHA ID!"}), 400

        if CAPTCHA_STORE[captcha_id]["text"] == user_input:
            del CAPTCHA_STORE[captcha_id]
            return jsonify({"success": True, "message": "CAPTCHA verified!"})
        else:
            return jsonify({"success": False, "message": "Incorrect CAPTCHA!"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
