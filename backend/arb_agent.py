#!/usr/bin/env python3
"""
=============================================================================
DESTINY SPORTS ENGINE — Line Discrepancy, Arbitrage & Steam Movement Agent
Pure Mathematical Arbitrage, Cross-Market Middles & Steam Velocity Engine
=============================================================================
"""

import sys
import os
import json
import time
import datetime
import logging
from typing import List, Dict, Any, Tuple, Optional

# Ensure local modules are importable
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Configure Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
logger = logging.getLogger("sports_engine.arb_agent")

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

class ArbitrageSteamAgent:
    def __init__(self, base_bankroll: float = 1000.0):
        self.base_bankroll = base_bankroll

    def detect_arbitrage(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Scans pairs of outcomes across books to find market margins where Total Implied Probability < 1.0.
        Calculates exact stake split for $1,000 base and ROI%.
        """
        arb_alerts = []
        events_map: Dict[str, List[Dict[str, Any]]] = {}

        for r in records:
            event_id = r.get("canonical_event_id") or r.get("event_id") or "UNKNOWN_EVENT"
            events_map.setdefault(event_id, []).append(r)

        for event_id, event_records in events_map.items():
            # Group records by outcome/bookmaker
            home_outcomes = []
            away_outcomes = []
            over_outcomes = []
            under_outcomes = []

            for r in event_records:
                kind = r.get("market_kind") or r.get("_kind") or "game"
                book = r.get("bookmaker") or r.get("provider") or "Kalshi"
                odds = r.get("american_odds") or r.get("odds") or 0
                dec_odds = american_to_decimal(odds)
                title = str(r.get("title") or r.get("market_title") or "").lower()

                item = {
                    "book": book,
                    "american_odds": odds,
                    "decimal_odds": dec_odds,
                    "line": r.get("line") or r.get("spread_line") or r.get("total_line") or 0,
                    "raw_record": r
                }

                if "over" in title or kind == "total" and "over" in str(r.get("yes_sub_title", "")).lower():
                    over_outcomes.append(item)
                elif "under" in title or kind == "total" and "under" in str(r.get("yes_sub_title", "")).lower():
                    under_outcomes.append(item)
                elif r.get("home_team") and str(r.get("home_team")).lower() in title or "yes" in str(r.get("yes_sub_title", "")).lower():
                    home_outcomes.append(item)
                else:
                    away_outcomes.append(item)

            # Evaluate 2-way Arbitrage: Side A vs Side B
            pairs_to_check = [
                ("Home vs Away", home_outcomes, away_outcomes),
                ("Over vs Under Total", over_outcomes, under_outcomes)
            ]

            for label, side_a_list, side_b_list in pairs_to_check:
                for a in side_a_list:
                    for b in side_b_list:
                        dec_a = a["decimal_odds"]
                        dec_b = b["decimal_odds"]

                        if dec_a <= 1.0 or dec_b <= 1.0:
                            continue

                        implied_prob = (1.0 / dec_a) + (1.0 / dec_b)
                        if implied_prob < 0.999:
                            profit_margin_pct = round(((1.0 / implied_prob) - 1.0) * 100.0, 2)
                            stake_a = round((self.base_bankroll / dec_a) / implied_prob, 2)
                            stake_b = round((self.base_bankroll / dec_b) / implied_prob, 2)
                            guaranteed_profit = round(self.base_bankroll * ((1.0 / implied_prob) - 1.0), 2)

                            arb_alerts.append({
                                "event_id": event_id,
                                "type": "PURE_ARBITRAGE",
                                "label": label,
                                "implied_probability": round(implied_prob, 4),
                                "roi_percent": profit_margin_pct,
                                "guaranteed_profit_usd": guaranteed_profit,
                                "side_a": {
                                    "book": a["book"],
                                    "american_odds": a["american_odds"],
                                    "decimal_odds": dec_a,
                                    "recommended_stake": stake_a
                                },
                                "side_b": {
                                    "book": b["book"],
                                    "american_odds": b["american_odds"],
                                    "decimal_odds": dec_b,
                                    "recommended_stake": stake_b
                                },
                                "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()
                            })

        return arb_alerts

    def detect_line_middles(self, records: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Identifies market middles / soft lines where overlapping lines between books create win/push target windows.
        """
        middle_alerts = []
        events_map: Dict[str, List[Dict[str, Any]]] = {}

        for r in records:
            event_id = r.get("canonical_event_id") or r.get("event_id") or "UNKNOWN_EVENT"
            events_map.setdefault(event_id, []).append(r)

        for event_id, event_records in events_map.items():
            spread_records = [r for r in event_records if (r.get("market_kind") or r.get("_kind")) in ["spread", "game"]]
            total_records  = [r for r in event_records if (r.get("market_kind") or r.get("_kind")) in ["total"]]

            # Spread Middle Check
            for i in range(len(spread_records)):
                for j in range(i + 1, len(spread_records)):
                    r1 = spread_records[i]
                    r2 = spread_records[j]

                    b1 = r1.get("bookmaker") or r1.get("provider") or "Kalshi"
                    b2 = r2.get("bookmaker") or r2.get("provider") or "DraftKings"
                    if b1 == b2:
                        continue

                    line1 = float(r1.get("spread_line") or r1.get("line") or 0.0)
                    line2 = float(r2.get("spread_line") or r2.get("line") or 0.0)

                    # Spread middle condition: e.g. Team A +3.5 at Book 1, Team B +2.5 (Team A -2.5) at Book 2
                    middle_window = abs(line1 - line2)
                    if middle_window >= 1.5:
                        middle_alerts.append({
                            "event_id": event_id,
                            "type": "MARKET_MIDDLE",
                            "market": "Spread Window",
                            "book_a": b1,
                            "line_a": line1,
                            "book_b": b2,
                            "line_b": line2,
                            "window_points": round(middle_window, 1),
                            "summary": f"🎯 Market Middle ({middle_window:.1f} pts): {b1} line ({line1:+.1f}) vs {b2} line ({line2:+.1f})",
                            "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()
                        })

        return middle_alerts

    def detect_steam_velocity(self, current_records: List[Dict[str, Any]], previous_records: Optional[List[Dict[str, Any]]] = None) -> List[Dict[str, Any]]:
        """
        Compares consecutive snapshot timestamps (<= 10 mins).
        Flags point spread moves >= 1.5 pts or moneyline shifts >= 25 cents.
        """
        steam_alerts = []
        if not previous_records:
            return steam_alerts

        prev_map = {}
        for r in previous_records:
            key = f"{r.get('canonical_event_id')}|{r.get('bookmaker')}|{r.get('market_kind')}"
            prev_map[key] = r

        for r in current_records:
            key = f"{r.get('canonical_event_id')}|{r.get('bookmaker')}|{r.get('market_kind')}"
            prev_r = prev_map.get(key)
            if not prev_r:
                continue

            event_id = r.get("canonical_event_id") or "EVENT"
            book = r.get("bookmaker") or "Kalshi"
            market_kind = r.get("market_kind") or "spread"

            curr_line = float(r.get("spread_line") or r.get("line") or 0.0)
            prev_line = float(prev_r.get("spread_line") or prev_r.get("line") or 0.0)

            curr_odds = float(r.get("american_odds") or r.get("odds") or 0.0)
            prev_odds = float(prev_r.get("american_odds") or prev_r.get("odds") or 0.0)

            line_delta = abs(curr_line - prev_line)
            odds_delta = abs(curr_odds - prev_odds)

            if line_delta >= 1.5 or odds_delta >= 25:
                steam_alerts.append({
                    "event_id": event_id,
                    "type": "STEAM_MOVE",
                    "bookmaker": book,
                    "market_kind": market_kind,
                    "prev_line": prev_line,
                    "curr_line": curr_line,
                    "line_delta": round(line_delta, 1),
                    "prev_odds": prev_odds,
                    "curr_odds": curr_odds,
                    "odds_delta": round(odds_delta, 1),
                    "summary": f"⚡ STEAM MOVE: Line shifted {prev_line:+.1f} -> {curr_line:+.1f} (Δ {line_delta:.1f} pts / {odds_delta:.0f}¢) at {book}",
                    "timestamp_utc": datetime.datetime.now(datetime.timezone.utc).isoformat()
                })

        return steam_alerts

    def scan(self, current_records: List[Dict[str, Any]], previous_records: Optional[List[Dict[str, Any]]] = None) -> Dict[str, Any]:
        """
        Executes full discrepancy scan: Arbitrage + Middles + Steam Velocity.
        Saves results snapshot to backend/snapshots/arb_opportunities.json.
        """
        logger.info("Executing Arbitrage & Steam Movement Discovery Scan...")
        arbs = self.detect_arbitrage(current_records)
        middles = self.detect_line_middles(current_records)
        steam = self.detect_steam_velocity(current_records, previous_records)

        result_summary = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "timestamp_cdt": datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S CDT"),
            "total_arbs_found": len(arbs),
            "total_middles_found": len(middles),
            "total_steam_moves": len(steam),
            "arbitrage_alerts": arbs,
            "middle_alerts": middles,
            "steam_alerts": steam
        }

        self._archive_arb_snapshot(result_summary)

        # Evaluate & dispatch outbound webhooks (Discord / Telegram)
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

        logger.info(f"Scan Complete: Arbs: {len(arbs)} | Middles: {len(middles)} | Steam Moves: {len(steam)}")
        return result_summary

    def _archive_arb_snapshot(self, summary: Dict[str, Any]):
        snapshots_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "snapshots")
        try:
            os.makedirs(snapshots_dir, exist_ok=True)
            filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "arb_opportunities.json")
            with open(filepath, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2)

            # Archive copy in snapshots/
            ts = int(time.time())
            snap_file = os.path.join(snapshots_dir, f"arb_snap_{ts}.json")
            with open(snap_file, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2)
            logger.info(f"Arb opportunities saved to {filepath}")
        except Exception as e:
            logger.warning(f"Could not archive arb snapshot: {e}")

