#!/usr/bin/env python3
"""
=============================================================================
DESTINY SPORTS ENGINE — Odds Sanity Firewall Agent
Tier 2 Market Validation & Corrupted Feed Suppression Engine
=============================================================================
1. Outlier & Range Validation:
   - Game Totals: NFL [20, 75], NBA [180, 260], MLB [5, 16]
   - Spreads: Abs(Spread) <= 45.0
   - Moneylines: Flag American odds > +2500 or < -2500 for secondary confirmation
2. Palpable Error & Vig Check:
   - Reject two-way markets where total implied probability < 85% (feed corruption / misplaced decimal)
3. Staleness Filter:
   - Track line staleness across 15+ cycles while consensus moves.
=============================================================================
"""

import os
import json
import time
import logging
import datetime
from typing import List, Dict, Any, Tuple, Optional

logger = logging.getLogger("sports_engine.firewall_agent")

FIREWALL_SNAPSHOT_PATH = os.path.join(os.path.dirname(__file__), "firewall_snapshot.json")
FIREWALL_STATE_PATH = os.path.join(os.path.dirname(__file__), "firewall_state.json")

class OddsSanityFirewall:
    """
    Tier 2 Firewall validating audited market lines before downstream agent processing.
    """
    def __init__(self):
        self.state = self._load_state()

    def _load_state(self) -> Dict[str, Any]:
        """Loads historical cycle state for staleness tracking across runs."""
        if os.path.exists(FIREWALL_STATE_PATH):
            try:
                with open(FIREWALL_STATE_PATH, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load firewall state: {e}")
        return {"cycle_count": 0, "lines_history": {}}

    def _save_state(self) -> None:
        """Saves updated cycle state to disk."""
        try:
            with open(FIREWALL_STATE_PATH, "w", encoding="utf-8") as f:
                json.dump(self.state, f, indent=2)
        except Exception as e:
            logger.warning(f"Could not save firewall state: {e}")

    @staticmethod
    def american_to_implied_prob(american_odds: float) -> float:
        """Converts American odds into implied probability (0.0 to 1.0)."""
        try:
            odds = float(american_odds)
            if odds == 0:
                return 0.50
            if odds > 0:
                return 100.0 / (odds + 100.0)
            else:
                return abs(odds) / (abs(odds) + 100.0)
        except Exception:
            return 0.50

    def validate(self, records: List[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Any]]:
        """
        Validates records through range limits, palpable error checks, and staleness filtering.
        Returns (sanitized_records, firewall_report).
        """
        self.state["cycle_count"] = self.state.get("cycle_count", 0) + 1
        current_cycle = self.state["cycle_count"]
        lines_history = self.state.get("lines_history", {})

        sanitized_records = []
        rejected_records = []

        range_failures = 0
        palpable_errors = 0
        staleness_drops = 0
        extreme_ml_flags = 0

        # Build market consensus lines per (canonical_event_id, market_kind) to detect isolated stale books
        event_consensus = {}
        for r in records:
            event_id = r.get("canonical_event_id") or r.get("event_id") or "UNKNOWN"
            kind = r.get("market_kind", "game")
            key = f"{event_id}|{kind}"
            if key not in event_consensus:
                event_consensus[key] = []
            
            line_val = r.get("line") or r.get("spread_line") or r.get("total_line") or r.get("american_odds")
            if line_val is not None:
                try:
                    event_consensus[key].append(float(line_val))
                except (ValueError, TypeError):
                    pass

        # Validate each record
        for r in records:
            league = (r.get("league") or "GENERAL").upper()
            kind = r.get("market_kind", "game")
            book = r.get("bookmaker") or r.get("provider") or "Consensus"
            event_id = r.get("canonical_event_id") or r.get("event_id") or "UNKNOWN"

            # -----------------------------------------------------------------
            # Gate A: Outlier & Range Validation
            # -----------------------------------------------------------------
            # 1. Totals check
            if kind == "total":
                total_val = r.get("total_line") or r.get("line")
                if total_val is not None:
                    try:
                        tv = float(total_val)
                        if league == "NFL" and (tv < 20.0 or tv > 75.0):
                            range_failures += 1
                            rejected_records.append({**r, "reject_reason": f"NFL total {tv} out of bounds [20, 75]"})
                            continue
                        elif league == "NBA" and (tv < 180.0 or tv > 260.0):
                            range_failures += 1
                            rejected_records.append({**r, "reject_reason": f"NBA total {tv} out of bounds [180, 260]"})
                            continue
                        elif league == "MLB" and (tv < 5.0 or tv > 16.0):
                            range_failures += 1
                            rejected_records.append({**r, "reject_reason": f"MLB total {tv} out of bounds [5, 16]"})
                            continue
                    except (ValueError, TypeError):
                        pass

            # 2. Spreads check
            if kind == "spread":
                spread_val = r.get("spread_line") or r.get("line")
                if spread_val is not None:
                    try:
                        sv = abs(float(spread_val))
                        if sv > 45.0:
                            range_failures += 1
                            rejected_records.append({**r, "reject_reason": f"Spread {sv} exceeds maximum limit 45.0"})
                            continue
                    except (ValueError, TypeError):
                        pass

            # 3. Moneylines extreme odds check (Flagged for secondary confirmation)
            am_odds = r.get("american_odds")
            if am_odds is not None:
                try:
                    ao = float(am_odds)
                    if ao > 2500 or ao < -2500:
                        extreme_ml_flags += 1
                        r["flag_extreme_moneyline"] = True
                        r["secondary_confirmation_required"] = True
                except (ValueError, TypeError):
                    pass

            # -----------------------------------------------------------------
            # Gate B: Palpable Error & Vig Check
            # -----------------------------------------------------------------
            # Evaluate implied probability of two-way markets
            if am_odds is not None:
                prob = self.american_to_implied_prob(am_odds)
                # If opposing side odds are provided in the same object
                opp_odds = r.get("opposing_american_odds")
                if opp_odds is not None:
                    opp_prob = self.american_to_implied_prob(opp_odds)
                    tot_prob = prob + opp_prob
                    if tot_prob < 0.85:
                        palpable_errors += 1
                        rejected_records.append({**r, "reject_reason": f"Palpable Error: Total implied prob {tot_prob:.2f} < 0.85"})
                        continue

            # -----------------------------------------------------------------
            # Gate C: Staleness Filter Across 15+ Cycles
            # -----------------------------------------------------------------
            history_key = f"{event_id}|{kind}|{book}"
            current_val = r.get("line") or r.get("spread_line") or r.get("total_line") or r.get("american_odds") or 0.0

            hist = lines_history.get(history_key, {"last_val": current_val, "unchanged_cycles": 0})
            if hist["last_val"] == current_val:
                hist["unchanged_cycles"] += 1
            else:
                hist["last_val"] = current_val
                hist["unchanged_cycles"] = 1

            lines_history[history_key] = hist

            # Check if market consensus moved significantly while this line stayed frozen 15+ cycles
            event_key = f"{event_id}|{kind}"
            all_lines = event_consensus.get(event_key, [])
            if hist["unchanged_cycles"] >= 15 and len(all_lines) >= 2:
                consensus_avg = sum(all_lines) / len(all_lines)
                try:
                    diff = abs(float(current_val) - consensus_avg)
                    if diff > 1.5:  # Significant consensus divergence
                        staleness_drops += 1
                        rejected_records.append({**r, "reject_reason": f"Stale feed: Unchanged 15+ cycles (Divergence {diff:.2f} from consensus)"})
                        continue
                except (ValueError, TypeError):
                    pass

            sanitized_records.append(r)

        self.state["lines_history"] = lines_history
        self._save_state()

        report = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "status": "ACTIVE",
            "total_input": len(records),
            "total_passed": len(sanitized_records),
            "total_rejected": len(rejected_records),
            "range_failures": range_failures,
            "palpable_errors": palpable_errors,
            "staleness_drops": staleness_drops,
            "extreme_ml_flags": extreme_ml_flags,
            "rejections": rejected_records[:10]  # Sample of top 10 rejections
        }

        # Save snapshot
        try:
            with open(FIREWALL_SNAPSHOT_PATH, "w", encoding="utf-8") as f:
                json.dump(report, f, indent=2)
            logger.info(f"Odds Sanity Firewall Snapshot saved ({len(sanitized_records)} passed, {len(rejected_records)} dropped).")
        except Exception as err:
            logger.warning(f"Could not save firewall snapshot: {err}")

        return sanitized_records, report

