#!/usr/bin/env python3
"""
=============================================================================
DESTINY SPORTS ENGINE — Injury Impact & Roster Intelligence Agent (Agent #15)
100% Free Live Multi-League Injury Ingestion & Scratch Detection Engine
=============================================================================
Endpoints:
  - NFL:    https://site.web.api.espn.com/apis/site/v2/sports/football/nfl/injuries
  - NCAAF:  https://site.web.api.espn.com/apis/site/v2/sports/football/college-football/injuries
  - NBA:    https://site.web.api.espn.com/apis/site/v2/sports/basketball/nba/injuries
  - NCAAB:  https://site.web.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/injuries
  - MLB:    https://site.web.api.espn.com/apis/site/v2/sports/baseball/mlb/injuries
  - NHL:    https://site.web.api.espn.com/apis/site/v2/sports/hockey/nhl/injuries
  - WNBA:   https://site.web.api.espn.com/apis/site/v2/sports/basketball/wnba/injuries
=============================================================================
"""

import sys
import os
import json
import time
import re
import datetime
import logging
import asyncio
import urllib.request
from typing import List, Dict, Any, Optional

# Ensure local backend modules are importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from quality_agent import DataQualityAgent

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("sports_engine.injury_agent")

INJURY_ENDPOINTS = {
    "NFL": "https://site.web.api.espn.com/apis/site/v2/sports/football/nfl/injuries",
    "NCAAF": "https://site.web.api.espn.com/apis/site/v2/sports/football/college-football/injuries",
    "NBA": "https://site.web.api.espn.com/apis/site/v2/sports/basketball/nba/injuries",
    "NCAAB": "https://site.web.api.espn.com/apis/site/v2/sports/basketball/mens-college-basketball/injuries",
    "MLB": "https://site.web.api.espn.com/apis/site/v2/sports/baseball/mlb/injuries",
    "NHL": "https://site.web.api.espn.com/apis/site/v2/sports/hockey/nhl/injuries",
    "WNBA": "https://site.web.api.espn.com/apis/site/v2/sports/basketball/wnba/injuries"
}

CRITICAL_KEYWORDS = {"out", "injured reserve", "ir", "60-day il", "60-day-il", "suspended", "injury_status_out", "pup"}
VOLATILE_KEYWORDS = {"questionable", "doubtful", "day-to-day", "day-to-day", "gtd", "game-time decision"}

SNAPSHOT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "snapshots", "injury_report_latest.json")
FALLBACK_SNAPSHOT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "injury_report_latest.json")

def normalize_name(name: str) -> str:
    """Normalizes player name string for fuzzy matching (e.g., 'Amon-Ra St. Brown' -> 'amonrastbrown')."""
    if not name:
        return ""
    return re.sub(r'[^a-z0-9]', '', str(name).lower())

