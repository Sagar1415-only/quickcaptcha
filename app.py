from flask import Flask, request, jsonify, render_template_string, send_file
import os, random, string, io
from captcha.image import ImageCaptcha

app = Flask(__name__)

CAPTCHA_STORE = {}

HTML_TEMPLATE = """
<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>QuickCaptcha</title>
<style>
    body {
        margin: 0;
        font-family: "Segoe UI", Tahoma, Geneva, Verdana, sans-serif;
        background: linear-gradient(135deg, #dfe9f3 0%, #ffffff 100%);
        height: 100vh;
        display: flex;
        justify-content: center;
        align-items: center;
    }
    .captcha-box {
        background: #fff;
        border-radius: 12px;
        box-shadow: 0 6px 18px rgba(0, 0, 0, 0.1);
        padding: 35px 30px;
        text-align: center;
        width: 350px;
    }
    h1 {
        font-size: 1.7rem;
        color: #2c3e50;
        margin-bottom: 25px;
    }
    img {
        border: 1px solid #ddd;
        border-radius: 8px;
        margin-bottom: 15px;
        width: 100%;
        max-width: 260px;
        height: auto;
        box-shadow: 0 4px 10px rgba(0,0,0,0.1);
    }
    input[type="text"] {
        width: 100%;
        padding: 10px;
        font-size: 1rem;
        border: 1px solid #ccc;
        border-radius: 6px;
        margin-bottom: 15px;
        transition: all 0.2s ease-in-out;
    }
    input[type="text"]:focus {
        border-color: #3498db;
        box-shadow: 0 0 5px rgba(52, 152, 219, 0.4);
        outline: none;
    }
    button {
        background-color: #3498db;
        color: white;
        border: none;
        border-radius: 6px;
        padding: 10px 0;
        width: 100%;
        font-size: 1rem;
        font-weight: 500;
        cursor: pointer;
        transition: 0.2s ease-in-out;
    }
    button:hover {
        background-color: #2980b9;
    }
    .refresh {
        color: #3498db;
        font-size: 0.9rem;
        text-decoration: none;
        display: block;
        margin-top: 10px;
    }
    .refresh:hover {
        color: #21618c;
    }
    .message {
        margin-top: 15px;
        font-weight: 600;
        color: {{ color | default('#2c3e50') }};
    }
</style>
</head>
<body>
<div class="captcha-box">
    <h1>QuickCaptcha</h1>
    <form method="POST" action="/verify">
        <img src="/captcha" alt="CAPTCHA" id="captcha-image">
        <a href="#" class="refresh" onclick="refreshCaptcha(event)">🔄 Refresh CAPTCHA</a>
        <input type="text" name="captcha" placeholder="Enter CAPTCHA" required>
        <button type="submit">Verify</button>
    </form>
    {% if message %}
    <p class="message" style="color: {{ color }}">{{ message }}</p>
    {% endif %}
</div>

<script>
function refreshCaptcha(e) {
    e.preventDefault();
    document.getElementById("captcha-image").src = "/captcha?" + new Date().getTime();
}
</script>
</body>
</html>
"""

@app.route("/")
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route("/captcha")
def captcha():
    text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    image = ImageCaptcha()
    data = io.BytesIO()
    image.write(text, data)
    data.seek(0)
    CAPTCHA_STORE['current'] = text
    return send_file(data, mimetype='image/png')

@app.route("/verify", methods=["POST"])
def verify():
    user_input = request.form.get("captcha", "").strip().upper()
    correct = CAPTCHA_STORE.get('current', "")

    if user_input == correct:
        message = "✅ CAPTCHA Verified Successfully!"
        color = "#2ecc71"
    else:
        message = "❌ Incorrect CAPTCHA. Try Again!"
        color = "#e74c3c"

    return render_template_string(HTML_TEMPLATE, message=message, color=color)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