def main():
    """Dry run test for OddsSanityFirewall."""
    firewall = OddsSanityFirewall()
    test_records = [
        # Normal NFL Total
        {"league": "NFL", "market_kind": "total", "total_line": 48.5, "bookmaker": "DraftKings", "american_odds": -110},
        # Invalid NFL Total (Range Failure)
        {"league": "NFL", "market_kind": "total", "total_line": 14.0, "bookmaker": "CorruptedBook", "american_odds": -110},
        # Invalid NBA Total (Range Failure)
        {"league": "NBA", "market_kind": "total", "total_line": 310.0, "bookmaker": "BadFeed", "american_odds": -110},
        # Extreme Moneyline Flag
        {"league": "NFL", "market_kind": "game", "american_odds": 3500, "bookmaker": "LongshotBook"},
        # Palpable Error (Implied prob sum < 0.85)
        {"league": "MLB", "market_kind": "game", "american_odds": 400, "opposing_american_odds": 400, "bookmaker": "PalpBook"}
    ]
    passed, report = firewall.validate(test_records)
    print("=" * 70)
    print("DESTINY AGENT FLEET — ODDS SANITY FIREWALL TEST")
    print("=" * 70)
    print(f"Passed: {len(passed)} / {len(test_records)}")
    print(json.dumps(report, indent=2))

if __name__ == "__main__":
    main()
