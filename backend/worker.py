#!/usr/bin/env python3
"""
=============================================================================
DESTINY SPORTS ENGINE — Background Worker Scaffold (Python Engine)
Continuous Asynchronous Loop:
  1. Ingest live lines/props from Kalshi trade API / Sportsbooks endpoints.
  2. Normalize away vs. home spreads, totals, and props into clean schema.
  3. Push/upsert structured snapshot into Database (Supabase) + local fallback cache.
  4. Resilient error handling with exponential backoff logging.
=============================================================================
"""

import sys
import os
import time
import argparse
import asyncio
import logging
import datetime
import aiohttp
from typing import List, Dict, Any

# Ensure local modules are importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from normalizer import normalize_market, create_snapshot
from db import DatabaseManager
from weather_agent import generate_all_stadium_weather
from quality_agent import DataQualityAgent
from arb_agent import ArbitrageSteamAgent
from props_hunter_agent import PropsHunterAgent
from fetchers.espn_fetcher import fetch_all_sports_odds
from fetchers.kalshi_fetcher import fetch_sports_markets

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("sports_engine.worker")

# Target Series Tickers for Sports & Props Ingestion
SERIES_LIST = [
    # Game / Moneyline / Spread / Total
    {"ticker": "KXMLBGAME",   "league": "MLB",   "kind": "game"},
    {"ticker": "KXMLBSPREAD", "league": "MLB",   "kind": "spread"},
    {"ticker": "KXMLBTOTAL",  "league": "MLB",   "kind": "total"},
    {"ticker": "KXNFLGAME",   "league": "NFL",   "kind": "game"},
    {"ticker": "KXNFLSPREAD", "league": "NFL",   "kind": "spread"},
    {"ticker": "KXNFLTOTAL",  "league": "NFL",   "kind": "total"},
    {"ticker": "KXNBAGAME",   "league": "NBA",   "kind": "game"},
    {"ticker": "KXNBASPREAD", "league": "NBA",   "kind": "spread"},
    {"ticker": "KXNBATOTAL",  "league": "NBA",   "kind": "total"},
    {"ticker": "KXNHLGAME",   "league": "NHL",   "kind": "game"},
    {"ticker": "KXNHLSPREAD", "league": "NHL",   "kind": "spread"},
    {"ticker": "KXNHLTOTAL",  "league": "NHL",   "kind": "total"},
    {"ticker": "KXNCAAFGAME", "league": "NCAAF", "kind": "game"},
    {"ticker": "KXWNBAGAME",  "league": "WNBA",  "kind": "game"},

    # Player Props
    {"ticker": "KXNBAPTS",     "league": "NBA",  "kind": "prop", "stat": "Points"},
    {"ticker": "KXNBAREB",     "league": "NBA",  "kind": "prop", "stat": "Rebounds"},
    {"ticker": "KXNBAAST",     "league": "NBA",  "kind": "prop", "stat": "Assists"},
    {"ticker": "KXNBA3PT",     "league": "NBA",  "kind": "prop", "stat": "3-Pointers"},
    {"ticker": "KXNFLPASSYDS", "league": "NFL",  "kind": "prop", "stat": "Passing Yards"},
    {"ticker": "KXNFLRSHYDS",  "league": "NFL",  "kind": "prop", "stat": "Rushing Yards"},
    {"ticker": "KXNFLRECYDS",  "league": "NFL",  "kind": "prop", "stat": "Receiving Yards"},
    {"ticker": "KXNFLREC",     "league": "NFL",  "kind": "prop", "stat": "Receptions"},
]

KALSHI_API_BASE = "https://api.elections.kalshi.com/trade-api/v2/markets"

