from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi import HTTPException
from pydantic import HttpUrl

from backend.app.infrastructure.database.models import Document, User
from backend.app.infrastructure.documents.parsers import WebHTMLParser
from backend.app.presentation.api.routes.documents import (
    LinkCreateRequest,
    LinkUpdateRequest,
    add_link,
    list_documents,
    update_link,
)


def test_web_html_parser() -> None:
    html = """
    <html>
        <head>
            <title>My Cool Page</title>
            <style>body { color: red; }</style>
            <script>console.log("hello");</script>
        </head>
        <body>
            <header>
                <nav>
                    <a href="/home">Home</a>
                </nav>
            </header>
            <main>
                <h1>Welcome to the Page</h1>
                <p>This is the first paragraph. It has some useful info.</p>
                <div>Here is some other content in a div.</div>
            </main>
            <footer>
                <p>&copy; 2026 Organization</p>
            </footer>
        </body>
    </html>
    """
    parser = WebHTMLParser()
    parser.feed(html)

    # Title should be extracted
    assert parser.title.strip() == "My Cool Page"

    # Ignored tags (style, script, nav, header, footer) should NOT be present in text
    text = parser.get_text()
    assert "body { color: red; }" not in text
    assert "console.log" not in text
    assert "Home" not in text
    assert "Organization" not in text

    # Body tags (h1, p, div) should be extracted and normalized
    assert "Welcome to the Page" in text
    assert "This is the first paragraph. It has some useful info." in text
    assert "Here is some other content in a div." in text


@pytest.mark.asyncio
async def test_add_link_endpoint() -> None:
    session = AsyncMock()
    settings = MagicMock()
    background_tasks = MagicMock()
    user = User(id=1, email="admin@knowledgehub.local")

    request = LinkCreateRequest(
        name="Org Wiki",
        url=HttpUrl("https://example.com/index"),
        category="General",
    )

    res = await add_link(
        request=request,
        background_tasks=background_tasks,
        session=session,
        settings=settings,
        user=user,
    )

    assert res["status"] == "queued"
    assert isinstance(res["id"], int) or res["id"] is None
    session.add.assert_called_once()
    session.commit.assert_called_once()
    background_tasks.add_task.assert_called_once()


@pytest.mark.asyncio
async def test_add_link_endpoint_rejects_loopback() -> None:
    session = AsyncMock()
    settings = MagicMock()
    background_tasks = MagicMock()
    user = User(id=1, email="admin@knowledgehub.local")

    # SSRF loopback URL
    request = LinkCreateRequest(
        name="Local API",
        url=HttpUrl("http://localhost:8000/admin"),
        category="General",
    )

    with pytest.raises(HTTPException) as exc_info:
        await add_link(
            request=request,
            background_tasks=background_tasks,
            session=session,
            settings=settings,
            user=user,
        )

    assert exc_info.value.status_code == 400
    assert "Localhost domains are not allowed" in exc_info.value.detail
    session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_update_link_endpoint_success() -> None:
    session = AsyncMock()
    settings = MagicMock()
    background_tasks = MagicMock()

    doc = Document(
        id=1,
        name="Org Link",
        path="https://example.com/index",
        document_type="link",
        status="indexed",
        category="General",
    )
    session.get.return_value = doc

    request = LinkUpdateRequest(
        name="Updated Link Name",
        url=HttpUrl("https://example.com/new-path"),
        category="Engineering",
    )

    with patch("backend.app.infrastructure.vectorstores.factory.create_vector_store") as mock_vector_store_factory:
        mock_store = MagicMock()
        mock_vector_store_factory.return_value = mock_store

        res = await update_link(
            document_id=1,
            request=request,
            background_tasks=background_tasks,
            session=session,
            settings=settings,
        )

        assert res["status"] == "pending"
        assert doc.name == "Updated Link Name"
        assert doc.path == "https://example.com/new-path"
        assert doc.category == "Engineering"

        mock_store.delete_document.assert_called_once_with("Org Link")
        session.commit.assert_called_once()
        background_tasks.add_task.assert_called_once()


@pytest.mark.asyncio
async def test_update_link_endpoint_not_found() -> None:
    session = AsyncMock()
    settings = MagicMock()
    background_tasks = MagicMock()

    session.get.return_value = None

    request = LinkUpdateRequest(name="Name")
    with pytest.raises(HTTPException) as exc_info:
        await update_link(
            document_id=99,
            request=request,
            background_tasks=background_tasks,
            session=session,
            settings=settings,
        )

    assert exc_info.value.status_code == 404
    session.commit.assert_not_called()


@pytest.mark.asyncio
async def test_list_documents_includes_path() -> None:
    session = AsyncMock()
    user = User(id=1, email="admin@knowledgehub.local")

    doc = Document(
        id=1,
        name="DocA",
        path="data/uploads/DocA.pdf",
        document_type="pdf",
        status="indexed",
        category="General",
        access_level="user",
    )

    scalars_mock = MagicMock()
    scalars_mock.all.return_value = [doc]
    session.scalars.return_value = scalars_mock

    res = await list_documents(session=session, user=user)
    assert len(res) == 1
    assert res[0]["name"] == "DocA"
    assert res[0]["path"] == "data/uploads/DocA.pdf"