class InjuryImpactAgent:
    """
    Agent #15: Ingests, categorizes, and tracks real-time roster injuries across all 7 leagues.
    """
    def __init__(self):
        self.quality_agent = DataQualityAgent()
        self.all_injuries: List[Dict[str, Any]] = []
        self.critical_scratches: List[Dict[str, Any]] = []
        self.volatile_decisions: List[Dict[str, Any]] = []
        self.last_updated_utc: Optional[str] = None
        self._load_cached_snapshot()

    def _load_cached_snapshot(self) -> None:
        """Loads historical snapshot if available."""
        target = SNAPSHOT_PATH if os.path.exists(SNAPSHOT_PATH) else FALLBACK_SNAPSHOT_PATH
        if os.path.exists(target):
            try:
                with open(target, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.all_injuries = data.get("injuries", [])
                    self.critical_scratches = data.get("critical_scratches", [])
                    self.volatile_decisions = data.get("volatile_decisions", [])
                    self.last_updated_utc = data.get("timestamp")
            except Exception as e:
                logger.warning(f"Could not load cached injury snapshot: {e}")

    def categorize_status(self, raw_status: str) -> str:
        """Categorizes raw status string into CRITICAL, VOLATILE, or OTHER."""
        st = str(raw_status).lower().strip()
        for kw in CRITICAL_KEYWORDS:
            if kw in st:
                return "CRITICAL"
        for kw in VOLATILE_KEYWORDS:
            if kw in st:
                return "VOLATILE"
        return "OTHER"

    def fetch_league_injuries(self, league: str, url: str) -> List[Dict[str, Any]]:
        """Synchronous fetcher for a single league's injury API endpoint."""
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        req = urllib.request.Request(url, headers=headers)
        records = []
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                for team_group in data.get("injuries", []):
                    team_info = team_group.get("team") or (team_group.get("injuries", [{}])[0].get("athlete", {}).get("team") if team_group.get("injuries") else {})
                    team_name = team_info.get("displayName") or team_info.get("name") or "Unknown Team"
                    team_abbrev = team_info.get("abbreviation") or "UNK"
                    canonical_id = self.quality_agent.resolve_team(team_name, league) or f"{league}_{team_abbrev}"

                    for item in team_group.get("injuries", []):
                        ath = item.get("athlete", {})
                        ath_name = ath.get("displayName") or ath.get("fullName") or "Unknown Player"
                        ath_id = str(ath.get("id") or item.get("id") or "")
                        pos = ath.get("position", {}).get("abbreviation") or ath.get("position", {}).get("name") or "N/A"
                        
                        raw_status = item.get("status") or item.get("type", {}).get("description") or item.get("details", {}).get("fantasyStatus", {}).get("description") or "Unknown"
                        details = item.get("details", {})
                        injury_type = details.get("type") or item.get("type", {}).get("name") or "Undisclosed"
                        
                        notes_items = item.get("notes", {}).get("items", [])
                        notes = item.get("longComment") or item.get("shortComment") or (notes_items[0].get("text") if notes_items else "")

                        category = self.categorize_status(raw_status)

                        records.append({
                            "league": league,
                            "team_name": team_name,
                            "team_abbrev": team_abbrev,
                            "canonical_team_id": canonical_id,
                            "athlete_name": ath_name,
                            "normalized_name": normalize_name(ath_name),
                            "athlete_id": ath_id,
                            "position": pos,
                            "status": raw_status,
                            "category": category,
                            "injury_type": injury_type,
                            "analyst_notes": notes,
                            "updated_at_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()
                        })
        except Exception as err:
            logger.warning(f"Error fetching {league} injuries from {url}: {err}")

        return records

    def scan_all_leagues(self) -> Dict[str, Any]:
        """
        Fetches live injury scoreboards across all 7 leagues and archives structured snapshot.
        """
        logger.info("Gathering live injury & roster reports across 7 leagues...")
        all_records = []
        by_league = {}

        for lg, url in INJURY_ENDPOINTS.items():
            league_recs = self.fetch_league_injuries(lg, url)
            all_records.extend(league_recs)
            by_league[lg] = len(league_recs)

        self.all_injuries = all_records
        self.critical_scratches = [r for r in all_records if r["category"] == "CRITICAL"]
        self.volatile_decisions = [r for r in all_records if r["category"] == "VOLATILE"]
        self.last_updated_utc = datetime.datetime.now(datetime.timezone.utc).isoformat()

        snapshot = {
            "timestamp": self.last_updated_utc,
            "total_injuries": len(all_records),
            "critical_out": len(self.critical_scratches),
            "volatile_q": len(self.volatile_decisions),
            "by_league": by_league,
            "critical_scratches": self.critical_scratches,
            "volatile_decisions": self.volatile_decisions,
            "injuries": all_records
        }

        self._archive_snapshot(snapshot)
        logger.info(f"Injury Scan Complete: Total: {len(all_records)} | Critical Out: {len(self.critical_scratches)} | Volatile Q: {len(self.volatile_decisions)}")
        return snapshot

    def _archive_snapshot(self, snapshot: Dict[str, Any]) -> None:
        """Saves injury report snapshot to disk."""
        os.makedirs(os.path.dirname(SNAPSHOT_PATH), exist_ok=True)
        for target in [SNAPSHOT_PATH, FALLBACK_SNAPSHOT_PATH]:
            try:
                with open(target, "w", encoding="utf-8") as f:
                    json.dump(snapshot, f, indent=2)
            except Exception as err:
                logger.warning(f"Could not save injury snapshot to {target}: {err}")

    # -- Interoperability Helper Methods -------------------------------------

    def is_player_out(self, player_name: str, team_alias: Optional[str] = None) -> bool:
        """
        Checks if a player is currently in CRITICAL scratch status (Out, IR, etc.).
        Supports fuzzy name matching (e.g. 'Amon-Ra St. Brown' vs 'A. St. Brown').
        """
        if not player_name:
            return False
        norm_target = normalize_name(player_name)
        if not norm_target:
            return False

        for rec in self.critical_scratches:
            rec_norm = rec["normalized_name"]
            # Direct match or substring match
            if norm_target in rec_norm or rec_norm in norm_target or (len(norm_target) > 5 and norm_target[-6:] in rec_norm):
                if team_alias:
                    canon = self.quality_agent.resolve_team(team_alias, rec["league"])
                    if canon and rec["canonical_team_id"] and canon != rec["canonical_team_id"]:
                        continue
                return True
        return False

    def get_team_injuries(self, team_alias: str) -> List[Dict[str, Any]]:
        """Returns all active injury records matching team alias or canonical ID."""
        if not team_alias:
            return []
        matching = []
        for rec in self.all_injuries:
            if team_alias.lower() in rec["team_name"].lower() or team_alias.upper() == rec["team_abbrev"] or team_alias.upper() == rec["canonical_team_id"]:
                matching.append(rec)
        return matching

    def get_critical_scratches(self, league: Optional[str] = None) -> List[Dict[str, Any]]:
        """Returns all CRITICAL scratch records, optionally filtered by league."""
        if not league:
            return self.critical_scratches
        return [r for r in self.critical_scratches if r["league"].upper() == league.upper()]


def main():
    """Standalone CLI test harness for Injury Impact Agent."""
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    print("=" * 70)
    print("DESTINY AGENT FLEET — INJURY & ROSTER INTEL AGENT DRY RUN")
    print("=" * 70)

    agent = InjuryImpactAgent()
    report = agent.scan_all_leagues()

    print(f"\nIngested {report['total_injuries']} Total Injuries across 7 Leagues.")
    print(f"Critical Scratches (OUT / IR): {report['critical_out']}")
    print(f"Volatile Decisions (Questionable / Day-To-Day): {report['volatile_q']}")
    print("\nLeague Breakdown:")
    for lg, count in report['by_league'].items():
        print(f"  - {lg}: {count} records")

    if report['critical_scratches']:
        print("\nSample Critical Scratch Record:")
        print(json.dumps(report['critical_scratches'][0], indent=2))

if __name__ == "__main__":
    main()
