"""
Rules Engine – loads JSON rule definitions and evaluates transactions.
"""
from __future__ import annotations

import csv
import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

RULES_DIR = Path(__file__).parent

_rules_config: list[dict] | None = None
_suspicious_addresses: set[str] | None = None
_country_risk: dict[str, dict] | None = None
_country_risk_default: int = 1


@dataclass
class RuleMatch:
    rule_id: str
    rule_name: str
    alert_level: str
    risk_score: int
    message: str
    details: dict[str, Any] = field(default_factory=dict)


def _load_rules() -> list[dict]:
    global _rules_config
    if _rules_config is None:
        with open(RULES_DIR / "rules.json") as f:
            _rules_config = json.load(f)["rules"]
    return _rules_config


def _load_suspicious_addresses() -> set[str]:
    global _suspicious_addresses
    if _suspicious_addresses is None:
        path = RULES_DIR / "suspicious_addresses.csv"
        _suspicious_addresses = set()
        with open(path, newline="") as f:
            reader = csv.DictReader(f)
            for row in reader:
                addr = row.get("address", "").strip().lower()
                if addr:
                    _suspicious_addresses.add(addr)
    return _suspicious_addresses


def _load_country_risk() -> tuple[dict[str, dict], int]:
    global _country_risk, _country_risk_default
    if _country_risk is None:
        with open(RULES_DIR / "country_risk.json") as f:
            data = json.load(f)
        _country_risk = {k.upper(): v for k, v in data["country_risk"].items()}
        _country_risk_default = data.get("default_risk_level", 1)
    return _country_risk, _country_risk_default


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------

def reload_all() -> None:
    """Force reload of all rule data from disk (useful after config changes)."""
    global _rules_config, _suspicious_addresses, _country_risk, _country_risk_default
    _rules_config = None
    _suspicious_addresses = None
    _country_risk = None
    _country_risk_default = 1
    _load_rules()
    _load_suspicious_addresses()
    _load_country_risk()


def get_country_risk_level(country_code: str | None) -> int:
    """Return risk level 1-3 for an ISO-3166 country code."""
    if not country_code:
        return _country_risk_default
    risk_map, default = _load_country_risk()
    entry = risk_map.get(country_code.upper())
    return entry["risk_level"] if entry else default


def is_suspicious_address(address: str) -> bool:
    addresses = _load_suspicious_addresses()
    return address.strip().lower() in addresses


# ---------------------------------------------------------------------------
# Evaluation
# ---------------------------------------------------------------------------

def evaluate(
    transaction: dict,
    tx_history: list[dict],
) -> list[RuleMatch]:
    """
    Evaluate a transaction dict against all enabled rules.

    Parameters
    ----------
    transaction : dict
        Keys: from_address, to_address, amount, currency, timestamp,
              country_code (optional)
    tx_history : list[dict]
        Recent transactions for the same from_address (used for velocity /
        cumulative checks).  Each entry has the same schema as *transaction*.

    Returns
    -------
    list[RuleMatch]
    """
    rules = _load_rules()
    matches: list[RuleMatch] = []

    for rule in rules:
        if not rule.get("enabled", True):
            continue

        rule_type = rule["type"]
        params = rule.get("params", {})

        match rule_type:
            case "velocity":
                match = _check_velocity(rule, params, transaction, tx_history)
            case "threshold_cumulative":
                match = _check_threshold_cumulative(rule, params, transaction, tx_history)
            case "threshold_single":
                match = _check_threshold_single(rule, params, transaction)
            case "counterparty_blocklist":
                match = _check_counterparty_blocklist(rule, params, transaction)
            case "country_risk":
                match = _check_country_risk(rule, params, transaction)
            case _:
                match = None

        if match:
            matches.append(match)

    return matches


# ---------------------------------------------------------------------------
# Individual rule checkers
# ---------------------------------------------------------------------------

def _check_velocity(
    rule: dict,
    params: dict,
    tx: dict,
    history: list[dict],
) -> RuleMatch | None:
    import datetime

    max_count: int = params.get("max_count", 5)
    window_sec: int = params.get("window_seconds", 3600)

    tx_ts = _parse_ts(tx.get("timestamp"))
    cutoff = tx_ts - datetime.timedelta(seconds=window_sec)

    recent = [
        t for t in history
        if _parse_ts(t.get("timestamp")) >= cutoff
        and t.get("from_address", "").lower() == tx.get("from_address", "").lower()
    ]
    # Include the current transaction
    count = len(recent) + 1

    if count > max_count:
        msg = rule["message"].format(
            max_count=max_count,
            window_seconds=window_sec,
        )
        return RuleMatch(
            rule_id=rule["id"],
            rule_name=rule["name"],
            alert_level=rule["alert_level"],
            risk_score=rule["risk_score"],
            message=msg,
            details={"transaction_count": count, "window_seconds": window_sec},
        )
    return None


