from __future__ import annotations


class KnowledgeHubError(Exception):
    pass


class LowConfidenceError(KnowledgeHubError):
    pass


class NotFoundError(KnowledgeHubError):
    pass


class NotAuthorizedError(KnowledgeHubError):
    pass

