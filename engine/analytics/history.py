"""Local Benchmark Persistence and History Management for CoreSync.

Strict Architectural Rule: This module MUST NOT import PySide6 or any Qt modules.
Provides secure, isolated JSON file persistence for historical scalability benchmarks.
Excludes arbitrary system/process private data; resilience against corrupted records.
"""

import json
import logging
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from engine.analytics.benchmarking import BenchmarkSessionResult

logger = logging.getLogger("CoreSync.AnalyticsHistory")

DEFAULT_BENCHMARK_DIR = Path.home() / ".coresync" / "benchmarks"


def migrate_session_record(data: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize legacy benchmark records to Phase 9.1.3 measurement schema."""
    for key in ("warmup_records", "measured_records"):
        recs = data.get(key, [])
        for r in recs:
            extra = r.get("extra_metrics", {})
            if "no_worker_compute_time_s" not in extra:
                val = extra.get(
                    "idle_gap_time_s",
                    extra.get("aggregate_estimated_residual_s", extra.get("estimated_distribution_overhead_s", 0.0)),
                )
                extra["no_worker_compute_time_s"] = val
            if "idle_gap_time_s" not in extra:
                extra["idle_gap_time_s"] = extra["no_worker_compute_time_s"]
    return data


class BenchmarkHistoryManager:
    """Manages local persistent storage and retrieval of benchmark session records."""

    def __init__(self, storage_dir: Optional[Path] = None):
        env_dir = os.environ.get("CORESYNC_BENCHMARK_DIR")
        if storage_dir is not None:
            self.storage_dir = Path(storage_dir)
            try:
                self.storage_dir.mkdir(parents=True, exist_ok=True)
            except (OSError, PermissionError):
                pass
        elif env_dir:
            self.storage_dir = Path(env_dir)
            try:
                self.storage_dir.mkdir(parents=True, exist_ok=True)
            except (OSError, PermissionError):
                pass
        else:
            candidates = [
                DEFAULT_BENCHMARK_DIR,
                Path(os.getcwd()) / ".coresync_benchmarks",
                Path("/tmp/coresync_benchmarks"),
            ]
            for cand in candidates:
                try:
                    cand.mkdir(parents=True, exist_ok=True)
                    self.storage_dir = cand
                    break
                except (OSError, PermissionError):
                    continue
            else:
                self.storage_dir = Path("/tmp/coresync_benchmarks")
                try:
                    self.storage_dir.mkdir(parents=True, exist_ok=True)
                except (OSError, PermissionError):
                    pass

        self._summary_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}
        self._comparison_cache: Dict[str, Tuple[float, Dict[str, Any]]] = {}

    def save_session(self, session: BenchmarkSessionResult) -> Path:
        """Serialize a BenchmarkSessionResult to a structured JSON file.

        Args:
            session: Benchmark session outcome object.

        Returns:
            Path to the saved JSON record file.
        """
        try:
            self.storage_dir.mkdir(parents=True, exist_ok=True)
        except (OSError, PermissionError):
            pass
        file_path = self.storage_dir / f"{session.benchmark_id}.json"

        payload = session.to_dict()
        payload["schema_version"] = "1.0"

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2)

        logger.info("Saved benchmark session: %s", file_path)
        return file_path

    def list_sessions(self) -> List[Dict[str, Any]]:
        """Scan storage directory and return summarized index of all valid benchmark records.

        Safely skips corrupted or unreadable JSON files.
        Sorted by start_timestamp descending (newest first).
        """
        if not self.storage_dir.exists():
            return []

        sessions = []
        for p in self.storage_dir.glob("*.json"):
            try:
                mtime = p.stat().st_mtime
                cache_key = str(p)
                if cache_key in self._summary_cache and self._summary_cache[cache_key][0] == mtime:
                    sessions.append(self._summary_cache[cache_key][1])
                    continue

                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)

                # Validate essential fields
                b_id = data.get("benchmark_id", data.get("comparison_id", p.stem))
                is_comp = data.get("session_type") == "real_vs_virtual_comparison" or "comparison_id" in data
                engine_name = "Real vs Virtual Comparison" if is_comp else data.get("engine_name", data.get("engine_type", "Unknown"))
                workload = data.get("workload_name", data.get("configuration", {}).get("workload", {}).get("workload_name", "Unknown"))
                ts = data.get("start_timestamp", data.get("timestamp", ""))
                speedup_stat = data.get("statistics", {}).get("speedup", {})
                mean_speedup = speedup_stat.get("mean", 1.0)
                eff_stat = data.get("statistics", {}).get("efficiency_pct", {})
                mean_eff = eff_stat.get("mean", 100.0)
                verified = data.get("verification_passed", data.get("success", False))
                workers = data.get("worker_count", data.get("configuration", {}).get("real_config", {}).get("worker_count", 1))

                item = {
                    "benchmark_id": b_id,
                    "engine_type": "comparison" if is_comp else data.get("engine_type"),
                    "engine_name": engine_name,
                    "workload_name": workload,
                    "worker_count": workers,
                    "start_timestamp": ts,
                    "mean_speedup": mean_speedup,
                    "mean_efficiency_pct": mean_eff,
                    "verification_passed": verified,
                    "file_path": str(p),
                }
                self._summary_cache[cache_key] = (mtime, item)
                sessions.append(item)
            except Exception as e:
                logger.warning("Skipping corrupted benchmark file %s: %s", p, e)

        # Sort newest first
        sessions.sort(key=lambda s: s.get("start_timestamp", ""), reverse=True)
        return sessions

    def list_summaries(self) -> List[Dict[str, Any]]:
        """Alias for list_sessions."""
        return self.list_sessions()

    def list_comparisons(self) -> List[Dict[str, Any]]:
        """Scan storage directory and return index of all Real vs Virtual comparison records."""
        if not self.storage_dir.exists():
            return []
        comparisons = []
        for p in self.storage_dir.glob("*.json"):
            try:
                mtime = p.stat().st_mtime
                cache_key = str(p)
                if cache_key in self._comparison_cache and self._comparison_cache[cache_key][0] == mtime:
                    c_item = self._comparison_cache[cache_key][1]
                    if c_item is not None:
                        comparisons.append(c_item)
                    continue

                with open(p, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if data.get("session_type") == "real_vs_virtual_comparison" or "comparison_id" in data:
                    c_id = data.get("comparison_id", p.stem)
                    cfg = data.get("configuration", {})
                    w_name = cfg.get("workload", {}).get("workload_name", "Unknown")
                    mode = cfg.get("execution_mode", "compare_both")
                    ts = data.get("timestamp", "")
                    success = data.get("success", True)
                    item = {
                        "comparison_id": c_id,
                        "workload_name": w_name,
                        "execution_mode": mode,
                        "timestamp": ts,
                        "success": success,
                        "file_path": str(p),
                    }
                    self._comparison_cache[cache_key] = (mtime, item)
                    comparisons.append(item)
                else:
                    self._comparison_cache[cache_key] = (mtime, None)
            except Exception:
                continue
        comparisons.sort(key=lambda s: s.get("timestamp", ""), reverse=True)
        return comparisons

    def load_comparison(self, comparison_id: str) -> Optional[Dict[str, Any]]:
        """Load comparison session dictionary by comparison_id."""
        return self.load_session(comparison_id)

    def load_session(self, benchmark_id: str) -> Optional[Dict[str, Any]]:
        """Load complete benchmark session record by ID.

        Returns:
            Dictionary data or None if record is missing or corrupt.
        """
        file_path = self.storage_dir / f"{benchmark_id}.json"
        if not file_path.exists():
            return None

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                return migrate_session_record(data)
        except Exception as e:
            logger.error("Failed to load benchmark session %s: %s", benchmark_id, e)
            return None

    def delete_session(self, benchmark_id: str) -> bool:
        """Remove an individual benchmark session record file."""
        file_path = self.storage_dir / f"{benchmark_id}.json"
        if file_path.exists():
            try:
                file_path.unlink()
                self._summary_cache.pop(str(file_path), None)
                self._comparison_cache.pop(str(file_path), None)
                logger.info("Deleted benchmark session: %s", benchmark_id)
                return True
            except Exception as e:
                logger.error("Failed to delete benchmark session %s: %s", benchmark_id, e)
                return False
        return False

    def clear_all(self) -> int:
        """Delete all benchmark record files in the storage directory."""
        self._summary_cache.clear()
        self._comparison_cache.clear()
        if not self.storage_dir.exists():
            return 0
        deleted_count = 0
        for p in self.storage_dir.glob("*.json"):
            try:
                p.unlink()
                deleted_count += 1
            except Exception:
                pass
        return deleted_count


def list_comparisons(storage_dir: Optional[Path] = None) -> List[Dict[str, Any]]:
    """Convenience module function to list comparison records."""
    return BenchmarkHistoryManager(storage_dir).list_comparisons()


def load_comparison(comparison_id: str, storage_dir: Optional[Path] = None) -> Optional[Dict[str, Any]]:
    """Convenience module function to load a comparison record."""
    return BenchmarkHistoryManager(storage_dir).load_comparison(comparison_id)

