from __future__ import annotations

import json
from pathlib import Path

from sqlalchemy.ext.asyncio import AsyncSession

from backend.app.config.settings import Settings
from backend.app.infrastructure.database.models import Chunk, Document
from backend.app.infrastructure.documents.chunking import Chunker
from backend.app.infrastructure.documents.cleaning import clean_pages
from backend.app.infrastructure.documents.parsers import DocumentParser, ParsedPage
from backend.app.infrastructure.embeddings.providers import create_embedding_provider
from backend.app.infrastructure.vectorstores.factory import create_vector_store


class IngestDocumentUseCase:
    def __init__(self, settings: Settings, session: AsyncSession) -> None:
        self.settings = settings
        self.session = session

    async def execute(self, document: Document) -> None:
        if document.document_type == "link":
            import re
            from urllib.parse import urljoin, urlparse
            import httpx
            from backend.app.infrastructure.documents.parsers import WebHTMLParser
            from backend.app.shared.validation import validate_url_security

            # Parse metadata parameters from tags
            try:
                meta = json.loads(document.tags)
                depth = meta.get("depth", 0)
                max_pages = meta.get("max_pages", 10)
                js_render = meta.get("js_render", False)
            except Exception as e:
                print(f"DEBUG: Exception parsing tags: {e}, document.tags: {document.tags}")
                depth = 0
                max_pages = 10
                js_render = False

            visited = set()
            queue = [(document.path, 0)]
            parsed = []

            base_parsed = urlparse(document.path)
            base_domain = base_parsed.netloc

            while queue and len(visited) < max_pages:
                url, curr_depth = queue.pop(0)
                if url in visited:
                    continue
                visited.add(url)

                try:
                    html_content = ""
                    if js_render:
                        try:
                            from playwright.async_api import async_playwright
                            async with async_playwright() as p:
                                browser = await p.chromium.launch(headless=True)
                                page = await browser.new_page()
                                await page.goto(url, wait_until="networkidle", timeout=15000)
                                html_content = await page.content()
                                await browser.close()
                        except Exception as js_err:
                            # Fallback to standard httpx if playwright fails
                            async with httpx.AsyncClient() as client:
                                response = await client.get(url, follow_redirects=True, timeout=12.0)
                                response.raise_for_status()
                                html_content = response.text
                    else:
                        async with httpx.AsyncClient() as client:
                            response = await client.get(url, follow_redirects=True, timeout=12.0)
                            response.raise_for_status()
                            html_content = response.text

                    parser = WebHTMLParser()
                    parser.feed(html_content)
                    text = parser.get_text()
                    title = parser.title.strip() or f"Page {len(visited)}"
                    parsed.append(ParsedPage(text=text, section=title))

                    # If we need to go deeper, extract links from the parsed page
                    if curr_depth < depth:
                        links = re.findall(r'href=["\'](.*?)["\']', html_content)
                        for link in links:
                            full_url = urljoin(url, link)
                            link_parsed = urlparse(full_url)
                            if link_parsed.netloc == base_domain and link_parsed.scheme in ("http", "https"):
                                clean_url = full_url.split("#")[0]
                                if clean_url not in visited:
                                    try:
                                        validate_url_security(clean_url)
                                        queue.append((clean_url, curr_depth + 1))
                                    except ValueError:
                                        pass  # skip loopback or private sublinks
                except Exception as page_err:
                    # If the base URL fails, we raise so it registers as failed.
                    # If nested links fail, we skip them and continue.
                    if len(visited) <= 1:
                        raise ValueError(f"Failed to load URL {url}: {str(page_err)}") from page_err
                    else:
                        continue
        else:
            parser = DocumentParser()
            parsed = parser.parse(Path(document.path))
        cleaned_text = clean_pages([page.text for page in parsed])
        cleaned_pages = [
            ParsedPage(text=text, page_number=page.page_number, section=page.section)
            for text, page in zip(cleaned_text, parsed, strict=False)
        ]
        chunks = Chunker(self.settings.chunking).chunk(
            cleaned_pages,
            document.name,
            document.document_type,
        )
        if not chunks:
            raise ValueError("No indexable text could be extracted from this document.")
        chunks = [
            type(chunk)(
                text=chunk.text,
                document_name=chunk.document_name,
                document_type=chunk.document_type,
                page_number=chunk.page_number,
                section=chunk.section,
                metadata={
                    **chunk.metadata,
                    "access_level": document.access_level,
                    "category": document.category,
                    "uploaded_by": str(document.uploaded_by_id or ""),
                    "uploaded_date": str(document.created_at or ""),
                },
            )
            for chunk in chunks
        ]
        embedding_provider = create_embedding_provider(self.settings.embeddings)
        embeddings = embedding_provider.embed_documents([chunk.text for chunk in chunks])
        vector_store = create_vector_store(self.settings.vector_store)
        vector_store.add_documents(chunks, embeddings)

        for index, chunk in enumerate(chunks):
            self.session.add(
                Chunk(
                    document_id=document.id,
                    text=chunk.text,
                    page_number=chunk.page_number,
                    section=chunk.section,
                    vector_id=f"{document.id}:{index}",
                    metadata_json=json.dumps(chunk.metadata),
                )
            )
        document.status = "indexed"
        await self.session.commit()
