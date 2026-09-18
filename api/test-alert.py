"""
api/test-alert.py

TEMPORARY test endpoint — visit this URL in any browser to fire a test
Telegram message. Self-contained (no external packages, no imports from
other project files) so it builds cleanly on Vercel. Delete once confirmed
working.
"""

from http.server import BaseHTTPRequestHandler
import json
import urllib.request
import urllib.error

TELEGRAM_BOT_TOKEN = "8940771064:AAHz6XRKxJrhaciM7yYlHKpGl9xRqGKMPN0"
TELEGRAM_CHAT_ID = "6168326177"


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
        payload = json.dumps({
            "chat_id": TELEGRAM_CHAT_ID,
            "text": "Test alert from Destiny Agent Fleet. If you see this, it's working!",
        }).encode("utf-8")

        req = urllib.request.Request(
            url,
            data=payload,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                body = resp.read().decode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(f'{{"status": "sent", "telegram_response": {body}}}'.encode())
        except urllib.error.HTTPError as e:
            err_body = e.read().decode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(f'{{"status": "telegram_error", "details": {err_body}}}'.encode())
        except Exception as e:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(f'{{"status": "error", "message": "{str(e)}"}}'.encode())
