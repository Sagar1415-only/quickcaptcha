from flask import Flask, send_file
import random, string
from captcha.image import ImageCaptcha
import io

app = Flask(__name__)

@app.route("/captcha")
def generate_captcha():
    # Generate random 5-character string
    text = ''.join(random.choices(string.ascii_uppercase + string.digits, k=5))

    # Generate CAPTCHA image
    image = ImageCaptcha()
    data = image.generate(text)

    # Return image as response
    return send_file(data, mimetype='image/png')

@app.route("/verify", methods=["POST"])
def verify():
    # Phase 1 placeholder verification
    return {"success": True, "message": "CAPTCHA verified!"}

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)
