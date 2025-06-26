# src/backend/services/orchestrator.py

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class Orchestrator:
    """
    Simple, robust orchestrator that can handle missing dependencies.
    """

    def __init__(self, chatbot_agent=None):
        """
        Initialize orchestrator with optional chatbot agent.
        """
        self.chatbot_agent = chatbot_agent
        self.is_functional = chatbot_agent is not None
        
        if self.is_functional:
            logger.info("Orchestrator initialized with functional ChatbotAgent.")
        else:
            logger.warning("Orchestrator initialized without ChatbotAgent - limited functionality.")

    def process_query(self, query: str) -> Dict[str, Any]:
        """
        Process a user query.
        """
        logger.info(f"Processing query: {query[:50]}...")
        
        if not self.is_functional:
            logger.warning("ChatbotAgent not available for query processing")
            return {
                "answer": "Service temporarily unavailable. Please configure PINECONE_API_KEY and GEMINI_API_KEY environment variables to enable AI functionality.",
                "success": False,
                "error": "ChatbotAgent not initialized - missing API configuration"
            }
        
        try:
            logger.info("Delegating query to ChatbotAgent")
            response = self.chatbot_agent.answer_question(query)
            logger.info("Successfully processed query through ChatbotAgent")
            return response
        except Exception as e:
            logger.error(f"Error processing query: {e}", exc_info=True)
            return {
                "answer": "An error occurred while processing your question. Please try again.",
                "success": False,
                "error": str(e)
            }

    def ingest_document(self, file_path: str, user_id: str = None) -> bool:
        """
        Ingest a document.
        """
        if not self.is_functional:
            logger.error("Cannot ingest document: ChatbotAgent not available")
            return False
        
        try:
            return self.chatbot_agent.upload_data(file_path, user_id=user_id)
        except Exception as e:
            logger.error(f"Error ingesting document: {e}", exc_info=True)
            return False

    def get_service_health(self) -> Dict[str, Any]:
        """
        Get service health status.
        """
        if not self.is_functional:
            return {
                "orchestrator": True,
                "chatbot_agent": False,
                "overall_health": False,
                "message": "ChatbotAgent not initialized"
            }
        
        try:
            health = self.chatbot_agent.health_check()
            health["orchestrator"] = True
            return health
        except Exception as e:
            logger.error(f"Error checking health: {e}", exc_info=True)
            return {
                "orchestrator": True,
                "chatbot_agent": False,
                "overall_health": False,
                "error": str(e)
            }