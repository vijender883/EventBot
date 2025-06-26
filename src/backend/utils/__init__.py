"""
Backend utilities and service initialization module.

This module provides initialization functions for core services
used throughout the PDF processing application.
"""

import logging
from ..config import config
from ..services.embedding_service import EmbeddingService

logger = logging.getLogger(__name__)


def initialize_embedding_service() -> EmbeddingService:
    """
    Initialize and return the embedding service with Google Gemini.
    
    Returns:
        EmbeddingService: Configured embedding service instance
        
    Raises:
        RuntimeError: If initialization fails
    """
    try:
        # Validate required configurations
        config.validate_pinecone_config()
        config.validate_gemini_config()
        
        pinecone_config = {
            'api_key': config.PINECONE_API_KEY,
            'index_name': config.PINECONE_INDEX_NAME,
            'dimension': config.PINECONE_DIMENSION,
            'cloud': config.PINECONE_CLOUD,
            'region': config.PINECONE_REGION
        }
        
        embedding_service = EmbeddingService(config.GEMINI_API_KEY, pinecone_config)
        logger.info("Embedding service initialized successfully")
        return embedding_service
        
    except Exception as e:
        logger.error(f"Failed to initialize embedding service: {str(e)}")
        raise RuntimeError(f"Embedding service initialization failed: {str(e)}")


__all__ = [
    'initialize_embedding_service',
]