"""Custom exceptions for the doc-qna application."""


class DocumentProcessingError(Exception):
    """Raised when document ingestion or processing fails."""

    def __init__(self, document_id: str, reason: str) -> None:
        self.document_id = document_id
        self.reason = reason
        super().__init__(f"Failed to process document {document_id}: {reason}")


class UnsupportedFileTypeError(Exception):
    """Raised when an uploaded file has an unsupported extension."""

    def __init__(self, file_type: str) -> None:
        self.file_type = file_type
        super().__init__(f"Unsupported file type: {file_type}")


class ProviderError(Exception):
    """Raised when an LLM or embedder provider call fails."""

    def __init__(self, provider: str, reason: str) -> None:
        self.provider = provider
        self.reason = reason
        super().__init__(f"Provider '{provider}' error: {reason}")


class RetrievalError(Exception):
    """Raised when vector search or retrieval fails."""

    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Retrieval error: {reason}")
