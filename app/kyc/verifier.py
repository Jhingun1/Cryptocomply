"""
KYC/KYB stub – in-memory identity verification store.

In a production system this module would integrate an external KYC provider
(e.g. Jumio, Onfido, Sumsub).  Here we simulate the workflow with an
in-memory dict so that the API surface is realistic and easily replaceable.
"""
from __future__ import annotations

import threading
from datetime import datetime, timezone
from enum import Enum
from typing import Any


class VerificationStatus(str, Enum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    UNDER_REVIEW = "UNDER_REVIEW"


_lock = threading.Lock()
_store: dict[str, dict] = {}


def _now() -> str:
    return datetime.now(tz=timezone.utc).isoformat()


def get_or_create(user_id: str) -> dict:
    """Return the verification record for *user_id*, creating one if absent."""
    with _lock:
        if user_id not in _store:
            _store[user_id] = {
                "user_id": user_id,
                "status": VerificationStatus.PENDING,
                "created_at": _now(),
                "updated_at": _now(),
                "notes": "Verification not yet submitted.",
                "documents": [],
            }
        return dict(_store[user_id])


def submit_verification(user_id: str, payload: dict[str, Any]) -> dict:
    """
    Simulate submitting identity documents for verification.

    Applies a simple deterministic rule:
    - If ``payload`` contains ``"reject": true`` → REJECTED
    - If ``payload`` contains ``"review": true`` → UNDER_REVIEW
    - Otherwise → APPROVED
    """
    with _lock:
        record = _store.setdefault(
            user_id,
            {
                "user_id": user_id,
                "status": VerificationStatus.PENDING,
                "created_at": _now(),
                "updated_at": _now(),
                "notes": "",
                "documents": [],
            },
        )

        if payload.get("reject"):
            record["status"] = VerificationStatus.REJECTED
            record["notes"] = "Submission flagged for rejection."
        elif payload.get("review"):
            record["status"] = VerificationStatus.UNDER_REVIEW
            record["notes"] = "Manual review required."
        else:
            record["status"] = VerificationStatus.APPROVED
            record["notes"] = "Auto-approved by stub verifier."

        doc = payload.get("document_type", "unknown")
        record["documents"].append({"type": doc, "submitted_at": _now()})
        record["updated_at"] = _now()

        return dict(record)


def update_status(user_id: str, status: VerificationStatus, notes: str = "") -> dict:
    """Directly update a user's verification status (admin use)."""
    with _lock:
        if user_id not in _store:
            raise KeyError(f"User {user_id!r} not found.")
        _store[user_id]["status"] = status
        _store[user_id]["notes"] = notes
        _store[user_id]["updated_at"] = _now()
        return dict(_store[user_id])


def list_users(status_filter: VerificationStatus | None = None) -> list[dict]:
    with _lock:
        records = list(_store.values())
    if status_filter:
        records = [r for r in records if r["status"] == status_filter]
    return records
