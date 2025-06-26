# src/backend/services/orchestrator.py

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)

class Orchestrator:
    """
    Orchestrator that can work with either RAG Agent or Manager Agent
    """

    def __init__(self, chatbot_agent=None, manager_agent=None):
        """
        Initialize orchestrator with optional agents.
        
        Args:
            chatbot_agent: Legacy RAG-based chatbot agent
            manager_agent: New LangGraph-based manager agent
        """
        self.chatbot_agent = chatbot_agent
        self.manager_agent = manager_agent
        
        # Determine functionality based on available agents
        self.is_functional = (chatbot_agent is not None) or (manager_agent is not None)
        self.use_manager = manager_agent is not None
        
        if self.use_manager:
            logger.info("Orchestrator initialized with Manager Agent (LangGraph).")
        elif chatbot_agent:
            logger.info("Orchestrator initialized with legacy ChatbotAgent.")
        else:
            logger.warning("Orchestrator initialized without any agents - limited functionality.")

    def process_query(self, query: str) -> Dict[str, Any]:
        """
        Process a user query using the available agent.
        """
        logger.info(f"Processing query: {query[:50]}...")
        
        if not self.is_functional:
            logger.warning("No agents available for query processing")
            return {
                "answer": "Service temporarily unavailable. Please configure PINECONE_API_KEY and GEMINI_API_KEY environment variables to enable AI functionality.",
                "success": False,
                "error": "No agents initialized - missing API configuration"
            }
        
        try:
            if self.use_manager:
                logger.info("Delegating query to Manager Agent")
                response = self.manager_agent.process_query(query)
                logger.info("Successfully processed query through Manager Agent")
                return response
            else:
                logger.info("Delegating query to legacy ChatbotAgent")
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

    def get_service_health(self) -> Dict[str, Any]:
        """
        Get service health status.
        """
        health_status = {
            "orchestrator": True,
            "chatbot_agent": False,
            "manager_agent": False,
            "overall_health": False,
            "active_agent": None
        }
        
        if self.use_manager and self.manager_agent:
            try:
                manager_health = self.manager_agent.health_check()
                health_status["manager_agent"] = manager_health.get("overall_health", False)
                health_status["active_agent"] = "manager"
                health_status["manager_details"] = manager_health
            except Exception as e:
                logger.error(f"Error checking Manager Agent health: {e}", exc_info=True)
                health_status["manager_agent"] = False
        
        elif self.chatbot_agent:
            try:
                chatbot_health = self.chatbot_agent.health_check()
                health_status["chatbot_agent"] = chatbot_health.get("overall_health", False)
                health_status["active_agent"] = "chatbot"
                health_status["chatbot_details"] = chatbot_health
            except Exception as e:
                logger.error(f"Error checking ChatbotAgent health: {e}", exc_info=True)
                health_status["chatbot_agent"] = False
        
        # Overall health is true if any agent is healthy
        health_status["overall_health"] = (
            health_status["manager_agent"] or health_status["chatbot_agent"]
        )
        
        if not health_status["overall_health"]:
            health_status["message"] = "No healthy agents available"
        
        logger.info(f"Service health status: {health_status['overall_health']}")
        return health_status