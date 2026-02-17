from fastapi import APIRouter

from app.api.routes import admin, agent, artifacts, billing, change_requests, dashboard, decision_gates, deploy_readiness, execution_plans, features, generation, health, jobs, onboarding, projects, strategy_graph, timeline, understanding

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(agent.router, prefix="/agent", tags=["agent"])
api_router.include_router(projects.router, prefix="/projects", tags=["projects"])
api_router.include_router(onboarding.router, prefix="/onboarding", tags=["onboarding"])
api_router.include_router(understanding.router, prefix="/understanding", tags=["understanding"])
api_router.include_router(jobs.router, prefix="/jobs", tags=["jobs"])
api_router.include_router(generation.router, prefix="/generation", tags=["generation"])
api_router.include_router(artifacts.router, prefix="/artifacts", tags=["artifacts"])
api_router.include_router(dashboard.router, prefix="/dashboard", tags=["dashboard"])
api_router.include_router(decision_gates.router, prefix="/gates", tags=["decision-gates"])
api_router.include_router(execution_plans.router, prefix="/plans", tags=["execution-plans"])
api_router.include_router(change_requests.router, prefix="/change-requests", tags=["change-requests"])
api_router.include_router(deploy_readiness.router, prefix="/deploy-readiness", tags=["deploy-readiness"])
api_router.include_router(admin.router, tags=["admin"])
api_router.include_router(billing.router, tags=["billing"])
api_router.include_router(features.router, prefix="/features", tags=["features"])
api_router.include_router(strategy_graph.router, prefix="/graph", tags=["strategy-graph"])
api_router.include_router(timeline.router, prefix="/timeline", tags=["timeline"])
