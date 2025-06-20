# src/chatbot_backend/config.py

import os
import logging

logger = logging.getLogger(__name__)

class Config:
    """
    Configuration class for the Flask application.

    Loads environment variables and defines application-wide settings.
    """
    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB
    ALLOWED_EXTENSIONS = {'pdf'}
    UPLOAD_FOLDER = 'uploads' # This should typically be outside the source code, e.g., in a data directory or cloud storage.
    
    # Ensure upload directory exists
    try:
        os.makedirs(UPLOAD_FOLDER, exist_ok=True)
        logger.info(f"Ensured upload folder '{UPLOAD_FOLDER}' exists.")
    except OSError as e:
        logger.error(f"Error creating upload folder '{UPLOAD_FOLDER}': {e}")

    # EventBot (now ChatbotAgent) related configurations
    # These are directly used by the ChatbotAgent, but defined here for centralized config
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
    PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX")
    PINECONE_CLOUD = os.getenv("PINECONE_CLOUD", "aws")
    PINECONE_REGION = os.getenv("PINECONE_REGION", "us-east-1")

    # Flask specific configs
    FLASK_ENV = os.getenv('FLASK_ENV', 'development')
    DEBUG = FLASK_ENV == 'development'
    PORT = int(os.getenv('PORT', 5000))

    @staticmethod
    def validate_required_env_vars():
        """Validate all required environment variables for the chatbot agent."""
        required_vars = {
            "GEMINI_API_KEY": Config.GEMINI_API_KEY,
            "PINECONE_API_KEY": Config.PINECONE_API_KEY,
            "PINECONE_INDEX": Config.PINECONE_INDEX_NAME
        }
        missing_vars = [var for var, value in required_vars.items() if not value]
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
        logger.info("All required environment variables are present.")

