from fastapi import APIRouter

from app.api.routes import admin, agent, health, projects

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(agent.router, prefix="/agent", tags=["agent"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(admin.router, tags=["admin"])
