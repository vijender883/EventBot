# src/backend/config.py
import logging
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Configure logging based on environment variable
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(level=getattr(logging, log_level),
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class Config:
    def __init__(self):
        # File upload configuration
        self.ALLOWED_EXTENSIONS = os.getenv(
            "ALLOWED_EXTENSIONS", "pdf").split(",")
        self.MAX_FILE_SIZE = int(
            os.getenv("MAX_FILE_SIZE", 10 * 1024 * 1024))  # 10MB
        
        # Flask/FastAPI Configuration
        self.HOST = os.getenv("HOST", "0.0.0.0")  # Added missing HOST
        self.PORT = int(os.getenv("PORT", 5000))
        self.DEBUG = os.getenv("DEBUG", "False").lower() == "true"  # Added missing DEBUG
        self.ENDPOINT = os.getenv("ENDPOINT", f"http://localhost:{self.PORT}")
        
        # Database configuration
        self.DATABASE_USER = os.getenv("DATABASE_USER")
        self.DATABASE_PASSWORD = os.getenv("DATABASE_PASSWORD")
        self.DATABASE_HOST = os.getenv("DATABASE_HOST")
        self.DATABASE_PORT = os.getenv("DATABASE_PORT", "3306")
        self.DATABASE_NAME = os.getenv("DATABASE_NAME")
        
        # Pinecone configuration (updated to match your template)
        self.PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
        self.PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX", "pdf-assistant-index")
        self.PINECONE_CLOUD = os.getenv("PINECONE_CLOUD", "aws")
        self.PINECONE_REGION = os.getenv("PINECONE_REGION", "us-east-1")
        self.PINECONE_DIMENSION = 768  # Matches Google Gemini embedding-001
        
        # Google AI configuration (updated to match your template)
        self.GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

        logger.info("Configuration loaded successfully")

    def validate_database_config(self):
        """Validate database configuration when needed."""
        if not self.DATABASE_PORT.isdigit():
            logger.error(f"Invalid DATABASE_PORT: {self.DATABASE_PORT}")
            raise ValueError("DATABASE_PORT must be a valid integer")
        
        if not all([self.DATABASE_USER, self.DATABASE_PASSWORD, 
                   self.DATABASE_HOST, self.DATABASE_NAME]):
            missing = [key for key, val in {
                'DATABASE_USER': self.DATABASE_USER,
                'DATABASE_PASSWORD': self.DATABASE_PASSWORD,
                'DATABASE_HOST': self.DATABASE_HOST,
                'DATABASE_NAME': self.DATABASE_NAME
            }.items() if not val]
            logger.error(f"Missing required database environment variables: {missing}")
            raise ValueError(f"Missing required database environment variables: {missing}")

    def validate_pinecone_config(self):
        """Validate Pinecone configuration when needed."""
        if not self.PINECONE_API_KEY:
            logger.error("PINECONE_API_KEY environment variable is not set")
            raise ValueError("PINECONE_API_KEY is required")

    def validate_gemini_config(self):
        """Validate Gemini configuration when needed."""
        if not self.GEMINI_API_KEY:
            logger.error("GEMINI_API_KEY environment variable is not set")
            raise ValueError("GEMINI_API_KEY is required")

    @staticmethod
    def validate_required_env_vars():
        """Validate all required environment variables for ChatbotAgent."""
        config_instance = Config()
        config_instance.validate_pinecone_config()
        config_instance.validate_gemini_config()

    @property
    def database_url(self):
        """Get database URL, validating config first."""
        self.validate_database_config()
        return (
            f"mysql+pymysql://{self.DATABASE_USER}:{self.DATABASE_PASSWORD}"
            f"@{self.DATABASE_HOST}:{self.DATABASE_PORT}/{self.DATABASE_NAME}"
            f"?charset=utf8mb4"
        )


# Global config instance
config = Config()