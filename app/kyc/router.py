"""
KYC/KYB FastAPI router.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel, Field

from app.kyc.verifier import (
    VerificationStatus,
    get_or_create,
    list_users,
    submit_verification,
    update_status,
)

router = APIRouter(prefix="/kyc", tags=["KYC / KYB"])


# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

class KYCStatusResponse(BaseModel):
    user_id: str
    status: VerificationStatus
    created_at: str
    updated_at: str
    notes: str
    documents: list[dict[str, Any]]


class SubmitVerificationRequest(BaseModel):
    document_type: str | None = Field(
        "passport",
        description="Type of identity document submitted (passport, driver_license, etc.)"
    )
    full_name: str | None = Field(None, description="User's full legal name")
    date_of_birth: str | None = Field(None, description="Date of birth (YYYY-MM-DD)")
    nationality: str | None = Field(None, description="ISO-3166-1 alpha-2 nationality code")
    # Simulation flags – not used in production
    reject: bool = Field(False, description="[Stub] Force a REJECTED outcome")
    review: bool = Field(False, description="[Stub] Force an UNDER_REVIEW outcome")


class UpdateStatusRequest(BaseModel):
    status: VerificationStatus
    notes: str = ""


# ---------------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------------

@router.get(
    "/status/{user_id}",
    response_model=KYCStatusResponse,
    summary="Get KYC status for a user",
)
async def get_status(user_id: str) -> dict:
    """
    Returns the current KYC/KYB verification status for *user_id*.
    A new PENDING record is created if this is the first lookup.
    """
    return get_or_create(user_id)


@router.post(
    "/submit/{user_id}",
    response_model=KYCStatusResponse,
    summary="Submit identity verification documents",
)
async def submit(user_id: str, body: SubmitVerificationRequest) -> dict:
    """
    Simulate submitting identity documents for a user.

    In production this endpoint would forward documents to a KYC provider.
    The stub auto-approves unless the ``reject`` or ``review`` flags are set.
    """
    return submit_verification(user_id, body.model_dump())


@router.patch(
    "/status/{user_id}",
    response_model=KYCStatusResponse,
    summary="Manually update a user's KYC status (admin)",
)
async def patch_status(user_id: str, body: UpdateStatusRequest) -> dict:
    """
    Admin endpoint to manually override a user's verification status.
    """
    try:
        return update_status(user_id, body.status, body.notes)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get(
    "/users",
    response_model=list[KYCStatusResponse],
    summary="List all KYC users (admin)",
)
async def list_all(
    status: VerificationStatus | None = Query(None, description="Filter by status"),
) -> list[dict]:
    """
    Return all users in the KYC store, optionally filtered by status.
    """
    return list_users(status_filter=status)
