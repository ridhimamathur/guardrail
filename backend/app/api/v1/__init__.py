from fastapi import APIRouter

from app.api.v1 import actions, approvals, audit, auth, health, metrics, tasks

api_router = APIRouter(prefix="/api/v1")
api_router.include_router(auth.router)
api_router.include_router(tasks.router)
api_router.include_router(actions.router)
api_router.include_router(approvals.router)
api_router.include_router(audit.router)
api_router.include_router(health.router)
api_router.include_router(metrics.router)
