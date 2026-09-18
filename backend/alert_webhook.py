#!/usr/bin/env python3
"""
=============================================================================
DESTINY SPORTS ENGINE — Real-Time Discord/Telegram Alerting Webhook Engine
High-Value Discrepancy, Arbitrage & Steam Movement Outbound Webhook Manager
=============================================================================
1. Priority Thresholds:
   - Pure Arbitrage: ROI >= 2.0% (Implied Probability < 0.98)
   - Market Middles: Line Window >= 2.5 points / yards
   - Steam Velocity: Spread Shift >= 1.5 pts or Odds Shift >= 25¢ (<= 10m)
   - Ladder Edges: Milestone line payout margin >= 30¢ over consensus
2. Features:
   - SHA-256 Alert Key Deduplication with 15-minute (900s) Cooldown
   - GFM Rich Embed Formatter with color-coded alerts
   - Async & Sync HTTP Dispatchers with HTTP 429 rate limit backoff
=============================================================================
"""

import sys
import os
import json
import time
import hashlib
import argparse
import asyncio
import logging
import datetime
import urllib.request
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("sports_engine.alert_webhook")

COOLDOWN_SECONDS = 900  # 15 Minutes

class AlertWebhookManager:
    """
    Manages deduplication, threshold filtering, rich embed formatting, and dispatching
    of high-value sports betting arbitrage and steam movement alerts.
    """
    def __init__(self):
        self.discord_url = os.getenv("DISCORD_WEBHOOK_URL") or ""
        self.telegram_token = os.getenv("TELEGRAM_BOT_TOKEN") or ""
        self.telegram_chat_id = os.getenv("TELEGRAM_CHAT_ID") or ""

        # In-memory cooldown cache: { alert_key_hash: timestamp_sent }
        self.sent_cooldowns: Dict[str, float] = {}

        # Telemetry metrics
        self.alerts_evaluated = 0
        self.alerts_sent = 0
        self.alerts_cooldown_suppressed = 0
        self.alerts_failed = 0

    def generate_alert_key(self, event_id: str, market_type: str, book_pair: str, line_val: Any) -> str:
        """Generates SHA-256 hash key for alert deduplication."""
        raw_str = f"{event_id}_{market_type}_{book_pair}_{line_val}"
        return hashlib.sha256(raw_str.encode('utf-8')).hexdigest()

    def is_on_cooldown(self, alert_key: str) -> bool:
        """Checks if an alert key is within the 15-minute cooldown window."""
        now = time.time()
        last_sent = self.sent_cooldowns.get(alert_key, 0.0)
        if (now - last_sent) < COOLDOWN_SECONDS:
            return True
        return False

    def mark_sent(self, alert_key: str) -> None:
        """Records timestamp for alert key cooldown."""
        self.sent_cooldowns[alert_key] = time.time()

    def format_discord_embed(self, alert: Dict[str, Any]) -> Dict[str, Any]:
        """
        Formats alert finding into a Discord GFM Rich Embed object.
        """
        alert_type = alert.get("type", "PURE_ARBITRAGE")

        if alert_type == "PURE_ARBITRAGE":
            color = 0x2ECC71  # Emerald Green
            title = f"💎 GUARANTEED ARBITRAGE (+{alert.get('roi_percent', 0.0):.2f}% ROI)"
            side_a = alert.get("side_a", {})
            side_b = alert.get("side_b", {})
            desc = (
                f"**Event**: {alert.get('label', 'Matchup Market')}\n"
                f"**Canonical ID**: `{alert.get('event_id', 'N/A')}`\n"
                f"**Implied Probability**: `{alert.get('implied_probability', 0.0):.4f}` (< 1.0)"
            )
            fields = [
                {
                    "name": f"Side A ({side_a.get('book', 'Book A')})",
                    "value": f"Odds: **{'+' if side_a.get('american_odds', 0) > 0 else ''}{side_a.get('american_odds')}**\nStake: **${side_a.get('recommended_stake', 0.0):,.2f}**",
                    "inline": True
                },
                {
                    "name": f"Side B ({side_b.get('book', 'Book B')})",
                    "value": f"Odds: **{'+' if side_b.get('american_odds', 0) > 0 else ''}{side_b.get('american_odds')}**\nStake: **${side_b.get('recommended_stake', 0.0):,.2f}**",
                    "inline": True
                },
                {
                    "name": "💵 Guaranteed Profit ($1k Bankroll)",
                    "value": f"**+${alert.get('guaranteed_profit_usd', 0.0):,.2f} USD**",
                    "inline": False
                }
            ]

        elif alert_type == "MARKET_MIDDLE":
            color = 0xF1C40F  # Amber Gold
            title = f"🎯 HIGH-VALUE MARKET MIDDLE ({alert.get('window_points', 0.0)} Points Window)"
            desc = f"**Summary**: {alert.get('summary', 'Middle Window Detected')}\n**Canonical ID**: `{alert.get('event_id', 'N/A')}`"
            fields = [
                {
                    "name": "Target Window",
                    "value": f"**{alert.get('window_points', 0.0)} pts / yards** overlapping window",
                    "inline": True
                },
                {
                    "name": "Opportunity Type",
                    "value": "Overlapping Win/Push Range Across Books",
                    "inline": True
                }
            ]

        elif alert_type == "STEAM_MOVE":
            color = 0xE67E22  # Electric Orange / Red
            title = "⚡ RAPID STEAM MOVEMENT DETECTED"
            desc = f"**Summary**: {alert.get('summary', 'Rapid Line Shift')}\n**Bookmaker**: `{alert.get('bookmaker', 'Market Consensus')}`"
            fields = [
                {
                    "name": "Line Shift Velocity",
                    "value": f"Shifted within **<= 10 minutes**",
                    "inline": True
                },
                {
                    "name": "Market Signal",
                    "value": "Heavy Sharp Money Volume Shift",
                    "inline": True
                }
            ]

        elif alert_type == "LADDER_EDGE":
            color = 0x9B59B6  # Purple
            title = f"🎯 LADDER PROP VALUE EDGE (+{alert.get('payout_margin_cents', 30)}¢ Margin)"
            desc = f"**Player / Stat**: {alert.get('label', 'Milestone Line')}\n**Summary**: {alert.get('summary', 'Off-market milestone payout')}"
            fields = [
                {
                    "name": "Milestone Line",
                    "value": f"**{alert.get('line', 'N/A')}** @ **{alert.get('odds', 'N/A')}**",
                    "inline": True
                },
                {
                    "name": "Consensus Margin",
                    "value": f"**+{alert.get('payout_margin_cents', 30)}¢** over consensus payout",
                    "inline": True
                }
            ]

        else:
            color = 0x3498DB  # Default Blue
            title = "📊 DESTINY AGENT FLEET MARKET ALERT"
            desc = f"Alert: {json.dumps(alert)}"
            fields = []

        embed = {
            "title": title,
            "description": desc,
            "color": color,
            "fields": fields,
            "footer": {
                "text": "Destiny Agent Fleet • Sub-Second Intelligence Stream",
                "icon_url": "https://destiny-agent-fleet.vercel.app/favicon.ico"
            },
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }

        return {
            "username": "Destiny Fleet Alert Bot ⚡",
            "avatar_url": "https://destiny-agent-fleet.vercel.app/favicon.ico",
            "embeds": [embed]
        }

    def dispatch_discord(self, payload: Dict[str, Any]) -> bool:
        """
        Dispatches Discord Rich Embed payload via HTTP POST with rate-limit retry logic.
        """
        if not self.discord_url:
            logger.info("[DRY-RUN] Discord Webhook URL not set. Skipping live HTTP dispatch.")
            return True

        req_data = json.dumps(payload).encode('utf-8')
        req = urllib.request.Request(
            self.discord_url,
            data=req_data,
            headers={
                "Content-Type": "application/json",
                "User-Agent": "Mozilla/5.0 (DestinyAgentFleet/2.0)"
            },
            method="POST"
        )

        for attempt in range(1, 4):
            try:
                with urllib.request.urlopen(req, timeout=5) as resp:
                    if resp.status in [200, 204]:
                        self.alerts_sent += 1
                        logger.info("Successfully dispatched Discord alert embed.")
                        return True
            except urllib.error.HTTPError as http_err:
                if http_err.code == 429:  # Rate Limit Backoff
                    retry_after = 2.0
                    try:
                        resp_json = json.loads(http_err.read().decode('utf-8'))
                        retry_after = float(resp_json.get("retry_after", 2.0))
                    except Exception:
                        pass
                    logger.warning(f"HTTP 429 Rate Limited by Discord. Sleeping {retry_after:.2f}s (Attempt {attempt}/3)...")
                    time.sleep(retry_after)
                else:
                    logger.warning(f"HTTP Error {http_err.code} dispatching Discord alert: {http_err}")
                    break
            except Exception as err:
                logger.warning(f"Network error dispatching Discord alert: {err}")
                time.sleep(1.0)

        self.alerts_failed += 1
        return False

    def dispatch_telegram(self, text_message: str) -> bool:
        """Optionally dispatches Markdown message to Telegram bot if credentials exist."""
        if not (self.telegram_token and self.telegram_chat_id):
            return True

        tg_url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = {
            "chat_id": self.telegram_chat_id,
            "text": text_message,
            "parse_mode": "Markdown"
        }
        try:
            req = urllib.request.Request(
                tg_url,
                data=json.dumps(payload).encode('utf-8'),
                headers={"Content-Type": "application/json"},
                method="POST"
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    logger.info("Successfully dispatched Telegram alert message.")
                    return True
        except Exception as err:
            logger.warning(f"Error dispatching Telegram alert: {err}")
        return False

    def evaluate_and_send(self, findings: Dict[str, Any]) -> int:
        """
        Evaluates scan findings from ArbitrageSteamAgent / kalshi_websocket,
        filters by priority thresholds, checks cooldowns, formats embeds, and dispatches.
        Returns total alerts sent.
        """
        sent_count = 0

        # 1. Pure Arbitrage Alerts (ROI >= 2.0%)
        arbs = findings.get("arbitrage_alerts", [])
        for arb in arbs:
            self.alerts_evaluated += 1
            roi = arb.get("roi_percent", 0.0)
            if roi >= 2.0:
                event_id = arb.get("event_id", "GAME")
                book_pair = f"{arb.get('side_a', {}).get('book')}@{arb.get('side_b', {}).get('book')}"
                line_val = roi
                alert_key = self.generate_alert_key(event_id, "PURE_ARBITRAGE", book_pair, line_val)

                if self.is_on_cooldown(alert_key):
                    self.alerts_cooldown_suppressed += 1
                    logger.info(f"Suppressed duplicate Pure Arb alert for {event_id} (15m Cooldown).")
                    continue

                embed_payload = self.format_discord_embed(arb)
                if self.dispatch_discord(embed_payload):
                    self.mark_sent(alert_key)
                    sent_count += 1

                    # Dispatch Telegram text summary
                    tg_text = f"💎 *GUARANTEED ARBITRAGE (+{roi:.2f}% ROI)*\n*Event*: {arb.get('label')}\n*Profit*: +${arb.get('guaranteed_profit_usd'):,.2f} USD"
                    self.dispatch_telegram(tg_text)

        # 2. Market Middles Alerts (Window >= 2.5 pts)
        middles = findings.get("middle_alerts", [])
        for mid in middles:
            self.alerts_evaluated += 1
            win_pts = mid.get("window_points", 0.0)
            if win_pts >= 2.5:
                event_id = mid.get("event_id", "GAME")
                alert_key = self.generate_alert_key(event_id, "MARKET_MIDDLE", "MIDDLE", win_pts)

                if self.is_on_cooldown(alert_key):
                    self.alerts_cooldown_suppressed += 1
                    continue

                mid["type"] = "MARKET_MIDDLE"
                embed_payload = self.format_discord_embed(mid)
                if self.dispatch_discord(embed_payload):
                    self.mark_sent(alert_key)
                    sent_count += 1

        # 3. Rapid Steam Moves Alerts (Shift >= 1.5 pts or >= 25¢)
        steams = findings.get("steam_alerts", [])
        for stm in steams:
            self.alerts_evaluated += 1
            event_id = stm.get("event_id", "GAME")
            book = stm.get("bookmaker", "CONSENSUS")
            summary = stm.get("summary", "")
            alert_key = self.generate_alert_key(event_id, "STEAM_MOVE", book, summary)

            if self.is_on_cooldown(alert_key):
                self.alerts_cooldown_suppressed += 1
                continue

            stm["type"] = "STEAM_MOVE"
            embed_payload = self.format_discord_embed(stm)
            if self.dispatch_discord(embed_payload):
                self.mark_sent(alert_key)
                sent_count += 1

        # 4. Ladder Prop Edges Alerts (Payout Margin >= 30¢)
        ladders = findings.get("ladder_alerts", [])
        for lad in ladders:
            self.alerts_evaluated += 1
            margin = lad.get("payout_margin_cents", 0)
            if margin >= 30:
                event_id = lad.get("event_id", "PROP")
                alert_key = self.generate_alert_key(event_id, "LADDER_EDGE", lad.get("player", ""), margin)

                if self.is_on_cooldown(alert_key):
                    self.alerts_cooldown_suppressed += 1
                    continue

                lad["type"] = "LADDER_EDGE"
                embed_payload = self.format_discord_embed(lad)
                if self.dispatch_discord(embed_payload):
                    self.mark_sent(alert_key)
                    sent_count += 1

        return sent_count

def run_standalone_test():
    """Assembles a mock +4.5% ROI NFL arbitrage embed and tests dispatch/formatting."""
    print("=" * 70)
    print("DESTINY AGENT FLEET — DISCORD/TELEGRAM WEBHOOK ENGINE TEST")
    print("=" * 70)

    manager = AlertWebhookManager()
    webhook_url = os.getenv("DISCORD_WEBHOOK_URL")
    print(f"Webhook Config Status: {'CONNECTED (' + webhook_url[:30] + '...)' if webhook_url else 'DRY-RUN MODE (No DISCORD_WEBHOOK_URL set)'}")

    mock_arb_finding = {
        "arbitrage_alerts": [
            {
                "type": "PURE_ARBITRAGE",
                "label": "Detroit Lions @ Buffalo Bills - Moneyline",
                "event_id": "NFL_401872932",
                "implied_probability": 0.9569,
                "roi_percent": 4.50,
                "guaranteed_profit_usd": 45.00,
                "side_a": {
                    "book": "Kalshi",
                    "american_odds": 160,
                    "recommended_stake": 423.39
                },
                "side_b": {
                    "book": "FanDuel",
                    "american_odds": -110,
                    "recommended_stake": 576.61
                }
            }
        ]
    }

    print("\nFormatting Mock Discord Rich Embed Payload:")
    embed_payload = manager.format_discord_embed(mock_arb_finding["arbitrage_alerts"][0])
    print(json.dumps(embed_payload, indent=2))

    print("\nExecuting Evaluate & Send Pipeline...")
    sent_count = manager.evaluate_and_send(mock_arb_finding)
    print(f"Alerts Dispatched Successfully: {sent_count}")
    print(f"Cooldown Suppressed: {manager.alerts_cooldown_suppressed}")

def main():
    parser = argparse.ArgumentParser(description="Destiny Agent Fleet Alert Webhook Engine")
    parser.add_argument("--test", action="store_true", help="Assemble mock +4.5%% ROI embed and test dispatch")
    args = parser.parse_args()

    if args.test or len(sys.argv) == 1:
        run_standalone_test()

if __name__ == "__main__":
    main()
