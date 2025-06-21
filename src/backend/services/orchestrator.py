# src/backend/services/orchestrator.py

import logging
from typing import Dict, Any

from ..agents.rag_agent import ChatbotAgent # Import the specific agent

logger = logging.getLogger(__name__)

class Orchestrator:
    """
    Orchestrates interactions between different agents or services.

    For this initial setup, it primarily wraps the ChatbotAgent,
    but it's designed to be extensible for multi-agent scenarios.
    """

    def __init__(self, chatbot_agent: ChatbotAgent):
        """
        Initializes the Orchestrator with an instance of ChatbotAgent.

        Args:
            chatbot_agent (ChatbotAgent): An initialized instance of the ChatbotAgent.
        """
        if not isinstance(chatbot_agent, ChatbotAgent):
            raise TypeError("Provided agent is not an instance of ChatbotAgent.")
        self.chatbot_agent = chatbot_agent
        logger.info("Orchestrator initialized with ChatbotAgent.")

    def process_query(self, query: str) -> Dict[str, Any]:
        """
        Processes a user query by delegating it to the appropriate agent.

        In this version, it simply calls the ChatbotAgent's answer_question method.
        Future versions could add logic to:
        - Determine intent (e.g., event question vs. resume question)
        - Route to different specialized agents
        - Combine responses from multiple agents
        - Handle conversational context

        Args:
            query (str): The user's question.

        Returns:
            Dict[str, Any]: The response from the delegated agent.
        """
        logger.info(f"Orchestrating query: {query[:50]}...")
        # For now, directly use the chatbot agent
        response = self.chatbot_agent.answer_question(query)
        return response

    def ingest_document(self, file_path: str, user_id: str = None) -> bool:
        """
        Ingests a document by delegating to the appropriate agent.

        Args:
            file_path (str): The path to the document file.
            user_id (str, optional): An identifier for the user associated with the document.
                                     Defaults to None.

        Returns:
            bool: True if ingestion was successful, False otherwise.
        """
        logger.info(f"Orchestrating document ingestion for: {file_path}")
        # For now, directly use the chatbot agent's upload_data method
        success = self.chatbot_agent.upload_data(file_path, user_id=user_id)
        return success

    def get_service_health(self) -> Dict[str, Any]:
        """
        Checks the health of the underlying chatbot agent and other services.
        """
        logger.info("Checking service health via orchestrator.")
        return self.chatbot_agent.health_check()