def _check_threshold_cumulative(
    rule: dict,
    params: dict,
    tx: dict,
    history: list[dict],
) -> RuleMatch | None:
    import datetime

    threshold: float = params.get("threshold", 10_000)
    currency: str | None = params.get("currency")
    window_sec: int = params.get("window_seconds", 86400)

    tx_ts = _parse_ts(tx.get("timestamp"))
    cutoff = tx_ts - datetime.timedelta(seconds=window_sec)

    total = float(tx.get("amount", 0))
    for t in history:
        if _parse_ts(t.get("timestamp")) < cutoff:
            continue
        if t.get("from_address", "").lower() != tx.get("from_address", "").lower():
            continue
        if currency and t.get("currency", "").upper() != currency.upper():
            continue
        total += float(t.get("amount", 0))

    # Apply currency filter to current tx
    if currency and tx.get("currency", "").upper() != currency.upper():
        return None

    if total > threshold:
        msg = rule["message"].format(threshold=threshold, currency=currency or "ANY")
        return RuleMatch(
            rule_id=rule["id"],
            rule_name=rule["name"],
            alert_level=rule["alert_level"],
            risk_score=rule["risk_score"],
            message=msg,
            details={"cumulative_amount": total, "threshold": threshold, "currency": currency},
        )
    return None


def _check_threshold_single(
    rule: dict,
    params: dict,
    tx: dict,
) -> RuleMatch | None:
    threshold: float = params.get("threshold", 50_000)
    amount = float(tx.get("amount", 0))

    if amount > threshold:
        msg = rule["message"].format(amount=amount, threshold=threshold)
        return RuleMatch(
            rule_id=rule["id"],
            rule_name=rule["name"],
            alert_level=rule["alert_level"],
            risk_score=rule["risk_score"],
            message=msg,
            details={"amount": amount, "threshold": threshold},
        )
    return None


def _check_counterparty_blocklist(
    rule: dict,
    params: dict,  # noqa: ARG001
    tx: dict,
) -> RuleMatch | None:
    for field_name in ("from_address", "to_address"):
        addr = tx.get(field_name, "")
        if addr and is_suspicious_address(addr):
            msg = rule["message"].format(address=addr)
            return RuleMatch(
                rule_id=rule["id"],
                rule_name=rule["name"],
                alert_level=rule["alert_level"],
                risk_score=rule["risk_score"],
                message=msg,
                details={"flagged_address": addr, "field": field_name},
            )
    return None


def _check_country_risk(
    rule: dict,
    params: dict,
    tx: dict,
) -> RuleMatch | None:
    min_level: int = params.get("min_risk_level", 3)
    max_level: int = params.get("max_risk_level", 3)

    country = tx.get("country_code", "")
    if not country:
        return None

    risk_map, _ = _load_country_risk()
    entry = risk_map.get(country.upper())
    if not entry:
        return None

    level = entry["risk_level"]
    if min_level <= level <= max_level:
        msg = rule["message"].format(
            country=country.upper(),
            risk_level=level,
            min_risk_level=min_level,
        )
        return RuleMatch(
            rule_id=rule["id"],
            rule_name=rule["name"],
            alert_level=rule["alert_level"],
            risk_score=rule["risk_score"],
            message=msg,
            details={"country_code": country.upper(), "risk_level": level, "reason": entry.get("reason", "")},
        )
    return None


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _parse_ts(ts) -> "datetime.datetime":
    import datetime

    if isinstance(ts, datetime.datetime):
        return ts
    if isinstance(ts, (int, float)):
        return datetime.datetime.fromtimestamp(ts, tz=datetime.timezone.utc)
    if isinstance(ts, str):
        # ISO 8601
        try:
            return datetime.datetime.fromisoformat(ts.replace("Z", "+00:00"))
        except ValueError:
            pass
    return datetime.datetime.now(tz=datetime.timezone.utc)
