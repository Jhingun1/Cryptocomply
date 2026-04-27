# CryptoComply – AML/KYC Orchestration API

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.111-green.svg)](https://fastapi.tiangolo.com/)

A lightweight, open-source **AML/KYC orchestration API** built with FastAPI,
targeting small crypto and fintech startups (stablecoin apps, DeFi dashboards, payment processors).

---

## Table of Contents

1. [Features](#features)
2. [Project Structure](#project-structure)
3. [Setup & Installation](#setup--installation)
4. [Running the API](#running-the-api)
5. [API Reference](#api-reference)
6. [API Examples](#api-examples)
7. [Extending Custom Rules](#extending-custom-rules)
8. [Blockchain Integration](#blockchain-integration)
9. [License](#license)

---

## Features

| Module | Description |
|--------|-------------|
| **Rules Engine** | JSON-configurable risk scoring: velocity checks, amount thresholds, suspicious-address blocklist, country risk |
| **Transaction Monitoring** | `POST /transactions/score` scores any transaction 0-100 and returns triggered alerts |
| **Alerts Feed** | `GET /transactions/alerts` returns recent flagged transactions |
| **KYC/KYB Stub** | In-memory identity verification simulation; swappable for a real provider |
| **Blockchain Client** | Fetches transaction history from Etherscan or BSCScan (free API tier) |

---

## Project Structure

```
CryptoComply/
├── app/
│   ├── rules/
│   │   ├── __init__.py
│   │   ├── engine.py               # Core rule evaluation logic
│   │   ├── rules.json              # Rule definitions (velocity, threshold, etc.)
│   │   ├── suspicious_addresses.csv# Known mixer / sanctioned addresses
│   │   └── country_risk.json       # ISO country risk levels (1-3)
│   ├── monitoring/
│   │   ├── __init__.py
│   │   ├── router.py               # FastAPI endpoints for scoring & alerts
│   │   ├── scorer.py               # Aggregates rule matches into a risk score
│   │   └── store.py                # In-memory transaction & alert store
│   ├── kyc/
│   │   ├── __init__.py
│   │   ├── router.py               # FastAPI endpoints for KYC
│   │   └── verifier.py             # In-memory KYC stub
│   ├── blockchain/
│   │   ├── __init__.py
│   │   ├── router.py               # FastAPI endpoints for on-chain lookup
│   │   └── etherscan.py            # Etherscan / BSCScan async client
│   └── __init__.py
├── main.py                         # App factory + entry point
├── requirements.txt
└── README.md
```

---

## Setup & Installation

### Prerequisites

- Python **3.11+**
- An Etherscan API key (free at https://etherscan.io/register) – optional but recommended

### 1 – Clone and install dependencies

```bash
git clone https://github.com/Jhingun1/Cryptocomply.git
cd Cryptocomply
pip install -r requirements.txt
```

### 2 – Configure environment variables

Create a `.env` file or export variables in your shell:

```bash
# Blockchain API keys (free tier)
ETHERSCAN_API_KEY=your_etherscan_key_here
BSCSCAN_API_KEY=your_bscscan_key_here   # optional

# Chain used by default (ethereum | bsc)
DEFAULT_CHAIN=ethereum

# Server settings (optional)
HOST=0.0.0.0
PORT=8000

# CORS origins – comma-separated (default: all)
CORS_ORIGINS=*
```

`python-dotenv` will load `.env` automatically if the file exists.

---

## Running the API

```bash
# Development (auto-reload)
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Or via Python directly
python main.py

# Production (e.g. 4 workers)
uvicorn main:app --workers 4 --host 0.0.0.0 --port 8000
```

Open the interactive docs at **http://localhost:8000/docs** (Swagger UI) or
**http://localhost:8000/redoc**.

---

## API Reference

### Transaction Monitoring

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/transactions/score` | Score a transaction (0-100) and list triggered rules |
| `GET` | `/transactions/alerts` | Get recent flagged transactions |
| `DELETE` | `/transactions/alerts` | Clear all alerts (dev/test use) |

### KYC / KYB

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/kyc/status/{user_id}` | Get verification status for a user |
| `POST` | `/kyc/submit/{user_id}` | Submit identity documents |
| `PATCH` | `/kyc/status/{user_id}` | Manually update status (admin) |
| `GET` | `/kyc/users` | List all KYC records (admin) |

### Blockchain

| Method | Path | Description |
|--------|------|-------------|
| `GET` | `/blockchain/transactions/{address}` | Last N normal transactions (Etherscan) |
| `GET` | `/blockchain/token-transfers/{address}` | Last N ERC-20 token transfers |

### Health

| Method | Path |
|--------|------|
| `GET` | `/` |
| `GET` | `/health` |

---

## API Examples

### Score a transaction (curl)

```bash
curl -X POST http://localhost:8000/transactions/score \
  -H "Content-Type: application/json" \
  -d '{
    "from_address": "0x1da5821544e25c636c1417ba96ade4cf6d2f9b5a",
    "to_address": "0xabcdef1234567890abcdef1234567890abcdef12",
    "amount": 75000,
    "currency": "USDC",
    "timestamp": "2024-01-15T12:00:00Z",
    "country_code": "KP"
  }'
```

**Response:**

```json
{
  "transaction_id": "c8f3a1b2-...",
  "risk_score": 100,
  "risk_level": "CRITICAL",
  "flagged": true,
  "triggered_rules": [
    {
      "rule_id": "suspicious_counterparty",
      "rule_name": "Suspicious Counterparty",
      "alert_level": "CRITICAL",
      "risk_score": 80,
      "message": "Address 0x1da58... is on the suspicious counterparty blocklist",
      "details": { "flagged_address": "0x1da5...", "field": "from_address" }
    },
    {
      "rule_id": "single_large_tx",
      "rule_name": "Single Large Transaction",
      "alert_level": "MEDIUM",
      "risk_score": 30,
      "message": "Single transaction amount 75000.0 exceeds threshold of 50000",
      "details": { "amount": 75000.0, "threshold": 50000 }
    }
  ],
  "scored_at": "2024-01-15T12:00:01Z",
  "from_address": "0x1da5821544e25c636c1417ba96ade4cf6d2f9b5a",
  "to_address": "0xabcdef...",
  "amount": 75000.0,
  "currency": "USDC",
  "timestamp": "2024-01-15T12:00:00Z"
}
```

### Score a transaction (Python)

```python
import requests, datetime

resp = requests.post("http://localhost:8000/transactions/score", json={
    "from_address": "0xabc123",
    "to_address": "0xdef456",
    "amount": 500,
    "currency": "ETH",
    "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
})
print(resp.json())
```

### Get flagged transactions

```bash
# All alerts
curl http://localhost:8000/transactions/alerts

# Filter by alert level and sender
curl "http://localhost:8000/transactions/alerts?alert_level=CRITICAL&limit=20"
```

### KYC – submit identity documents

```bash
# Check status (creates PENDING record on first call)
curl http://localhost:8000/kyc/status/user_42

# Submit documents
curl -X POST http://localhost:8000/kyc/submit/user_42 \
  -H "Content-Type: application/json" \
  -d '{"document_type": "passport", "full_name": "Alice Smith", "nationality": "US"}'

# Force review outcome (stub only)
curl -X POST http://localhost:8000/kyc/submit/user_42 \
  -H "Content-Type: application/json" \
  -d '{"document_type": "passport", "review": true}'
```

### Blockchain – fetch transaction history

```bash
# Last 10 ETH transactions
curl "http://localhost:8000/blockchain/transactions/0xde0B295669a9FD93d5F28D9Ec85E40f4cb697BAe?limit=10&chain=ethereum"

# ERC-20 token transfers on BSC
curl "http://localhost:8000/blockchain/token-transfers/0xde0B295669a9FD93d5F28D9Ec85E40f4cb697BAe?chain=bsc"
```

---

## Extending Custom Rules

All rules are defined in `app/rules/rules.json`. No code changes are required to add new rules.

### Rule schema

```json
{
  "id": "my_new_rule",
  "name": "My New Rule",
  "description": "Human-readable description",
  "enabled": true,
  "type": "threshold_single",
  "params": {
    "threshold": 1000
  },
  "risk_score": 25,
  "alert_level": "MEDIUM",
  "message": "Amount {amount} exceeded threshold {threshold}"
}
```

### Supported rule types

| `type` | Description | Key `params` |
|--------|-------------|--------------|
| `velocity` | Max transactions in a time window (per sender) | `max_count`, `window_seconds` |
| `threshold_single` | Single-transaction amount exceeds a value | `threshold` |
| `threshold_cumulative` | Cumulative amount in a time window exceeds a value | `threshold`, `currency`, `window_seconds` |
| `counterparty_blocklist` | Sender or recipient is in `suspicious_addresses.csv` | *(none)* |
| `country_risk` | Sender's country code has a risk level in range [min, max] | `min_risk_level`, `max_risk_level` |

### Adding a new address to the blocklist

Append a row to `app/rules/suspicious_addresses.csv`:

```
0xNEW_ADDRESS_HERE,Label,mixer
```

Call `GET /admin/reload-rules` (or restart the server) to pick up changes.
The engine lazily reloads data on the **first request** after a process start.
To force a hot-reload, call `app.rules.engine.reload_all()`.

### Adding a new country risk entry

Edit `app/rules/country_risk.json`:

```json
"XX": { "name": "Examplestan", "risk_level": 3, "reason": "Sanctions" }
```

### Adding a new rule *type*

1. Add a new case to the `match rule_type:` block in `app/rules/engine.py`.
2. Implement a `_check_<type>()` function following the existing pattern.
3. Add rule entries in `rules.json` with the new type.

---

## Blockchain Integration

The Etherscan client (`app/blockchain/etherscan.py`) exposes two async functions:

```python
from app.blockchain.etherscan import get_transaction_history, get_token_transfers

# Fetch last 10 normal transactions
txs = await get_transaction_history("0xabc...", limit=10, chain="ethereum")

# Fetch last 10 ERC-20 transfers
transfers = await get_token_transfers("0xabc...", limit=10, chain="bsc")
```

Each result dict contains: `hash`, `block_number`, `timestamp`, `from_address`,
`to_address`, `value_eth`, `gas`, `is_error`, `token_symbol`, etc.

To swap in a different provider, replace the implementation in `etherscan.py` while
keeping the same function signatures.

---

## License

This project is licensed under the **MIT License** – see below.

```
MIT License

Copyright (c) 2024 CryptoComply Contributors

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
```