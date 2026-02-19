"""Deploy readiness checks domain module.

Pure domain functions and constants for assessing deployment readiness.
No I/O, no side effects, fully deterministic.

Used by DEPL-01 (readiness boolean, blocking issues, deploy path recommendations).
"""

import json
import re
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class DeployCheck:
    """Result of a single deploy readiness check."""

    id: str
    title: str
    status: Literal["pass", "warn", "fail"]
    message: str
    fix_instruction: str | None = None


@dataclass
class DeployPathOption:
    """A deployment path option with full details for founder decision-making."""

    id: str
    name: str
    description: str
    difficulty: Literal["easy", "medium", "hard"]
    cost: str
    tradeoffs: list[str] = field(default_factory=list)
    steps: list[str] = field(default_factory=list)


# Hardcoded deploy path constants — no LLM needed.
# Per locked decision: include tradeoffs and step-by-step instructions.
DEPLOY_PATHS: list[DeployPathOption] = [
    DeployPathOption(
        id="vercel",
        name="Vercel",
        description="Zero-config deployment for frontend-heavy or full-stack Next.js apps. Best for rapid iteration.",
        difficulty="easy",
        cost="Free tier generous; $20/month Pro for team features",
        tradeoffs=[
            "Best for Node.js/Next.js — backend must be serverless functions or separate service",
            "Vendor lock-in on edge functions and image optimization",
            "Automatic HTTPS, global CDN, and preview deployments out of the box",
            "Limited to 10s function timeout on free tier (60s on Pro)",
        ],
        steps=[
            "Push code to GitHub (ensure .gitignore excludes secrets)",
            "Visit vercel.com and sign in with GitHub",
            "Click 'New Project' and import your repository",
            "Configure build settings (framework auto-detected for Next.js)",
            "Add environment variables from your .env.example",
            "Click 'Deploy' — live URL provided in ~2 minutes",
            "Set up custom domain in Project Settings → Domains",
        ],
    ),
    DeployPathOption(
        id="railway",
        name="Railway",
        description="Full-stack PaaS with built-in Postgres, Redis, and Docker support. Best for Python/FastAPI backends.",
        difficulty="easy",
        cost="Free tier: $5 credit/month; Hobby: $5/month + usage",
        tradeoffs=[
            "Supports any language/framework via Docker or Nixpacks auto-detection",
            "Built-in PostgreSQL, Redis, and MongoDB as managed services",
            "No cold starts (unlike Vercel serverless functions)",
            "Less control over infrastructure compared to AWS",
            "Simpler pricing model but can become expensive at scale",
        ],
        steps=[
            "Push code to GitHub with a Dockerfile or Procfile",
            "Visit railway.app and sign in with GitHub",
            "Click 'New Project' → 'Deploy from GitHub repo'",
            "Select your repository — Railway auto-detects language",
            "Add a PostgreSQL plugin if needed (instant managed DB)",
            "Set environment variables in the Variables tab",
            "Railway provides a public URL automatically on deploy",
            "Set up custom domain in Settings → Domains",
        ],
    ),
    DeployPathOption(
        id="aws",
        name="AWS ECS Fargate",
        description="Production-grade container orchestration. Best for scaling, compliance, and existing AWS infrastructure.",
        difficulty="hard",
        cost="~$30-100/month for small apps; scales with usage",
        tradeoffs=[
            "Full control over networking, security groups, and IAM policies",
            "Integrates natively with RDS, ElastiCache, Secrets Manager",
            "Requires CDK/Terraform knowledge for infrastructure-as-code",
            "More operational overhead — logging, auto-scaling, health checks manual",
            "Best for teams with AWS experience or compliance requirements (SOC2, HIPAA)",
        ],
        steps=[
            "Containerize app with a production-ready Dockerfile",
            "Create ECR repository: aws ecr create-repository --repository-name my-app",
            "Build and push Docker image: docker build -t my-app . && docker tag ... && docker push ...",
            "Define ECS Task Definition with CPU/memory, env vars from Secrets Manager",
            "Create ECS Cluster (Fargate launch type) and Service",
            "Configure Application Load Balancer with target group health checks",
            "Set up Route53 A record pointing to ALB DNS name",
            "Configure CloudWatch Logs for container output",
            "Enable Auto Scaling based on CPU/memory metrics",
        ],
    ),
]


# Patterns indicating hardcoded secrets (checked against non-.env.example files)
_SECRET_PATTERNS: list[re.Pattern] = [
    re.compile(r'(?:API_KEY|api_key)\s*=\s*["\'](?!your_|<|example|placeholder|xxx|test_)[^"\']{8,}', re.IGNORECASE),
    re.compile(r'(?:SECRET|secret)\s*=\s*["\'][^"\']{8,}', re.IGNORECASE),
    re.compile(r'(?:PASSWORD|password)\s*=\s*["\'][^"\']{4,}', re.IGNORECASE),
    re.compile(r'(?:TOKEN|token)\s*=\s*["\'][^"\']{8,}', re.IGNORECASE),
    re.compile(r"sk-[a-zA-Z0-9]{20,}"),  # OpenAI-style keys
    re.compile(r'(?:PRIVATE_KEY|private_key)\s*=\s*["\'][^"\']{8,}', re.IGNORECASE),
]


