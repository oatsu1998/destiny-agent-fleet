"""
backend/alert_webhook.py

Destiny Agent Fleet — Real-Time Alerting Engine

Called by arb_agent.py (and other agents) as:
    from alert_webhook import AlertWebhookManager
    webhook_mgr = AlertWebhookManager()
    alerts_sent = webhook_mgr.evaluate_and_send(result_summary)

Applies VIP thresholds on top of what each agent already found, dedupes
with a 15-minute cooldown fingerprint, and sends to Telegram (and Discord,
once a webhook URL is added). Never raises — logs and continues so the
pipeline never crashes because of alerting.
"""

import hashlib
import json
import time
import urllib.request
import urllib.error
from typing import Any, Dict, List, Optional


# ---------------------------------------------------------------------------
# CONFIG
# ---------------------------------------------------------------------------

TELEGRAM_BOT_TOKEN = "8940771064:AAHz6XRKxJrhaciM7yYlHKpGl9xRqGKMPN0"
TELEGRAM_CHAT_ID = "6168326177"

# Optional — set this once you create a Discord webhook. Leave None until then.
DISCORD_WEBHOOK_URL: Optional[str] = None

COOLDOWN_SECONDS = 900  # 15 minutes

# VIP thresholds (from spec) — filters applied ON TOP of whatever each
# agent's own detection already found, since agents may use looser
# internal thresholds for their own snapshot/logging purposes.
MIN_ARB_ROI_PERCENT = 2.0
MIN_MIDDLE_WINDOW_POINTS = 2.5
MIN_STEAM_LINE_DELTA = 1.5
MIN_STEAM_ODDS_DELTA = 25
MIN_LADDER_MARGIN_CENTS = 30

ALERT_EMOJI = {
    "PURE_ARBITRAGE": "🟢",
    "MARKET_MIDDLE": "🟡",
    "STEAM_MOVE": "⚡",
    "LADDER_EDGE": "🟣",
    "CRITICAL_SCRATCH": "🩹"
}


