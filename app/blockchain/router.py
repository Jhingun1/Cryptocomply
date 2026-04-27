"""
Blockchain query FastAPI router.
"""
from __future__ import annotations

from typing import Annotated, Any

import httpx
from fastapi import APIRouter, HTTPException, Path, Query

from app.blockchain.etherscan import get_token_transfers, get_transaction_history

router = APIRouter(prefix="/blockchain", tags=["Blockchain"])


@router.get(
    "/transactions/{address}",
    summary="Get transaction history for an address",
)
async def tx_history(
    address: Annotated[str, Path(description="Blockchain address (0x…)")],
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    chain: Annotated[str, Query(description="Chain: ethereum or bsc")] = "ethereum",
) -> dict[str, Any]:
    """
    Fetch the last *limit* transactions for *address* from Etherscan/BSCScan.
    """
    try:
        txs = await get_transaction_history(address, limit=limit, chain=chain)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Upstream API error: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {"address": address, "chain": chain, "count": len(txs), "transactions": txs}


@router.get(
    "/token-transfers/{address}",
    summary="Get ERC-20 token transfer history for an address",
)
async def token_transfers(
    address: Annotated[str, Path(description="Blockchain address (0x…)")],
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    chain: Annotated[str, Query(description="Chain: ethereum or bsc")] = "ethereum",
) -> dict[str, Any]:
    """
    Fetch ERC-20 token transfer events for *address* from Etherscan/BSCScan.
    """
    try:
        transfers = await get_token_transfers(address, limit=limit, chain=chain)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Upstream API error: {exc}") from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {
        "address": address,
        "chain": chain,
        "count": len(transfers),
        "transfers": transfers,
    }
