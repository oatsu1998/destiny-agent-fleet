#!/usr/bin/env python3
"""
=============================================================================
DESTINY SPORTS ENGINE — Kalshi Real-Time WebSocket Streaming Daemon
Sub-Second Order Book Delta Ingestion & Implied Probability Engine
=============================================================================
1. Authentication & RSA-PSS Signature Generation:
   - Signs string: "{timestamp_ms}GET/trade-api/ws/v2"
   - Uses RSA-PSS SHA-256 (MGF1, salt length = PSS.DIGEST_LENGTH)
   - Headers: KALSHI-ACCESS-KEY, KALSHI-ACCESS-TIMESTAMP, KALSHI-ACCESS-SIGNATURE
2. WebSocket Engine:
   - Connects to wss://external-api-ws.kalshi.com/trade-api/ws/v2
   - Subscribes to orderbook_delta across active sports tickers
3. In-Memory Order Book Manager:
   - Tracks live Yes/No bids and asks per ticker
   - Computes top-of-book implied probability & spread in real time
4. Integration & Persistence:
   - Forwards sub-second ticks to OddsSanityFirewall & ArbitrageSteamAgent
   - Persists live order book to backend/snapshots/kalshi_orderbook_live.json
=============================================================================
"""

import sys
import os
import json
import time
import base64
import argparse
import asyncio
import logging
import datetime
from typing import Dict, Any, List, Optional, Tuple

import websockets

# Ensure local backend modules are importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from firewall_agent import OddsSanityFirewall
from arb_agent import ArbitrageSteamAgent
from alert_webhook import AlertWebhookManager

# RSA-PSS Signing imports from cryptography
try:
    from cryptography.hazmat.primitives import hashes
    from cryptography.hazmat.primitives.asymmetric import padding
    from cryptography.hazmat.primitives.serialization import load_pem_private_key
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("sports_engine.kalshi_websocket")

KALSHI_WS_URL = "wss://external-api-ws.kalshi.com/trade-api/ws/v2"
KALSHI_WS_PUBLIC_URL = "wss://api.elections.kalshi.com/trade-api/ws/v2"

SNAPSHOT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "snapshots", "kalshi_orderbook_live.json")
FALLBACK_SNAPSHOT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "kalshi_orderbook_live.json")
STREAM_INPUT_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "live_market_stream.json")

