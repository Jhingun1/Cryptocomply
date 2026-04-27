"""
CryptoComply – AML/KYC Orchestration API
=========================================
Entry point for the FastAPI application.
"""
from __future__ import annotations

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.blockchain.router import router as blockchain_router
from app.kyc.router import router as kyc_router
from app.monitoring.router import router as monitoring_router

# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------

def create_app() -> FastAPI:
    app = FastAPI(
        title="CryptoComply – AML/KYC Orchestration API",
        description=(
            "Lightweight, modular AML/KYC orchestration API for crypto and fintech startups. "
            "Provides transaction risk scoring, rule-based alerting, KYC stub verification, "
            "and blockchain transaction history via Etherscan/BSCScan."
        ),
        version="1.0.0",
        contact={
            "name": "CryptoComply",
            "url": "https://github.com/Jhingun1/Cryptocomply",
        },
        license_info={"name": "MIT"},
    )

    # CORS – allow all origins by default (restrict in production)
    origins = os.getenv("CORS_ORIGINS", "*").split(",")
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Include routers
    app.include_router(monitoring_router)
    app.include_router(kyc_router)
    app.include_router(blockchain_router)

    @app.get("/", tags=["Health"], summary="Health check")
    async def root() -> dict:
        return {
            "service": "CryptoComply AML/KYC API",
            "version": "1.0.0",
            "status": "ok",
            "docs": "/docs",
        }

    @app.get("/health", tags=["Health"], summary="Liveness probe")
    async def health() -> dict:
        return {"status": "ok"}

    return app


app = create_app()

# ---------------------------------------------------------------------------
# Run directly with `python main.py` (dev convenience)
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "main:app",
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", "8000")),
        reload=True,
    )
