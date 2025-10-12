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
    <p class="message">{{ message }}</p>
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
