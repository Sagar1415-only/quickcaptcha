from flask import Flask, send_file, request, jsonify, send_from_directory
import os
import random, string
from captcha.image import ImageCaptcha
import io


app = Flask(__name__)

# Store generated CAPTCHAs in memory (temporary storage)
CAPTCHA_STORE = {}

@app.route("/")
def home():
    return jsonify({
        "service": "QuickCaptcha",
        "status": "live",
        "endpoints": ["/captcha", "/verify (POST)"],
        "message": "QuickCaptcha service is live! Use /captcha to get a CAPTCHA."
    })

@app.route("/captcha")
def generate_captcha():
    # Generate random 5-character string
    text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))

    # Generate CAPTCHA image
    image = ImageCaptcha()
    data = io.BytesIO()
    image.write(text, data)
    data.seek(0)

    # Create random ID and store the text
    captcha_id = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
    CAPTCHA_STORE[captcha_id] = text

    # Return image with ID in header
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
@app.route("/")
def home():
    return "QuickCaptcha is live!"


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
