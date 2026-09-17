import os
import json
import logging
import datetime
from pathlib import Path
from typing import Dict, Any, Optional

logger = logging.getLogger("sports_engine.db")

# Path for local fallback snapshot cache
FALLBACK_SNAPSHOT_PATH = Path(__file__).parent / "latest_snapshot.json"
TELEMETRY_CACHE_PATH = Path(__file__).parent / "agent_telemetry.json"

class DatabaseManager:
    """
    Manages snapshot persistence to Supabase DB with automated local file fallback.
    """
    def __init__(self):
        self.supabase_url = os.getenv("SUPABASE_URL") or os.getenv("NEXT_PUBLIC_SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_ROLE_KEY") or os.getenv("NEXT_PUBLIC_SUPABASE_ANON_KEY")
        self.client = None

        if self.supabase_url and self.supabase_key:
            try:
                from supabase import create_client
                self.client = create_client(self.supabase_url, self.supabase_key)
                logger.info("Successfully initialized Supabase client connection.")
            except Exception as e:
                logger.warning(f"Could not initialize Supabase client: {e}. Defaulting to resilient local file persistence.")
        else:
            logger.info("Supabase environment variables not found. Operating in resilient local snapshot persistence mode.")

    def push_snapshot(self, snapshot: Dict[str, Any]) -> bool:
        """
        Upsert snapshot into Supabase table 'market_snapshots', or write to local cache if DB unconfigured.
        """
        success = False
        if self.client:
            try:
                # Upsert into market_snapshots table
                data, count = self.client.table("market_snapshots").upsert({
                    "snapshot_id": snapshot["snapshot_id"],
                    "timestamp": snapshot["timestamp"],
                    "total_markets_processed": snapshot["total_markets_processed"],
                    "leagues_covered": snapshot["leagues_covered"],
                    "records_payload": snapshot["records"]
                }).execute()
                logger.info(f"Supabase upsert successful for snapshot {snapshot['snapshot_id']} ({snapshot['total_markets_processed']} records).")
                success = True
            except Exception as e:
                logger.error(f"Supabase upsert failed: {e}. Falling back to local file persistence.")

        # Always maintain local snapshot file as fail-safe
        try:
            with open(FALLBACK_SNAPSHOT_PATH, "w", encoding="utf-8") as f:
                json.dump(snapshot, f, indent=2)
            logger.info(f"Local snapshot cache saved to {FALLBACK_SNAPSHOT_PATH}")
            if not self.client:
                success = True
        except Exception as e:
            logger.error(f"Error saving local fallback snapshot: {e}")

        return success

    def update_agent_telemetry(self, agent_id: str, agent_name: str, status: str, records_processed: int, latency_ms: float) -> None:
        """
        Update agent health metrics in DB / telemetry store.
        """
        telemetry_item = {
            "agent_id": agent_id,
            "agent_name": agent_name,
            "status": status,
            "last_run": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "records_processed": records_processed,
            "latency_ms": latency_ms,
            "uptime_pct": 99.9
        }

        if self.client:
            try:
                self.client.table("agent_telemetry").upsert(telemetry_item).execute()
            except Exception as e:
                logger.debug(f"Telemetry DB upsert notice: {e}")

        # Maintain telemetry file cache for local UI API endpoint
        try:
            existing = {}
            if TELEMETRY_CACHE_PATH.exists():
                try:
                    with open(TELEMETRY_CACHE_PATH, "r", encoding="utf-8") as f:
                        existing = json.load(f)
                except Exception:
                    existing = {}

            existing[agent_id] = telemetry_item
            with open(TELEMETRY_CACHE_PATH, "w", encoding="utf-8") as f:
                json.dump(existing, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to write telemetry cache file: {e}")
