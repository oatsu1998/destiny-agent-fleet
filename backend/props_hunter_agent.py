#!/usr/bin/env python3
"""
=============================================================================
DESTINY SPORTS ENGINE — Player Props Matrix & Cross-Book Line Hunter Agent
Normalizes Player Names & Stat Categories across Prop Kingz, FanDuel,
DraftKings, BetOnline, Bovada to detect Prop Arbs, Middles, and Ladder Edges.
=============================================================================
"""

import sys
import os
import json
import time
import datetime
import logging
import re
from typing import List, Dict, Any, Optional, Tuple

# Ensure local modules are importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("sports_engine.props_hunter")

# Player Canonical Dictionary Alias Mapping
PLAYER_ALIAS_MAP = {
    # NFL - Lions & Bills & Star Players
    "amon ra st brown": "Amon-Ra St. Brown",
    "amon-ra st. brown": "Amon-Ra St. Brown",
    "amon ra st. brown": "Amon-Ra St. Brown",
    "a. st. brown": "Amon-Ra St. Brown",
    "a. st brown": "Amon-Ra St. Brown",
    "amonra st brown": "Amon-Ra St. Brown",
    
    "jahmyr gibbs": "Jahmyr Gibbs",
    "j. gibbs": "Jahmyr Gibbs",
    
    "josh allen": "Josh Allen",
    "j. allen": "Josh Allen",
    
    "stefon diggs": "Stefon Diggs",
    "s. diggs": "Stefon Diggs",
    
    "patrick mahomes": "Patrick Mahomes",
    "p. mahomes": "Patrick Mahomes",
    
    "travis kelce": "Travis Kelce",
    "t. kelce": "Travis Kelce",
    
    "derrick henry": "Derrick Henry",
    "d. henry": "Derrick Henry",

    # NBA
    "luka doncic": "Luka Doncic",
    "l. doncic": "Luka Doncic",
    "luka dončić": "Luka Doncic",
    
    "nikola jokic": "Nikola Jokic",
    "n. jokic": "Nikola Jokic",
    "nikola jokić": "Nikola Jokic",
    
    "shai gilgeous alexander": "Shai Gilgeous-Alexander",
    "s. gilgeous alexander": "Shai Gilgeous-Alexander",
    "shai gilgeous-alexander": "Shai Gilgeous-Alexander",
    "sga": "Shai Gilgeous-Alexander",
    
    "giannis antetokounmpo": "Giannis Antetokounmpo",
    "g. antetokounmpo": "Giannis Antetokounmpo",
    
    "anthony davis": "Anthony Davis",
    "a. davis": "Anthony Davis",

    # MLB
    "shohei ohtani": "Shohei Ohtani",
    "s. ohtani": "Shohei Ohtani",
    "tarik skubal": "Tarik Skubal",
    "t. skubal": "Tarik Skubal"
}

# Stat Category Mapping
STAT_TYPE_MAP = {
    "receiving yards": "receiving_yards",
    "rec yds": "receiving_yards",
    "receiving_yards": "receiving_yards",
    "receptions": "receptions",
    "rec": "receptions",
    "passing yards": "passing_yards",
    "pass yds": "passing_yards",
    "passing_yards": "passing_yards",
    "rushing yards": "rushing_yards",
    "rush yds": "rushing_yards",
    "rushing_yards": "rushing_yards",
    "points": "player_points",
    "pts": "player_points",
    "player_points": "player_points",
    "rebounds": "rebounds",
    "reb": "rebounds",
    "assists": "assists",
    "ast": "assists",
    "3-pointers": "three_pointers",
    "3pt": "three_pointers",
    "three_pointers": "three_pointers",
    "strikeouts": "strikeouts",
    "so": "strikeouts",
    "k": "strikeouts"
}

def american_to_decimal(american_odds: float) -> float:
    """Converts American odds (+150, -110, etc.) to Decimal odds."""
    try:
        odds = float(american_odds)
        if odds == 0:
            return 1.0
        if odds > 0:
            return round((odds / 100.0) + 1.0, 4)
        else:
            return round((100.0 / abs(odds)) + 1.0, 4)
    except Exception:
        return 1.0

