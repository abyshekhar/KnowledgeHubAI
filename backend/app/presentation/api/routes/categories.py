from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.infrastructure.database.models import Category
from backend.app.presentation.api.dependencies import get_session, require_roles

router = APIRouter()


class CategoryCreate(BaseModel):
    name: str
    description: str | None = None


@router.get("")
async def list_categories(session: Annotated[AsyncSession, Depends(get_session)]) -> list[dict]:
    categories = (await session.scalars(select(Category).order_by(Category.name))).all()
    return [
        {
            "id": cat.id,
            "name": cat.name,
            "description": cat.description,
        }
        for cat in categories
    ]


@router.post("", dependencies=[Depends(require_roles("admin"))])
async def create_category(
    payload: CategoryCreate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict:
    existing = await session.scalar(select(Category).where(Category.name == payload.name))
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Category already exists"
        )
    
    category = Category(
        name=payload.name,
        description=payload.description,
    )
    session.add(category)
    await session.commit()
    await session.refresh(category)
    return {"id": category.id, "name": category.name, "description": category.description}


class CategoryUpdate(BaseModel):
    name: str | None = None
    description: str | None = None


@router.put("/{category_id}", dependencies=[Depends(require_roles("admin"))])
async def update_category(
    category_id: int,
    payload: CategoryUpdate,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, str]:
    category = await session.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    
    if payload.name is not None:
        existing = await session.scalar(
            select(Category).where(Category.name == payload.name, Category.id != category_id)
        )
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Category name already exists"
            )
        category.name = payload.name
        
    if payload.description is not None:
        category.description = payload.description
        
    await session.commit()
    return {"status": "ok"}


@router.delete("/{category_id}", dependencies=[Depends(require_roles("admin"))])
async def delete_category(
    category_id: int,
    session: Annotated[AsyncSession, Depends(get_session)],
) -> dict[str, str]:
    category = await session.get(Category, category_id)
    if category is None:
        raise HTTPException(status_code=404, detail="Category not found")
    
    await session.delete(category)
    await session.commit()
    return {"status": "ok"}
