"""
Custom exception classes for the content generation pipeline.

This module defines a hierarchy of exceptions that provide clear,
actionable error messages for different failure scenarios.
"""


class ContentGenerationError(Exception):
    """Base exception for all content generation errors."""
    pass


# ============================================================================
# API Errors
# ============================================================================

class APIError(ContentGenerationError):
    """Base class for LLM API failures."""
    pass


class RateLimitError(APIError):
    """Raised when API rate limit is exceeded."""
    
    def __init__(self, message: str = "API rate limit exceeded. Please try again later."):
        super().__init__(message)


class TimeoutError(APIError):
    """Raised when API request times out."""
    
    def __init__(self, message: str = "API request timed out. Please check your connection."):
        super().__init__(message)


class AuthenticationError(APIError):
    """Raised when API authentication fails."""
    
    def __init__(self, message: str = "API authentication failed. Please check your API key."):
        super().__init__(message)


# ============================================================================
# Vector Store Errors
# ============================================================================

class VectorStoreError(ContentGenerationError):
    """Base class for ChromaDB vector store failures."""
    pass


class CollectionNotFoundError(VectorStoreError):
    """Raised when a vector store collection is not found."""
    
    def __init__(self, collection_name: str):
        self.collection_name = collection_name
        super().__init__(f"Vector store collection '{collection_name}' not found. "
                        f"Please run data ingestion first.")


class QueryError(VectorStoreError):
    """Raised when a vector store query fails."""
    
    def __init__(self, message: str = "Vector store query failed."):
        super().__init__(message)


# ============================================================================
# Validation Errors
# ============================================================================

class ValidationError(ContentGenerationError):
    """Base class for output validation failures."""
    pass


class BriefValidationError(ValidationError):
    """Raised when brief JSON validation fails."""
    
    def __init__(self, message: str = "Brief validation failed. Invalid JSON structure."):
        super().__init__(message)


class ContentValidationError(ValidationError):
    """Raised when content quality validation fails."""
    
    def __init__(self, message: str = "Content validation failed. Quality threshold not met."):
        super().__init__(message)


# ============================================================================
# Agent Errors
# ============================================================================

class AgentError(ContentGenerationError):
    """Raised when an agent execution fails."""
    
    def __init__(self, agent_name: str, message: str):
        self.agent_name = agent_name
        super().__init__(f"[{agent_name}] {message}")


class PlannerError(AgentError):
    """Raised when the Planner agent fails."""
    
    def __init__(self, message: str):
        super().__init__("Planner", message)


class ResearcherError(AgentError):
    """Raised when the Researcher agent fails."""
    
    def __init__(self, message: str):
        super().__init__("Researcher", message)


class WriterError(AgentError):
    """Raised when the Writer agent fails."""
    
    def __init__(self, message: str):
        super().__init__("Writer", message)


class EditorError(AgentError):
    """Raised when the Editor agent fails."""
    
    def __init__(self, message: str):
        super().__init__("Editor", message)


class SEOError(AgentError):
    """Raised when the SEO agent fails."""
    
    def __init__(self, message: str):
        super().__init__("SEO", message)