async def fetch_series(session: aiohttp.ClientSession, item: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Fetch open markets for a single series ticker from Kalshi API."""
    ticker = item["ticker"]
    url = f"{KALSHI_API_BASE}?series_ticker={ticker}&status=open&limit=500"
    try:
        async with session.get(url, timeout=aiohttp.ClientTimeout(total=10)) as response:
            if response.status != 200:
                logger.warning(f"HTTP {response.status} when querying ticker {ticker}")
                return []
            data = await response.json()
            markets = data.get("markets", [])
            for m in markets:
                m["_league"] = item["league"]
                m["_kind"] = item["kind"]
                if "stat" in item:
                    m["_stat"] = item["stat"]
            return markets
    except Exception as err:
        logger.warning(f"Network error querying ticker {ticker}: {err}")
        return []

async def run_ingestion_cycle(db_manager: DatabaseManager) -> int:
    """
    Executes one ingestion -> normalization -> database persistence cycle.
    """
    start_time = time.time()
    logger.info("Starting ingestion cycle from live providers...")

    async with aiohttp.ClientSession() as session:
        tasks = [fetch_series(session, item) for item in SERIES_LIST]
        results = await asyncio.gather(*tasks, return_exceptions=True)

    espn_result, kalshi_public_result = await asyncio.gather(
        fetch_all_sports_odds(),
        fetch_sports_markets(),
        return_exceptions=True
    )

    raw_markets = []
    for res in results:
        if isinstance(res, list):
            raw_markets.extend(res)

    espn_records = espn_result.get("records", []) if isinstance(espn_result, dict) else []
    kalshi_public_records = kalshi_public_result.get("records", []) if isinstance(kalshi_public_result, dict) else []

    raw_markets.extend(espn_records)
    raw_markets.extend(kalshi_public_records)

    logger.info(f"Ingested {len(raw_markets)} raw market records (Kalshi Series: {len(raw_markets) - len(espn_records) - len(kalshi_public_records)}, ESPN Free: {len(espn_records)}, Kalshi Public: {len(kalshi_public_records)}).")

    # Persist Live Market Stream Payload Snapshot
    snapshots_dir = os.path.join(os.path.dirname(__file__), "snapshots")
    os.makedirs(snapshots_dir, exist_ok=True)
    live_stream_payload = {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "total_records": len(raw_markets),
        "sources": {
            "espn_records": len(espn_records),
            "kalshi_public_records": len(kalshi_public_records),
            "kalshi_series_records": len(raw_markets) - len(espn_records) - len(kalshi_public_records)
        },
        "records": raw_markets
    }
    for path_target in [
        os.path.join(snapshots_dir, "live_market_stream.json"),
        os.path.join(os.path.dirname(__file__), "live_market_stream.json")
    ]:
        try:
            import json
            with open(path_target, "w", encoding="utf-8") as f:
                json.dump(live_stream_payload, f, indent=2)
        except Exception as write_err:
            logger.warning(f"Could not save live market stream to {path_target}: {write_err}")

    # Run Data Quality & Feed Guardian 8-Gate Audit
    try:
        quality_agent = DataQualityAgent()
        audited_records, health_report = quality_agent.audit(raw_markets, sport="MULTI_SPORT")
        records_to_normalize = audited_records if audited_records else raw_markets
        health_status = health_report.get("status", "HEALTHY")
    except Exception as q_err:
        logger.warning(f"Could not complete DataQualityAgent audit: {q_err}")
        records_to_normalize = raw_markets
        health_status = "DEGRADED"

    normalized_records = []
    for raw in records_to_normalize:
        norm = normalize_market(raw)
        if norm:
            normalized_records.append(norm)

    elapsed = time.time() - start_time
    logger.info(f"Normalized {len(normalized_records)} valid lines/props in {elapsed:.2f} seconds.")

    snapshot = create_snapshot(normalized_records, elapsed)
    db_manager.push_snapshot(snapshot)

    # Run Weather Edge Microclimate Forecast Analysis
    try:
        weather_snap = generate_all_stadium_weather()
        venues_count = weather_snap.get("total_venues_scanned", 8)
    except Exception as w_err:
        logger.warning(f"Could not complete weather ingestion cycle: {w_err}")
        venues_count = 8

    # Run Line Discrepancy, Arbitrage & Steam Movement Discovery Scan
    try:
        arb_agent = ArbitrageSteamAgent()
        arb_summary = arb_agent.scan(records_to_normalize)
        total_arb_findings = arb_summary.get("total_arbs_found", 0) + arb_summary.get("total_middles_found", 0) + arb_summary.get("total_steam_moves", 0)
    except Exception as a_err:
        logger.warning(f"Could not complete Arbitrage & Steam scan: {a_err}")
        total_arb_findings = 0

    # Run Player Props Matrix & Cross-Book Line Hunter Scan
    try:
        props_hunter = PropsHunterAgent()
        props_summary = props_hunter.scan(records_to_normalize)
        total_props_findings = props_summary.get("matrix_count", 0)
    except Exception as p_err:
        logger.warning(f"Could not complete Props Hunter scan: {p_err}")
        total_props_findings = 0

    # Update Fleet Telemetry
    db_manager.update_agent_telemetry(
        agent_id="espn_scraper",
        agent_name="ESPN Free Odds Scraper 🏈⚾🏀",
        status="Live",
        records_processed=len(espn_records),
        latency_ms=round(elapsed * 1000, 2)
    )
    db_manager.update_agent_telemetry(
        agent_id="kalshi_scraper",
        agent_name="Kalshi Market Scraper",
        status="Live",
        records_processed=len(kalshi_public_records) if kalshi_public_records else len(normalized_records),
        latency_ms=round(elapsed * 1000, 2)
    )
    db_manager.update_agent_telemetry(
        agent_id="prop_normalizer",
        agent_name="Player Props Normalizer",
        status="Live",
        records_processed=len([r for r in normalized_records if r.get('market_kind') == 'prop']),
        latency_ms=round(elapsed * 1000, 2)
    )
    db_manager.update_agent_telemetry(
        agent_id="data_quality",
        agent_name="Data Quality & Feed Guardian Agent 🛡️",
        status="Live" if health_status == "HEALTHY" else "Active",
        records_processed=len(audited_records) if 'audited_records' in locals() else len(normalized_records),
        latency_ms=round(elapsed * 1000, 2)
    )
    db_manager.update_agent_telemetry(
        agent_id="weather_agent",
        agent_name="Atmospheric & Weather Edge Agent 🌦️",
        status="Live",
        records_processed=venues_count,
        latency_ms=round(elapsed * 1000, 2)
    )
    db_manager.update_agent_telemetry(
        agent_id="arb_steam_hunter",
        agent_name="Line Discrepancy, Arbitrage & Steam Hunter ⚡",
        status="Live",
        records_processed=total_arb_findings,
        latency_ms=round(elapsed * 1000, 2)
    )
    db_manager.update_agent_telemetry(
        agent_id="props_matrix_hunter",
        agent_name="Player Props Matrix & Cross-Book Hunter 🎯",
        status="Active (Cross-Book Prop Ingestion)",
        records_processed=total_props_findings,
        latency_ms=round(elapsed * 1000, 2)
    )
    db_manager.update_agent_telemetry(
        agent_id="supabase_ingestor",
        agent_name="Supabase DB Ingestor",
        status="Live",
        records_processed=len(normalized_records),
        latency_ms=round(elapsed * 1000, 2)
    )

    return len(normalized_records)

async def worker_loop(interval: int, once: bool = False):
    """
    Continuous worker loop with exponential backoff error recovery.
    """
    logger.info(f"Initializing Sports Data Background Engine (Loop Interval: {interval}s)...")
    db_manager = DatabaseManager()

    backoff = 5
    max_backoff = 60

    while True:
        try:
            records_count = await run_ingestion_cycle(db_manager)
            backoff = 5  # Reset backoff on successful cycle
            logger.info(f"Ingestion cycle completed successfully ({records_count} records). Sleeping for {interval}s...")
        except Exception as e:
            logger.error(f"Error during ingestion loop: {e}", exc_info=True)
            logger.warning(f"Applying exponential backoff: retrying in {backoff} seconds...")
            await asyncio.sleep(backoff)
            backoff = min(backoff * 2, max_backoff)
            continue

        if once:
            logger.info("Flag --once specified. Exiting worker process.")
            break

        await asyncio.sleep(interval)

def main():
    parser = argparse.ArgumentParser(description="Destiny Sports Engine Background Worker")
    parser.add_argument("--interval", type=int, default=45, help="Polling interval in seconds (default: 45)")
    parser.add_argument("--once", action="store_true", help="Run a single ingestion iteration and exit")
    args = parser.parse_args()

    try:
        asyncio.run(worker_loop(interval=args.interval, once=args.once))
    except KeyboardInterrupt:
        logger.info("Worker process interrupted by user. Exiting cleanly.")

if __name__ == "__main__":
    main()
