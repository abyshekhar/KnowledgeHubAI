from __future__ import annotations

import json
import re

from pydantic import BaseModel, Field, ValidationError


class GapAnalysisResult(BaseModel):
    ready: bool = False
    questions: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)


class GeneratedTestCase(BaseModel):
    title: str
    preconditions: str = ""
    steps: list[str] = Field(default_factory=list)
    expected_result: str = ""
    priority: str = "medium"
    case_type: str = "positive"


class GeneratedScenario(BaseModel):
    title: str
    description: str = ""
    priority: str = "medium"
    test_cases: list[GeneratedTestCase] = Field(default_factory=list)


class GenerationResult(BaseModel):
    scenarios: list[GeneratedScenario] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)


def _extract_json_object(raw: str) -> str:
    """Ollama's json format usually returns a bare object, but models
    sometimes wrap it in prose or a markdown code fence. Grab the outermost
    {...} span so json.loads has a fighting chance."""
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    return match.group(0) if match else raw


def parse_llm_json(raw: str, schema: type[BaseModel]) -> BaseModel | None:
    try:
        return schema.model_validate(json.loads(_extract_json_object(raw)))
    except (json.JSONDecodeError, ValidationError):
        return None
