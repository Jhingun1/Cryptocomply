"""
Etherscan (and BSCScan) blockchain API client.

Uses the **free** tier of Etherscan's API.  Set the ETHERSCAN_API_KEY
environment variable (or BSCSCAN_API_KEY for BSC) before starting the server.
"""
from __future__ import annotations

import os
import time
from typing import Any

import httpx

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

ETHERSCAN_BASE_URL = os.getenv("ETHERSCAN_BASE_URL", "https://api.etherscan.io/api")
BSCSCAN_BASE_URL = os.getenv("BSCSCAN_BASE_URL", "https://api.bscscan.com/api")

ETHERSCAN_API_KEY = os.getenv("ETHERSCAN_API_KEY", "")
BSCSCAN_API_KEY = os.getenv("BSCSCAN_API_KEY", "")

DEFAULT_CHAIN = os.getenv("DEFAULT_CHAIN", "ethereum")  # "ethereum" or "bsc"

_HTTP_TIMEOUT = 10.0  # seconds


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

def _base_url(chain: str) -> str:
    return BSCSCAN_BASE_URL if chain.lower() == "bsc" else ETHERSCAN_BASE_URL


def _api_key(chain: str) -> str:
    return BSCSCAN_API_KEY if chain.lower() == "bsc" else ETHERSCAN_API_KEY


def _to_tx_dict(raw: dict) -> dict:
    """Normalise a raw Etherscan transaction record."""
    return {
        "hash": raw.get("hash", ""),
        "block_number": int(raw.get("blockNumber", 0) or 0),
        "timestamp": int(raw.get("timeStamp", 0) or 0),
        "from_address": raw.get("from", ""),
        "to_address": raw.get("to", ""),
        "value_wei": raw.get("value", "0"),
        "value_eth": round(int(raw.get("value", "0")) / 1e18, 8),
        "gas": int(raw.get("gas", 0) or 0),
        "gas_price": int(raw.get("gasPrice", 0) or 0),
        "is_error": raw.get("isError", "0") == "1",
        "confirmations": int(raw.get("confirmations", 0) or 0),
        "contract_address": raw.get("contractAddress", ""),
        "token_name": raw.get("tokenName", ""),
        "token_symbol": raw.get("tokenSymbol", ""),
        "token_decimal": raw.get("tokenDecimal", ""),
    }


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def get_transaction_history(
    address: str,
    limit: int = 10,
    chain: str = DEFAULT_CHAIN,
) -> list[dict]:
    """
    Fetch the last *limit* transactions for *address* from Etherscan/BSCScan.

    Parameters
    ----------
    address : str
        Blockchain address (0x…).
    limit : int
        Number of most-recent transactions to return (max 100).
    chain : str
        "ethereum" or "bsc".

    Returns
    -------
    list[dict]
        Normalised transaction records.

    Raises
    ------
    httpx.HTTPError
        On network failure.
    ValueError
        If the API returns an error status.
    """
    limit = min(limit, 100)
    params: dict[str, Any] = {
        "module": "account",
        "action": "txlist",
        "address": address,
        "startblock": 0,
        "endblock": 99_999_999,
        "page": 1,
        "offset": limit,
        "sort": "desc",
        "apikey": _api_key(chain) or "YourApiKeyToken",
    }

    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
        resp = await client.get(_base_url(chain), params=params)
        resp.raise_for_status()
        data = resp.json()

    status = data.get("status", "0")
    message = data.get("message", "")

    # "No transactions found" is not an error
    if status == "0" and message not in ("No transactions found", "No records found"):
        raise ValueError(f"Etherscan API error: {message} – {data.get('result', '')}")

    raw_list = data.get("result") or []
    if isinstance(raw_list, str):
        # Some error messages come back as a string in result
        return []

    return [_to_tx_dict(tx) for tx in raw_list[:limit]]


async def get_token_transfers(
    address: str,
    limit: int = 10,
    chain: str = DEFAULT_CHAIN,
) -> list[dict]:
    """
    Fetch ERC-20 token transfer events for *address*.
    """
    limit = min(limit, 100)
    params: dict[str, Any] = {
        "module": "account",
        "action": "tokentx",
        "address": address,
        "page": 1,
        "offset": limit,
        "sort": "desc",
        "apikey": _api_key(chain) or "YourApiKeyToken",
    }

    async with httpx.AsyncClient(timeout=_HTTP_TIMEOUT) as client:
        resp = await client.get(_base_url(chain), params=params)
        resp.raise_for_status()
        data = resp.json()

    status = data.get("status", "0")
    message = data.get("message", "")

    if status == "0" and message not in ("No transactions found", "No records found"):
        raise ValueError(f"Etherscan API error: {message}")

    raw_list = data.get("result") or []
    if isinstance(raw_list, str):
        return []

    return [_to_tx_dict(tx) for tx in raw_list[:limit]]
