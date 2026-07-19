from __future__ import annotations

import json
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from backend.app.application.testgen.analyze_requirement import AnalyzeRequirementUseCase
from backend.app.config.settings import Settings
from backend.app.infrastructure.auth.passwords import hash_password
from backend.app.infrastructure.database.models import (
    Document,
    Role,
    TestCase,
    TestClarifyingQuestion,
    TestGenSession,
    TestScenario,
    User,
)
from backend.app.infrastructure.database.session import create_session_factory, init_database


def _test_settings(tmp_path) -> Settings:
    settings = Settings()
    settings.database.url = f"sqlite+aiosqlite:///{tmp_path}/test.db"
    settings.app.upload_dir = str(tmp_path / "uploads")
    settings.app.index_dir = str(tmp_path / "indexes")
    settings.vector_store.path = str(tmp_path / "indexes" / "faiss")
    settings.embeddings.provider = "deterministic"
    settings.retrieval.score_threshold = 0.0
    settings.retrieval.reranker.enabled = False
    settings.test_generation.max_clarifying_rounds = 2
    return settings


GAP_ANALYSIS_ROUND_1 = json.dumps(
    {
        "ready": False,
        "questions": ["What authentication method does the login page use?"],
        "assumptions": [],
    }
)
GAP_ANALYSIS_ROUND_2 = json.dumps({"ready": True, "questions": [], "assumptions": []})
GENERATION_RESULT = json.dumps(
    {
        "scenarios": [
            {
                "title": "Successful login",
                "description": "Verify a registered user can log in.",
                "priority": "high",
                "test_cases": [
                    {
                        "title": "Valid email/password logs the user in",
                        "preconditions": "A registered, active user account exists.",
                        "steps": ["Navigate to the login page", "Enter valid credentials", "Submit the form"],
                        "expected_result": "The user is redirected to the dashboard.",
                        "priority": "high",
                        "case_type": "positive",
                    }
                ],
            }
        ],
        "assumptions": ["Assumed standard email/password authentication."],
    }
)


@pytest.mark.asyncio
async def test_analyze_then_answer_then_generate_flow(tmp_path) -> None:
    settings = _test_settings(tmp_path)
    await init_database(settings.database.url)

    upload_dir = tmp_path / "uploads"
    upload_dir.mkdir(parents=True, exist_ok=True)
    requirement_file = upload_dir / "login_requirement.txt"
    requirement_file.write_text("Users must be able to log in to the application using their credentials.")

    session_factory = create_session_factory(settings.database.url)

    async with session_factory() as session:
        user_role = await session.scalar(select(Role).where(Role.name == "user"))
        analyst = User(
            email="analyst@test.local",
            full_name="Analyst",
            password_hash=hash_password("password123"),
            role_id=user_role.id,
            is_active=True,
        )
        session.add(analyst)
        await session.flush()

        document = Document(
            name="login_requirement.txt",
            path=str(requirement_file),
            document_type="txt",
            status="pending",
            uploaded_by_id=analyst.id,
        )
        session.add(document)
        await session.flush()

        test_session = TestGenSession(
            requirement_document_id=document.id,
            user_id=analyst.id,
            status="analyzing",
        )
        session.add(test_session)
        await session.commit()
        test_session_id = test_session.id

    mock_provider = AsyncMock()
    mock_provider.generate.side_effect = [GAP_ANALYSIS_ROUND_1, GAP_ANALYSIS_ROUND_2, GENERATION_RESULT]

    with (
        patch("backend.app.application.testgen.analyze_requirement.create_llm_provider", return_value=mock_provider),
        patch("backend.app.application.testgen.generate_tests.create_llm_provider", return_value=mock_provider),
    ):
        async with session_factory() as session:
            await AnalyzeRequirementUseCase(settings, session).execute(test_session_id)

        async with session_factory() as session:
            test_session = await session.get(TestGenSession, test_session_id)
            assert test_session.status == "questions_pending"
            assert test_session.clarifying_round == 1

            questions = (
                await session.scalars(
                    select(TestClarifyingQuestion).where(TestClarifyingQuestion.session_id == test_session_id)
                )
            ).all()
            assert len(questions) == 1
            questions[0].answer = "Email and password, verified against the users table."
            questions[0].status = "answered"
            test_session.status = "analyzing"
            await session.commit()

        async with session_factory() as session:
            await AnalyzeRequirementUseCase(settings, session).execute(test_session_id)

        async with session_factory() as session:
            test_session = await session.get(TestGenSession, test_session_id)
            assert test_session.status == "completed"
            assert json.loads(test_session.assumptions_json) == [
                "Assumed standard email/password authentication."
            ]

            scenarios = (
                await session.scalars(select(TestScenario).where(TestScenario.session_id == test_session_id))
            ).all()
            assert len(scenarios) == 1
            assert scenarios[0].title == "Successful login"

            cases = (
                await session.scalars(select(TestCase).where(TestCase.scenario_id == scenarios[0].id))
            ).all()
            assert len(cases) == 1
            assert cases[0].case_type == "positive"
            assert json.loads(cases[0].steps_json) == [
                "Navigate to the login page",
                "Enter valid credentials",
                "Submit the form",
            ]

    assert mock_provider.generate.call_count == 3
