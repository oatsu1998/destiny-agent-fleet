#!/usr/bin/env python3
"""
=============================================================================
DESTINY SPORTS ENGINE — Kalshi Public API Sports Fetcher
100% Free Live Trade API Markets Ingestion (NFL, MLB, NBA, NHL, Player Props)
=============================================================================
"""

import sys
import os
import json
import time
import datetime
import logging
import asyncio
import urllib.request
from typing import List, Dict, Any, Optional

# Ensure local modules are importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from normalizer import normalize_market

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("sports_engine.kalshi_fetcher")

KALSHI_MARKETS_URL = "https://api.elections.kalshi.com/trade-api/v2/markets?status=open&limit=200"

def extract_price_cents(m: Dict[str, Any]) -> int:
    """Extract price in cents (1-99) or default to 50 cents baseline."""
    for field in ['last_price_dollars', 'yes_bid_dollars', 'yes_ask_dollars', 'previous_price_dollars']:
        val = m.get(field)
        if val is not None and float(val) > 0:
            return round(float(val) * 100)
    for field in ['yes_bid', 'yes_ask', 'last_price']:
        val = m.get(field)
        if val is not None and int(val) > 0:
            return int(val)
    return 50

def _sync_fetch_kalshi_markets() -> List[Dict[str, Any]]:
    """Synchronous fetcher for open public markets from Kalshi Trade API."""
    req = urllib.request.Request(KALSHI_MARKETS_URL, headers={"User-Agent": "Mozilla/5.0"})
    try:
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode('utf-8'))
            raw_markets = data.get("markets", [])
            logger.info(f"Fetched {len(raw_markets)} raw markets from Kalshi Public API.")

            sports_records = []
            for m in raw_markets:
                ticker = m.get("ticker", "").upper()
                title = str(m.get("title") or "")
                
                # Tag sports series & sport metadata
                league = "GENERAL"
                sport = "general"
                kind = "game"

                if "KXCFB" in ticker or "NCAAF" in ticker or "COLLEGE FOOTBALL" in title.upper():
                    league = "NCAAF"
                    sport = "football"
                elif "KXCBB" in ticker or "NCAAB" in ticker or "COLLEGE BASKETBALL" in title.upper():
                    league = "NCAAB"
                    sport = "basketball"
                elif "KXNFL" in ticker or "NFL" in ticker or ("FOOTBALL" in title.upper() and "COLLEGE" not in title.upper()) or "LIONS" in title.upper() or "BILLS" in title.upper() or "CHIEFS" in title.upper():
                    league = "NFL"
                    sport = "football"
                elif "KXNHL" in ticker or "NHL" in ticker or "HOCKEY" in title.upper():
                    league = "NHL"
                    sport = "hockey"
                elif "KXWNBA" in ticker or "WNBA" in ticker:
                    league = "WNBA"
                    sport = "basketball"
                elif "KXMLB" in ticker or "MLB" in ticker or "BASEBALL" in title.upper() or "MARINERS" in title.upper() or "YANKEES" in title.upper():
                    league = "MLB"
                    sport = "baseball"
                elif "KXNBA" in ticker or "NBA" in ticker or "BASKETBALL" in title.upper() or "CLIPPERS" in title.upper() or "TIMBERWOLVES" in title.upper() or "CELTICS" in title.upper():
                    league = "NBA"
                    sport = "basketball"

                if "SPREAD" in ticker or "spread" in title.lower():
                    kind = "spread"
                elif "TOTAL" in ticker or "over" in title.lower() or "under" in title.lower():
                    kind = "total"
                elif "PTS" in ticker or "YDS" in ticker or "PROP" in ticker or "REC" in ticker or ":" in title:
                    kind = "prop"

                m["_league"] = league
                m["_sport"] = sport
                m["_kind"] = kind
                m["bookmaker"] = "Kalshi"
                m["provider"] = "Kalshi"

                # Ensure price cents field exists for normalizer
                price_cents = extract_price_cents(m)
                price_dollars = round(price_cents / 100.0, 2)
                if price_dollars <= 0.0 or price_dollars >= 1.0:
                    price_dollars = 0.50

                m["last_price_dollars"] = str(price_dollars)
                m["yes_bid_dollars"] = str(price_dollars)
                m["yes_ask_dollars"] = str(price_dollars)

                normalized = normalize_market(m)
                if normalized:
                    sports_records.append(normalized)

            logger.info(f"Filtered & normalized {len(sports_records)} active Kalshi sports markets.")
            return sports_records
    except Exception as err:
        logger.warning(f"Error fetching Kalshi public markets: {err}")
        return []

async def fetch_sports_markets() -> Dict[str, Any]:
    """
    Asynchronously fetches and normalizes live sports contract markets from Kalshi v2 public API.
    """
    logger.info("Connecting to Kalshi v2 Public Trade API...")
    loop = asyncio.get_event_loop()
    records = await loop.run_in_executor(None, _sync_fetch_kalshi_markets)

    return {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "total_records": len(records),
        "records": records
    }

def main():
    """Dry run test for Kalshi Fetcher."""
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    print("=" * 70)
    print("DESTINY AGENT FLEET — KALSHI PUBLIC SPORTS FETCHER DRY RUN")
    print("=" * 70)

    result = asyncio.run(fetch_sports_markets())
    print(f"\nFetched {result['total_records']} total normalized sports market lines from Kalshi.")
    if result["records"]:
        print("\nSample Kalshi Market Record:")
        print(json.dumps(result["records"][0], indent=2))

if __name__ == "__main__":
    main()
