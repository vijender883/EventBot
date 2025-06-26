# src/backend/__init__.py
import logging
import traceback
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from .routes.chat import router as chat_router
from .config import Config
from .utils.helper import (
    http_exception_handler,
    payload_too_large_handler,
    method_not_allowed_handler,
)
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exceptions import RequestValidationError

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app():
    """
    Creates and configures the FastAPI application.
    """
    logger.info("Starting FastAPI application creation...")
    
    app = FastAPI(
        title="EventBot API",
        description="API for the EventBot application, powered by FastAPI.",
        version="1.0.0"
    )

    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    logger.info("CORS middleware added")

    # Config initialization
    try:
        app.state.config = Config()
        logger.info("Config initialized successfully")
    except Exception as e:
        logger.error(f"Failed to initialize config: {e}", exc_info=True)
        raise

    # Initialize services with detailed logging
    chatbot_agent = None
    orchestrator = None
    
    try:
        logger.info("Attempting to import and initialize services...")
        
        # Import orchestrator first (simpler)
        try:
            from .services.orchestrator import Orchestrator
            logger.info("Successfully imported Orchestrator")
        except Exception as e:
            logger.error(f"Failed to import Orchestrator: {e}", exc_info=True)
            raise
        
        # Try to import and initialize ChatbotAgent
        try:
            logger.info("Attempting to import ChatbotAgent...")
            from .agents.rag_agent import ChatbotAgent
            logger.info("Successfully imported ChatbotAgent")
            
            logger.info("Attempting to initialize ChatbotAgent...")
            chatbot_agent = ChatbotAgent()
            logger.info("Successfully initialized ChatbotAgent")
            
        except ValueError as e:
            logger.warning(f"ChatbotAgent initialization failed due to configuration: {e}")
            chatbot_agent = None
        except Exception as e:
            logger.error(f"ChatbotAgent initialization failed with unexpected error: {e}", exc_info=True)
            chatbot_agent = None
        
        # Initialize orchestrator (always succeeds)
        try:
            logger.info("Initializing Orchestrator...")
            orchestrator = Orchestrator(chatbot_agent)
            logger.info("Successfully initialized Orchestrator")
        except Exception as e:
            logger.error(f"Failed to initialize Orchestrator: {e}", exc_info=True)
            # Create a minimal fallback orchestrator
            orchestrator = Orchestrator(None)
            logger.info("Created fallback Orchestrator")
        
        # Set app state
        app.state.chatbot_agent = chatbot_agent
        app.state.orchestrator = orchestrator
        
        if chatbot_agent:
            logger.info("✅ Full functionality available - ChatbotAgent and Orchestrator ready")
        else:
            logger.info("⚠️  Limited functionality - Orchestrator ready but ChatbotAgent unavailable")
            
    except Exception as e:
        logger.error(f"Critical error during service initialization: {e}", exc_info=True)
        # Set minimal state to prevent crashes
        app.state.chatbot_agent = None
        app.state.orchestrator = None

    # Add routes
    try:
        app.include_router(chat_router)
        logger.info("Chat router added successfully")
    except Exception as e:
        logger.error(f"Failed to add chat router: {e}", exc_info=True)
        raise

    # Add exception handlers
    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(405, method_not_allowed_handler)
    app.add_exception_handler(413, payload_too_large_handler)

    logger.info("FastAPI app created and configured successfully.")
    return app