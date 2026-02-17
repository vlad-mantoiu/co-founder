"""Project management API routes — DB-backed."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import exists, and_, func, select

from app.core.auth import ClerkUser, require_auth, require_subscription
from app.core.llm_config import get_or_create_user_settings
from app.db.base import get_session_factory
from app.db.models.artifact import Artifact
from app.db.models.decision_gate import DecisionGate
from app.db.models.project import Project
from app.db.models.understanding_session import UnderstandingSession

router = APIRouter()


class ProjectCreate(BaseModel):
    name: str
    description: str = ""
    github_repo: str | None = None


class ProjectResponse(BaseModel):
    id: str
    name: str
    description: str
    github_repo: str | None
    created_at: str
    status: str
    has_pending_gate: bool = False
    has_understanding_session: bool = False
    has_brief: bool = False


async def _compute_project_flags(session, project_id: str) -> dict:
    """Compute boolean context flags for a project via efficient EXISTS subqueries."""
    pending_gate_q = select(
        exists().where(
            and_(
                DecisionGate.project_id == project_id,
                DecisionGate.status == "pending",
            )
        )
    )
    understanding_session_q = select(
        exists().where(
            and_(
                UnderstandingSession.project_id == project_id,
                UnderstandingSession.status == "in_progress",
            )
        )
    )
    brief_q = select(
        exists().where(
            and_(
                Artifact.project_id == project_id,
                Artifact.artifact_type == "idea_brief",
            )
        )
    )

    has_pending_gate = (await session.execute(pending_gate_q)).scalar() or False
    has_understanding_session = (await session.execute(understanding_session_q)).scalar() or False
    has_brief = (await session.execute(brief_q)).scalar() or False

    return {
        "has_pending_gate": has_pending_gate,
        "has_understanding_session": has_understanding_session,
        "has_brief": has_brief,
    }


@router.post("/", response_model=ProjectResponse)
async def create_project(request: ProjectCreate, user: ClerkUser = Depends(require_subscription)):
    """Create a new project, respecting plan limits."""
    factory = get_session_factory()

    # Check plan limit
    user_settings = await get_or_create_user_settings(user.user_id)
    max_projects = (
        user_settings.override_max_projects
        if user_settings.override_max_projects is not None
        else user_settings.plan_tier.max_projects
    )

    async with factory() as session:
        if max_projects != -1:
            result = await session.execute(
                select(func.count(Project.id)).where(
                    Project.clerk_user_id == user.user_id,
                    Project.status == "active",
                )
            )
            count = result.scalar() or 0
            if count >= max_projects:
                raise HTTPException(
                    status_code=403,
                    detail=f"Project limit reached ({count}/{max_projects}). Upgrade your plan.",
                )

        project = Project(
            clerk_user_id=user.user_id,
            name=request.name,
            description=request.description,
            github_repo=request.github_repo,
        )
        session.add(project)
        await session.commit()
        await session.refresh(project)

        return ProjectResponse(
            id=str(project.id),
            name=project.name,
            description=project.description,
            github_repo=project.github_repo,
            created_at=project.created_at.isoformat(),
            status=project.status,
            has_pending_gate=False,
            has_understanding_session=False,
            has_brief=False,
        )


@router.get("/", response_model=list[ProjectResponse])
async def list_projects(user: ClerkUser = Depends(require_auth)):
    """List all projects for the current user."""
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(Project)
            .where(Project.clerk_user_id == user.user_id)
            .order_by(Project.created_at.desc())
        )
        projects = result.scalars().all()
        responses = []
        for p in projects:
            flags = await _compute_project_flags(session, str(p.id))
            responses.append(
                ProjectResponse(
                    id=str(p.id),
                    name=p.name,
                    description=p.description,
                    github_repo=p.github_repo,
                    created_at=p.created_at.isoformat(),
                    status=p.status,
                    **flags,
                )
            )
        return responses


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, user: ClerkUser = Depends(require_auth)):
    """Get a specific project."""
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(Project).where(
                Project.id == project_id,
                Project.clerk_user_id == user.user_id,
            )
        )
        project = result.scalar_one_or_none()
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")

        flags = await _compute_project_flags(session, str(project.id))

        return ProjectResponse(
            id=str(project.id),
            name=project.name,
            description=project.description,
            github_repo=project.github_repo,
            created_at=project.created_at.isoformat(),
            status=project.status,
            **flags,
        )


@router.delete("/{project_id}")
async def delete_project(project_id: str, user: ClerkUser = Depends(require_auth)):
    """Soft-delete a project."""
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(Project).where(
                Project.id == project_id,
                Project.clerk_user_id == user.user_id,
            )
        )
        project = result.scalar_one_or_none()
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")

        project.status = "deleted"
        await session.commit()
        return {"status": "deleted"}


@router.post("/{project_id}/link-github")
async def link_github_repo(
    project_id: str, github_repo: str, user: ClerkUser = Depends(require_auth)
):
    """Link a GitHub repository to a project."""
    factory = get_session_factory()
    async with factory() as session:
        result = await session.execute(
            select(Project).where(
                Project.id == project_id,
                Project.clerk_user_id == user.user_id,
            )
        )
        project = result.scalar_one_or_none()
        if project is None:
            raise HTTPException(status_code=404, detail="Project not found")

        project.github_repo = github_repo
        await session.commit()

        return {"status": "linked", "github_repo": github_repo}
