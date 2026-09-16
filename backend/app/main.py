"""
ClearFlow Small Chits Workflow Automation — FastAPI backend entrypoint.

Authentication Guardrail (Blueprint section 3): unauthenticated requests to
any /api route other than /api/auth/* and /api/health are rejected at the
dependency layer (see app.core.security.get_current_manager), not here — this
keeps the guardrail testable per-router rather than as brittle middleware.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.routers import auth, chittis, dashboard, drive, onboarding, shares, whatsapp

settings = get_settings()

app = FastAPI(
    title=settings.APP_NAME,
    description="Small Chits Workflow Automation — Master SaaS Blueprint (ClearFlow Automations)",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(onboarding.router)
app.include_router(chittis.router)
app.include_router(shares.router)
app.include_router(dashboard.router)
app.include_router(whatsapp.router)
app.include_router(drive.router)


@app.get("/api/health")
async def health_check():
    return {"status": "ok", "service": settings.APP_NAME}
