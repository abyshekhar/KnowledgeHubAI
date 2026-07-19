from __future__ import annotations

import re
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException

from backend.app.infrastructure.database.models import User
from backend.app.presentation.api.dependencies import get_current_user

router = APIRouter()

_README_PATH = Path("README.md")
_CENTERED_HTML_BLOCK = re.compile(r'<p align="center">.*?</p>\s*', re.DOTALL)
_LEADING_TITLE = re.compile(r"^#\s+KnowledgeHub AI\s*\n")


@router.get("/guide")
async def get_help_guide(user: Annotated[User, Depends(get_current_user)]) -> dict:
    del user  # authenticated access check only, no role restriction
    if not _README_PATH.exists():
        raise HTTPException(status_code=404, detail="Help guide is not available.")
    raw = _README_PATH.read_text(encoding="utf-8")
    # The README's centered banner/nav-pill/badge blocks are raw HTML that
    # doesn't render meaningfully in the in-app markdown viewer, and the
    # leading title duplicates the page's own header.
    content = _LEADING_TITLE.sub("", raw, count=1)
    content = _CENTERED_HTML_BLOCK.sub("", content)
    return {"content": content.strip()}
