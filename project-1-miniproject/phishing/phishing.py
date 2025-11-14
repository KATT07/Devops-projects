#testing sites:
#use with caution
#https://google.com/ - Good sites
#https://youtube.com/ - Good site with suspicious iframes
#https://cahtgpt.com/ - Bad Sites
#https://expired.badssl.com/ - SSL Expired
#https://аррӏе.com/ (actual link is https://www.xn--80ak6aa92e.com/) - PunyCode

from flask import Flask, request, render_template_string
import io
import sys
import datetime
import socket
import ssl
from urllib.parse import urlparse
import requests
import time

# ======== CONFIG ========
GEMINI_API_KEY = "XXX"
DEFAULT_HTTPS_PORT = 443
SOCKET_CONNECTION_TIMEOUT_SECONDS = 10
WARN_IF_DAYS_LESS_THAN = 7
# ========================

app = Flask(__name__)

# ------------------ SSL Certificate Check ------------------
def make_host_port_pair(endpoint):
    host, _, specified_port = endpoint.partition(':')
    port = int(specified_port or DEFAULT_HTTPS_PORT)
    return host, port


def pluralise(singular, count):
    return f"{count} {singular}{'' if count == 1 else 's'}"


def get_certificate_expiry_date_time(context, host, port):
    with socket.create_connection((host, port), SOCKET_CONNECTION_TIMEOUT_SECONDS) as tcp_socket:
        with context.wrap_socket(tcp_socket, server_hostname=host) as ssl_socket:
            cert_info = ssl_socket.getpeercert()
            exp_date_text = cert_info['notAfter']
            return datetime.datetime.fromtimestamp(ssl.cert_time_to_seconds(exp_date_text), datetime.timezone.utc)


def format_time_remaining(time_remaining):
    day_count = time_remaining.days
    if day_count >= WARN_IF_DAYS_LESS_THAN:
        return pluralise('day', day_count)
    else:
        seconds_unaccounted_for = time_remaining.seconds
        hours = int(seconds_unaccounted_for / 3600)
        minutes = int((seconds_unaccounted_for % 3600) / 60)
        return f"{pluralise('day', day_count)} {pluralise('hour', hours)} {pluralise('min', minutes)}"


def check_certificate(domain):
    context = ssl.create_default_context()
    host, port = make_host_port_pair(domain)
    try:
        expiry_time = get_certificate_expiry_date_time(context, host, port)
    except Exception as ex:
        return {"status": "ERROR", "error": str(ex)}

    time_remaining = expiry_time - datetime.datetime.now(datetime.timezone.utc)
    days_remaining = time_remaining.days
    return {
        "status": "OK" if days_remaining >= WARN_IF_DAYS_LESS_THAN else "WARN",
        "days_remaining": days_remaining,
        "time_remaining": format_time_remaining(time_remaining),
        "expiry_time": expiry_time.strftime("%Y-%m-%d %H:%M:%S UTC"),
    }

# ------------------ ASCII URL Check ------------------
def is_ascii_url(url):
    try:
        url.encode('ascii')
        return True
    except UnicodeEncodeError:
        return False

# ------------------ Gemini AI API ------------------
def call_gemini_api(prompt, model="gemini-2.0-flash", temperature=0.0):
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {"x-goog-api-key": GEMINI_API_KEY, "Content-Type": "application/json"}
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": temperature}
    }
    resp = requests.post(url, headers=headers, json=body)
    if resp.status_code == 429:
        return "⚠️ Rate limit hit (429 Too Many Requests). Try again later."
    resp.raise_for_status()
    data = resp.json()
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        return str(data)

# ------------------ Website Content ------------------
def fetch_website_content(url):
    try:
        resp = requests.get(url, timeout=10)
        resp.raise_for_status()
        return resp.text
    except Exception as e:
        return f"ERROR: {e}"

# ------------------ Main Flow ------------------
def analyze_website(website_url):
    output = io.StringIO()
    sys.stdout = output
    try:
        print(f"\nAnalyzing website: {website_url}")
        parsed = urlparse(website_url)
        domain = parsed.netloc or parsed.path

        ascii_status = is_ascii_url(website_url)
        print(f"\n[1] URL encoding check: {'All ASCII : ✅' if ascii_status else 'Contains non-ASCII : ⚠️ (possible punycode)'}")

        cert_info = check_certificate(domain)
        if cert_info['status'] == 'ERROR':
            print("\n[2] SSL certificate check: ⚠️")
            print(cert_info)
        else:
            print("\n[2] SSL certificate check: ✅")
            print(cert_info)

            html = fetch_website_content(website_url)
            prompt = (
                f"Analyze this website:\n"
                f"URL: {website_url}\n"
                f"HTML Content (first 3000 chars):\n{html[:3000]}\n"
                f"Detect phishing/malicious signs.\n"
                f"Output final conclusion as: Trustworthy✅ / Not Trustworthy⚠️"
            )

            print("\n[3] Gemini AI combined analysis (URL + HTML):")
            start=time.time()
            ai_result = call_gemini_api(prompt)
            end=time.time()
            print(ai_result)
            print(f"Execution time: {end - start:.6f} seconds")
    finally:
        sys.stdout = sys.__stdout__
    return output.getvalue()

# ------------------ Flask Web Interface ------------------
HTML_TEMPLATE = """
<!DOCTYPE html>
<html>
<head>
    <title>Website Analyzer (NIDS)</title>
    <style>
        body { font-family: monospace; margin: 30px; background-color: #111; color: #eee; }
        h1 { color: #4ef; }
        textarea { width: 100%; height: 400px; background-color: #000; color: #0f0; padding: 10px; border: 1px solid #555; }
        input[type=text] { width: 80%; padding: 8px; font-size: 16px; }
        input[type=submit] { padding: 8px 16px; font-size: 16px; background-color: #4ef; border: none; color: #000; cursor: pointer; }
        input[type=submit]:hover { background-color: #0ff; }
        .output-box { margin-top: 20px; }
    </style>
</head>
<body>
    <h1>🔍 Website Analysis Console (Please wait upto 60 seconds for AI analysis)</h1>
    <form method="POST">
        <label>Enter website URL:</label><br>
        <input type="text" name="url" placeholder="https://example.com" required>
        <input type="submit" value="Analyze">
    </form>

    {% if result %}
    <div class="output-box">
        <h2>📄 Output:</h2>
        <textarea readonly>{{ result }}</textarea>
    </div>
    {% endif %}
</body>
</html>
"""

@app.route("/", methods=["GET", "POST"])
def index():
    result = None
    if request.method == "POST":
        url = request.form.get("url").strip()
        result = analyze_website(url)
    return render_template_string(HTML_TEMPLATE, result=result)

# ------------------ Run Server ------------------
if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080, debug=True)
