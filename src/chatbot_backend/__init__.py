import logging
from flask import Flask
from flask_cors import CORS
from dotenv import load_dotenv
from .agents.rag_agent import ChatbotAgent 
# Load environment variables early
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app():
    """
    Creates and configures the Flask application.

    This function initializes the Flask app, applies CORS settings,
    and registers blueprints for API routes.
    """
    app = Flask(__name__)
    CORS(app)  # Enable CORS for Streamlit integration or other frontends

    # Load configuration from config.py
    from .config import Config
    app.config.from_object(Config)

    # Initialize the ChatbotAgent (formerly EventBot)
    # This is done here to ensure it's initialized once per app instance
    try:
        app.chatbot_agent = ChatbotAgent()
        logger.info("ChatbotAgent initialized successfully within app context.")
    except Exception as e:
        logger.error(f"Failed to initialize ChatbotAgent: {e}")
        app.chatbot_agent = None # Set to None if initialization fails

    # Register blueprints (routes)
    from .routes.chat import chat_bp
    app.register_blueprint(chat_bp)

    # Register error handlers
    from .utils.helper import not_found, method_not_allowed, payload_too_large
    app.errorhandler(404)(not_found)
    app.errorhandler(405)(method_not_allowed)
    app.errorhandler(413)(payload_too_large)

    logger.info("Flask app created and configured.")
    return app