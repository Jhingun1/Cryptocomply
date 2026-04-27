"""
Transaction monitoring FastAPI router.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field, field_validator

from app.monitoring.scorer import score_transaction
from app.monitoring.store import get_alerts, clear_alerts

router = APIRouter(prefix="/transactions", tags=["Transaction Monitoring"])


# ---------------------------------------------------------------------------
# Request / Response schemas
# ---------------------------------------------------------------------------

class TransactionRequest(BaseModel):
    from_address: str = Field(..., description="Sender blockchain address")
    to_address: str = Field(..., description="Recipient blockchain address")
    amount: float = Field(..., gt=0, description="Transaction amount (positive)")
    currency: str = Field(..., description="Currency ticker, e.g. USDC, ETH")
    timestamp: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc),
        description="Transaction timestamp (ISO 8601). Defaults to now.",
    )
    country_code: str | None = Field(
        None, description="ISO-3166-1 alpha-2 country code of the sender"
    )
    transaction_id: str | None = Field(
        None, description="Optional client-supplied idempotency key"
    )
    metadata: dict[str, Any] | None = Field(
        None, description="Arbitrary extra fields passed through unchanged"
    )

    @field_validator("currency")
    @classmethod
    def upper_currency(cls, v: str) -> str:
        return v.upper()

    @field_validator("country_code")
    @classmethod
    def upper_country(cls, v: str | None) -> str | None:
        return v.upper() if v else None


class TriggeredRule(BaseModel):
    rule_id: str
    rule_name: str
    alert_level: str
    risk_score: int
    message: str
    details: dict[str, Any]


class ScoreResponse(BaseModel):
    transaction_id: str
    risk_score: int = Field(..., ge=0, le=100)
    risk_level: str
    flagged: bool
    triggered_rules: list[TriggeredRule]
    scored_at: str
    from_address: str
    to_address: str
    amount: float
    currency: str
    timestamp: datetime


class AlertsResponse(BaseModel):
    total: int
    alerts: list[dict[str, Any]]


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.post("/score", response_model=ScoreResponse, summary="Score a transaction")
async def score(body: TransactionRequest) -> dict:
    """
    Submit a transaction for AML/KYC risk scoring.

    Returns a **risk score** (0-100) and any **triggered rule alerts**.
    """
    tx_dict = body.model_dump()
    result = score_transaction(tx_dict)
    return result


@router.get("/alerts", response_model=AlertsResponse, summary="Get flagged transactions")
async def alerts(
    limit: Annotated[int, Query(ge=1, le=1000)] = 100,
    alert_level: Annotated[str | None, Query(description="Filter by alert level: LOW, MEDIUM, HIGH, CRITICAL")] = None,
    from_address: Annotated[str | None, Query(description="Filter by sender address")] = None,
) -> dict:
    """
    Retrieve recently flagged (alerted) transactions.
    """
    items = get_alerts(limit=limit, alert_level=alert_level, from_address=from_address)
    return {"total": len(items), "alerts": items}


@router.delete("/alerts", summary="Clear all alerts (admin)")
async def delete_alerts() -> dict:
    """
    Clear all stored alerts from the in-memory store.
    Useful for testing / development resets.
    """
    count = clear_alerts()
    return {"cleared": count}