def main():
    """Dry run test mode for verifying arbitrage math, middles, and steam velocity."""
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8')

    print("=" * 70)
    print("DESTINY AGENT FLEET — ARBITRAGE & STEAM DISCOVERY AGENT DRY RUN")
    print("=" * 70)

    agent = ArbitrageSteamAgent(base_bankroll=1000.0)

    sample_current = [
        # Arbitrage Test Case: Kalshi Yes (+160 = 2.60) vs FanDuel No (+110 = 2.10)
        # IP = 1/2.60 + 1/2.10 = 0.3846 + 0.4762 = 0.8608 < 1.0 (16.17% ROI)
        {
            "canonical_event_id": "NBA_20260917_MIN@LAC",
            "market_kind": "game",
            "title": "Minnesota Timberwolves vs LA Clippers - Moneyline",
            "home_team": "LA Clippers",
            "away_team": "Minnesota Timberwolves",
            "bookmaker": "Kalshi",
            "american_odds": 160,
            "line": 0
        },
        {
            "canonical_event_id": "NBA_20260917_MIN@LAC",
            "market_kind": "game",
            "title": "Minnesota Timberwolves vs LA Clippers - Away Moneyline",
            "home_team": "LA Clippers",
            "away_team": "Minnesota Timberwolves",
            "bookmaker": "FanDuel",
            "american_odds": 110,
            "line": 0
        },
        # Middle Test Case: Kalshi Clippers +3.5 vs DraftKings Clippers -2.5
        {
            "canonical_event_id": "NBA_20260917_MIN@LAC",
            "market_kind": "spread",
            "title": "Clippers Spread",
            "home_team": "LA Clippers",
            "away_team": "Minnesota Timberwolves",
            "bookmaker": "Kalshi",
            "spread_line": 3.5,
            "american_odds": -110
        },
        {
            "canonical_event_id": "NBA_20260917_MIN@LAC",
            "market_kind": "spread",
            "title": "Clippers Spread",
            "home_team": "LA Clippers",
            "away_team": "Minnesota Timberwolves",
            "bookmaker": "DraftKings",
            "spread_line": -2.5,
            "american_odds": -110
        },
        # Steam Move Target Case
        {
            "canonical_event_id": "NFL_20260917_DET@GB",
            "market_kind": "spread",
            "title": "Lions Spread",
            "home_team": "Green Bay Packers",
            "away_team": "Detroit Lions",
            "bookmaker": "BetOnline",
            "spread_line": -4.5,
            "american_odds": -135
        }
    ]

    sample_previous = [
        {
            "canonical_event_id": "NFL_20260917_DET@GB",
            "market_kind": "spread",
            "title": "Lions Spread",
            "home_team": "Green Bay Packers",
            "away_team": "Detroit Lions",
            "bookmaker": "BetOnline",
            "spread_line": -3.0,
            "american_odds": -110
        }
    ]

    results = agent.scan(sample_current, sample_previous)

    print("\nSCAN SUMMARY REPORT:")
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    main()
