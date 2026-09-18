#!/usr/bin/env python3
"""
=============================================================================
DESTINY SPORTS ENGINE — ESPN Site API Free Odds & Scoreboard Fetcher
100% Free Live Scores & Betting Odds Ingestion (NFL, MLB, NBA)
=============================================================================
"""

import sys
import os
import json
import time
import datetime
import logging
import re
import asyncio
import urllib.request
from typing import List, Dict, Any, Optional

# Ensure local modules are importable
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("sports_engine.espn_fetcher")

# ESPN Free CDN Scoreboard Endpoints
ESPN_LEAGUE_ENDPOINTS = {
    "NFL": "https://cdn.espn.com/core/nfl/scoreboard?xhr=1",
    "MLB": "https://cdn.espn.com/core/mlb/scoreboard?xhr=1",
    "NBA": "https://cdn.espn.com/core/nba/scoreboard?xhr=1"
}

def parse_espn_event(event: Dict[str, Any], league: str) -> List[Dict[str, Any]]:
    """
    Parses a single ESPN scoreboard event into clean, normalized market records.
    """
    records = []
    try:
        event_id = event.get("id", "")
        event_name = event.get("name", "")
        date_str = event.get("date", "")
        
        competitions = event.get("competitions", [])
        if not competitions:
            return records

        comp = competitions[0]
        competitors = comp.get("competitors", [])
        if len(competitors) < 2:
            return records

        home_team_info = next((c for c in competitors if c.get("homeAway") == "home"), competitors[0])
        away_team_info = next((c for c in competitors if c.get("homeAway") == "away"), competitors[1])

        home_team = home_team_info.get("team", {}).get("displayName") or home_team_info.get("team", {}).get("name", "Home")
        home_abbrev = home_team_info.get("team", {}).get("abbreviation") or "HOME"
        home_score = home_team_info.get("score", "0")

        away_team = away_team_info.get("team", {}).get("displayName") or away_team_info.get("team", {}).get("name", "Away")
        away_abbrev = away_team_info.get("team", {}).get("abbreviation") or "AWAY"
        away_score = away_team_info.get("score", "0")

        status_type = comp.get("status", {}).get("type", {})
        game_status = status_type.get("description", "Scheduled")
        game_state = status_type.get("state", "pre")  # pre, in, post

        # Odds parsing
        odds_list = comp.get("odds", [])
        if not odds_list:
            # Baseline game record if odds array is empty
            records.append({
                "source": "ESPN",
                "canonical_event_id": f"{league}_{event_id}",
                "event_id": event_id,
                "league": league,
                "market_kind": "game",
                "title": f"{away_team} @ {home_team}",
                "home_team": home_team,
                "away_team": away_team,
                "home_abbrev": home_abbrev,
                "away_abbrev": away_abbrev,
                "home_score": home_score,
                "away_score": away_score,
                "game_status": game_status,
                "game_state": game_state,
                "bookmaker": "ESPN Consensus",
                "american_odds": -110,
                "line": 0.0,
                "ingested_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()
            })
            return records

        for odds_item in odds_list:
            provider = odds_item.get("provider", {}).get("name", "ESPN BET")
            details = odds_item.get("details", "")  # e.g. "BUF -2.5"
            over_under = odds_item.get("overUnder")  # e.g. 48.5
            
            away_ml = odds_item.get("awayTeamOdds", {}).get("moneyLine", -110)
            home_ml = odds_item.get("homeTeamOdds", {}).get("moneyLine", -110)

            # Spread line extraction
            spread_line = 0.0
            if details:
                match = re.search(r'([-+]?\d+\.?\d*)', details)
                if match:
                    spread_line = float(match.group(1))

            # Moneyline Record
            records.append({
                "source": "ESPN",
                "canonical_event_id": f"{league}_{event_id}",
                "event_id": event_id,
                "league": league,
                "market_kind": "game",
                "title": f"{away_team} @ {home_team} - Moneyline",
                "home_team": home_team,
                "away_team": away_team,
                "home_abbrev": home_abbrev,
                "away_abbrev": away_abbrev,
                "home_score": home_score,
                "away_score": away_score,
                "game_status": game_status,
                "game_state": game_state,
                "bookmaker": provider,
                "american_odds": home_ml,
                "line": 0.0,
                "ingested_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()
            })

            # Spread Record
            records.append({
                "source": "ESPN",
                "canonical_event_id": f"{league}_{event_id}",
                "event_id": event_id,
                "league": league,
                "market_kind": "spread",
                "title": f"{away_team} @ {home_team} - Spread",
                "home_team": home_team,
                "away_team": away_team,
                "home_abbrev": home_abbrev,
                "away_abbrev": away_abbrev,
                "spread_line": spread_line,
                "bookmaker": provider,
                "american_odds": -110,
                "ingested_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()
            })

            # Total Record (if available)
            if over_under is not None:
                records.append({
                    "source": "ESPN",
                    "canonical_event_id": f"{league}_{event_id}",
                    "event_id": event_id,
                    "league": league,
                    "market_kind": "total",
                    "title": f"{away_team} @ {home_team} - Over/Under Total",
                    "home_team": home_team,
                    "away_team": away_team,
                    "total_line": float(over_under),
                    "bookmaker": provider,
                    "american_odds": -110,
                    "ingested_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()
                })

    except Exception as err:
        logger.warning(f"Error parsing ESPN event: {err}")

    return records

def _sync_fetch_league(league: str, url: str) -> List[Dict[str, Any]]:
    """Synchronous fetcher for a single ESPN league scoreboard."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9"
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            raw_bytes = resp.read()
            data = json.loads(raw_bytes.decode('utf-8'))
            events = data.get("content", {}).get("sbData", {}).get("events", []) or data.get("events", [])
            league_records = []
            for ev in events:
                parsed = parse_espn_event(ev, league)
                league_records.extend(parsed)
            logger.info(f"Fetched {len(events)} games ({len(league_records)} market lines) from ESPN {league}.")
            return league_records
    except Exception as err:
        logger.warning(f"Error fetching ESPN {league}: {err}")
        return []

async def fetch_all_sports_odds() -> Dict[str, Any]:
    """
    Orchestrates concurrent pulls across all free ESPN scoreboards (NFL, MLB, NBA).
    """
    logger.info("Connecting to ESPN Free Site API scoreboards...")
    loop = asyncio.get_event_loop()
    tasks = [
        loop.run_in_executor(None, _sync_fetch_league, league, url)
        for league, url in ESPN_LEAGUE_ENDPOINTS.items()
    ]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    all_records = []
    for res in results:
        if isinstance(res, list):
            all_records.extend(res)

    logger.info(f"ESPN Free API Ingestion Complete: {len(all_records)} live market records fetched.")
    return {
        "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "total_records": len(all_records),
        "records": all_records
    }

def main():
    """Dry run test for ESPN Fetcher."""
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    print("=" * 70)
    print("DESTINY AGENT FLEET — ESPN FREE ODDS FETCHER DRY RUN")
    print("=" * 70)

    result = asyncio.run(fetch_all_sports_odds())
    print(f"\nFetched {result['total_records']} total market lines from ESPN.")
    if result["records"]:
        print("\nSample ESPN Live Event Record:")
        print(json.dumps(result["records"][0], indent=2))

if __name__ == "__main__":
    main()
