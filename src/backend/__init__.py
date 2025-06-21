import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse
from .agents.rag_agent import ChatbotAgent
from .services.orchestrator import Orchestrator
from .routes.chat import router
from .config import Config

logger = logging.getLogger(__name__)


def create_app():
    """
    Creates and configures the FastAPI application.

    Initializes the FastAPI app, applies CORS settings, loads configuration,
    initializes the ChatbotAgent and Orchestrator, includes API routers,
    and registers error handlers.
    """
    app = FastAPI(
        title="PDF Assistant Chatbot API",
        version="1.0.0",
        description="API for uploading and querying PDF documents with text and table retrieval."
    )

    # Enable CORS for Streamlit integration
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["http://localhost:8501"],  # Streamlit frontend
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Load configuration
    app.config = Config()
    if not app.config.GEMINI_API_KEY or not app.config.PINECONE_API_KEY:
        logger.error(
            "Missing required environment variables: GEMINI_API_KEY or PINECONE_API_KEY")
        raise ValueError("Missing required environment variables")

    # Initialize ChatbotAgent and Orchestrator
    try:
        app.state.chatbot_agent = ChatbotAgent()
        app.state.orchestrator = Orchestrator(app.state.chatbot_agent)
        logger.info(
            "ChatbotAgent and Orchestrator initialized successfully within app context.")
    except Exception as e:
        logger.error(f"Failed to initialize ChatbotAgent: {e}")
        app.state.chatbot_agent = None
        app.state.orchestrator = None

    # Include API router
    app.include_router(router)

    # Register error handlers
    @app.exception_handler(404)
    async def not_found(request: Request, exc):
        logger.warning(f"404 Not Found: {request.url}")
        return JSONResponse(
            status_code=404,
            content={"success": False, "message": "Resource not found",
                     "error": "404 Not Found"}
        )

    @app.exception_handler(405)
    async def method_not_allowed(request: Request, exc):
        logger.warning(f"405 Method Not Allowed: {request.url}")
        return JSONResponse(
            status_code=405,
            content={"success": False, "message": "Method not allowed",
                     "error": "405 Method Not Allowed"}
        )

    @app.exception_handler(413)
    async def payload_too_large(request: Request, exc):
        logger.warning(f"413 Payload Too Large: {request.url}")
        return JSONResponse(
            status_code=413,
            content={
                "success": False,
                "message": f"File too large. Maximum size is {app.config.MAX_FILE_SIZE // (1024*1024)}MB",
                "error": "413 Payload Too Large"
            }
        )

    logger.info("FastAPI app created and configured.")
    return app
