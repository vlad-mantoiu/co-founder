"""AutonomousRunner: Stub runner — placeholder until Phase 41 TAOR implementation.

This stub satisfies the Runner protocol so the feature flag (Plan 04) can route
to AutonomousRunner without import errors. Every method raises NotImplementedError
until Phase 41 implements the TAOR autonomous agent loop.

Phase 41 will replace these stubs with the actual Claude-based TAOR implementation.
"""

import structlog

from app.agent.state import CoFounderState

logger = structlog.get_logger(__name__)


class AutonomousRunner:
    """Stub runner — placeholder until Phase 41 TAOR implementation.

    Implements all Runner protocol methods with NotImplementedError.
    Phase 41 will replace each stub with the real TAOR agent logic.
    """

    async def run(self, state: CoFounderState) -> CoFounderState:
        """Execute the full pipeline.

        Raises:
            NotImplementedError: AutonomousRunner not yet implemented — Phase 41
        """
        raise NotImplementedError("AutonomousRunner.run() not yet implemented — Phase 41")

    async def step(self, state: CoFounderState, stage: str) -> CoFounderState:
        """Execute a single named node from the pipeline.

        Raises:
            NotImplementedError: AutonomousRunner not yet implemented — Phase 41
        """
        raise NotImplementedError("AutonomousRunner.step() not yet implemented — Phase 41")

    async def generate_questions(self, context: dict) -> list[dict]:
        """Generate onboarding questions tailored to the user's idea context.

        Raises:
            NotImplementedError: AutonomousRunner not yet implemented — Phase 41
        """
        raise NotImplementedError("AutonomousRunner.generate_questions() not yet implemented — Phase 41")

    async def generate_brief(self, answers: dict) -> dict:
        """Generate a structured product brief from onboarding answers.

        Raises:
            NotImplementedError: AutonomousRunner not yet implemented — Phase 41
        """
        raise NotImplementedError("AutonomousRunner.generate_brief() not yet implemented — Phase 41")

    async def generate_artifacts(self, brief: dict) -> dict:
        """Generate documentation artifacts from the product brief.

        Raises:
            NotImplementedError: AutonomousRunner not yet implemented — Phase 41
        """
        raise NotImplementedError("AutonomousRunner.generate_artifacts() not yet implemented — Phase 41")

    async def generate_understanding_questions(self, context: dict) -> list[dict]:
        """Generate adaptive understanding questions (deeper than onboarding).

        Raises:
            NotImplementedError: AutonomousRunner not yet implemented — Phase 41
        """
        raise NotImplementedError("AutonomousRunner.generate_understanding_questions() not yet implemented — Phase 41")

    async def generate_idea_brief(self, idea: str, questions: list[dict], answers: dict) -> dict:
        """Generate Rationalised Idea Brief from understanding interview answers.

        Raises:
            NotImplementedError: AutonomousRunner not yet implemented — Phase 41
        """
        raise NotImplementedError("AutonomousRunner.generate_idea_brief() not yet implemented — Phase 41")

    async def check_question_relevance(
        self, idea: str, answered: list[dict], answers: dict, remaining: list[dict]
    ) -> dict:
        """Check if remaining questions are still relevant after an answer edit.

        Raises:
            NotImplementedError: AutonomousRunner not yet implemented — Phase 41
        """
        raise NotImplementedError("AutonomousRunner.check_question_relevance() not yet implemented — Phase 41")

    async def assess_section_confidence(self, section_key: str, content: str) -> str:
        """Assess confidence level for a brief section.

        Raises:
            NotImplementedError: AutonomousRunner not yet implemented — Phase 41
        """
        raise NotImplementedError("AutonomousRunner.assess_section_confidence() not yet implemented — Phase 41")

    async def generate_execution_options(self, brief: dict, feedback: str | None = None) -> dict:
        """Generate 2-3 execution plan options from the Idea Brief.

        Raises:
            NotImplementedError: AutonomousRunner not yet implemented — Phase 41
        """
        raise NotImplementedError("AutonomousRunner.generate_execution_options() not yet implemented — Phase 41")

    async def generate_strategy_graph(self, idea: str, brief: dict, onboarding_answers: dict) -> dict:
        """Generate Strategy Graph artifact from idea brief and onboarding data.

        Raises:
            NotImplementedError: AutonomousRunner not yet implemented — Phase 41
        """
        raise NotImplementedError("AutonomousRunner.generate_strategy_graph() not yet implemented — Phase 41")

    async def generate_mvp_timeline(self, idea: str, brief: dict, tier: str) -> dict:
        """Generate MVP Timeline artifact with relative-week milestones.

        Raises:
            NotImplementedError: AutonomousRunner not yet implemented — Phase 41
        """
        raise NotImplementedError("AutonomousRunner.generate_mvp_timeline() not yet implemented — Phase 41")

    async def generate_app_architecture(self, idea: str, brief: dict, tier: str) -> dict:
        """Generate App Architecture artifact with component diagram and cost estimates.

        Raises:
            NotImplementedError: AutonomousRunner not yet implemented — Phase 41
        """
        raise NotImplementedError("AutonomousRunner.generate_app_architecture() not yet implemented — Phase 41")

    async def run_agent_loop(self, context: dict) -> dict:
        """Execute the autonomous TAOR agent loop for a build session.

        Raises:
            NotImplementedError: AutonomousRunner not yet implemented — Phase 41
        """
        raise NotImplementedError("AutonomousRunner.run_agent_loop() not yet implemented — Phase 41")