class OrderBookManager:
    """
    Maintains in-memory order book state for subscribed Kalshi market tickers.
    """
    def __init__(self):
        # Structure: { ticker: { "yes_bids": {price_cents: qty}, "yes_asks": {...}, "no_bids": {...}, "no_asks": {...} } }
        self.books: Dict[str, Dict[str, Dict[int, int]]] = {}

    def _get_or_create_book(self, ticker: str) -> Dict[str, Dict[int, int]]:
        if ticker not in self.books:
            self.books[ticker] = {
                "yes_bids": {},
                "yes_asks": {},
                "no_bids": {},
                "no_asks": {}
            }
        return self.books[ticker]

    def apply_snapshot(self, ticker: str, msg: Dict[str, Any]) -> None:
        """Seeds initial order book snapshot for a ticker."""
        book = self._get_or_create_book(ticker)
        book["yes_bids"].clear()
        book["yes_asks"].clear()
        book["no_bids"].clear()
        book["no_asks"].clear()

        # Parse Yes/No bids/asks arrays [[price, qty], ...]
        for price_cents, qty in msg.get("yes_dollars", []):
            try:
                book["yes_bids"][int(round(float(price_cents) * 100))] = int(qty)
            except (ValueError, TypeError):
                pass
        for price_cents, qty in msg.get("no_dollars", []):
            try:
                book["no_bids"][int(round(float(price_cents) * 100))] = int(qty)
            except (ValueError, TypeError):
                pass

    def apply_delta(self, ticker: str, msg: Dict[str, Any]) -> Tuple[bool, Dict[str, Any]]:
        """
        Applies a price level delta to the order book.
        Returns (top_of_book_changed, top_of_book_summary).
        """
        book = self._get_or_create_book(ticker)
        old_top = self.get_top_of_book(ticker)

        price_cents = msg.get("price") or msg.get("price_cents") or 0
        delta_qty = msg.get("delta") or msg.get("delta_quantity") or 0
        side = (msg.get("side") or "yes").lower()

        if isinstance(price_cents, float) and price_cents <= 1.0:
            price_cents = int(round(price_cents * 100))

        target_dict = book["yes_bids"] if side == "yes" else book["no_bids"]
        curr_qty = target_dict.get(price_cents, 0)
        new_qty = max(0, curr_qty + delta_qty)
        if new_qty == 0:
            target_dict.pop(price_cents, None)
        else:
            target_dict[price_cents] = new_qty

        new_top = self.get_top_of_book(ticker)
        changed = (old_top["best_yes_bid"] != new_top["best_yes_bid"] or
                   old_top["best_yes_ask"] != new_top["best_yes_ask"])

        return changed, new_top

    def get_top_of_book(self, ticker: str) -> Dict[str, Any]:
        """Computes top-of-book best Yes bid/ask, No bid/ask, and implied probability."""
        book = self.books.get(ticker, {"yes_bids": {}, "yes_asks": {}, "no_bids": {}, "no_asks": {}})
        
        yes_bids = book["yes_bids"]
        best_yes_bid = max(yes_bids.keys()) if yes_bids else 0

        # Ask for YES is equivalent to (100 - best NO bid)
        no_bids = book["no_bids"]
        best_no_bid = max(no_bids.keys()) if no_bids else 0
        best_yes_ask = (100 - best_no_bid) if best_no_bid > 0 else 100

        mid_price_cents = (best_yes_bid + best_yes_ask) / 2.0 if (best_yes_bid and best_yes_ask < 100) else (best_yes_bid or 50)
        implied_prob = round(mid_price_cents / 100.0, 4)

        return {
            "ticker": ticker,
            "best_yes_bid": best_yes_bid,
            "best_yes_ask": best_yes_ask,
            "best_no_bid": best_no_bid,
            "spread_cents": max(0, best_yes_ask - best_yes_bid),
            "implied_probability": implied_prob,
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }

def generate_kalshi_auth_headers() -> Tuple[Dict[str, str], str]:
    """
    Generates authentication headers using RSA-PSS SHA-256 signature if credentials exist.
    Returns (headers_dict, connection_url).
    """
    access_key = os.getenv("KALSHI_ACCESS_KEY") or os.getenv("KALSHI_API_KEY")
    key_path = os.getenv("KALSHI_PRIVATE_KEY_PATH", "kalshi_private.pem")
    key_pem = os.getenv("KALSHI_PRIVATE_KEY_PEM")

    if not access_key:
        logger.info("No Kalshi API Key configured. Operating in public streaming mode.")
        return {}, KALSHI_WS_PUBLIC_URL

    if not CRYPTO_AVAILABLE:
        logger.warning("Python 'cryptography' library unavailable for RSA-PSS signing. Operating in public mode.")
        return {}, KALSHI_WS_PUBLIC_URL

    # Load PEM private key
    private_key = None
    if key_pem:
        try:
            private_key = load_pem_private_key(key_pem.encode('utf-8'), password=None)
        except Exception as err:
            logger.warning(f"Could not parse KALSHI_PRIVATE_KEY_PEM: {err}")
    elif os.path.exists(key_path):
        try:
            with open(key_path, "rb") as f:
                private_key = load_pem_private_key(f.read(), password=None)
        except Exception as err:
            logger.warning(f"Could not read private key file {key_path}: {err}")

    if not private_key:
        logger.info("No valid RSA private key found. Defaulting to public Kalshi WebSocket endpoint.")
        return {}, KALSHI_WS_PUBLIC_URL

    # Signature generation: timestamp_ms + "GET/trade-api/ws/v2"
    timestamp_ms = str(int(time.time() * 1000))
    message_str = f"{timestamp_ms}GET/trade-api/ws/v2"
    message_bytes = message_str.encode('utf-8')

    try:
        signature = private_key.sign(
            message_bytes,
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.DIGEST_LENGTH
            ),
            hashes.SHA256()
        )
        signature_b64 = base64.b64encode(signature).decode('utf-8')

        headers = {
            "KALSHI-ACCESS-KEY": access_key,
            "KALSHI-ACCESS-TIMESTAMP": timestamp_ms,
            "KALSHI-ACCESS-SIGNATURE": signature_b64
        }
        logger.info("Successfully generated RSA-PSS authentication handshake headers.")
        return headers, KALSHI_WS_URL
    except Exception as sig_err:
        logger.warning(f"Failed to generate RSA-PSS signature: {sig_err}")
        return {}, KALSHI_WS_PUBLIC_URL

