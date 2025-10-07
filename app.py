from flask import Flask, send_file, request, jsonify
import os
import random, string
from captcha.image import ImageCaptcha
import io
from datetime import datetime, timedelta

app = Flask(__name__)

# Store generated CAPTCHAs with timestamps
CAPTCHA_STORE = {}

# Auto-expiry time for CAPTCHAs (e.g., 5 minutes)
CAPTCHA_EXPIRY = timedelta(minutes=5)

def cleanup_captchas():
    """Remove expired CAPTCHAs"""
    now = datetime.utcnow()
    expired = [cid for cid, val in CAPTCHA_STORE.items() if val["time"] < now]
    for cid in expired:
        del CAPTCHA_STORE[cid]

@app.route("/")
def index():
    """Home endpoint showing live service info"""
    cleanup_captchas()
    return jsonify({
        "service": "QuickCaptcha",
        "status": "live",
        "active_captchas": len(CAPTCHA_STORE),
        "endpoints": ["/captcha", "/verify (POST)"],
        "message": "QuickCaptcha service is live! Use /captcha to get a CAPTCHA."
    })

@app.route("/captcha")
def generate_captcha():
    """Generate a CAPTCHA image and return it with an ID"""
    cleanup_captchas()

    # Generate random 5-character string
    text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))

    # Generate CAPTCHA image
    image = ImageCaptcha()
    data = io.BytesIO()
    image.write(text, data)
    data.seek(0)

    # Create random ID and store the text with timestamp
    captcha_id = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    CAPTCHA_STORE[captcha_id] = {"text": text, "time": datetime.utcnow()}

    # Return image with ID in header
    response = send_file(data, mimetype='image/png')
    response.headers["X-Captcha-ID"] = captcha_id
    return response

@app.route("/verify", methods=["POST"])
def verify():
    """Verify user input against the stored CAPTCHA"""
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
