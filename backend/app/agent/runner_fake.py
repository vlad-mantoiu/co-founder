"""RunnerFake: Scenario-based test double for Runner protocol.

Provides deterministic, instant responses for 4 named scenarios:
- happy_path: Full successful flow with realistic content
- llm_failure: API/rate limit failure at any stage
- partial_build: Code generated but tests fail
- rate_limited: Worker capacity exceeded

All scenarios return instantly (no LLM calls, no delays) with realistic content.
"""

from app.agent.runner import Runner
from app.agent.state import CoFounderState, ErrorInfo, FileChange, PlanStep


class RunnerFake:
    """Scenario-based test double for Runner protocol.

    Designed for TDD throughout the project. Each scenario provides
    pre-built, deterministic responses that cover the full founder flow.
    """

    VALID_SCENARIOS = {"happy_path", "llm_failure", "partial_build", "rate_limited"}

    # Valid stage names for step() method
    VALID_STAGES = {"architect", "coder", "executor", "debugger", "reviewer", "git_manager"}

    def __init__(self, scenario: str = "happy_path"):
        """Initialize RunnerFake with a named scenario.

        Args:
            scenario: One of 'happy_path', 'llm_failure', 'partial_build', 'rate_limited'

        Raises:
            ValueError: If scenario is not recognized
        """
        if scenario not in self.VALID_SCENARIOS:
            raise ValueError(
                f"Unknown scenario: {scenario}. Valid scenarios: {self.VALID_SCENARIOS}"
            )
        self.scenario = scenario

    async def run(self, state: CoFounderState) -> CoFounderState:
        """Execute full pipeline for the configured scenario.

        Args:
            state: Initial state with user goal and context

        Returns:
            Final state after complete pipeline execution

        Raises:
            RuntimeError: For llm_failure and rate_limited scenarios
        """
        if self.scenario == "llm_failure":
            raise RuntimeError("Anthropic API rate limit exceeded. Retry after 60 seconds.")

        if self.scenario == "rate_limited":
            raise RuntimeError(
                "Worker capacity exceeded. Estimated wait: 5 minutes. Current queue depth: 12."
            )

        # Build scenario-specific state
        if self.scenario == "happy_path":
            return self._build_happy_path_state(state)

        if self.scenario == "partial_build":
            return self._build_partial_build_state(state)

        # Fallback (should never reach due to validation)
        return state

    async def step(self, state: CoFounderState, stage: str) -> CoFounderState:
        """Execute a single pipeline stage.

        Args:
            state: Current state
            stage: Stage name (architect, coder, executor, debugger, reviewer, git_manager)

        Returns:
            Updated state after executing the stage

        Raises:
            ValueError: If stage name is invalid
            RuntimeError: For llm_failure and rate_limited scenarios
        """
        if stage not in self.VALID_STAGES:
            raise ValueError(
                f"Invalid stage: {stage}. Valid stages: {self.VALID_STAGES}"
            )

        if self.scenario == "llm_failure":
            raise RuntimeError("Anthropic API rate limit exceeded. Retry after 60 seconds.")

        if self.scenario == "rate_limited":
            raise RuntimeError(
                "Worker capacity exceeded. Estimated wait: 5 minutes. Current queue depth: 12."
            )

        # Return stage-specific partial state
        updated_state = {**state, "current_node": stage}

        if stage == "architect":
            updated_state["plan"] = self._get_realistic_plan()

        if stage == "coder":
            updated_state["working_files"] = self._get_realistic_code()

        return CoFounderState(**updated_state)

    async def generate_questions(self, context: dict) -> list[dict]:
        """Generate onboarding questions.

        Args:
            context: Idea context (keywords, domain, etc.)

        Returns:
            List of question dicts with id, text, required keys

        Raises:
            RuntimeError: For llm_failure and rate_limited scenarios
        """
        if self.scenario == "llm_failure":
            raise RuntimeError("Anthropic API rate limit exceeded. Retry after 60 seconds.")

        if self.scenario == "rate_limited":
            raise RuntimeError(
                "Worker capacity exceeded. Estimated wait: 5 minutes. Current queue depth: 12."
            )

        return [
            {
                "id": "q1",
                "text": "Who is your target customer? Be as specific as possible.",
                "required": True,
            },
            {
                "id": "q2",
                "text": "What is the core problem you're solving for them?",
                "required": True,
            },
            {
                "id": "q3",
                "text": "How are they solving this problem today?",
                "required": True,
            },
            {
                "id": "q4",
                "text": "What makes your solution different or better?",
                "required": False,
            },
            {
                "id": "q5",
                "text": "How will you validate that people actually want this?",
                "required": True,
            },
            {
                "id": "q6",
                "text": "What's your monetization strategy (if any)?",
                "required": False,
            },
        ]

    async def generate_brief(self, answers: dict) -> dict:
        """Generate product brief from answers.

        Args:
            answers: Dictionary mapping question IDs to user answers

        Returns:
            Brief dict with all 8 required keys

        Raises:
            RuntimeError: For llm_failure and rate_limited scenarios
        """
        if self.scenario == "llm_failure":
            raise RuntimeError("Anthropic API rate limit exceeded. Retry after 60 seconds.")

        if self.scenario == "rate_limited":
            raise RuntimeError(
                "Worker capacity exceeded. Estimated wait: 5 minutes. Current queue depth: 12."
            )

        return {
            "problem_statement": "Small business owners lack a simple, reliable way to track inventory across multiple locations without expensive enterprise software.",
            "target_user": "Retail shop owners with 1-10 employees managing physical products across 1-3 locations",
            "value_prop": "Dead-simple inventory tracking with barcode scanning, real-time sync, and automatic reorder alerts - no training required",
            "differentiation": "Unlike Shopify or Square POS (which bundle inventory with payments), we're inventory-first with deeper tracking features. Unlike enterprise ERPs, we're affordable ($49/mo) and setup takes 10 minutes.",
            "monetization_hypothesis": "SaaS subscription at $49/mo per location. Target 100 paying customers in first 6 months. Average customer value: $588/year.",
            "assumptions": "Shop owners will pay for inventory software if it saves >2 hours/week. Barcode scanning is a must-have. Mobile app is critical (owners check inventory on-the-go).",
            "risks": "Competition from POS systems adding inventory features. Customer acquisition cost may exceed LTV if we rely on paid ads. Integration complexity with existing systems.",
            "smallest_viable_experiment": "Single-location inventory tracker with manual entry and CSV export. Test with 10 local shop owners for 2 weeks. Success = 7/10 would pay $49/mo.",
        }

    async def generate_artifacts(self, brief: dict) -> dict:
        """Generate documentation artifacts from brief.

        Args:
            brief: Structured product brief

        Returns:
            Artifacts dict with 5 document keys

        Raises:
            RuntimeError: For llm_failure and rate_limited scenarios
        """
        if self.scenario == "llm_failure":
            raise RuntimeError("Anthropic API rate limit exceeded. Retry after 60 seconds.")

        if self.scenario == "rate_limited":
            raise RuntimeError(
                "Worker capacity exceeded. Estimated wait: 5 minutes. Current queue depth: 12."
            )

        return {
            "product_brief": """# Inventory Tracker Product Brief

## Problem
Small retail businesses waste 5-10 hours/week manually tracking inventory in spreadsheets, leading to stockouts, overordering, and lost sales.

## Solution
Mobile-first inventory app with barcode scanning, real-time sync, and automatic reorder alerts. Setup in 10 minutes, no training required.

## Target Market
Retail shops with 1-10 employees, 1-3 locations, managing 100-1000 SKUs. Initial focus: gift shops, boutiques, cafes.

## Business Model
$49/month per location. Target: 100 paying customers in 6 months ($4,900 MRR).""",
            "mvp_scope": """# MVP Scope

## In Scope
- Single-location inventory tracking
- Manual product entry (name, SKU, quantity, reorder point)
- Stock adjustment logging (with notes)
- Low stock alerts (email notifications)
- CSV import/export
- Basic reporting (stock levels, adjustment history)

## Out of Scope (Phase 2+)
- Multi-location sync
- Barcode scanning
- Mobile app (web-only for MVP)
- Integrations (Shopify, Square, etc.)
- Advanced analytics
- Supplier management""",
            "milestones": """# Project Milestones

## Week 1: Foundation
- Database schema (products, stock_adjustments)
- Authentication (email/password)
- Product CRUD operations

## Week 2: Core Features
- Stock adjustment workflow
- Low stock threshold alerts
- Email notification system

## Week 3: Polish
- CSV import/export
- Basic reporting views
- Responsive design

## Week 4: Launch
- User testing with 5 beta customers
- Bug fixes and refinements
- Deploy to production
- Onboard first 10 customers""",
            "risk_log": """# Risk Log

## High Priority
1. **Customer acquisition cost** - Mitigation: Start with local outreach, partnerships with retail associations
2. **Retention risk** - Mitigation: Weekly check-ins during first month, feature requests prioritization
3. **Data migration complexity** - Mitigation: Robust CSV import with validation, dedicated onboarding support

## Medium Priority
4. **Competition from POS systems** - Mitigation: Focus on depth of inventory features, not breadth
5. **Mobile dependency** - Mitigation: Ensure web app is mobile-responsive for MVP

## Low Priority
6. **Scalability concerns** - Mitigation: Start with proven stack (PostgreSQL, Redis), optimize later""",
            "how_it_works": """# How It Works

## User Flow
1. **Sign up** → Email/password, verify email
2. **Add products** → Name, SKU, quantity, reorder point (or bulk CSV import)
3. **Track stock** → Log adjustments when receiving shipments or making sales
4. **Get alerts** → Email when stock falls below reorder point
5. **Review reports** → Check current stock levels, adjustment history

## Technical Architecture
- **Frontend**: Next.js (responsive web app)
- **Backend**: FastAPI (async Python)
- **Database**: PostgreSQL (products, adjustments, users)
- **Auth**: JWT tokens with refresh rotation
- **Notifications**: SendGrid (email alerts)
- **Hosting**: AWS ECS (Docker containers)

## Key Screens
- Dashboard (stock overview, recent adjustments)
- Product list (search, filter by low stock)
- Product detail (adjustment history, edit)
- New adjustment form (increase/decrease stock, add note)
- Reports (stock levels by category, adjustment trends)""",
        }

    # =========================================================================
    # PRIVATE HELPERS
    # =========================================================================

    def _get_realistic_plan(self) -> list[PlanStep]:
        """Generate realistic plan for inventory tracker."""
        return [
            PlanStep(
                index=0,
                description="Create Product model with name, SKU, quantity, and reorder point fields",
                status="pending",
                files_to_modify=["src/models/product.py", "src/db/migrations/001_create_products.sql"],
            ),
            PlanStep(
                index=1,
                description="Implement StockAdjustment model to track inventory changes with timestamps and notes",
                status="pending",
                files_to_modify=["src/models/stock_adjustment.py", "src/db/migrations/002_create_stock_adjustments.sql"],
            ),
            PlanStep(
                index=2,
                description="Build product CRUD API endpoints (create, read, update, delete)",
                status="pending",
                files_to_modify=["src/api/routes/products.py", "src/api/schemas/product.py"],
            ),
            PlanStep(
                index=3,
                description="Implement stock adjustment workflow with validation and automatic quantity updates",
                status="pending",
                files_to_modify=["src/api/routes/adjustments.py", "src/services/inventory.py"],
            ),
        ]

    def _get_realistic_code(self) -> dict[str, FileChange]:
        """Generate realistic code for inventory tracker."""
        return {
            "src/models/product.py": FileChange(
                path="src/models/product.py",
                original_content=None,
                new_content="""from sqlalchemy import Column, Integer, String, Numeric, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone

from src.db.base import Base


class Product(Base):
    __tablename__ = "products"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    sku = Column(String, unique=True, nullable=False, index=True)
    quantity = Column(Integer, default=0, nullable=False)
    reorder_point = Column(Integer, default=10, nullable=False)
    unit_price = Column(Numeric(10, 2), nullable=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))

    # Relationships
    adjustments = relationship("StockAdjustment", back_populates="product", cascade="all, delete-orphan")

    def is_low_stock(self) -> bool:
        \"\"\"Check if current quantity is below reorder point.\"\"\"
        return self.quantity < self.reorder_point

    def __repr__(self):
        return f"<Product(sku={self.sku}, name={self.name}, qty={self.quantity})>"
""",
                change_type="create",
            ),
            "src/api/routes/products.py": FileChange(
                path="src/api/routes/products.py",
                original_content=None,
                new_content="""from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from src.db.base import get_session
from src.models.product import Product
from src.api.schemas.product import ProductCreate, ProductResponse

router = APIRouter(prefix="/products", tags=["products"])


@router.post("/", response_model=ProductResponse, status_code=201)
async def create_product(
    product_data: ProductCreate,
    db: AsyncSession = Depends(get_session),
):
    \"\"\"Create a new product.\"\"\"
    # Check for duplicate SKU
    existing = await db.execute(
        select(Product).where(Product.sku == product_data.sku)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="SKU already exists")

    product = Product(**product_data.model_dump())
    db.add(product)
    await db.commit()
    await db.refresh(product)

    return product


@router.get("/{product_id}", response_model=ProductResponse)
async def get_product(
    product_id: int,
    db: AsyncSession = Depends(get_session),
):
    \"\"\"Retrieve a product by ID.\"\"\"
    product = await db.get(Product, product_id)
    if not product:
        raise HTTPException(status_code=404, detail="Product not found")

    return product
""",
                change_type="create",
            ),
        }

    def _build_happy_path_state(self, state: CoFounderState) -> CoFounderState:
        """Build complete successful state."""
        return CoFounderState(
            **{
                **state,
                "plan": self._get_realistic_plan(),
                "working_files": self._get_realistic_code(),
                "is_complete": True,
                "current_node": "git_manager",
                "last_command_exit_code": 0,
                "status_message": "All steps completed successfully",
            }
        )

    def _build_partial_build_state(self, state: CoFounderState) -> CoFounderState:
        """Build state where code generated but tests failed."""
        return CoFounderState(
            **{
                **state,
                "plan": self._get_realistic_plan(),
                "working_files": self._get_realistic_code(),
                "is_complete": False,
                "current_node": "executor",
                "last_command_exit_code": 1,
                "active_errors": [
                    ErrorInfo(
                        step_index=2,
                        error_type="TypeError",
                        message="Expected argument 'quantity' to be int, got NoneType",
                        stdout="",
                        stderr="Traceback (most recent call last):\n  File 'test_product.py', line 42, in test_create_product\n    product = Product(name='Test', sku='TST-001', quantity=None)\nTypeError: Expected argument 'quantity' to be int, got NoneType",
                        file_path="src/models/product.py",
                    )
                ],
                "status_message": "Tests failed with type errors",
            }
        )
