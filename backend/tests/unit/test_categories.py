from __future__ import annotations

import pytest
from fastapi import HTTPException
from unittest.mock import AsyncMock, MagicMock

from backend.app.infrastructure.database.models import Category
from backend.app.presentation.api.routes.categories import list_categories, create_category, delete_category, CategoryCreate


@pytest.mark.asyncio
async def test_list_categories() -> None:
    session = AsyncMock()
    cat1 = Category(name="CatA", description="DescA")
    cat2 = Category(name="CatB", description="DescB")
    
    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [cat1, cat2]
    session.scalars.return_value = scalars_mock
    
    res = await list_categories(session)
    assert len(res) == 2
    assert res[0]["name"] == "CatA"
    assert res[1]["name"] == "CatB"


@pytest.mark.asyncio
async def test_create_category_success() -> None:
    session = AsyncMock()
    session.scalar.return_value = None
    
    payload = CategoryCreate(name="NewCat", description="NewDesc")
    res = await create_category(payload, session)
    assert res["name"] == "NewCat"
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_create_category_conflict() -> None:
    session = AsyncMock()
    session.scalar.return_value = Category(name="Exist", description="ExistDesc")
    
    payload = CategoryCreate(name="Exist", description="ExistDesc")
    with pytest.raises(HTTPException) as exc_info:
        await create_category(payload, session)
        
    assert exc_info.value.status_code == 409
    assert exc_info.value.detail == "Category already exists"
    session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_delete_category_success() -> None:
    session = AsyncMock()
    cat = Category(name="CatToDelete")
    session.get.return_value = cat
    
    res = await delete_category(category_id=1, session=session)
    assert res == {"status": "ok"}
    session.delete.assert_called_once_with(cat)
    session.commit.assert_called_once()


@pytest.mark.asyncio
async def test_delete_category_not_found() -> None:
    session = AsyncMock()
    session.get.return_value = None
    
    with pytest.raises(HTTPException) as exc_info:
        await delete_category(category_id=1, session=session)
        
    assert exc_info.value.status_code == 404
    session.commit.assert_not_called()
