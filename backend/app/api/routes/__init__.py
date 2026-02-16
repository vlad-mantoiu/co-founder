from fastapi import APIRouter

from app.api.routes import admin, agent, billing, features, health, onboarding, projects

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(agent.router, prefix="/agent", tags=["agent"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(onboarding.router, prefix="/onboarding", tags=["onboarding"])
api_router.include_router(admin.router, tags=["admin"])
api_router.include_router(billing.router, tags=["billing"])
api_router.include_router(features.router, prefix="/features", tags=["features"])
