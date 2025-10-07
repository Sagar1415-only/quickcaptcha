from flask import Flask, send_file, request, jsonify
import random, string
from captcha.image import ImageCaptcha
import io
import os

app = Flask(__name__)

# Store generated CAPTCHAs in memory for Phase 1 (simple approach)
CAPTCHA_STORE = {}

@app.route("/captcha")
def generate_captcha():
    # Generate random 5-character string
    text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))

    # Generate CAPTCHA image
    image = ImageCaptcha()
    data = image.generate(text)

    # Store CAPTCHA text with a random ID
    captcha_id = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    CAPTCHA_STORE[captcha_id] = text

    # Return image as response with ID
    return send_file(data, mimetype='image/png', headers={"X-Captcha-ID": captcha_id})

@app.route("/verify", methods=["POST"])
def verify():
    # Get captcha ID and user input
    data = request.json
    captcha_id = data.get("captcha_id")
    user_input = data.get("user_input", "").upper()

    # Check if captcha exists
    if captcha_id not in CAPTCHA_STORE:
        return jsonify({"success": False, "message": "Invalid CAPTCHA ID!"})

    # Verify user input
    if CAPTCHA_STORE[captcha_id] == user_input:
        del CAPTCHA_STORE[captcha_id]  # Remove after verification
        return jsonify({"success": True, "message": "CAPTCHA verified!"})
    else:
        return jsonify({"success": False, "message": "Incorrect CAPTCHA!"})

if __name__ == "__main__":
    # Use dynamic port for Render
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
