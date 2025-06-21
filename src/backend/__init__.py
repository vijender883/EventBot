import logging
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
from .agents.rag_agent import ChatbotAgent
from .routes.chat import chat_router
from .config import Config
from .utils.helper import (
    http_exception_handler,
    payload_too_large_handler,
    method_not_allowed_handler,
)
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.exceptions import RequestValidationError

load_dotenv()

#logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_app():
    """
    Creates and configures the FastAPI application.
    """
    app = FastAPI(
        title="EventBot API",
        description="API for the EventBot application, powered by FastAPI.",
        version="1.0.0"
    )

    #CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    #config initialization
    app.state.config = Config()

    try:
        app.state.chatbot_agent = ChatbotAgent()
        logger.info("ChatbotAgent initialized successfully within app context.")
    except Exception as e:
        logger.error(f"Failed to initialize ChatbotAgent: {e}")
        app.state.chatbot_agent = None

    app.include_router(chat_router)

    app.add_exception_handler(StarletteHTTPException, http_exception_handler)
    app.add_exception_handler(405, method_not_allowed_handler)
    app.add_exception_handler(413, payload_too_large_handler)


    logger.info("FastAPI app created and configured.")
    return app