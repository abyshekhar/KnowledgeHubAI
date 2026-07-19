from __future__ import annotations

import json

from backend.app.application.testgen.schemas import (
    GapAnalysisResult,
    GenerationResult,
    parse_llm_json,
)


def test_parse_llm_json_valid_gap_analysis():
    raw = json.dumps({"ready": True, "questions": [], "assumptions": ["a"]})
    result = parse_llm_json(raw, GapAnalysisResult)
    assert isinstance(result, GapAnalysisResult)
    assert result.ready is True
    assert result.assumptions == ["a"]


def test_parse_llm_json_extracts_object_from_prose_wrapper():
    raw = 'Sure, here is the JSON:\n```json\n{"ready": false, "questions": ["Q1"], "assumptions": []}\n```'
    result = parse_llm_json(raw, GapAnalysisResult)
    assert result is not None
    assert result.questions == ["Q1"]


def test_parse_llm_json_invalid_returns_none():
    assert parse_llm_json("not json at all", GapAnalysisResult) is None


def test_parse_llm_json_schema_mismatch_returns_none():
    raw_bad = json.dumps({"scenarios": [{"test_cases": [{"foo": "bar"}]}]})
    assert parse_llm_json(raw_bad, GenerationResult) is None


def test_generation_result_parses_nested_cases():
    raw = json.dumps(
        {
            "scenarios": [
                {
                    "title": "Login",
                    "description": "desc",
                    "priority": "high",
                    "test_cases": [
                        {
                            "title": "Valid login",
                            "preconditions": "user exists",
                            "steps": ["a", "b"],
                            "expected_result": "success",
                            "priority": "high",
                            "case_type": "positive",
                        }
                    ],
                }
            ],
            "assumptions": [],
        }
    )
    result = parse_llm_json(raw, GenerationResult)
    assert isinstance(result, GenerationResult)
    assert result.scenarios[0].test_cases[0].title == "Valid login"