def normalize_player_name(raw_name: str) -> str:
    """Resolves player name variations to a single canonical name."""
    if not raw_name:
        return "Unknown Player"
    cleaned = raw_name.strip().lower()
    cleaned = re.sub(r'[^a-z0-9\s.-]', '', cleaned)
    return PLAYER_ALIAS_MAP.get(cleaned, raw_name.strip().title())

def normalize_stat_type(raw_stat: str) -> str:
    """Normalizes raw stat strings into standardized category keys."""
    if not raw_stat:
        return "general_prop"
    cleaned = raw_stat.strip().lower()
    return STAT_TYPE_MAP.get(cleaned, cleaned.replace(" ", "_"))

try:
    from injury_agent import InjuryImpactAgent
except ImportError:
    InjuryImpactAgent = None

class PropsHunterAgent:
    def __init__(self):
        if InjuryImpactAgent:
            try:
                self.injury_agent = InjuryImpactAgent()
            except Exception:
                self.injury_agent = None
        else:
            self.injury_agent = None

    def normalize_prop_entry(self, raw_entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Parses and standardizes player, team, stat type, line, over/under/milestone, odds, and sportsbook.
        """
        book = raw_entry.get("bookmaker") or raw_entry.get("provider") or raw_entry.get("book") or "DraftKings"
        player_raw = raw_entry.get("player") or raw_entry.get("player_name") or raw_entry.get("title") or "Unknown"
        
        # If player name is embedded in title (e.g. "Amon-Ra St. Brown - Receiving Yards")
        if " - " in player_raw:
            parts = player_raw.split(" - ")
            player_raw = parts[0]
            if not raw_entry.get("stat_type") and len(parts) > 1:
                raw_entry["stat_type"] = parts[1]

        canonical_player = normalize_player_name(player_raw)
        team = raw_entry.get("team") or raw_entry.get("team_code") or "NFL_DET"
        stat_type = normalize_stat_type(raw_entry.get("stat_type") or raw_entry.get("stat") or raw_entry.get("stat_category") or "receiving_yards")

        line = float(raw_entry.get("line") or raw_entry.get("line_value") or raw_entry.get("strike_line") or 0.0)
        odds = float(raw_entry.get("american_odds") or raw_entry.get("odds") or -110.0)
        dec_odds = american_to_decimal(odds)
        prop_kind = raw_entry.get("prop_kind") or raw_entry.get("type") or "main_line"  # main_line or milestone_over

        return {
            "player": canonical_player,
            "team": team,
            "stat_type": stat_type,
            "book": book,
            "line": line,
            "odds": odds,
            "decimal_odds": dec_odds,
            "prop_kind": prop_kind,
            "over_under": raw_entry.get("over_under") or ("over" if odds >= 0 else "under"),
            "raw": raw_entry
        }

    def aggregate_prop_matrix(self, props_list: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Groups props into a searchable matrix keyed by (canonical_player_id, prop_type).
        """
        matrix: Dict[str, Dict[str, Any]] = {}

        for raw_p in props_list:
            p = self.normalize_prop_entry(raw_p)
            key = f"{p['player']}|{p['stat_type']}"

            is_scratched = self.injury_agent.is_player_out(p['player'], p['team']) if self.injury_agent else False

            if key not in matrix:
                matrix[key] = {
                    "player": p["player"],
                    "team": p["team"],
                    "prop_type": p["stat_type"],
                    "status": "SCRATCHED_SUPPRESSED" if is_scratched else "ACTIVE",
                    "books": {},
                    "best_over": None,
                    "best_under": None,
                    "middle_window": {"spread_points": 0.0, "viable": False}
                }
            elif is_scratched:
                matrix[key]["status"] = "SCRATCHED_SUPPRESSED"

            entry = matrix[key]
            book = p["book"]

            if book not in entry["books"]:
                entry["books"][book] = []

            # Structure line entry under book
            line_info = {
                "line": p["line"],
                "type": p["prop_kind"],
                "odds": p["odds"],
                "dec": p["decimal_odds"],
                "over_under": p["over_under"]
            }
            entry["books"][book].append(line_info)

            # Evaluate Best Over (Lowest Line, Highest Odds)
            if p["over_under"] == "over":
                if not entry["best_over"] or p["line"] < entry["best_over"]["line"] or (p["line"] == entry["best_over"]["line"] and p["decimal_odds"] > entry["best_over"]["dec"]):
                    entry["best_over"] = {
                        "book": book,
                        "line": p["line"],
                        "odds": p["odds"],
                        "dec": p["decimal_odds"]
                    }

            # Evaluate Best Under (Highest Line, Highest Odds)
            if p["over_under"] == "under":
                if not entry["best_under"] or p["line"] > entry["best_under"]["line"] or (p["line"] == entry["best_under"]["line"] and p["decimal_odds"] > entry["best_under"]["dec"]):
                    entry["best_under"] = {
                        "book": book,
                        "line": p["line"],
                        "odds": p["odds"],
                        "dec": p["decimal_odds"]
                    }

        # Calculate Middle Window for each player prop
        for key, entry in matrix.items():
            if entry["best_over"] and entry["best_under"]:
                best_over_line = entry["best_over"]["line"]
                best_under_line = entry["best_under"]["line"]
                gap = round(best_under_line - best_over_line, 1)

                if gap >= 1.5:
                    entry["middle_window"] = {
                        "spread_points": gap,
                        "viable": True,
                        "over_book": entry["best_over"]["book"],
                        "over_line": best_over_line,
                        "under_book": entry["best_under"]["book"],
                        "under_line": best_under_line,
                        "summary": f"🎯 {gap} YD/PT Middle Window: Over {best_over_line} ({entry['best_over']['book']}) vs Under {best_under_line} ({entry['best_under']['book']})"
                    }
                else:
                    entry["middle_window"] = {
                        "spread_points": gap,
                        "viable": False
                    }

        return matrix

    def find_prop_discrepancies(self, matrix: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extracts top outlier values, prop arbs, market middles, and ladder milestone edges.
        """
        prop_arbs = []
        prop_middles = []
        ladder_edges = []

        for key, entry in matrix.items():
            if entry.get("status") == "SCRATCHED_SUPPRESSED":
                logger.info(f"Skipping prop discrepancy alerts for scratched player: {entry['player']}")
                continue

            player = entry["player"]
            stat_type = entry["prop_type"]

            # 1. Check Prop Arbitrage (Implied Prob < 1.0)
            if entry["best_over"] and entry["best_under"]:
                dec_over = entry["best_over"]["dec"]
                dec_under = entry["best_under"]["dec"]

                if dec_over > 1.0 and dec_under > 1.0:
                    ip = (1.0 / dec_over) + (1.0 / dec_under)
                    if ip < 0.999:
                        roi = round(((1.0 / ip) - 1.0) * 100.0, 2)
                        profit_usd = round(1000.0 * ((1.0 / ip) - 1.0), 2)
                        prop_arbs.append({
                            "player": player,
                            "stat_type": stat_type,
                            "type": "PROP_ARBITRAGE",
                            "implied_probability": round(ip, 4),
                            "roi_percent": roi,
                            "profit_on_1k": profit_usd,
                            "over_side": entry["best_over"],
                            "under_side": entry["best_under"],
                            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
                        })

            # 2. Check Middle Windows
            if entry["middle_window"].get("viable"):
                prop_middles.append({
                    "player": player,
                    "stat_type": stat_type,
                    "type": "PROP_MIDDLE",
                    "middle_info": entry["middle_window"],
                    "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
                })

            # 3. Check Ladder Milestone Off-Market Edges
            for book, lines in entry["books"].items():
                for item in lines:
                    if item.get("type") == "milestone_over" and item.get("odds") >= 150:
                        # Find main market line baseline
                        main_line = entry["best_over"]["line"] if entry["best_over"] else 75.0
                        if item["line"] >= main_line + 30.0:
                            ladder_edges.append({
                                "player": player,
                                "stat_type": stat_type,
                                "book": book,
                                "milestone_line": item["line"],
                                "american_odds": item["odds"],
                                "decimal_odds": item["dec"],
                                "baseline_line": main_line,
                                "summary": f"⚡ LADDER EDGE: {player} {item['line']}+ {stat_type.replace('_', ' ')} @ +{item['odds']} at {book} (Consensus Main: {main_line})",
                                "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat()
                            })

        return {
            "total_props_analyzed": len(matrix),
            "total_arbs_found": len(prop_arbs),
            "total_middles_found": len(prop_middles),
            "total_ladder_edges": len(ladder_edges),
            "prop_arbs": prop_arbs,
            "prop_middles": prop_middles,
            "ladder_edges": ladder_edges
        }

    def scan(self, current_records: List[Dict[str, Any]], extra_sample_props: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Executes full prop normalization, matrix aggregation, and discrepancy detection.
        Saves snapshot to backend/snapshots/props_matrix_latest.json.
        """
        logger.info("Executing Player Props Matrix & Cross-Book Line Hunter Scan...")
        all_props = list(current_records)
        if extra_sample_props:
            all_props.extend(extra_sample_props)

        matrix = self.aggregate_prop_matrix(all_props)
        discrepancies = self.find_prop_discrepancies(matrix)

        # Build alert payload arrays formatted for AlertWebhookManager
        ladder_alerts = []
        for edge in discrepancies.get("ladder_edges", []):
            margin_cents = int(round(edge.get("milestone_line", 0) - edge.get("baseline_line", 0)))
            if margin_cents < 30:
                margin_cents = max(30, int(edge.get("american_odds", 150) - 100))
            ladder_alerts.append({
                "event_id": f"PROP_{edge.get('player', 'PLAYER')}_{edge.get('stat_type', 'STAT')}",
                "book": edge.get("book", "Unknown"),
                "milestone": f"{edge.get('milestone_line', '')} {edge.get('stat_type', '').replace('_', ' ')}",
                "margin_cents": margin_cents,
                "summary": edge.get("summary", "")
            })

        arbitrage_alerts = []
        for arb in discrepancies.get("prop_arbs", []):
            arbitrage_alerts.append({
                "event_id": arb.get("event_id", f"PROP_{arb.get('player')}_{arb.get('stat_type')}"),
                "label": arb.get("label", f"{arb.get('player')} - {arb.get('stat_type')}"),
                "roi_percent": arb.get("roi_percent", 0.0),
                "guaranteed_profit_usd": arb.get("guaranteed_profit_usd", 0.0),
                "side_a": arb.get("side_a", {}),
                "side_b": arb.get("side_b", {})
            })

        middle_alerts = []
        for mid in discrepancies.get("prop_middles", []):
            info = mid.get("middle_info", {})
            middle_alerts.append({
                "event_id": mid.get("event_id", f"PROP_{mid.get('player')}_{mid.get('stat_type')}"),
                "book_a": info.get("over_book", ""),
                "line_a": info.get("over_line", 0.0),
                "book_b": info.get("under_book", ""),
                "line_b": info.get("under_line", 0.0),
                "window_points": info.get("spread_points", 0.0),
                "summary": info.get("summary", "")
            })

        result_summary = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "timestamp_cdt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S CDT"),
            "matrix_count": len(matrix),
            "discrepancies": discrepancies,
            "matrix": matrix,
            "ladder_alerts": ladder_alerts,
            "arbitrage_alerts": arbitrage_alerts,
            "middle_alerts": middle_alerts
        }

        self._archive_props_snapshot(result_summary)

        # Dispatch outbound webhooks (Discord / Telegram)
        try:
            from alert_webhook import AlertWebhookManager
            webhook_mgr = AlertWebhookManager()
            alerts_sent = webhook_mgr.evaluate_and_send(result_summary)
            result_summary["alerts_sent"] = alerts_sent
            result_summary["webhook_status"] = "Active" if webhook_mgr.discord_url else "Dry-Run"
        except Exception as w_err:
            logger.warning(f"Could not dispatch alert webhooks: {w_err}")
            result_summary["alerts_sent"] = 0
            result_summary["webhook_status"] = "Disabled"

        logger.info(f"Props Hunter Scan Complete: Analyzed {len(matrix)} props | Arbs: {discrepancies['total_arbs_found']} | Middles: {discrepancies['total_middles_found']} | Ladder Edges: {discrepancies['total_ladder_edges']} | Alerts Dispatched: {result_summary.get('alerts_sent', 0)}")
        return result_summary

    def _archive_props_snapshot(self, summary: Dict[str, Any]):
        snapshots_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "snapshots")
        try:
            os.makedirs(snapshots_dir, exist_ok=True)
            filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "props_matrix_latest.json")
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2)

            ts = int(time.time())
            snap_file = os.path.join(snapshots_dir, f"props_snap_{ts}.json")
            with open(snap_file, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2)
            logger.info(f"Player Props Matrix snapshot saved to {filepath}")
        except Exception as e:
            logger.warning(f"Could not archive props snapshot: {e}")

