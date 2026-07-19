from __future__ import annotations

import csv
import io
import json
import logging
import re
from typing import Annotated

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Response
from pydantic import BaseModel
from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from backend.app.application.testgen.analyze_requirement import AnalyzeRequirementUseCase
from backend.app.application.testgen.generate_tests import GenerateTestArtifactsUseCase
from backend.app.config.settings import Settings
from backend.app.infrastructure.database.models import (
    Document,
    TestCase,
    TestClarifyingQuestion,
    TestGenSession,
    TestScenario,
    User,
)
from backend.app.presentation.api.dependencies import get_current_user, get_session, get_settings

logger = logging.getLogger(__name__)

router = APIRouter()


class SessionCreateRequest(BaseModel):
    requirement_document_id: int
    context_category: str | None = None


class AnswerItem(BaseModel):
    question_id: int
    answer: str | None = None
    skip: bool = False


class AnswersRequest(BaseModel):
    answers: list[AnswerItem]


class ScenarioUpdateRequest(BaseModel):
    title: str | None = None
    description: str | None = None
    priority: str | None = None


class CaseUpdateRequest(BaseModel):
    title: str | None = None
    preconditions: str | None = None
    steps: list[str] | None = None
    expected_result: str | None = None
    priority: str | None = None
    case_type: str | None = None


async def _load_owned_session(session: AsyncSession, session_id: int, user: User) -> TestGenSession:
    test_session = await session.get(TestGenSession, session_id)
    if test_session is None:
        raise HTTPException(status_code=404, detail="Test generation session not found")
    role_name = user.role.name if user.role else ""
    if test_session.user_id != user.id and role_name != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to access this session")
    return test_session


@router.post("/sessions")
async def create_session(
    payload: SessionCreateRequest,
    background_tasks: BackgroundTasks,
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    user: Annotated[User, Depends(get_current_user)],
) -> dict:
    document = await session.get(Document, payload.requirement_document_id)
    if document is None:
        raise HTTPException(status_code=404, detail="Requirement document not found")
    if document.document_type == "link":
        raise HTTPException(
            status_code=400, detail="Web links are not supported as requirement documents yet."
        )

    test_session = TestGenSession(
        requirement_document_id=document.id,
        user_id=user.id,
        context_category=payload.context_category,
        status="analyzing",
    )
    session.add(test_session)
    await session.commit()
    await session.refresh(test_session)
    background_tasks.add_task(_analyze_session, test_session.id, settings)
    return {"id": test_session.id, "status": test_session.status}


