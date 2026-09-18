#!/usr/bin/env python3
"""
=============================================================================
DESTINY SPORTS ENGINE — Game Lifecycle Router Agent
Tier 3 Dynamic Queue Router & Event Lifecycle Dispatcher
=============================================================================
Partition verified market records into 3 distinct lifecycle execution queues:
1. PREGAME: Scheduled start > current time or game_state in ['pre', 'scheduled']
   -> Routed to Weather Edge Agent, Props Matrix Hunter, & Pregame Middles
2. LIVE: In-progress games or game_state in ['in', 'in_progress', 'live']
   -> Routed to Steam Velocity Agent & Real-Time Zero-Risk Hedge Bot
3. FINAL: Completed games or game_state in ['post', 'final', 'completed']
   -> Routed to PnL Settlement Engine & Historical Raw Archive
=============================================================================
"""

import os
import json
import logging
import datetime
from typing import List, Dict, Any, Tuple

logger = logging.getLogger("sports_engine.lifecycle_router")

LIFECYCLE_SNAPSHOT_PATH = os.path.join(os.path.dirname(__file__), "lifecycle_snapshot.json")

class GameLifecycleRouter:
    """
    Tier 3 Router partitioning sanitized records into PREGAME, LIVE, and FINAL queues.
    """
    @staticmethod
    def classify_record(r: Dict[str, Any]) -> str:
        """Determines whether a record belongs to PREGAME, LIVE, or FINAL."""
        state = str(r.get("game_state") or "").lower().strip()
        status = str(r.get("game_status") or "").lower().strip()

        # Final / Completed checks
        if state in ["post", "final", "completed"] or "final" in status or "completed" in status:
            return "FINAL"

        # Live / In-Progress checks
        if state in ["in", "in_progress", "live"] or any(term in status for term in [
            "in progress", "halftime", "1st qtr", "2nd qtr", "3rd qtr", "4th qtr",
            "top", "bottom", "1st", "2nd", "3rd", "ot", "extra"
        ]):
            return "LIVE"

        # Default fallback for scheduled or unstarted lines
        return "PREGAME"

    def route(self, records: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Partitions records into PREGAME, LIVE, and FINAL queues and updates lifecycle snapshot.
        """
        pregame_queue = []
        live_queue = []
        final_queue = []

        for r in records:
            stage = self.classify_record(r)
            r["lifecycle_stage"] = stage  # Tag record with stage label
            if stage == "PREGAME":
                pregame_queue.append(r)
            elif stage == "LIVE":
                live_queue.append(r)
            elif stage == "FINAL":
                final_queue.append(r)

        summary = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "status": "ROUTED",
            "total_records": len(records),
            "pregame_count": len(pregame_queue),
            "live_count": len(live_queue),
            "final_count": len(final_queue),
            "routing_targets": {
                "PREGAME": ["Weather Edge Agent", "Props Matrix Hunter", "Pregame Middle Finder"],
                "LIVE": ["Steam Velocity Hunter", "Real-Time Hedge Bot"],
                "FINAL": ["PnL Settlement Engine", "Historical Snapshot Archive"]
            }
        }

        result = {
            "PREGAME": pregame_queue,
            "LIVE": live_queue,
            "FINAL": final_queue,
            "summary": summary
        }

        # Save snapshot
        try:
            with open(LIFECYCLE_SNAPSHOT_PATH, "w", encoding="utf-8") as f:
                json.dump(summary, f, indent=2)
            logger.info(f"Game Lifecycle Router Snapshot saved (PREGAME: {len(pregame_queue)}, LIVE: {len(live_queue)}, FINAL: {len(final_queue)}).")
        except Exception as err:
            logger.warning(f"Could not save lifecycle snapshot: {err}")

        return result

def main():
    """Dry run test for GameLifecycleRouter."""
    router = GameLifecycleRouter()
    test_records = [
        {"event_id": "1", "title": "Lions @ Bills", "game_state": "pre", "game_status": "Scheduled"},
        {"event_id": "2", "title": "Yankees @ Red Sox", "game_state": "in", "game_status": "Top 4th"},
        {"event_id": "3", "title": "Chiefs @ Eagles", "game_state": "post", "game_status": "Final"},
    ]
    routed = router.route(test_records)
    print("=" * 70)
    print("DESTINY AGENT FLEET — GAME LIFECYCLE ROUTER TEST")
    print("=" * 70)
    print(json.dumps(routed["summary"], indent=2))

if __name__ == "__main__":
    main()