class AlertWebhookManager:
    """
    Stateless across process restarts (cooldown cache is in-memory only —
    fine for a long-running worker, resets on redeploy/restart).
    """

    def __init__(self):
        self.telegram_token = TELEGRAM_BOT_TOKEN
        self.telegram_chat_id = TELEGRAM_CHAT_ID
        self.discord_url = DISCORD_WEBHOOK_URL
        self._last_sent: Dict[str, float] = {}

    # -- Public API -----------------------------------------------------

    def evaluate_and_send(self, result_summary: Dict[str, Any]) -> int:
        """
        Takes the dict produced by an agent's scan() (with keys like
        arbitrage_alerts, middle_alerts, steam_alerts, ladder_alerts,
        critical_scratches — any that are missing are just skipped) and sends the ones that
        clear VIP thresholds and aren't on cooldown. Returns count sent.
        """
        sent_count = 0

        for arb in result_summary.get("arbitrage_alerts", []):
            if arb.get("roi_percent", 0) >= MIN_ARB_ROI_PERCENT:
                if self._dispatch(self._build_arb_message(arb), self._arb_fingerprint(arb)):
                    sent_count += 1

        for mid in result_summary.get("middle_alerts", []):
            if mid.get("window_points", 0) >= MIN_MIDDLE_WINDOW_POINTS:
                if self._dispatch(self._build_middle_message(mid), self._middle_fingerprint(mid)):
                    sent_count += 1

        for steam in result_summary.get("steam_alerts", []):
            if steam.get("line_delta", 0) >= MIN_STEAM_LINE_DELTA or steam.get("odds_delta", 0) >= MIN_STEAM_ODDS_DELTA:
                if self._dispatch(self._build_steam_message(steam), self._steam_fingerprint(steam)):
                    sent_count += 1

        for ladder in result_summary.get("ladder_alerts", []):
            if ladder.get("margin_cents", 0) >= MIN_LADDER_MARGIN_CENTS:
                if self._dispatch(self._build_ladder_message(ladder), self._ladder_fingerprint(ladder)):
                    sent_count += 1

        for inj in result_summary.get("injury_alerts", []) or result_summary.get("critical_scratches", []):
            if inj.get("category") == "CRITICAL" or str(inj.get("status", "")).lower() in ["out", "ir", "injured reserve", "60-day il", "injury_status_out"]:
                if self._dispatch(self._build_injury_message(inj), self._injury_fingerprint(inj)):
                    sent_count += 1

        return sent_count

    # -- Message builders -------------------------------------------------

    def _build_arb_message(self, arb: Dict[str, Any]) -> str:
        emoji = ALERT_EMOJI["PURE_ARBITRAGE"]
        a, b = arb.get("side_a", {}), arb.get("side_b", {})
        return (
            f"{emoji} Pure arbitrage — {arb.get('roi_percent')}% ROI\n"
            f"{arb.get('label', '')}\n"
            f"{a.get('book')}: {a.get('american_odds')} (stake ${a.get('recommended_stake')})\n"
            f"{b.get('book')}: {b.get('american_odds')} (stake ${b.get('recommended_stake')})\n"
            f"Guaranteed profit: ${arb.get('guaranteed_profit_usd')}"
        )

    def _build_middle_message(self, mid: Dict[str, Any]) -> str:
        emoji = ALERT_EMOJI["MARKET_MIDDLE"]
        return (
            f"{emoji} Market middle — {mid.get('window_points')} pt window\n"
            f"{mid.get('book_a')}: {mid.get('line_a'):+.1f}  vs  {mid.get('book_b')}: {mid.get('line_b'):+.1f}"
        )

    def _build_steam_message(self, steam: Dict[str, Any]) -> str:
        emoji = ALERT_EMOJI["STEAM_MOVE"]
        return (
            f"{emoji} Steam move — {steam.get('bookmaker')}\n"
            f"{steam.get('prev_line')} → {steam.get('curr_line')} "
            f"(Δ {steam.get('line_delta')} pts / {steam.get('odds_delta')}¢)"
        )

    def _build_ladder_message(self, ladder: Dict[str, Any]) -> str:
        emoji = ALERT_EMOJI["LADDER_EDGE"]
        return (
            f"{emoji} Ladder prop edge — {ladder.get('margin_cents')}¢ over consensus\n"
            f"{ladder.get('summary', '')}"
        )

    def _build_injury_message(self, inj: Dict[str, Any]) -> str:
        emoji = ALERT_EMOJI.get("CRITICAL_SCRATCH", "🩹")
        notes = (inj.get("analyst_notes") or "N/A")[:120]
        return (
            f"{emoji} HIGH-PRIORITY CRITICAL SCRATCH — {inj.get('athlete_name')} ({inj.get('position', 'N/A')})\n"
            f"Team: {inj.get('team_name')} ({inj.get('league')})\n"
            f"Status: {inj.get('status')} | Injury: {inj.get('injury_type', 'Undisclosed')}\n"
            f"Notes: {notes}"
        )

    # -- Fingerprints (sha256(event_id_market_type_book_pair_line)) -------

    @staticmethod
    def _fingerprint(event_id: str, market_type: str, book_pair: str, line: str) -> str:
        raw = f"{event_id}_{market_type}_{book_pair}_{line}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _arb_fingerprint(self, arb: Dict[str, Any]) -> str:
        a, b = arb.get("side_a", {}), arb.get("side_b", {})
        book_pair = f"{a.get('book')}/{b.get('book')}"
        line = f"{a.get('decimal_odds')}/{b.get('decimal_odds')}"
        return self._fingerprint(arb.get("event_id", ""), arb.get("label", "arb"), book_pair, line)

    def _middle_fingerprint(self, mid: Dict[str, Any]) -> str:
        book_pair = f"{mid.get('book_a')}/{mid.get('book_b')}"
        line = f"{mid.get('line_a')}/{mid.get('line_b')}"
        return self._fingerprint(mid.get("event_id", ""), "middle", book_pair, line)

    def _steam_fingerprint(self, steam: Dict[str, Any]) -> str:
        line = f"{steam.get('prev_line')}->{steam.get('curr_line')}"
        return self._fingerprint(steam.get("event_id", ""), steam.get("market_kind", "steam"), steam.get("bookmaker", ""), line)

    def _ladder_fingerprint(self, ladder: Dict[str, Any]) -> str:
        return self._fingerprint(
            ladder.get("event_id", ""),
            "ladder",
            ladder.get("book", ""),
            str(ladder.get("milestone", ""))
        )

    def _injury_fingerprint(self, inj: Dict[str, Any]) -> str:
        return self._fingerprint(
            inj.get("athlete_id") or inj.get("athlete_name", ""),
            "injury_scratch",
            inj.get("team_name", ""),
            str(inj.get("status", "out"))
        )

    # -- Cooldown ---------------------------------------------------------

    def _is_on_cooldown(self, fingerprint: str) -> bool:
        last = self._last_sent.get(fingerprint)
        if last is None:
            return False
        return (time.time() - last) < COOLDOWN_SECONDS

    # -- Dispatch -----------------------------------------------------------

    def _dispatch(self, message: str, fingerprint: str) -> bool:
        if self._is_on_cooldown(fingerprint):
            return False
        self._last_sent[fingerprint] = time.time()

        self._send_telegram(message)
        self._send_discord(message)
        return True

    def _send_telegram(self, message: str):
        if not self.telegram_token or not self.telegram_chat_id:
            print(f"[alert_webhook][dry-run] (no Telegram config): {message}")
            return

        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = json.dumps({"chat_id": self.telegram_chat_id, "text": message}).encode("utf-8")
        req = urllib.request.Request(url, data=payload, headers={"Content-Type": "application/json"}, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp.read()
        except urllib.error.HTTPError as e:
            print(f"[alert_webhook] Telegram HTTP error: {e.read().decode('utf-8')}")
        except Exception as e:
            print(f"[alert_webhook] Telegram send failed: {e}")

    def _send_discord(self, message: str):
        if not self.discord_url:
            print(f"[alert_webhook][dry-run] (no Discord webhook set): {message}")
            return

        payload = json.dumps({"content": message}).encode("utf-8")
        req = urllib.request.Request(self.discord_url, data=payload, headers={"Content-Type": "application/json"}, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                resp.read()
        except Exception as e:
            print(f"[alert_webhook] Discord send failed: {e}")


# ---------------------------------------------------------------------------
# QUICK TEST — run this file directly to send yourself a test alert
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    mgr = AlertWebhookManager()
    fake_summary = {
        "arbitrage_alerts": [{
            "event_id": "TEST_EVENT",
            "label": "Home vs Away",
            "roi_percent": 3.1,
            "guaranteed_profit_usd": 31.0,
            "side_a": {"book": "DraftKings", "american_odds": 150, "decimal_odds": 2.5, "recommended_stake": 400},
            "side_b": {"book": "Kalshi", "american_odds": -120, "decimal_odds": 1.83, "recommended_stake": 546},
        }],
        "middle_alerts": [],
        "steam_alerts": [],
    }
    count = mgr.evaluate_and_send(fake_summary)
    print(f"Alerts sent: {count}")
