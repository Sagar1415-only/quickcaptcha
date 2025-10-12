from flask import Flask, request, jsonify, render_template_string
import os
import random, string
from captcha.image import ImageCaptcha
import io
import base64

app = Flask(__name__)

CAPTCHA_STORE = {}

# Complete HTML + CSS + JS frontend with base64 embedded CAPTCHA
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
        font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
        background: linear-gradient(135deg, #f5f7fa, #c3cfe2);
        display: flex;
        justify-content: center;
        align-items: center;
        height: 100vh;
    } 
    .captcha-container {
        background-color: rgba(255, 255, 255, 0.95);
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
        border-radius: 12px;
        text-align: center;
        width: 360px;
        padding: 30px 25px;
    }   
    h1 {
        margin-bottom: 20px;
        color: #333;
        font-size: 1.8rem;
        font-weight: 600;
    }   
    img.captcha {
        border-radius: 8px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.08);
        margin-bottom: 15px;
        max-width: 100%;
        height: auto;
    }   
    input[type="text"] {
        width: 100%;
        padding: 10px 12px;
        border-radius: 6px;
        border: 1px solid #ccc;
        font-size: 1rem;
        margin-bottom: 15px;
        transition: 0.2s all ease;
    }
    input[type="text"]:focus {
        border-color: #4a90e2;
        box-shadow: 0 0 5px rgba(74, 144, 226, 0.5);
        outline: none;
    }
   
    button {
        background-color: #4a90e2;
        color: #fff;
        font-size: 1rem;
        font-weight: 500;
        border: none;
        border-radius: 6px;
        cursor: pointer;
        width: 100%;
        padding: 10px;
        transition: 0.2s all ease;
    }

    button:hover {
        background-color: #357abd;
    }    
    .refresh-captcha {
        display: block;
        margin-top: 10px;
        font-size: 0.9rem;
        color: #4a90e2;
        text-decoration: none;
        transition: 0.2s color ease;
    }

    .refresh-captcha:hover {
        color: #357abd;
    }    
    .error {
        color: #e74c3c;
        font-size: 0.9rem;
        margin-bottom: 10px;
    }
</style>
</head>
<body>
    <div class="captcha-container">
        <h1>Verify You’re Human</h1>
        <!-- CAPTCHA Image -->
        <img src="/captcha" alt="CAPTCHA" class="captcha">
        <!-- Refresh Link -->
        <a href="/captcha" class="refresh-captcha">Refresh CAPTCHA</a>
        <!-- Input Field -->
        <form method="POST" action="/verify">
            <input type="text" name="captcha" placeholder="Enter CAPTCHA" required>
            <button type="submit">Submit</button>
        </form>
    </div>
</body>
</html>
"""

@app.route("/captcha")
def generate_captcha():
    # Generate CAPTCHA text
    text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))
    image = ImageCaptcha()
    data = io.BytesIO()
    image.write(text, data)
    data.seek(0)

    # Encode image to base64
    img_base64 = base64.b64encode(data.getvalue()).decode('utf-8')

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
            return jsonify({"success": False, "message": "Invalid CAPTCHA ID!"})

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
