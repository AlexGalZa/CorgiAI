"""
AIB entry point — FastAPI REST API serving the React frontend.

Run with:  python -m app
"""

from __future__ import annotations

import os

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles

from app import config
from app.database import test_connection
from app.routes.sessions import router as sessions_router
from app.routes.chat import router as chat_router
from app.routes.intakes import router as intakes_router

# ── FastAPI app ─────────────────────────────────────────────────────────
app = FastAPI(title="Corgi Insurance Broker API", version="1.0.0")

# CORS — allow React dev server in development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── API routes ──────────────────────────────────────────────────────────
app.include_router(sessions_router)
app.include_router(chat_router)
app.include_router(intakes_router)


@app.get("/api/health")
async def health():
    db_ok = test_connection()
    return JSONResponse({
        "status": "healthy" if db_ok else "degraded",
        "database": "connected" if db_ok else "disconnected (using in-memory fallback)",
    })


# ── Serve React build (production) ─────────────────────────────────────
# If client/dist exists, serve it as static files at /
_client_dist = os.path.join(os.path.dirname(os.path.dirname(__file__)), "client", "dist")
if os.path.isdir(_client_dist):
    # Serve static assets
    app.mount("/assets", StaticFiles(directory=os.path.join(_client_dist, "assets")), name="assets")

    # Serve other static files (favicon, logos, etc.)
    from fastapi.responses import FileResponse

    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        """Serve the React SPA — return index.html for all non-API routes."""
        file_path = os.path.join(_client_dist, full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
        return FileResponse(os.path.join(_client_dist, "index.html"))


# ── Main ────────────────────────────────────────────────────────────────
def main():
    db_ok = test_connection()
    if not db_ok:
        print("WARNING: Database not available. Using in-memory session storage.")

    print(f"Corgi Insurance Broker API starting on port {config.PORT}")
    print(f"Debug: {config.DEBUG}")

    if os.path.isdir(_client_dist):
        print(f"Serving React build from: {_client_dist}")
    else:
        print("No React build found. Run 'npm run build' in client/ for production.")
        print("For development, start the React dev server: cd client && npm run dev")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=config.PORT,
        log_level="debug" if config.DEBUG else "info",
    )


if __name__ == "__main__":
    main()
