from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class DocumentChunk:
    text: str
    document_name: str
    document_type: str
    page_number: int | None = None
    section: str | None = None
    metadata: dict[str, str | int | None] = field(default_factory=dict)

