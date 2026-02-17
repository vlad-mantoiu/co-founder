from fastapi import APIRouter

from app.api.routes import admin, agent, artifacts, billing, dashboard, decision_gates, execution_plans, features, health, jobs, onboarding, projects, understanding

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(agent.router, prefix="/agent", tags=["agent"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(onboarding.router, prefix="/onboarding", tags=["onboarding"])
api_router.include_router(understanding.router, prefix="/understanding", tags=["understanding"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(artifacts.router, prefix="/artifacts", tags=["artifacts"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(decision_gates.router, prefix="/gates", tags=["decision-gates"])
api_router.include_router(execution_plans.router, prefix="/plans", tags=["execution-plans"])
api_router.include_router(admin.router, tags=["admin"])
api_router.include_router(billing.router, tags=["billing"])
api_router.include_router(features.router, prefix="/features", tags=["features"])
