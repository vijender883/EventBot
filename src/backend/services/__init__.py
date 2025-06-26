"""
Backend services package.

This package contains service layer implementations including
orchestrator and embedding services.
"""

# You can import your existing orchestrator here if needed
# from .orchestrator import YourOrchestratorClass
from .embedding_service import EmbeddingService

__all__ = [
    'EmbeddingService',
    # 'YourOrchestratorClass',  # Uncomment when you want to expose it
]