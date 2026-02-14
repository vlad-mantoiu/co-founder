"""GitHub Integration: Manage repositories, branches, and pull requests.

This module provides GitHub App integration for:
- Cloning and syncing repositories
- Creating and managing branches
- Committing changes
- Opening and managing pull requests
"""

import base64
import tempfile
from datetime import datetime, timedelta
from pathlib import Path

import httpx
import jwt

from app.core.config import get_settings
from app.core.exceptions import GitOperationError


class GitHubClient:
    """Client for GitHub App API operations."""

    BASE_URL = "https://api.github.com"

    def __init__(self, installation_id: str | None = None):
        """Initialize GitHub client.

        Args:
            installation_id: GitHub App installation ID for the repo
        """
        self.settings = get_settings()
        self.installation_id = installation_id
        self._access_token: str | None = None
        self._token_expires: datetime | None = None

    async def _get_jwt(self) -> str:
        """Generate a JWT for GitHub App authentication."""
        if not self.settings.github_app_id or not self.settings.github_private_key:
            raise GitOperationError("GitHub App not configured")

        now = datetime.utcnow()
        payload = {
            "iat": int(now.timestamp()) - 60,  # Issued 60 seconds ago
            "exp": int((now + timedelta(minutes=10)).timestamp()),
            "iss": self.settings.github_app_id,
        }

        # Handle private key (may be base64 encoded or raw)
        private_key = self.settings.github_private_key
        if not private_key.startswith("-----BEGIN"):
            private_key = base64.b64decode(private_key).decode()

        return jwt.encode(payload, private_key, algorithm="RS256")

    async def _get_access_token(self) -> str:
        """Get an installation access token."""
        if self._access_token and self._token_expires and datetime.utcnow() < self._token_expires:
            return self._access_token

        if not self.installation_id:
            raise GitOperationError("Installation ID required for this operation")

        jwt_token = await self._get_jwt()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.BASE_URL}/app/installations/{self.installation_id}/access_tokens",
                headers={
                    "Authorization": f"Bearer {jwt_token}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
            )

            if response.status_code != 201:
                raise GitOperationError(f"Failed to get access token: {response.text}")

            data = response.json()
            self._access_token = data["token"]
            self._token_expires = datetime.utcnow() + timedelta(minutes=55)

            return self._access_token

    async def _request(
        self,
        method: str,
        endpoint: str,
        data: dict | None = None,
        use_jwt: bool = False,
    ) -> dict:
        """Make an authenticated request to GitHub API."""
        if use_jwt:
            token = await self._get_jwt()
            auth_header = f"Bearer {token}"
        else:
            token = await self._get_access_token()
            auth_header = f"Bearer {token}"

        headers = {
            "Authorization": auth_header,
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }

        async with httpx.AsyncClient() as client:
            if method == "GET":
                response = await client.get(f"{self.BASE_URL}{endpoint}", headers=headers)
            elif method == "POST":
                response = await client.post(
                    f"{self.BASE_URL}{endpoint}",
                    headers=headers,
                    json=data,
                )
            elif method == "PUT":
                response = await client.put(
                    f"{self.BASE_URL}{endpoint}",
                    headers=headers,
                    json=data,
                )
            elif method == "PATCH":
                response = await client.patch(
                    f"{self.BASE_URL}{endpoint}",
                    headers=headers,
                    json=data,
                )
            elif method == "DELETE":
                response = await client.delete(f"{self.BASE_URL}{endpoint}", headers=headers)
            else:
                raise ValueError(f"Unknown method: {method}")

            if response.status_code >= 400:
                raise GitOperationError(
                    f"GitHub API error ({response.status_code}): {response.text}"
                )

            if response.status_code == 204:
                return {}

            return response.json()

    # Repository operations

    async def get_repo(self, owner: str, repo: str) -> dict:
        """Get repository information."""
        return await self._request("GET", f"/repos/{owner}/{repo}")

    async def get_default_branch(self, owner: str, repo: str) -> str:
        """Get the default branch name for a repository."""
        repo_info = await self.get_repo(owner, repo)
        return repo_info.get("default_branch", "main")

    async def list_branches(self, owner: str, repo: str) -> list[dict]:
        """List all branches in a repository."""
        return await self._request("GET", f"/repos/{owner}/{repo}/branches")

    # Branch operations

    async def create_branch(
        self,
        owner: str,
        repo: str,
        branch_name: str,
        from_branch: str | None = None,
    ) -> dict:
        """Create a new branch.

        Args:
            owner: Repository owner
            repo: Repository name
            branch_name: Name for the new branch
            from_branch: Base branch (defaults to default branch)
        """
        # Get the SHA of the base branch
        if not from_branch:
            from_branch = await self.get_default_branch(owner, repo)

        ref_data = await self._request("GET", f"/repos/{owner}/{repo}/git/ref/heads/{from_branch}")
        sha = ref_data["object"]["sha"]

        # Create the new branch
        return await self._request(
            "POST",
            f"/repos/{owner}/{repo}/git/refs",
            data={
                "ref": f"refs/heads/{branch_name}",
                "sha": sha,
            },
        )

    async def delete_branch(self, owner: str, repo: str, branch_name: str) -> None:
        """Delete a branch."""
        await self._request("DELETE", f"/repos/{owner}/{repo}/git/refs/heads/{branch_name}")

    # File operations

    async def get_file_content(
        self,
        owner: str,
        repo: str,
        path: str,
        branch: str | None = None,
    ) -> dict:
        """Get the content of a file.

        Returns dict with 'content' (base64), 'sha', and 'path'.
        """
        endpoint = f"/repos/{owner}/{repo}/contents/{path}"
        if branch:
            endpoint += f"?ref={branch}"

        return await self._request("GET", endpoint)

    async def create_or_update_file(
        self,
        owner: str,
        repo: str,
        path: str,
        content: str,
        message: str,
        branch: str,
        sha: str | None = None,
    ) -> dict:
        """Create or update a file in the repository.

        Args:
            owner: Repository owner
            repo: Repository name
            path: File path
            content: File content (will be base64 encoded)
            message: Commit message
            branch: Target branch
            sha: Current file SHA (required for updates)
        """
        data = {
            "message": message,
            "content": base64.b64encode(content.encode()).decode(),
            "branch": branch,
        }

        if sha:
            data["sha"] = sha

        return await self._request("PUT", f"/repos/{owner}/{repo}/contents/{path}", data=data)

    async def delete_file(
        self,
        owner: str,
        repo: str,
        path: str,
        message: str,
        branch: str,
        sha: str,
    ) -> dict:
        """Delete a file from the repository."""
        return await self._request(
            "DELETE",
            f"/repos/{owner}/{repo}/contents/{path}",
            data={
                "message": message,
                "sha": sha,
                "branch": branch,
            },
        )

    # Pull request operations

    async def create_pull_request(
        self,
        owner: str,
        repo: str,
        title: str,
        body: str,
        head: str,
        base: str | None = None,
        draft: bool = False,
    ) -> dict:
        """Create a pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            title: PR title
            body: PR description
            head: Source branch
            base: Target branch (defaults to default branch)
            draft: Create as draft PR
        """
        if not base:
            base = await self.get_default_branch(owner, repo)

        return await self._request(
            "POST",
            f"/repos/{owner}/{repo}/pulls",
            data={
                "title": title,
                "body": body,
                "head": head,
                "base": base,
                "draft": draft,
            },
        )

    async def get_pull_request(self, owner: str, repo: str, pr_number: int) -> dict:
        """Get pull request details."""
        return await self._request("GET", f"/repos/{owner}/{repo}/pulls/{pr_number}")

    async def list_pull_requests(
        self,
        owner: str,
        repo: str,
        state: str = "open",
        head: str | None = None,
    ) -> list[dict]:
        """List pull requests."""
        endpoint = f"/repos/{owner}/{repo}/pulls?state={state}"
        if head:
            endpoint += f"&head={owner}:{head}"

        return await self._request("GET", endpoint)

    async def merge_pull_request(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        commit_title: str | None = None,
        merge_method: str = "squash",
    ) -> dict:
        """Merge a pull request.

        Args:
            owner: Repository owner
            repo: Repository name
            pr_number: PR number
            commit_title: Optional merge commit title
            merge_method: "merge", "squash", or "rebase"
        """
        data = {"merge_method": merge_method}
        if commit_title:
            data["commit_title"] = commit_title

        return await self._request(
            "PUT",
            f"/repos/{owner}/{repo}/pulls/{pr_number}/merge",
            data=data,
        )

    async def add_pr_comment(
        self,
        owner: str,
        repo: str,
        pr_number: int,
        body: str,
    ) -> dict:
        """Add a comment to a pull request."""
        return await self._request(
            "POST",
            f"/repos/{owner}/{repo}/issues/{pr_number}/comments",
            data={"body": body},
        )

    # Commit operations

    async def commit_multiple_files(
        self,
        owner: str,
        repo: str,
        branch: str,
        files: dict[str, str],
        message: str,
    ) -> dict:
        """Commit multiple files in a single commit using the Git Data API.

        Args:
            owner: Repository owner
            repo: Repository name
            branch: Target branch
            files: Dict of file paths to content
            message: Commit message

        Returns:
            Commit data including SHA
        """
        # Get the current commit SHA for the branch
        ref = await self._request("GET", f"/repos/{owner}/{repo}/git/ref/heads/{branch}")
        base_sha = ref["object"]["sha"]

        # Get the base tree
        commit = await self._request("GET", f"/repos/{owner}/{repo}/git/commits/{base_sha}")
        base_tree_sha = commit["tree"]["sha"]

        # Create blobs for each file
        tree_items = []
        for path, content in files.items():
            blob = await self._request(
                "POST",
                f"/repos/{owner}/{repo}/git/blobs",
                data={
                    "content": content,
                    "encoding": "utf-8",
                },
            )
            tree_items.append({
                "path": path,
                "mode": "100644",
                "type": "blob",
                "sha": blob["sha"],
            })

        # Create a new tree
        tree = await self._request(
            "POST",
            f"/repos/{owner}/{repo}/git/trees",
            data={
                "base_tree": base_tree_sha,
                "tree": tree_items,
            },
        )

        # Create the commit
        new_commit = await self._request(
            "POST",
            f"/repos/{owner}/{repo}/git/commits",
            data={
                "message": message,
                "tree": tree["sha"],
                "parents": [base_sha],
            },
        )

        # Update the branch reference
        await self._request(
            "PATCH",
            f"/repos/{owner}/{repo}/git/refs/heads/{branch}",
            data={"sha": new_commit["sha"]},
        )

        return new_commit


# Singleton instance
_github_client: GitHubClient | None = None


def get_github_client(installation_id: str | None = None) -> GitHubClient:
    """Get a GitHub client instance."""
    global _github_client
    if _github_client is None or installation_id:
        _github_client = GitHubClient(installation_id)
    return _github_client
