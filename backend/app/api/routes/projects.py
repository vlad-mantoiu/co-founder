"""Project management API routes."""

import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from app.core.auth import ClerkUser, require_auth

router = APIRouter()

# In-memory storage (replace with database in production)
_projects: dict[str, dict] = {}


class ProjectCreate(BaseModel):
    """Request to create a new project."""

    name: str
    description: str = ""
    github_repo: str | None = None


class ProjectResponse(BaseModel):
    """Project response model."""

    id: str
    name: str
    description: str
    github_repo: str | None
    created_at: str
    status: str


@router.post("/", response_model=ProjectResponse)
async def create_project(request: ProjectCreate, user: ClerkUser = Depends(require_auth)):
    """Create a new project."""
    project_id = str(uuid.uuid4())

    project = {
        "id": project_id,
        "name": request.name,
        "description": request.description,
        "github_repo": request.github_repo,
        "created_at": datetime.utcnow().isoformat(),
        "status": "active",
        "user_id": user.user_id,
    }

    _projects[project_id] = project

    return ProjectResponse(**project)


@router.get("/", response_model=list[ProjectResponse])
async def list_projects(user: ClerkUser = Depends(require_auth)):
    """List all projects for the current user."""
    return [
        ProjectResponse(**p) for p in _projects.values() if p["user_id"] == user.user_id
    ]


@router.get("/{project_id}", response_model=ProjectResponse)
async def get_project(project_id: str, user: ClerkUser = Depends(require_auth)):
    """Get a specific project."""
    if project_id not in _projects or _projects[project_id]["user_id"] != user.user_id:
        raise HTTPException(status_code=404, detail="Project not found")

    return ProjectResponse(**_projects[project_id])


@router.delete("/{project_id}")
async def delete_project(project_id: str, user: ClerkUser = Depends(require_auth)):
    """Delete a project."""
    if project_id not in _projects or _projects[project_id]["user_id"] != user.user_id:
        raise HTTPException(status_code=404, detail="Project not found")

    del _projects[project_id]
    return {"status": "deleted"}


@router.post("/{project_id}/link-github")
async def link_github_repo(
    project_id: str, github_repo: str, user: ClerkUser = Depends(require_auth)
):
    """Link a GitHub repository to a project."""
    if project_id not in _projects or _projects[project_id]["user_id"] != user.user_id:
        raise HTTPException(status_code=404, detail="Project not found")

    _projects[project_id]["github_repo"] = github_repo

    # TODO: Clone repo, create GitHub App installation, etc.

    return {"status": "linked", "github_repo": github_repo}
