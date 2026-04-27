"""
In-memory transaction store for recent transactions and flagged alerts.
Thread-safe for single-process usage.
"""
from __future__ import annotations

import threading
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import Any

_lock = threading.Lock()

# Circular buffer of the last N transactions (all, for velocity/cumulative checks)
_MAX_TX = 10_000
_transactions: deque[dict] = deque(maxlen=_MAX_TX)

# Flagged (alerted) transactions – kept indefinitely until cleared
_alerts: list[dict] = []


def add_transaction(tx: dict) -> str:
    """Store a transaction and return its assigned transaction_id."""
    tx_id = tx.get("transaction_id") or str(uuid.uuid4())
    record = {**tx, "transaction_id": tx_id}
    if "stored_at" not in record:
        record["stored_at"] = datetime.now(tz=timezone.utc).isoformat()
    with _lock:
        _transactions.append(record)
    return tx_id


def add_alert(scored_tx: dict) -> None:
    """Persist a scored transaction that triggered at least one alert."""
    with _lock:
        _alerts.append(scored_tx)


def get_recent_by_address(address: str, limit: int = 500) -> list[dict]:
    """Return recent transactions for a given from_address (newest first)."""
    addr = address.lower()
    with _lock:
        results = [
            t for t in reversed(_transactions)
            if t.get("from_address", "").lower() == addr
        ]
    return results[:limit]


def get_alerts(
    limit: int = 100,
    alert_level: str | None = None,
    from_address: str | None = None,
) -> list[dict]:
    """Return flagged transactions, optionally filtered."""
    with _lock:
        items = list(reversed(_alerts))

    if alert_level:
        items = [
            a for a in items
            if any(
                m["alert_level"] == alert_level.upper()
                for m in a.get("triggered_rules", [])
            )
        ]
    if from_address:
        items = [
            a for a in items
            if a.get("from_address", "").lower() == from_address.lower()
        ]
    return items[:limit]


def clear_alerts() -> int:
    """Remove all alerts. Returns number of alerts cleared."""
    with _lock:
        count = len(_alerts)
        _alerts.clear()
    return count
