# Services package for external integrations

from .vertex_ai_client import (
    GeminiClient,
    GeminiAPIError,
    MultimodalRequest,
    AIResponse,
    create_gemini_client
)

__all__ = [
    'GeminiClient',
    'GeminiAPIError',
    'MultimodalRequest',
    'AIResponse',
    'create_gemini_client'
]