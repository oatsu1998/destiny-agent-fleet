"""
api/test-alert.py

TEMPORARY test endpoint — visit this URL in any browser (including your
phone) to fire a test Telegram alert. Delete this file once you've
confirmed alerts are working; it's not part of the real pipeline.
"""

from http.server import BaseHTTPRequestHandler
import asyncio
import sys
import os

sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from backend.alert_webhook import send_alert, AlertType, get_alert_agent


class handler(BaseHTTPRequestHandler):
    def do_GET(self):
        try:
            sent = asyncio.run(self._fire())
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            if sent:
                msg = '{"status": "sent", "message": "Check Telegram!"}'
            else:
                msg = '{"status": "suppressed", "message": "On cooldown — wait 15 min and try again."}'
            self.wfile.write(msg.encode())
        except Exception as e:
            self.send_response(500)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(f'{{"status": "error", "message": "{str(e)}"}}'.encode())

    async def _fire(self):
        ok = await send_alert(
            event_id="phone-test-001",
            alert_type=AlertType.PURE_ARB,
            market_type="moneyline",
            book_pair="DraftKings/Kalshi",
            line="+150",
            title="Test alert from phone",
            detail="If you see this in Telegram, your alert pipeline works!",
            game="Test Game",
        )
        await get_alert_agent().aclose()
        return ok