def _has_start_script(workspace_files: dict[str, str]) -> bool:
    """Check if workspace has a start entry point."""
    # package.json with scripts.start
    if "package.json" in workspace_files:
        try:
            pkg = json.loads(workspace_files["package.json"])
            if isinstance(pkg.get("scripts"), dict) and pkg["scripts"].get("start"):
                return True
        except (json.JSONDecodeError, AttributeError):
            pass

    # Makefile
    if "Makefile" in workspace_files:
        return True

    # Procfile
    if "Procfile" in workspace_files:
        return True

    # main.py is NOT treated as a start script (no defined entry point)
    return False


def _has_dependencies_pinned(workspace_files: dict[str, str]) -> bool:
    """Check if dependencies are declared in a standard file."""
    return any(
        f in workspace_files for f in ("package.json", "requirements.txt", "pyproject.toml", "Gemfile", "go.mod")
    )


def _find_hardcoded_secrets(workspace_files: dict[str, str]) -> list[str]:
    """Scan files for hardcoded secrets, excluding .env.example."""
    violations: list[str] = []
    for filename, content in workspace_files.items():
        if filename == ".env.example":
            continue  # .env.example is intentionally placeholder values
        for pattern in _SECRET_PATTERNS:
            if pattern.search(content):
                violations.append(filename)
                break  # One violation per file is enough
    return violations


def run_deploy_checks(workspace_files: dict[str, str]) -> list[DeployCheck]:
    """Run all deploy readiness checks against the workspace files.

    Pure function — no I/O, no side effects.

    Args:
        workspace_files: Dict mapping filename to file content.

    Returns:
        List of DeployCheck results, one per check category.

    Checks performed:
        1. readme     — README.md exists (warn if missing)
        2. env_example — .env.example exists (warn if missing)
        3. start_script — Has a runnable entry point (fail if missing)
        4. no_secrets — No hardcoded secrets detected (fail if found)
        5. deps_pinned — Dependencies declared (warn if missing)
    """
    checks: list[DeployCheck] = []

    # Check 1: README.md
    if "README.md" in workspace_files or "readme.md" in workspace_files:
        checks.append(
            DeployCheck(
                id="readme",
                title="README.md present",
                status="pass",
                message="README.md found — deployment instructions and project description present.",
            )
        )
    else:
        checks.append(
            DeployCheck(
                id="readme",
                title="README.md missing",
                status="warn",
                message="No README.md found. Add one to document setup and deployment steps.",
                fix_instruction="Create README.md with project overview, setup instructions, and environment variable documentation.",
            )
        )

    # Check 2: .env.example
    if ".env.example" in workspace_files:
        checks.append(
            DeployCheck(
                id="env_example",
                title=".env.example present",
                status="pass",
                message=".env.example found — environment variables are documented.",
            )
        )
    else:
        checks.append(
            DeployCheck(
                id="env_example",
                title=".env.example missing",
                status="warn",
                message="No .env.example found. Document required environment variables.",
                fix_instruction="Create .env.example listing all required environment variables with placeholder values (e.g., API_KEY=your_key_here).",
            )
        )

    # Check 3: Start script / entry point
    if _has_start_script(workspace_files):
        checks.append(
            DeployCheck(
                id="start_script",
                title="Start script defined",
                status="pass",
                message="Entry point found — deployment platform can run the application.",
            )
        )
    else:
        checks.append(
            DeployCheck(
                id="start_script",
                title="No start script found",
                status="fail",
                message="No runnable entry point detected (package.json scripts.start, Procfile, or Makefile).",
                fix_instruction='Add a start script: in package.json add {"scripts": {"start": "node server.js"}}, or create a Procfile with \'web: python app.py\'.',
            )
        )

    # Check 4: No hardcoded secrets
    violations = _find_hardcoded_secrets(workspace_files)
    if violations:
        checks.append(
            DeployCheck(
                id="no_secrets",
                title="Hardcoded secrets detected",
                status="fail",
                message=f"Possible hardcoded secrets found in: {', '.join(violations)}.",
                fix_instruction="Move all secrets to environment variables. Use .env.example for documentation and load via os.environ or dotenv. Never commit real credentials.",
            )
        )
    else:
        checks.append(
            DeployCheck(
                id="no_secrets",
                title="No hardcoded secrets",
                status="pass",
                message="No hardcoded secrets detected in workspace files.",
            )
        )

    # Check 5: Dependencies pinned
    if _has_dependencies_pinned(workspace_files):
        checks.append(
            DeployCheck(
                id="deps_pinned",
                title="Dependencies declared",
                status="pass",
                message="Dependency file found — platform can install dependencies reliably.",
            )
        )
    else:
        checks.append(
            DeployCheck(
                id="deps_pinned",
                title="No dependency file found",
                status="warn",
                message="No package.json, requirements.txt, or equivalent found.",
                fix_instruction="Create a requirements.txt (Python) or package.json (Node.js) with pinned dependency versions.",
            )
        )

    return checks


def compute_overall_status(checks: list[DeployCheck]) -> str:
    """Compute overall deployment readiness from individual checks.

    Args:
        checks: List of DeployCheck results.

    Returns:
        "red"    — if any check has status "fail"
        "yellow" — if any check has status "warn" (and none are "fail")
        "green"  — if all checks have status "pass"
    """
    statuses = {c.status for c in checks}
    if "fail" in statuses:
        return "red"
    if "warn" in statuses:
        return "yellow"
    return "green"