@router.get("/sessions")
async def list_sessions(
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> list[dict]:
    stmt = (
        select(TestGenSession)
        .options(selectinload(TestGenSession.requirement_document))
        .order_by(TestGenSession.created_at.desc())
    )
    role_name = user.role.name if user.role else ""
    if role_name != "admin":
        stmt = stmt.where(TestGenSession.user_id == user.id)
    rows = (await session.scalars(stmt)).all()
    return [
        {
            "id": row.id,
            "status": row.status,
            "requirement_document_name": row.requirement_document.name if row.requirement_document else None,
            "clarifying_round": row.clarifying_round,
            "created_at": row.created_at,
        }
        for row in rows
    ]


@router.get("/sessions/{session_id}")
async def get_session_detail(
    session_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    user: Annotated[User, Depends(get_current_user)],
) -> dict:
    test_session = await _load_owned_session(session, session_id, user)
    document = await session.get(Document, test_session.requirement_document_id)

    questions = (
        await session.scalars(
            select(TestClarifyingQuestion)
            .where(TestClarifyingQuestion.session_id == session_id)
            .order_by(TestClarifyingQuestion.round, TestClarifyingQuestion.order_index)
        )
    ).all()

    scenarios = (
        await session.scalars(
            select(TestScenario).where(TestScenario.session_id == session_id).order_by(TestScenario.order_index)
        )
    ).all()
    scenario_ids = [scenario.id for scenario in scenarios]
    cases = []
    if scenario_ids:
        cases = (
            await session.scalars(
                select(TestCase).where(TestCase.scenario_id.in_(scenario_ids)).order_by(TestCase.order_index)
            )
        ).all()
    cases_by_scenario: dict[int, list[TestCase]] = {}
    for case in cases:
        cases_by_scenario.setdefault(case.scenario_id, []).append(case)

    return {
        "id": test_session.id,
        "status": test_session.status,
        "clarifying_round": test_session.clarifying_round,
        "max_clarifying_rounds": settings.test_generation.max_clarifying_rounds,
        "error_message": test_session.error_message,
        "context_category": test_session.context_category,
        "requirement_document_id": test_session.requirement_document_id,
        "requirement_document_name": document.name if document else None,
        "assumptions": json.loads(test_session.assumptions_json or "[]"),
        "questions": [
            {
                "id": question.id,
                "round": question.round,
                "question": question.question,
                "answer": question.answer,
                "status": question.status,
            }
            for question in questions
        ],
        "scenarios": [
            {
                "id": scenario.id,
                "title": scenario.title,
                "description": scenario.description,
                "priority": scenario.priority,
                "test_cases": [
                    {
                        "id": case.id,
                        "title": case.title,
                        "preconditions": case.preconditions,
                        "steps": json.loads(case.steps_json or "[]"),
                        "expected_result": case.expected_result,
                        "priority": case.priority,
                        "case_type": case.case_type,
                    }
                    for case in cases_by_scenario.get(scenario.id, [])
                ],
            }
            for scenario in scenarios
        ],
    }


@router.post("/sessions/{session_id}/answers")
async def submit_answers(
    session_id: int,
    payload: AnswersRequest,
    background_tasks: BackgroundTasks,
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    user: Annotated[User, Depends(get_current_user)],
) -> dict:
    test_session = await _load_owned_session(session, session_id, user)
    if test_session.status != "questions_pending":
        raise HTTPException(status_code=400, detail="This session is not awaiting answers.")

    question_ids = [item.question_id for item in payload.answers]
    questions = (
        await session.scalars(
            select(TestClarifyingQuestion).where(
                TestClarifyingQuestion.id.in_(question_ids),
                TestClarifyingQuestion.session_id == session_id,
            )
        )
    ).all()
    questions_by_id = {question.id: question for question in questions}
    for item in payload.answers:
        question = questions_by_id.get(item.question_id)
        if question is None:
            continue
        if item.skip or not (item.answer or "").strip():
            question.status = "skipped"
        else:
            question.answer = item.answer.strip()
            question.status = "answered"

    test_session.status = "analyzing"
    await session.commit()
    background_tasks.add_task(_analyze_session, test_session.id, settings)
    return {"id": test_session.id, "status": test_session.status}


@router.post("/sessions/{session_id}/generate")
async def force_generate(
    session_id: int,
    background_tasks: BackgroundTasks,
    session: Annotated[AsyncSession, Depends(get_session)],
    settings: Annotated[Settings, Depends(get_settings)],
    user: Annotated[User, Depends(get_current_user)],
) -> dict:
    test_session = await _load_owned_session(session, session_id, user)
    if test_session.status == "generating":
        raise HTTPException(status_code=400, detail="Generation is already in progress.")

    pending = (
        await session.scalars(
            select(TestClarifyingQuestion).where(
                TestClarifyingQuestion.session_id == session_id,
                TestClarifyingQuestion.status == "pending",
            )
        )
    ).all()
    for question in pending:
        question.status = "skipped"

    scenario_ids = (
        await session.scalars(select(TestScenario.id).where(TestScenario.session_id == session_id))
    ).all()
    if scenario_ids:
        await session.execute(delete(TestCase).where(TestCase.scenario_id.in_(scenario_ids)))
        await session.execute(delete(TestScenario).where(TestScenario.session_id == session_id))

    test_session.status = "ready"
    test_session.error_message = None
    await session.commit()
    background_tasks.add_task(_generate_session, test_session.id, settings)
    return {"id": test_session.id, "status": "generating"}


@router.get("/sessions/{session_id}/export.csv")
async def export_csv(
    session_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> Response:
    test_session = await _load_owned_session(session, session_id, user)
    if test_session.status != "completed":
        raise HTTPException(status_code=400, detail="This session has no completed test artifacts to export yet.")

    scenarios = (
        await session.scalars(
            select(TestScenario).where(TestScenario.session_id == session_id).order_by(TestScenario.order_index)
        )
    ).all()
    scenario_ids = [scenario.id for scenario in scenarios]
    cases = []
    if scenario_ids:
        cases = (
            await session.scalars(
                select(TestCase).where(TestCase.scenario_id.in_(scenario_ids)).order_by(TestCase.order_index)
            )
        ).all()
    cases_by_scenario: dict[int, list[TestCase]] = {}
    for case in cases:
        cases_by_scenario.setdefault(case.scenario_id, []).append(case)

    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["Scenario", "Test Case", "Preconditions", "Steps", "Expected Result", "Priority", "Type"])
    for scenario in scenarios:
        for case in cases_by_scenario.get(scenario.id, []):
            steps = "\n".join(json.loads(case.steps_json or "[]"))
            writer.writerow(
                [scenario.title, case.title, case.preconditions, steps, case.expected_result, case.priority, case.case_type]
            )

    document = await session.get(Document, test_session.requirement_document_id)
    safe_name = re.sub(r"[^A-Za-z0-9_.-]", "_", (document.name if document else str(session_id)))
    return Response(
        content=buffer.getvalue(),
        media_type="text/csv",
        headers={"Content-Disposition": f'attachment; filename="test-cases-{safe_name}.csv"'},
    )


@router.patch("/scenarios/{scenario_id}")
async def update_scenario(
    scenario_id: int,
    payload: ScenarioUpdateRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> dict:
    scenario = await session.get(TestScenario, scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Scenario not found")
    await _load_owned_session(session, scenario.session_id, user)

    if payload.title is not None:
        scenario.title = payload.title
    if payload.description is not None:
        scenario.description = payload.description
    if payload.priority is not None:
        scenario.priority = payload.priority
    await session.commit()
    return {"id": scenario.id, "status": "ok"}


@router.patch("/cases/{case_id}")
async def update_case(
    case_id: int,
    payload: CaseUpdateRequest,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> dict:
    case = await session.get(TestCase, case_id)
    if case is None:
        raise HTTPException(status_code=404, detail="Test case not found")
    scenario = await session.get(TestScenario, case.scenario_id)
    if scenario is None:
        raise HTTPException(status_code=404, detail="Test case not found")
    await _load_owned_session(session, scenario.session_id, user)

    if payload.title is not None:
        case.title = payload.title
    if payload.preconditions is not None:
        case.preconditions = payload.preconditions
    if payload.steps is not None:
        case.steps_json = json.dumps(payload.steps)
    if payload.expected_result is not None:
        case.expected_result = payload.expected_result
    if payload.priority is not None:
        case.priority = payload.priority
    if payload.case_type is not None:
        case.case_type = payload.case_type
    await session.commit()
    return {"id": case.id, "status": "ok"}


@router.delete("/sessions/{session_id}")
async def delete_session(
    session_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
    user: Annotated[User, Depends(get_current_user)],
) -> dict:
    test_session = await _load_owned_session(session, session_id, user)
    scenario_ids = (
        await session.scalars(select(TestScenario.id).where(TestScenario.session_id == session_id))
    ).all()
    if scenario_ids:
        await session.execute(delete(TestCase).where(TestCase.scenario_id.in_(scenario_ids)))
        await session.execute(delete(TestScenario).where(TestScenario.session_id == session_id))
    await session.execute(delete(TestClarifyingQuestion).where(TestClarifyingQuestion.session_id == session_id))
    await session.delete(test_session)
    await session.commit()
    return {"status": "ok"}


async def _analyze_session(session_id: int, settings: Settings) -> None:
    from backend.app.infrastructure.database.session import create_session_factory

    session_factory = create_session_factory(settings.database.url)
    async with session_factory() as session:
        try:
            await AnalyzeRequirementUseCase(settings, session).execute(session_id)
        except Exception:
            logger.exception("Test generation analysis failed for session %s", session_id)
            test_session = await session.get(TestGenSession, session_id)
            if test_session:
                test_session.status = "failed"
                test_session.error_message = "Unexpected error during requirement analysis."
                await session.commit()


async def _generate_session(session_id: int, settings: Settings) -> None:
    from backend.app.infrastructure.database.session import create_session_factory

    session_factory = create_session_factory(settings.database.url)
    async with session_factory() as session:
        try:
            await GenerateTestArtifactsUseCase(settings, session).execute(session_id)
        except Exception:
            logger.exception("Test artifact generation failed for session %s", session_id)
            test_session = await session.get(TestGenSession, session_id)
            if test_session:
                test_session.status = "failed"
                test_session.error_message = "Unexpected error during test generation."
                await session.commit()
