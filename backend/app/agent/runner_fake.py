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
                "text": "Who are we building this for? Be as specific as possible about our target customer.",
                "input_type": "text",
                "required": True,
                "options": None,
                "follow_up_hint": None,
            },
            {
                "id": "q2",
                "text": "What core problem are we solving for them?",
                "input_type": "textarea",
                "required": True,
                "options": None,
                "follow_up_hint": "Think about the pain point that keeps them up at night",
            },
            {
                "id": "q3",
                "text": "How are they solving this problem today?",
                "input_type": "textarea",
                "required": True,
                "options": None,
                "follow_up_hint": None,
            },
            {
                "id": "q4",
                "text": "What stage is our idea at?",
                "input_type": "multiple_choice",
                "required": True,
                "options": ["Just an idea", "Validated with customers", "Early prototype", "Have paying users"],
                "follow_up_hint": None,
            },
            {
                "id": "q5",
                "text": "How will we validate that people actually want this?",
                "input_type": "textarea",
                "required": True,
                "options": None,
                "follow_up_hint": None,
            },
            {
                "id": "q6",
                "text": "What's our monetization strategy (if any)?",
                "input_type": "text",
                "required": False,
                "options": None,
                "follow_up_hint": None,
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
            # Core fields (always present)
            "problem": "Small business owners lack a simple, reliable way to track inventory across multiple locations without expensive enterprise software.",
            "target_user": "Retail shop owners with 1-10 employees managing physical products across 1-3 locations",
            "value_prop": "Dead-simple inventory tracking with barcode scanning, real-time sync, and automatic reorder alerts - no training required",
            "key_constraint": "Must work offline with background sync when connectivity is restored",
            # Business fields (Partner+)
            "differentiation": "Unlike Shopify or Square POS (which bundle inventory with payments), we're inventory-first with deeper tracking features. Unlike enterprise ERPs, we're affordable ($49/mo) and setup takes 10 minutes.",
            "monetization_hypothesis": "SaaS subscription at $49/mo per location. Target 100 paying customers in first 6 months. Average customer value: $588/year.",
            # Strategic fields (CTO) - as lists
            "assumptions": [
                "Shop owners will pay for inventory software if it saves >2 hours/week",
                "Barcode scanning is a must-have feature",
                "Mobile app is critical (owners check inventory on-the-go)",
            ],
            "risks": [
                "Competition from POS systems adding inventory features",
                "Customer acquisition cost may exceed LTV if we rely on paid ads",
                "Integration complexity with existing systems",
            ],
            "smallest_viable_experiment": "Single-location inventory tracker with manual entry and CSV export. Test with 10 local shop owners for 2 weeks. Success = 7/10 would pay $49/mo.",
        }

    async def generate_artifacts(self, brief: dict) -> dict:
        """Generate structured artifacts matching Pydantic schemas.

        Args:
            brief: Context for artifact generation

        Returns:
            Dict with 5 artifact type keys, each containing structured content
            matching the corresponding Pydantic schema

        Raises:
            RuntimeError: For llm_failure and rate_limited scenarios
        """
        if self.scenario == "llm_failure":
            raise RuntimeError("Anthropic API rate limit exceeded. Retry after 60 seconds.")

        if self.scenario == "rate_limited":
            raise RuntimeError(
                "Worker capacity exceeded. Estimated wait: 5 minutes. Current queue depth: 12."
            )

        # Return structured data matching Pydantic schemas with cross-references
        return {
            # Product Brief (references in MVP Scope, Milestones, Risk Log, How It Works)
            "brief": {
                "_schema_version": 1,
                # Core fields (all tiers)
                "problem_statement": "Small retail business owners waste 5-10 hours per week manually tracking inventory in spreadsheets, leading to stockouts, overordering, and lost sales. We identified this problem as the #1 pain point in our customer interviews.",
                "target_user": "Retail shop owners with 1-10 employees managing physical products across 1-3 locations. We're focusing on gift shops, boutiques, and cafes that carry 100-1000 SKUs.",
                "value_proposition": "Dead-simple inventory tracking with barcode scanning, real-time sync, and automatic reorder alerts. We designed it so owners can start tracking in 10 minutes with zero training required.",
                "key_constraint": "We must support offline-first operation with background sync when connectivity is restored, since many retail locations have unreliable WiFi.",
                "differentiation_points": [
                    "Inventory-first focus vs POS bundled solutions",
                    "10-minute setup vs weeks of ERP configuration",
                    "Affordable at $49/mo vs $300+ enterprise tools"
                ],
                # Business tier (Partner+)
                "market_analysis": "We identified a $2B TAM in SMB inventory software. Our SAM (retail shops with <10 employees) is $400M. We're targeting a 1% market share ($4M ARR) within 3 years. The market is growing 12% annually as retailers digitize post-pandemic.",
                # Strategic tier (CTO)
                "competitive_strategy": "We will compete on depth of inventory features rather than breadth like POS systems. Our advantage: we can iterate faster on inventory-specific workflows (cycle counting, lot tracking, multi-location transfers) without POS baggage. We'll defend our position through network effects (supplier integrations) and switching costs (historical data)."
            },

            # MVP Scope (references Brief's value proposition)
            "mvp_scope": {
                "_schema_version": 1,
                # Core fields
                "core_features": [
                    {
                        "name": "Product Management",
                        "description": "We'll let users add products with name, SKU, quantity, and reorder point. Supports manual entry and bulk CSV import.",
                        "priority": "high"
                    },
                    {
                        "name": "Stock Adjustments",
                        "description": "We'll track every inventory change with timestamp, quantity delta, reason, and notes. Supports receiving shipments and recording sales.",
                        "priority": "high"
                    },
                    {
                        "name": "Low Stock Alerts",
                        "description": "We'll send email notifications when product quantity falls below reorder point. Delivers on our value proposition of automatic alerts.",
                        "priority": "high"
                    },
                    {
                        "name": "Basic Reporting",
                        "description": "We'll show current stock levels, adjustment history, and low stock summary. Filterable by product category.",
                        "priority": "medium"
                    },
                    {
                        "name": "CSV Export",
                        "description": "We'll export current inventory and adjustment logs to CSV for offline analysis or migration.",
                        "priority": "medium"
                    }
                ],
                "out_of_scope": [
                    "Multi-location sync (Phase 2)",
                    "Barcode scanning hardware (Phase 2)",
                    "Mobile native app (web-only for MVP)",
                    "Third-party integrations (Shopify, Square)"
                ],
                "success_metrics": [
                    "100 active users within 6 months",
                    "50% retention after 30 days",
                    "Average 3 stock adjustments per user per week"
                ],
                # Business tier
                "technical_architecture": "We're building with Next.js 14 (frontend), FastAPI (backend), and PostgreSQL (database). Chosen for team expertise and rapid iteration speed. Hosting on AWS ECS for scalability.",
                # Strategic tier
                "scalability_plan": "We'll scale horizontally by sharding database by customer (each shop is independent). When we hit 10k users, we'll add read replicas. At 50k users, we'll migrate to managed Postgres (RDS) with automatic failover."
            },

            # Milestones (references MVP features and Brief constraint)
            "milestones": {
                "_schema_version": 1,
                # Core fields
                "milestones": [
                    {
                        "title": "Week 1: Foundation",
                        "description": "We'll build the database schema and authentication system. Includes products, stock_adjustments tables, and email/password auth.",
                        "success_criteria": [
                            "Database migrations run successfully",
                            "User can sign up and log in",
                            "Product CRUD operations work"
                        ],
                        "estimated_weeks": 1
                    },
                    {
                        "title": "Week 2: Core Features",
                        "description": "We'll implement the Stock Adjustments and Low Stock Alerts features from our MVP Scope. This delivers our core value proposition.",
                        "success_criteria": [
                            "User can log stock adjustments",
                            "Low stock alerts trigger correctly",
                            "Email notifications send"
                        ],
                        "estimated_weeks": 1
                    },
                    {
                        "title": "Week 3: Reporting & Export",
                        "description": "We'll build the Basic Reporting and CSV Export features. Enables users to analyze trends and migrate data if needed.",
                        "success_criteria": [
                            "Stock level report shows accurate data",
                            "Adjustment history is queryable",
                            "CSV export includes all fields"
                        ],
                        "estimated_weeks": 1
                    },
                    {
                        "title": "Week 4: Launch",
                        "description": "We'll polish the UI, run user testing, and deploy to production. Addresses our key constraint by ensuring offline tolerance is tested.",
                        "success_criteria": [
                            "5 beta users complete workflows",
                            "No critical bugs in production",
                            "First 10 paying customers onboarded"
                        ],
                        "estimated_weeks": 1
                    }
                ],
                "critical_path": [
                    "Foundation (Week 1)",
                    "Core Features (Week 2)",
                    "Launch (Week 4)"
                ],
                "total_duration_weeks": 4,
                # Business tier
                "resource_plan": "We'll staff with 1 full-stack engineer (80h total) and 1 designer (20h for UI polish in Week 3). Founder handles user testing and onboarding. Total cost: $12k eng + $2k design = $14k.",
                # Strategic tier
                "risk_mitigation_timeline": "We'll address the Customer Acquisition Cost risk in Week 3 by finalizing our local outreach list. We'll mitigate Retention Risk in Week 4 by scheduling weekly check-in calls with first 10 customers."
            },

            # Risk Log (references specific Milestones and Brief assumptions)
            "risk_log": {
                "_schema_version": 1,
                # Core fields
                "technical_risks": [
                    {
                        "title": "Offline Sync Complexity",
                        "description": "We identified handling conflict resolution when multiple devices sync after offline edits. References our key constraint in the Brief.",
                        "severity": "high",
                        "mitigation": "We'll start with last-write-wins strategy in MVP. Phase 2 adds user-driven conflict resolution if needed."
                    },
                    {
                        "title": "Email Delivery Reliability",
                        "description": "We risk low stock alerts landing in spam, reducing value proposition effectiveness. Critical for Core Features milestone (Week 2).",
                        "severity": "medium",
                        "mitigation": "We'll use SendGrid with DKIM/SPF setup. Test deliverability with beta users in Week 4."
                    }
                ],
                "market_risks": [
                    {
                        "title": "Customer Acquisition Cost",
                        "description": "We assume CAC stays below $200, but paid ads may exceed LTV ($588/year). Impacts our monetization hypothesis.",
                        "severity": "high",
                        "mitigation": "We'll focus on organic channels: local retail associations, word-of-mouth, content marketing. Target 50% organic mix."
                    },
                    {
                        "title": "Competition from POS Systems",
                        "description": "We risk Square/Shopify adding our inventory features before we scale. Threatens our differentiation strategy.",
                        "severity": "medium",
                        "mitigation": "We'll build deeper inventory workflows (lot tracking, cycle counting) that POS systems won't prioritize. Create switching costs via data history."
                    }
                ],
                "execution_risks": [
                    {
                        "title": "Timeline Slippage",
                        "description": "We risk the 4-week timeline extending to 6+ weeks, delaying revenue and learning. Impacts all milestones.",
                        "severity": "medium",
                        "mitigation": "We'll cut scope aggressively if Week 1 foundation takes longer than planned. CSV import moves to Phase 2 if needed."
                    },
                    {
                        "title": "Beta User Churn",
                        "description": "We risk losing beta users before launch (Week 4 milestone). Would invalidate product-market fit assumptions.",
                        "severity": "low",
                        "mitigation": "We'll offer free first 3 months to beta users. Weekly check-ins to address feedback quickly."
                    }
                ],
                # Business tier
                "financial_risks": [
                    {
                        "title": "Burn Rate",
                        "description": "We risk exceeding $14k budget if engineering hours increase. Could delay follow-on funding.",
                        "severity": "medium",
                        "mitigation": "We'll cap hours at 80 (1 person-month). Defer nice-to-have features to Phase 2."
                    }
                ],
                # Strategic tier
                "strategic_risks": [
                    {
                        "title": "Market Timing",
                        "description": "We risk launching during retail off-season (post-holiday) when budgets are tight. Could slow customer acquisition.",
                        "severity": "low",
                        "mitigation": "We'll target cafes and gift shops that have year-round inventory needs. Avoid seasonal retailers in initial cohort."
                    }
                ]
            },

            # How It Works (references MVP features, Milestones, architecture)
            "how_it_works": {
                "_schema_version": 1,
                # Core fields
                "user_journey": [
                    {
                        "step_number": 1,
                        "title": "Sign Up",
                        "description": "We'll guide users through email/password signup with email verification. Delivered in Foundation milestone (Week 1)."
                    },
                    {
                        "step_number": 2,
                        "title": "Add Products",
                        "description": "We'll let users enter products manually or import via CSV. References Product Management feature from MVP Scope. Completed by Week 1."
                    },
                    {
                        "step_number": 3,
                        "title": "Track Stock Changes",
                        "description": "We'll provide a form to log stock adjustments (receiving shipments, recording sales). Core Features milestone (Week 2). Delivers on our value proposition."
                    },
                    {
                        "step_number": 4,
                        "title": "Receive Alerts",
                        "description": "We'll send email when stock falls below reorder point. Low Stock Alerts feature from Week 2. Automatic as promised in Brief."
                    },
                    {
                        "step_number": 5,
                        "title": "Review Reports",
                        "description": "We'll show current stock levels and adjustment history. Basic Reporting feature from Week 3. Supports data-driven restocking decisions."
                    }
                ],
                "architecture": "We're using a three-tier architecture: Next.js 14 frontend (responsive web app), FastAPI backend (async Python for high concurrency), PostgreSQL database (products, adjustments, users). Authentication via JWT tokens with refresh rotation. Email alerts via SendGrid API. Hosted on AWS ECS (Docker containers) behind ALB. References our technical architecture from MVP Scope.",
                "data_flow": "We designed the flow as: User submits adjustment form → Frontend validates quantity → API authenticates JWT → Backend checks product exists → DB transaction updates quantity and logs adjustment → If quantity < reorder_point, queue email alert → Response confirms success. Supports our offline constraint via local form validation.",
                # Business tier
                "integration_points": "We're planning SendGrid (email), Stripe (payments), AWS S3 (CSV storage), and CloudWatch (monitoring) for MVP. Phase 2 adds Shopify webhook integration for automatic stock sync when orders are placed.",
                # Strategic tier
                "security_compliance": "We'll implement AES-256 encryption at rest (RDS), TLS 1.3 in transit, and RBAC for multi-user shops. SOC 2 Type II compliance planned for Year 2 to serve enterprise customers. Password hashing via bcrypt with 12 rounds. Session tokens expire after 7 days."
            }
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

    # =========================================================================
    # UNDERSTANDING INTERVIEW METHODS
    # =========================================================================

    async def generate_understanding_questions(self, context: dict) -> list[dict]:
        """Generate adaptive understanding questions (deeper than onboarding).

        Args:
            context: Dictionary with keys like "idea_text", "answered_questions", "answers"

        Returns:
            List of 6 understanding questions focusing on market validation, competitive analysis,
            monetization depth, risk awareness, and smallest experiment.

        Raises:
            RuntimeError: For llm_failure and rate_limited scenarios
        """
        if self.scenario == "llm_failure":
            raise RuntimeError("Anthropic API rate limit exceeded. Retry after 60 seconds.")

        if self.scenario == "rate_limited":
            raise RuntimeError(
                "Worker capacity exceeded. Estimated wait: 5 minutes. Current queue depth: 12."
            )

        # Return 6 adaptive questions using "we" co-founder language
        return [
            {
                "id": "uq1",
                "text": "Who have we talked to that experiences this problem? What did they tell us?",
                "input_type": "textarea",
                "required": True,
                "options": None,
                "follow_up_hint": "Think about specific conversations, not hypothetical users",
            },
            {
                "id": "uq2",
                "text": "What are the top 3 alternatives our users consider today? What do they like and hate about each?",
                "input_type": "textarea",
                "required": True,
                "options": None,
                "follow_up_hint": "Include direct competitors and workarounds (spreadsheets, manual processes)",
            },
            {
                "id": "uq3",
                "text": "How will we make money? Be specific about pricing, customer acquisition, and unit economics.",
                "input_type": "textarea",
                "required": True,
                "options": None,
                "follow_up_hint": "Include assumptions about willingness to pay and customer lifetime value",
            },
            {
                "id": "uq4",
                "text": "What's the biggest risk that could kill this idea? How likely is it?",
                "input_type": "textarea",
                "required": True,
                "options": None,
                "follow_up_hint": "Be honest about technical, market, or execution risks",
            },
            {
                "id": "uq5",
                "text": "What's the smallest experiment we can run to validate our riskiest assumption?",
                "input_type": "textarea",
                "required": True,
                "options": None,
                "follow_up_hint": "Think smoke test, not MVP — what can we test in days, not months?",
            },
            {
                "id": "uq6",
                "text": "What constraints must we work within? (Budget, timeline, team, technology, regulation, etc.)",
                "input_type": "textarea",
                "required": False,
                "options": None,
                "follow_up_hint": None,
            },
        ]

    async def generate_idea_brief(self, idea: str, questions: list[dict], answers: dict) -> dict:
        """Generate Rationalised Idea Brief from understanding interview answers.

        Args:
            idea: Original idea text
            questions: List of understanding questions
            answers: Dictionary mapping question IDs to user answers

        Returns:
            Dict matching RationalisedIdeaBrief schema with realistic confidence scores

        Raises:
            RuntimeError: For llm_failure and rate_limited scenarios
        """
        if self.scenario == "llm_failure":
            raise RuntimeError("Anthropic API rate limit exceeded. Retry after 60 seconds.")

        if self.scenario == "rate_limited":
            raise RuntimeError(
                "Worker capacity exceeded. Estimated wait: 5 minutes. Current queue depth: 12."
            )

        # Return complete RationalisedIdeaBrief with investor-facing tone and confidence scores
        from datetime import datetime, timezone

        return {
            "_schema_version": 1,
            "problem_statement": "Small business owners waste 5-10 hours per week manually tracking inventory in spreadsheets, leading to stockouts, overordering, and lost sales. We've validated this through interviews with 12 retail shop owners who all cited inventory management as their #1 operational pain point.",
            "target_user": "Retail shop owners with 1-10 employees managing physical products across 1-3 locations. Our initial focus is gift shops, boutiques, and cafes that carry 100-1000 SKUs and lack dedicated IT staff.",
            "value_prop": "We provide dead-simple inventory tracking with barcode scanning, real-time sync across locations, and automatic reorder alerts. Our goal is zero training required — owners can start tracking inventory in under 10 minutes.",
            "differentiation": "We're inventory-first, unlike POS bundled solutions (Shopify, Square) that treat inventory as an afterthought. We compete on depth of inventory features (lot tracking, cycle counting, multi-location transfers) rather than breadth. Our setup takes 10 minutes vs weeks for enterprise ERPs, and we're affordable at $49/mo vs $300+ for enterprise tools.",
            "monetization_hypothesis": "We'll charge $49/month per location with a 14-day free trial. Based on our customer interviews, we believe 60% of trial users will convert if we save them 3+ hours per week. Our target is 100 paying customers in the first 6 months, generating $4,900 MRR. Average customer value: $588/year with 70% annual retention.",
            "market_context": "We've identified a $2B TAM in SMB inventory software, growing 12% annually as retailers digitize post-pandemic. Our SAM (retail shops with <10 employees) is $400M. The market is underserved — POS systems are overkill, and ERPs are too complex and expensive. We're targeting 1% market share ($4M ARR) within 3 years.",
            "key_constraints": [
                "Must work offline with background sync (many retail locations have unreliable WiFi)",
                "Must integrate with existing POS systems within 6 months (or we lose customers to bundled solutions)",
                "Must stay under $50/mo price point (validated willingness-to-pay threshold from interviews)",
            ],
            "assumptions": [
                "Shop owners will pay $49/mo if we save them 3+ hours per week (validated in 8/12 interviews)",
                "Barcode scanning is a must-have feature for conversion (mentioned by 10/12 interviewees)",
                "Mobile app is critical — owners check inventory on-the-go (9/12 interviewees requested this)",
                "We can acquire customers at <$200 CAC through local retail associations and word-of-mouth",
            ],
            "risks": [
                "Competition from POS systems adding inventory features (Square recently added basic inventory)",
                "Customer acquisition cost may exceed LTV if we rely on paid ads (estimated CAC via ads: $300-400)",
                "Integration complexity with legacy POS systems could delay roadmap by 3+ months",
                "Retention risk if we don't deliver mobile app within 6 months (mentioned by 75% of interviewees)",
            ],
            "smallest_viable_experiment": "We'll build a single-location inventory tracker with manual entry and CSV export. We'll test with 10 local shop owners for 2 weeks, offering free usage in exchange for daily feedback. Success criteria: 7/10 owners say they'd pay $49/mo, and at least 5 actively use it 3+ times per week. This validates core value prop before investing in barcode scanning or multi-location sync.",
            "confidence_scores": {
                "problem_statement": "strong",  # Validated through 12 interviews
                "target_user": "strong",  # Specific segment identified
                "value_prop": "moderate",  # Not yet tested with working product
                "differentiation": "moderate",  # Competitive analysis done, but untested in market
                "monetization_hypothesis": "moderate",  # Price validated, but conversion rate is assumed
                "market_context": "strong",  # TAM/SAM analysis with research backing
                "key_constraints": "strong",  # Identified through user interviews
                "assumptions": "moderate",  # Some validated, some unproven
                "risks": "strong",  # Comprehensive risk identification
                "smallest_viable_experiment": "strong",  # Clear, actionable experiment defined
            },
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }

    async def check_question_relevance(
        self, idea: str, answered: list[dict], answers: dict, remaining: list[dict]
    ) -> dict:
        """Check if remaining questions are still relevant after an answer edit.

        In the fake implementation, we always return no regeneration needed for simplicity.

        Args:
            idea: Original idea text
            answered: List of already-answered questions
            answers: Current answers dict
            remaining: List of remaining (unanswered) questions

        Returns:
            Dict with needs_regeneration=False, preserve_indices=[] (no changes in fake)

        Raises:
            RuntimeError: For llm_failure and rate_limited scenarios
        """
        if self.scenario == "llm_failure":
            raise RuntimeError("Anthropic API rate limit exceeded. Retry after 60 seconds.")

        if self.scenario == "rate_limited":
            raise RuntimeError(
                "Worker capacity exceeded. Estimated wait: 5 minutes. Current queue depth: 12."
            )

        # In fake, no regeneration needed (simplest behavior for testing)
        return {
            "needs_regeneration": False,
            "preserve_indices": [],
        }

    async def assess_section_confidence(self, section_key: str, content: str) -> str:
        """Assess confidence level for a brief section.

        Simple heuristic: length-based confidence (realistic for fake).

        Args:
            section_key: Section identifier (e.g., "problem_statement")
            content: Section content to assess

        Returns:
            Confidence level: "strong" | "moderate" | "needs_depth"

        Raises:
            RuntimeError: For llm_failure and rate_limited scenarios
        """
        if self.scenario == "llm_failure":
            raise RuntimeError("Anthropic API rate limit exceeded. Retry after 60 seconds.")

        if self.scenario == "rate_limited":
            raise RuntimeError(
                "Worker capacity exceeded. Estimated wait: 5 minutes. Current queue depth: 12."
            )

        # Simple heuristic for fake: length-based confidence
        content_length = len(content.strip())

        if content_length > 100:
            return "strong"
        elif content_length >= 50:
            return "moderate"
        else:
            return "needs_depth"

    async def generate_execution_options(self, brief: dict, feedback: str | None = None) -> dict:
        """Generate 2-3 execution plan options from the Idea Brief.

        Returns 3 realistic options:
        - Fast MVP (recommended, low risk, 70% scope, 3-4 weeks)
        - Full-Featured Launch (high risk, 95% scope, 8-10 weeks)
        - Hybrid Approach (medium risk, 85% scope, 5-6 weeks)

        Args:
            brief: Rationalised Idea Brief artifact content
            feedback: Optional feedback on previous options (for regeneration)

        Returns:
            Dict matching ExecutionPlanOptions schema with 3 options

        Raises:
            RuntimeError: For llm_failure and rate_limited scenarios
        """
        if self.scenario == "llm_failure":
            raise RuntimeError("Anthropic API rate limit exceeded. Retry after 60 seconds.")

        if self.scenario == "rate_limited":
            raise RuntimeError(
                "Worker capacity exceeded. Estimated wait: 5 minutes. Current queue depth: 12."
            )

        # Return 3 realistic execution plan options
        return {
            "options": [
                {
                    "id": "fast-mvp",
                    "name": "Fast MVP",
                    "is_recommended": True,
                    "time_to_ship": "3-4 weeks",
                    "engineering_cost": "Low (1 engineer, ~80 hours)",
                    "risk_level": "low",
                    "scope_coverage": 70,
                    "pros": [
                        "Fastest path to user feedback",
                        "Lowest cost and risk",
                        "Validates core assumptions quickly",
                        "Easy to pivot if needed",
                    ],
                    "cons": [
                        "Limited feature set may not wow users",
                        "May need significant Phase 2 work",
                        "Could miss competitive advantages",
                    ],
                    "technical_approach": "We'll focus on the core workflow with minimal UI polish. Use proven tech stack (Next.js, FastAPI, PostgreSQL) for speed. Manual processes replace automation where possible. Single-location only, defer multi-location sync to Phase 2.",
                    "tradeoffs": [
                        "Speed over completeness — ship fast, iterate based on feedback",
                        "Manual workarounds over automation — founder does setup tasks",
                        "Proven tech over optimal tech — use what the team knows best",
                    ],
                    "engineering_impact": "Single full-stack engineer can complete alone. Low coordination overhead. High velocity due to narrow scope.",
                    "cost_note": "$12-15k engineering cost (80 hours @ $150-190/hr). Add $2k for design. Total budget: ~$14-17k.",
                },
                {
                    "id": "full-featured",
                    "name": "Full-Featured Launch",
                    "is_recommended": False,
                    "time_to_ship": "8-10 weeks",
                    "engineering_cost": "High (2-3 engineers, ~400 hours)",
                    "risk_level": "high",
                    "scope_coverage": 95,
                    "pros": [
                        "Comprehensive feature set from day one",
                        "Stronger competitive positioning",
                        "Less follow-on work needed",
                        "Impressive demo for investors/partners",
                    ],
                    "cons": [
                        "Longer time to market and feedback",
                        "Higher cost and burn rate",
                        "Risk of building features nobody wants",
                        "Harder to pivot if core assumptions are wrong",
                    ],
                    "technical_approach": "We'll build the complete vision: multi-location sync, barcode scanning, mobile app, third-party integrations, advanced reporting. Invest in scalable architecture from the start. Polish UI/UX to production quality. Comprehensive test coverage.",
                    "tradeoffs": [
                        "Completeness over speed — launch with full feature set",
                        "Quality over iteration — get it right the first time",
                        "Scalability over simplicity — build for 10k users on day one",
                    ],
                    "engineering_impact": "Requires 2-3 engineers with coordination overhead. Frontend specialist + backend specialist + mobile developer. Higher management burden.",
                    "cost_note": "$60-76k engineering cost (400 hours @ $150-190/hr). Add $8k for design and QA. Total budget: ~$68-84k.",
                },
                {
                    "id": "hybrid",
                    "name": "Hybrid Approach",
                    "is_recommended": False,
                    "time_to_ship": "5-6 weeks",
                    "engineering_cost": "Medium (1-2 engineers, ~200 hours)",
                    "risk_level": "medium",
                    "scope_coverage": 85,
                    "pros": [
                        "Balanced speed and completeness",
                        "Includes key differentiators (e.g., barcode scanning)",
                        "Moderate cost and risk",
                        "Strong enough for early adopters",
                    ],
                    "cons": [
                        "Not as fast as Fast MVP",
                        "Not as complete as Full-Featured",
                        "May require tough scope decisions mid-build",
                    ],
                    "technical_approach": "We'll build core features plus 2-3 key differentiators (e.g., barcode scanning, basic multi-location). Defer advanced features like mobile app and integrations. Use responsive web app (works on mobile browsers). Moderate UI polish — clean but not pixel-perfect.",
                    "tradeoffs": [
                        "Strategic features over full scope — include competitive differentiators",
                        "Responsive web over native mobile — works everywhere, less dev time",
                        "Solid foundation over quick hacks — built to extend, not rewrite",
                    ],
                    "engineering_impact": "1-2 engineers depending on skillset. Can be done solo with longer timeline, or faster with pair. Moderate complexity.",
                    "cost_note": "$30-38k engineering cost (200 hours @ $150-190/hr). Add $4k for design. Total budget: ~$34-42k.",
                },
            ],
            "recommended_id": "fast-mvp",
        }
