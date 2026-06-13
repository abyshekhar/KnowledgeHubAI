from __future__ import annotations

import pytest

from backend.app.shared.validation import normalize_email_identifier


def test_normalize_email_identifier_allows_internal_local_domain() -> None:
    assert normalize_email_identifier(" Admin@KnowledgeHub.Local ") == "admin@knowledgehub.local"


@pytest.mark.parametrize(
    "value",
    [
        "missing-at-sign",
        "admin@",
        "@knowledgehub.local",
        "admin@knowledgehub",
        "admin @knowledgehub.local",
        "admin@knowledgehub..local",
    ],
)
def test_normalize_email_identifier_rejects_invalid_values(value: str) -> None:
    with pytest.raises(ValueError):
        normalize_email_identifier(value)
