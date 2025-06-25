import os
from typing import List
from dotenv import load_dotenv

load_dotenv()  # Load .env file


class Config:
    ALLOWED_EXTENSIONS = os.getenv("ALLOWED_EXTENSIONS", "pdf").split(",")
    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 10 * 1024 * 1024))  # 10MB
    GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
    PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
    PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME")
    PINECONE_CLOUD = os.getenv("PINECONE_CLOUD")
    PINECONE_REGION = os.getenv("PINECONE_REGION")
    ENDPOINT = os.getenv("ENDPOINT")
    PORT = int(os.getenv("PORT", 5000))
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"

    @staticmethod
    def validate_required_env_vars() -> None:
        """Validate that all required environment variables are set."""
        required_vars = [
            "GEMINI_API_KEY",
            "PINECONE_API_KEY",
            "PINECONE_INDEX_NAME",
            "PINECONE_CLOUD",
            "PINECONE_REGION",
            "ENDPOINT",
        ]
        missing_vars = [
            var for var in required_vars if not os.getenv(var) or os.getenv(var).strip() == ""
        ]
        if missing_vars:
            raise ValueError(
                f"Missing required environment variables: {', '.join(missing_vars)}")
