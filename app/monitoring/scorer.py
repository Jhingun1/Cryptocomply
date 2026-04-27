"""
Risk scorer – ties the rules engine to the transaction store.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from app.rules.engine import evaluate, RuleMatch
from app.monitoring.store import get_recent_by_address, add_transaction, add_alert


def score_transaction(tx: dict) -> dict:
    """
    Score a transaction dict, persist it, and return a scored result.

    Returns
    -------
    dict with keys:
        transaction_id, risk_score (0-100), risk_level, triggered_rules,
        flagged, original transaction fields
    """
    # Fetch recent history for the sender (excluding current tx)
    history = get_recent_by_address(tx.get("from_address", ""), limit=500)

    # Run rules engine
    matches: list[RuleMatch] = evaluate(tx, history)

    # Aggregate risk score (cap at 100, use additive model with diminishing returns)
    raw_score = sum(m.risk_score for m in matches)
    risk_score = min(100, raw_score)

    risk_level = _classify(risk_score)
    flagged = len(matches) > 0

    triggered_rules = [
        {
            "rule_id": m.rule_id,
            "rule_name": m.rule_name,
            "alert_level": m.alert_level,
            "risk_score": m.risk_score,
            "message": m.message,
            "details": m.details,
        }
        for m in matches
    ]

    # Build enriched tx record
    enriched = {
        **tx,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "flagged": flagged,
        "triggered_rules": triggered_rules,
        "scored_at": datetime.now(tz=timezone.utc).isoformat(),
    }

    # Persist
    tx_id = add_transaction(enriched)
    enriched["transaction_id"] = tx_id

    if flagged:
        add_alert(enriched)

    return enriched


def _classify(score: int) -> str:
    if score >= 70:
        return "CRITICAL"
    if score >= 40:
        return "HIGH"
    if score >= 20:
        return "MEDIUM"
    return "LOW"
