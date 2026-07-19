from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.application.testgen import context as ctx
from backend.app.application.testgen.schemas import GapAnalysisResult, parse_llm_json
from backend.app.config.settings import Settings
from backend.app.infrastructure.ai.providers import create_llm_provider
from backend.app.infrastructure.database.models import (
    Document,
    TestClarifyingQuestion,
    TestGenSession,
    User,
)


class AnalyzeRequirementUseCase:
    def __init__(self, settings: Settings, session: AsyncSession) -> None:
        self.settings = settings
        self.session = session

    async def execute(self, session_id: int) -> None:
        test_session = await self.session.get(TestGenSession, session_id)
        if test_session is None:
            return

        document = await self.session.get(Document, test_session.requirement_document_id)
        if document is None:
            await self._fail(test_session, "Requirement document no longer exists.")
            return

        try:
            requirement_text = ctx.requirement_text(document)
        except ValueError as exc:
            await self._fail(test_session, str(exc))
            return

        user = await self.session.scalar(
            select(User).options(selectinload(User.role)).where(User.id == test_session.user_id)
        )
        if user is None:
            await self._fail(test_session, "Requesting user no longer exists.")
            return

        context_results = await ctx.gather_context(
            self.settings, self.session, requirement_text, user, test_session.context_category, document.name
        )
        prior_qa = await self._prior_qa(test_session.id)
        prompt = self._build_analysis_prompt(requirement_text, context_results, prior_qa)

        try:
            result = await self._call_llm(prompt)
        except Exception as exc:
            await self._fail(test_session, f"Requirement analysis failed: {exc}")
            return

        at_round_cap = test_session.clarifying_round >= self.settings.test_generation.max_clarifying_rounds
        if result.ready or at_round_cap or not result.questions:
            test_session.status = "ready"
            await self.session.commit()
            from backend.app.application.testgen.generate_tests import GenerateTestArtifactsUseCase

            await GenerateTestArtifactsUseCase(self.settings, self.session).execute(session_id)
            return

        test_session.clarifying_round += 1
        for index, question in enumerate(result.questions):
            self.session.add(
                TestClarifyingQuestion(
                    session_id=test_session.id,
                    round=test_session.clarifying_round,
                    question=question,
                    status="pending",
                    order_index=index,
                )
            )
        test_session.status = "questions_pending"
        await self.session.commit()

    async def _fail(self, test_session: TestGenSession, message: str) -> None:
        test_session.status = "failed"
        test_session.error_message = message
        await self.session.commit()

    async def _prior_qa(self, session_id: int) -> list[TestClarifyingQuestion]:
        return list(
            (
                await self.session.scalars(
                    select(TestClarifyingQuestion)
                    .where(TestClarifyingQuestion.session_id == session_id)
                    .order_by(TestClarifyingQuestion.round, TestClarifyingQuestion.order_index)
                )
            ).all()
        )

    def _build_analysis_prompt(
        self,
        requirement_text: str,
        context_results,
        qa_pairs: list[TestClarifyingQuestion],
    ) -> str:
        return (
            "You are a QA analyst assistant for KnowledgeHub AI. Assess whether the "
            "requirement below has enough detail and app context to write accurate test "
            "scenarios and test cases.\n\n"
            f"Requirement document:\n{requirement_text}\n\n"
            f"Related knowledge base context:\n{ctx.format_context(context_results)}\n\n"
            f"Clarifications already gathered:\n{ctx.format_qa(qa_pairs)}\n\n"
            "Respond with ONLY a JSON object of the form "
            '{"ready": boolean, "questions": [string, ...], "assumptions": [string, ...]}. '
            "Set ready=true only if you have enough information to write accurate, specific "
            "test scenarios and test cases. Otherwise list up to 5 concise, specific "
            "clarifying questions about the app's behaviour, actors, data, or integrations "
            "that are needed to write accurate tests. Use assumptions for minor gaps you are "
            "comfortable filling in yourself instead of asking about them."
        )

    async def _call_llm(self, prompt: str) -> GapAnalysisResult:
        provider = create_llm_provider(self.settings.llm)
        raw = await provider.generate(prompt, response_format="json")
        result = parse_llm_json(raw, GapAnalysisResult)
        if result is not None:
            return result

        repair_prompt = (
            "Your previous response was not valid JSON matching the required schema. "
            "Return ONLY a valid JSON object of the form "
            '{"ready": boolean, "questions": [string, ...], "assumptions": [string, ...]}, '
            f"with no prose, markdown, or code fences.\n\nPrevious response:\n{raw}"
        )
        raw_retry = await provider.generate(repair_prompt, response_format="json")
        result = parse_llm_json(raw_retry, GapAnalysisResult)
        if result is not None:
            return result

        fallback_question = (raw_retry or raw).strip() or (
            "The assistant could not analyze this requirement automatically. "
            "Please describe the relevant app behaviour and constraints."
        )
        return GapAnalysisResult(ready=False, questions=[fallback_question[:1000]])