def main():
    """Dry run test harness verifying Detroit vs Buffalo & NBA prop matrix calculations."""
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    print("=" * 70)
    print("DESTINY AGENT FLEET — PLAYER PROPS MATRIX & LINE HUNTER DRY RUN")
    print("=" * 70)

    sample_props = [
        # Amon-Ra St. Brown Receiving Yards across 5 books
        {
            "player": "Amon-Ra St. Brown",
            "team": "NFL_DET",
            "stat_type": "receiving_yards",
            "book": "Prop Kingz",
            "line": 112.0,
            "prop_kind": "milestone_over",
            "american_odds": 195,
            "over_under": "over"
        },
        {
            "player": "A. St. Brown",
            "team": "NFL_DET",
            "stat_type": "receiving_yards",
            "book": "FanDuel",
            "line": 78.5,
            "prop_kind": "main_line",
            "american_odds": -115,
            "over_under": "under"
        },
        {
            "player": "Amon Ra St. Brown",
            "team": "NFL_DET",
            "stat_type": "rec yds",
            "book": "DraftKings",
            "line": 76.5,
            "prop_kind": "main_line",
            "american_odds": -110,
            "over_under": "over"
        },
        {
            "player": "Amon-Ra St. Brown",
            "team": "NFL_DET",
            "stat_type": "receiving_yards",
            "book": "BetOnline",
            "line": 77.5,
            "prop_kind": "main_line",
            "american_odds": 110,
            "over_under": "over"
        },
        {
            "player": "Amon-Ra St. Brown",
            "team": "NFL_DET",
            "stat_type": "receiving_yards",
            "book": "Bovada",
            "line": 77.5,
            "prop_kind": "main_line",
            "american_odds": -110,
            "over_under": "under"
        },
        
        # Jahmyr Gibbs Rushing Yards
        {
            "player": "Jahmyr Gibbs",
            "team": "NFL_DET",
            "stat_type": "rushing_yards",
            "book": "FanDuel",
            "line": 64.5,
            "prop_kind": "main_line",
            "american_odds": -110,
            "over_under": "over"
        },
        {
            "player": "J. Gibbs",
            "team": "NFL_DET",
            "stat_type": "rush yds",
            "book": "DraftKings",
            "line": 68.5,
            "prop_kind": "main_line",
            "american_odds": -105,
            "over_under": "under"
        },
        
        # Josh Allen Passing Yards
        {
            "player": "Josh Allen",
            "team": "NFL_BUF",
            "stat_type": "passing_yards",
            "book": "Prop Kingz",
            "line": 300.0,
            "prop_kind": "milestone_over",
            "american_odds": 220,
            "over_under": "over"
        },
        {
            "player": "J. Allen",
            "team": "NFL_BUF",
            "stat_type": "pass yds",
            "book": "DraftKings",
            "line": 242.5,
            "prop_kind": "main_line",
            "american_odds": -110,
            "over_under": "over"
        },

        # Luka Doncic Points (NBA Prop Arb Test Case)
        {
            "player": "Luka Doncic",
            "team": "NBA_DAL",
            "stat_type": "player_points",
            "book": "DraftKings",
            "line": 32.5,
            "prop_kind": "main_line",
            "american_odds": 115,
            "over_under": "over"
        },
        {
            "player": "L. Doncic",
            "team": "NBA_DAL",
            "stat_type": "pts",
            "book": "FanDuel",
            "line": 32.5,
            "prop_kind": "main_line",
            "american_odds": 105,
            "over_under": "under"
        }
    ]

    agent = PropsHunterAgent()
    results = agent.scan([], extra_sample_props=sample_props)

    print("\nPROPS HUNTER SCAN SUMMARY:")
    print(json.dumps(results["discrepancies"], indent=2))
    print(f"\nTotal Props Aggregated in Matrix: {results['matrix_count']}")

if __name__ == "__main__":
    main()
