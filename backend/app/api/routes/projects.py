"""Project management API routes — DB-backed."""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import func, select

from app.core.auth import ClerkUser, require_auth
from app.core.llm_config import get_or_create_user_settings
from app.db.base import get_session_factory
from app.db.models.project import Project

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


@router.post("/", response_model=ProjectResponse)
async def create_project(request: ProjectCreate, user: ClerkUser = Depends(require_auth)):
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
        return [
            ProjectResponse(
                id=str(p.id),
                name=p.name,
                description=p.description,
                github_repo=p.github_repo,
                created_at=p.created_at.isoformat(),
                status=p.status,
            )
            for p in projects
        ]


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

        return ProjectResponse(
            id=str(project.id),
            name=project.name,
            description=project.description,
            github_repo=project.github_repo,
            created_at=project.created_at.isoformat(),
            status=project.status,
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
