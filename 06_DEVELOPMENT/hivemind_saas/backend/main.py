"""
Everlight Hive Mind SaaS - FastAPI Backend
Multi-tenant AI orchestration platform.

Boot: uvicorn main:app --reload --port 8000
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
import logging
import time

from api.routers import auth, tenants, integrations, sessions, billing, mindmap, webhooks
from core.config import settings
from core.database import init_db

logger = logging.getLogger(__name__)

app = FastAPI(
    title="Everlight Hive Mind API",
    description="AI-powered multi-tenant SaaS orchestration platform",
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
)

# CORS - tighten in production to your actual frontend domain
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def add_request_timing(request: Request, call_next):
    start = time.time()
    response = await call_next(request)
    response.headers["X-Process-Time"] = f"{(time.time() - start)*1000:.1f}ms"
    return response


@app.on_event("startup")
async def on_startup():
    await init_db()
    logger.info("Everlight Hive Mind API started")


# Routers
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])
app.include_router(tenants.router, prefix="/api/tenants", tags=["Tenants"])
app.include_router(integrations.router, prefix="/api/integrations", tags=["Integrations"])
app.include_router(sessions.router, prefix="/api/sessions", tags=["Hive Sessions"])
app.include_router(mindmap.router, prefix="/api/mindmap", tags=["Mindmap"])
app.include_router(billing.router, prefix="/api/billing", tags=["Billing"])
app.include_router(webhooks.router, prefix="/api/webhooks", tags=["Webhooks"])


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "everlight-hive-mind"}
