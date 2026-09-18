"""
backend/alert_webhook.py

Destiny Agent Fleet — Real-Time Alerting Engine

Sends VIP alerts to Telegram (and optionally Discord) whenever an upstream
agent (arb_steam_hunter, props_matrix_hunter, etc.) finds something worth
a human's attention. Never crashes the pipeline — if a webhook is missing
or a send fails, it logs to console and moves on.
"""

import asyncio
import hashlib
import time
from dataclasses import dataclass
from enum import Enum
from typing import Optional

import httpx


# ---------------------------------------------------------------------------
# CONFIG — your Telegram bot is already wired in below.
# ---------------------------------------------------------------------------

TELEGRAM_BOT_TOKEN = "8940771064:AAHz6XRKxJrhaciM7yYlHKpGl9xRqGKMPN0"
TELEGRAM_CHAT_ID = "6168326177"

# Optional — leave as None/empty until you set up a Discord webhook.
# Agent falls back to console-only (dry-run) logging if this is missing.
DISCORD_WEBHOOK_URL: Optional[str] = None

# Anti-spam cooldown window (seconds) per unique event fingerprint.
COOLDOWN_SECONDS = 900  # 15 minutes


# ---------------------------------------------------------------------------
# ALERT TYPES
# ---------------------------------------------------------------------------

class AlertType(str, Enum):
    PURE_ARB = "pure_arb"
    MARKET_MIDDLE = "market_middle"
    STEAM_MOVE = "steam_move"
    LADDER_EDGE = "ladder_edge"


# Discord embed colors (hex ints) + emoji fallback for Telegram
ALERT_STYLE = {
    AlertType.PURE_ARB: {"color": 0x2ECC71, "emoji": "🟢", "label": "Pure arbitrage"},
    AlertType.MARKET_MIDDLE: {"color": 0xF1C40F, "emoji": "🟡", "label": "Market middle"},
    AlertType.STEAM_MOVE: {"color": 0xE67E22, "emoji": "⚡", "label": "Steam move"},
    AlertType.LADDER_EDGE: {"color": 0x9B59B6, "emoji": "🟣", "label": "Ladder prop edge"},
}


@dataclass
class AlertEvent:
    """A single alert-worthy event, as reported by an upstream agent."""
    event_id: str
    alert_type: AlertType
    market_type: str          # e.g. "spread", "moneyline", "player_prop"
    book_pair: str            # e.g. "DraftKings/Kalshi"
    line: str                 # e.g. "-3.5" or "112.5 rec yds"
    title: str                # short headline, e.g. "3.1% ROI arb — Lakers/Celtics"
    detail: str               # 1-2 sentence explanation
    game: Optional[str] = None


# ---------------------------------------------------------------------------
# ALERT WEBHOOK AGENT
# ---------------------------------------------------------------------------

