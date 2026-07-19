from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.application.testgen import context as ctx
from backend.app.application.testgen.schemas import GenerationResult, parse_llm_json
from backend.app.config.settings import Settings
from backend.app.infrastructure.ai.providers import create_llm_provider
from backend.app.infrastructure.database.models import (
    Document,
    TestCase,
    TestClarifyingQuestion,
    TestGenSession,
    TestScenario,
    User,
)


class GenerateTestArtifactsUseCase:
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

        test_session.status = "generating"
        await self.session.commit()

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
        qa_pairs = await self._qa_pairs(test_session.id)
        prompt = self._build_generation_prompt(requirement_text, context_results, qa_pairs)

        try:
            result = await self._call_llm(prompt)
        except Exception as exc:
            await self._fail(test_session, f"Test generation failed: {exc}")
            return

        if result is None or not result.scenarios:
            await self._fail(
                test_session,
                "The assistant could not produce valid test scenarios for this requirement. "
                "Try answering more clarifying questions or regenerating.",
            )
            return

        for scenario_index, scenario in enumerate(result.scenarios):
            scenario_row = TestScenario(
                session_id=test_session.id,
                title=scenario.title,
                description=scenario.description,
                priority=scenario.priority,
                order_index=scenario_index,
            )
            self.session.add(scenario_row)
            await self.session.flush()
            for case_index, case in enumerate(scenario.test_cases):
                self.session.add(
                    TestCase(
                        scenario_id=scenario_row.id,
                        title=case.title,
                        preconditions=case.preconditions,
                        steps_json=json.dumps(case.steps),
                        expected_result=case.expected_result,
                        priority=case.priority,
                        case_type=case.case_type,
                        order_index=case_index,
                    )
                )

        test_session.assumptions_json = json.dumps(result.assumptions)
        test_session.status = "completed"
        await self.session.commit()

    async def _fail(self, test_session: TestGenSession, message: str) -> None:
        test_session.status = "failed"
        test_session.error_message = message
        await self.session.commit()

    async def _qa_pairs(self, session_id: int) -> list[TestClarifyingQuestion]:
        return list(
            (
                await self.session.scalars(
                    select(TestClarifyingQuestion)
                    .where(TestClarifyingQuestion.session_id == session_id)
                    .order_by(TestClarifyingQuestion.round, TestClarifyingQuestion.order_index)
                )
            ).all()
        )

    def _build_generation_prompt(
        self,
        requirement_text: str,
        context_results,
        qa_pairs: list[TestClarifyingQuestion],
    ) -> str:
        return (
            "You are a QA engineer assistant for KnowledgeHub AI. Write test scenarios and "
            "detailed test cases strictly grounded in the requirement, the related app "
            "context, and the clarifications below. Do not invent behaviour that "
            "contradicts them.\n\n"
            f"Requirement document:\n{requirement_text}\n\n"
            f"Related knowledge base context:\n{ctx.format_context(context_results)}\n\n"
            f"Clarifications gathered from the user:\n{ctx.format_qa(qa_pairs)}\n\n"
            "Respond with ONLY a JSON object of the form "
            '{"scenarios": [{"title": string, "description": string, '
            '"priority": "low"|"medium"|"high", "test_cases": [{"title": string, '
            '"preconditions": string, "steps": [string, ...], "expected_result": string, '
            '"priority": "low"|"medium"|"high", '
            '"case_type": "positive"|"negative"|"edge"|"boundary"|"security"|"performance"}]}], '
            '"assumptions": [string, ...]}. '
            "Cover positive, negative, and edge/boundary cases. Use \"assumptions\" to list "
            "any gaps you filled in yourself rather than leaving them unaddressed."
        )

    async def _call_llm(self, prompt: str) -> GenerationResult | None:
        provider = create_llm_provider(self.settings.llm)
        raw = await provider.generate(prompt, response_format="json")
        result = parse_llm_json(raw, GenerationResult)
        if result is not None:
            return result

        repair_prompt = (
            "Your previous response was not valid JSON matching the required schema. "
            "Return ONLY a valid JSON object for the test scenarios/cases schema, with no "
            f"prose, markdown, or code fences.\n\nPrevious response:\n{raw}"
        )
        raw_retry = await provider.generate(repair_prompt, response_format="json")
        return parse_llm_json(raw_retry, GenerationResult)
