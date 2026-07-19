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


@pytest.mark.asyncio
async def test_add_link_endpoint_with_crawl_options() -> None:
    import json
    session = AsyncMock()
    settings = MagicMock()
    background_tasks = MagicMock()
    user = User(id=1, email="admin@knowledgehub.local")

    request = LinkCreateRequest(
        name="Org Wiki Custom",
        url=HttpUrl("https://example.com/custom"),
        category="Tech",
        depth=2,
        max_pages=5,
        js_render=True,
    )

    res = await add_link(
        request=request,
        background_tasks=background_tasks,
        session=session,
        settings=settings,
        user=user,
    )

    assert res["status"] == "queued"
    session.add.assert_called_once()
    # Extract the added document
    added_doc = session.add.call_args[0][0]
    assert added_doc.name == "Org Wiki Custom"
    assert str(added_doc.path).rstrip("/") == "https://example.com/custom"
    assert added_doc.category == "Tech"
    meta = json.loads(added_doc.tags)
    assert meta["depth"] == 2
    assert meta["max_pages"] == 5
    assert meta["js_render"] is True


@pytest.mark.asyncio
async def test_update_link_endpoint_with_crawl_options() -> None:
    import json
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
        tags='{"depth": 0, "max_pages": 10, "js_render": False}',
    )
    session.get.return_value = doc

    request = LinkUpdateRequest(
        depth=1,
        max_pages=20,
        js_render=True,
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
        meta = json.loads(doc.tags)
        assert meta["depth"] == 1
        assert meta["max_pages"] == 20
        assert meta["js_render"] is True
        session.commit.assert_called_once()
        background_tasks.add_task.assert_called_once()


@pytest.mark.asyncio
@patch("backend.app.application.documents.ingest_document.create_embedding_provider")
@patch("backend.app.application.documents.ingest_document.create_vector_store")
@patch("httpx.AsyncClient")
async def test_ingest_document_link_crawling_loop(mock_httpx_client_class, mock_create_vector_store, mock_create_embedding_provider) -> None:
    from backend.app.config.settings import Settings
    from backend.app.application.documents.ingest_document import IngestDocumentUseCase

    # Setup mock embedding provider
    mock_embeddings_provider = MagicMock()
    mock_embeddings_provider.embed_documents.return_value = [[0.1] * 384, [0.2] * 384]
    mock_create_embedding_provider.return_value = mock_embeddings_provider

    # Setup mock vector store
    mock_store = MagicMock()
    mock_create_vector_store.return_value = mock_store

    # Setup httpx mock
    mock_client = MagicMock()
    mock_httpx_client_class.return_value.__aenter__.return_value = mock_client

    # Define URL responses
    responses = {
        "https://example.com/index": "<html><body>Welcome <a href='https://example.com/page1'>Page 1</a></body></html>",
        "https://example.com/page1": "<html><body>Inside Page 1 <a href='http://127.0.0.1/private'>Private</a></body></html>",
    }

    async def mock_get(url, *args, **kwargs):
        mock_resp = MagicMock()
        mock_resp.text = responses.get(str(url), "<html></html>")
        mock_resp.is_redirect = False
        mock_resp.raise_for_status = MagicMock()
        return mock_resp

    mock_client.get = AsyncMock(side_effect=mock_get)

    # Ingest document setup
    settings = Settings()
    session = AsyncMock()
    doc = Document(
        id=123,
        name="Test Crawl Doc",
        path="https://example.com/index",
        document_type="link",
        status="pending",
        tags='{"depth": 1, "max_pages": 5, "js_render": false}',
        category="General",
        access_level="user",
        uploaded_by_id=1,
    )

    use_case = IngestDocumentUseCase(settings, session)
    await use_case.execute(doc)

    # Verify httpx client mock details
    called_urls = [str(call[0][0]) for call in mock_client.get.call_args_list]
    print(f"DEBUG: called_urls: {called_urls}")
    assert "https://example.com/index" in called_urls
    assert "https://example.com/page1" in called_urls
    assert any("127.0.0.1" in url for url in called_urls) is False

    # Check vector store operations
    mock_store.add_documents.assert_called_once()
    assert doc.status == "indexed"


@pytest.mark.asyncio
@patch("backend.app.application.documents.ingest_document.create_embedding_provider")
@patch("backend.app.application.documents.ingest_document.create_vector_store")
@patch("httpx.AsyncClient")
async def test_ingest_document_link_playwright_fallback(mock_httpx_client_class, mock_create_vector_store, mock_create_embedding_provider) -> None:
    from backend.app.config.settings import Settings
    from backend.app.application.documents.ingest_document import IngestDocumentUseCase

    # Setup mock embedding provider & vector store
    mock_embeddings_provider = MagicMock()
    mock_embeddings_provider.embed_documents.return_value = [[0.1] * 384]
    mock_create_embedding_provider.return_value = mock_embeddings_provider
    mock_store = MagicMock()
    mock_create_vector_store.return_value = mock_store

    # Setup httpx mock
    mock_client = MagicMock()
    mock_httpx_client_class.return_value.__aenter__.return_value = mock_client
    
    mock_resp = MagicMock()
    mock_resp.text = "<html><body>Fallback Page Content</body></html>"
    mock_resp.is_redirect = False
    mock_resp.raise_for_status = MagicMock()
    mock_client.get = AsyncMock(return_value=mock_resp)

    # Setup playwright mock to fail on launch
    with patch("playwright.async_api.async_playwright", side_effect=Exception("Playwright launch failed")):
        settings = Settings()
        session = AsyncMock()
        doc = Document(
            id=124,
            name="Test Playwright Fallback Doc",
            path="https://example.com/playwright",
            document_type="link",
            status="pending",
            tags='{"depth": 0, "max_pages": 5, "js_render": true}',
            category="General",
            access_level="user",
            uploaded_by_id=1,
        )

        use_case = IngestDocumentUseCase(settings, session)
        await use_case.execute(doc)

        # It should fall back to a safe HTTP fetch (redirects/timeout are now
        # configured on the AsyncClient itself, not passed to .get())
        mock_client.get.assert_called_once_with("https://example.com/playwright")
        assert doc.status == "indexed"