class AlertWebhookAgent:
    """
    Call `await agent.fire(event)` from any upstream agent (arb_steam_hunter,
    props_matrix_hunter, etc.) whenever a VIP-threshold condition is met.
    This agent handles dedup/cooldown and delivery — callers don't need to
    worry about spam or missing webhooks.
    """

    def __init__(self):
        self._last_sent: dict[str, float] = {}
        self._client = httpx.AsyncClient(timeout=10.0)

    # -- Public API ----------------------------------------------------

    async def fire(self, event: AlertEvent) -> bool:
        """
        Attempt to send an alert. Returns True if it was sent, False if it
        was suppressed by the cooldown. Never raises — logs and swallows
        any delivery failure so the pipeline keeps running.
        """
        fingerprint = self._fingerprint(event)

        if self._is_on_cooldown(fingerprint):
            print(f"[alert_webhook] Suppressed (cooldown): {event.title}")
            return False

        self._last_sent[fingerprint] = time.time()

        # Fire both channels concurrently; each fails independently.
        results = await asyncio.gather(
            self._send_telegram(event),
            self._send_discord(event),
            return_exceptions=True,
        )

        for result in results:
            if isinstance(result, Exception):
                print(f"[alert_webhook] Delivery error: {result}")

        return True

    async def aclose(self):
        await self._client.aclose()

    # -- Internals -------------------------------------------------------

    @staticmethod
    def _fingerprint(event: AlertEvent) -> str:
        raw = f"{event.event_id}_{event.market_type}_{event.book_pair}_{event.line}"
        return hashlib.sha256(raw.encode("utf-8")).hexdigest()

    def _is_on_cooldown(self, fingerprint: str) -> bool:
        last = self._last_sent.get(fingerprint)
        if last is None:
            return False
        return (time.time() - last) < COOLDOWN_SECONDS

    async def _send_telegram(self, event: AlertEvent):
        if not TELEGRAM_BOT_TOKEN or not TELEGRAM_CHAT_ID:
            print(f"[alert_webhook][dry-run] (no Telegram config) {event.title}")
            return

        style = ALERT_STYLE[event.alert_type]
        lines = [
            f"{style['emoji']} *{style['label']}*",
            f"*{event.title}*",
        ]
        if event.game:
            lines.append(f"Game: {event.game}")
        lines.append(event.detail)

        text = "\n".join(lines)
        url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"

        try:
            resp = await self._client.post(
                url,
                json={
                    "chat_id": TELEGRAM_CHAT_ID,
                    "text": text,
                    "parse_mode": "Markdown",
                },
            )
            resp.raise_for_status()
        except Exception as e:
            print(f"[alert_webhook] Telegram send failed: {e}")

    async def _send_discord(self, event: AlertEvent):
        if not DISCORD_WEBHOOK_URL:
            print(f"[alert_webhook][dry-run] (no Discord webhook set) {event.title}")
            return

        style = ALERT_STYLE[event.alert_type]
        embed = {
            "title": event.title,
            "description": event.detail,
            "color": style["color"],
            "fields": [
                {"name": "Type", "value": style["label"], "inline": True},
                {"name": "Book pair", "value": event.book_pair, "inline": True},
            ],
        }
        if event.game:
            embed["fields"].append({"name": "Game", "value": event.game, "inline": False})

        try:
            resp = await self._client.post(
                DISCORD_WEBHOOK_URL,
                json={"embeds": [embed]},
            )
            resp.raise_for_status()
        except Exception as e:
            print(f"[alert_webhook] Discord send failed: {e}")


# ---------------------------------------------------------------------------
# HELPER — build an AlertEvent + fire it, in one call, from upstream agents
# ---------------------------------------------------------------------------

_agent_singleton: Optional[AlertWebhookAgent] = None


def get_alert_agent() -> AlertWebhookAgent:
    global _agent_singleton
    if _agent_singleton is None:
        _agent_singleton = AlertWebhookAgent()
    return _agent_singleton


async def send_alert(
    event_id: str,
    alert_type: AlertType,
    market_type: str,
    book_pair: str,
    line: str,
    title: str,
    detail: str,
    game: Optional[str] = None,
) -> bool:
    """Convenience wrapper — import this one function from other agents."""
    event = AlertEvent(
        event_id=event_id,
        alert_type=alert_type,
        market_type=market_type,
        book_pair=book_pair,
        line=line,
        title=title,
        detail=detail,
        game=game,
    )
    return await get_alert_agent().fire(event)


# ---------------------------------------------------------------------------
# QUICK TEST — run this file directly to send yourself a test alert
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    async def _test():
        ok = await send_alert(
            event_id="test-001",
            alert_type=AlertType.PURE_ARB,
            market_type="moneyline",
            book_pair="DraftKings/Kalshi",
            line="+150",
            title="Test alert — 3.1% ROI arb",
            detail="This is a test message from alert_webhook.py. If you see this in Telegram, it's working.",
            game="Lakers @ Celtics",
        )
        print("Sent!" if ok else "Suppressed (cooldown).")
        await get_alert_agent().aclose()

    asyncio.run(_test())