def discover_active_sports_tickers() -> List[str]:
    """Discovers active sports market tickers from live market stream snapshot."""
    tickers = []
    if os.path.exists(STREAM_INPUT_PATH):
        try:
            with open(STREAM_INPUT_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                records = data.get("records", [])
                for r in records:
                    t = r.get("ticker")
                    if t and t not in tickers:
                        tickers.append(t)
        except Exception as err:
            logger.warning(f"Could not read live stream tickers: {err}")

    if not tickers:
        # Default fallback active sports tickers
        tickers = ["KXNFLGAME", "KXMLBGAME", "KXNBAGAME", "KXNFLSPREAD", "KXMLBTOTAL"]

    logger.info(f"Discovered {len(tickers)} active sports market tickers for WebSocket subscription.")
    return tickers[:50]

class KalshiWebSocketDaemon:
    """
    Sub-second real-time streaming client for Kalshi orderbook_delta events.
    """
    def __init__(self, dry_run: bool = False):
        self.dry_run = dry_run
        self.book_manager = OrderBookManager()
        self.firewall = OddsSanityFirewall()
        self.arb_agent = ArbitrageSteamAgent()
        self.webhook_mgr = AlertWebhookManager()
        self.received_deltas_count = 0

    def _persist_live_orderbook(self) -> None:
        """Saves active live order book state to local snapshots."""
        top_books = {t: self.book_manager.get_top_of_book(t) for t in self.book_manager.books.keys()}
        payload = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "total_markets_tracked": len(top_books),
            "orderbooks": top_books
        }

        os.makedirs(os.path.dirname(SNAPSHOT_PATH), exist_ok=True)
        for target in [SNAPSHOT_PATH, FALLBACK_SNAPSHOT_PATH]:
            try:
                with open(target, "w", encoding="utf-8") as f:
                    json.dump(payload, f, indent=2)
            except Exception as err:
                logger.warning(f"Could not save live orderbook to {target}: {err}")

    async def handle_message(self, message_str: str) -> None:
        """Processes incoming WebSocket JSON messages."""
        try:
            msg = json.loads(message_str)
        except json.JSONDecodeError:
            return

        msg_type = msg.get("type") or msg.get("cmd")
        market_ticker = msg.get("market_ticker") or msg.get("ticker") or "UNKNOWN"

        if msg_type == "orderbook_snapshot":
            self.book_manager.apply_snapshot(market_ticker, msg.get("msg", msg))
            logger.info(f"[SNAPSHOT] Seeded orderbook snapshot for ticker {market_ticker}")

        elif msg_type == "orderbook_delta" or msg.get("channel") == "orderbook_delta":
            delta_data = msg.get("msg", msg)
            changed, top_summary = self.book_manager.apply_delta(market_ticker, delta_data)
            self.received_deltas_count += 1

            if self.dry_run and self.received_deltas_count <= 3:
                print(f"\n[DELTA #{self.received_deltas_count}] Ticker: {market_ticker}")
                print(json.dumps({
                    "ticker": market_ticker,
                    "delta": delta_data,
                    "top_of_book": top_summary
                }, indent=2))

            if changed:
                # Forward real-time tick to OddsSanityFirewall & ArbitrageSteamAgent
                tick_record = {
                    "source": "Kalshi_WebSocket",
                    "event_id": market_ticker,
                    "canonical_event_id": f"KALSHI_{market_ticker}",
                    "league": "MULTI_SPORT",
                    "market_kind": "game",
                    "bookmaker": "Kalshi Live WS",
                    "american_odds": -110 if top_summary["best_yes_bid"] == 0 else int(round((100 / (top_summary["implied_probability"] or 0.5)) - 100)),
                    "line": top_summary["implied_probability"],
                    "ingested_at_utc": top_summary["timestamp"]
                }
                
                # Execute sub-second firewall & arbitrage evaluation
                self.firewall.validate([tick_record])
                arb_findings = self.arb_agent.scan([tick_record])
                self.webhook_mgr.evaluate_and_send(arb_findings)
                self._persist_live_orderbook()

    async def start(self) -> None:
        """Main daemon loop with exponential backoff reconnects."""
        headers, ws_url = generate_kalshi_auth_headers()
        tickers = discover_active_sports_tickers()

        if self.dry_run:
            print("=" * 70)
            print("DESTINY AGENT FLEET — KALSHI WEBSOCKET DAEMON DRY RUN")
            print("=" * 70)
            print(f"Target WebSocket Endpoint: {ws_url}")
            print(f"Authentication Mode: {'Authenticated (RSA-PSS)' if headers else 'Public Stream / Fallback'}")
            print(f"Subscribed Tickers Count: {len(tickers)}")

        backoff = 5
        max_backoff = 60

        while True:
            try:
                logger.info(f"Connecting to Kalshi WebSocket ({ws_url})...")
                connect_kwargs = {"ping_interval": 20, "ping_timeout": 10}
                if headers:
                    connect_kwargs["additional_headers"] = headers

                try:
                    ws_ctx = websockets.connect(ws_url, **connect_kwargs)
                except TypeError:
                    if "additional_headers" in connect_kwargs:
                        connect_kwargs["extra_headers"] = connect_kwargs.pop("additional_headers")
                    ws_ctx = websockets.connect(ws_url, **connect_kwargs)

                async with ws_ctx as ws:
                    logger.info("WebSocket Connection Handshake Established Successfully!")
                    backoff = 5  # Reset backoff on successful handshake

                    # Send subscription payload
                    sub_payload = {
                        "id": 1,
                        "cmd": "subscribe",
                        "params": {
                            "channels": ["orderbook_delta"],
                            "market_tickers": tickers
                        }
                    }
                    await ws.send(json.dumps(sub_payload))
                    logger.info(f"Sent orderbook_delta subscription request for {len(tickers)} tickers.")

                    # Message processing loop
                    async for message in ws:
                        await self.handle_message(message)
                        if self.dry_run and self.received_deltas_count >= 3:
                            logger.info("Dry-run limit of 3 orderbook_delta events reached. Exiting cleanly.")
                            return

            except (websockets.exceptions.WebSocketException, OSError, Exception) as err:
                logger.warning(f"WebSocket connection error: {err}")
                if self.dry_run:
                    logger.info("Operating in dry-run synthetic mode (missing active WS stream). Generating 3 sample deltas...")
                    await self._simulate_synthetic_deltas(tickers)
                    return

                logger.info(f"Applying exponential backoff: reconnecting in {backoff} seconds...")
                await asyncio.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)

    async def _simulate_synthetic_deltas(self, tickers: List[str]) -> None:
        """Generates synthetic delta events for dry-run verification when offline/unauthenticated."""
        sample_tickers = tickers[:3] or ["KXNFLGAME", "KXMLBGAME", "KXNBAGAME"]
        for i, ticker in enumerate(sample_tickers, 1):
            mock_delta = {
                "type": "orderbook_delta",
                "market_ticker": ticker,
                "msg": {
                    "price": 54,
                    "delta": 10,
                    "side": "yes"
                }
            }
            await self.handle_message(json.dumps(mock_delta))
            await asyncio.sleep(0.2)

def main():
    parser = argparse.ArgumentParser(description="Kalshi Real-Time WebSocket Streaming Daemon")
    parser.add_argument("--dry-run", action="store_true", help="Print handshake status and first 3 received orderbook_delta events then exit")
    args = parser.parse_args()

    daemon = KalshiWebSocketDaemon(dry_run=args.dry_run)
    try:
        asyncio.run(daemon.start())
    except KeyboardInterrupt:
        logger.info("Kalshi WebSocket daemon stopped by user. Exiting cleanly.")

if __name__ == "__main__":
    main()
