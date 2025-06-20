# src/chatbot_backend/agents/base.py

from abc import ABC, abstractmethod
from typing import Dict, Any

class BaseChatbotAgent(ABC):
    """
    Abstract base class for chatbot agents.

    Defines the common interface that all chatbot agents should implement.
    """

    @abstractmethod
    def __init__(self):
        """
        Initializes the agent.
        Subclasses should implement their specific initialization logic here.
        """
        pass

    @abstractmethod
    def answer_question(self, question: str, **kwargs) -> Dict[str, Any]:
        """
        Answers a given question based on its internal knowledge or capabilities.

        Args:
            question (str): The user's question.
            **kwargs: Additional keyword arguments specific to the agent's implementation
                      (e.g., top_k for retrieval).

        Returns:
            Dict[str, Any]: A dictionary containing the answer and any relevant metadata
                            (e.g., success status, error messages).
        """
        pass

    @abstractmethod
    def upload_data(self, data_source: Any, **kwargs) -> bool:
        """
        Uploads and processes data into the agent's knowledge base.

        Args:
            data_source (Any): The source of the data to be uploaded (e.g., file path, text).
            **kwargs: Additional keyword arguments (e.g., user_id for personalization, document_type).

        Returns:
            bool: True if the data was successfully uploaded and processed, False otherwise.
        """
        pass

    @abstractmethod
    def health_check(self) -> Dict[str, Any]:
        """
        Performs a health check of the agent's components and dependencies.

        Returns:
            Dict[str, Any]: A dictionary indicating the health status of various components
                            and an overall health status.
        """
        pass

