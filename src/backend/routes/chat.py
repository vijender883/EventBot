import os
import tempfile
import logging
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request, UploadFile, File, Depends
from pydantic import BaseModel
from typing import Dict, Any
from werkzeug.utils import secure_filename

logger = logging.getLogger(__name__)

# FastAPI router (equivalent to Flask Blueprint)
router = APIRouter(tags=["chat"])

# Configuration (loaded from src/backend/config.py or environment)


class Config:
    ALLOWED_EXTENSIONS = os.getenv("ALLOWED_EXTENSIONS", "pdf").split(",")
    MAX_FILE_SIZE = int(os.getenv("MAX_FILE_SIZE", 10 * 1024 * 1024))  # 10MB


config = Config()

# Dependency to get ChatbotAgent (injected from app.py or main.py)


def get_chatbot_agent(request: Request):
    chatbot_agent = getattr(request.app.state, "chatbot_agent", None)
    if not chatbot_agent:
        raise HTTPException(
            status_code=500, detail="ChatbotAgent not initialized")
    return chatbot_agent

# Helper functions


def allowed_file(filename: str) -> bool:
    """Check if the uploaded file is allowed based on its extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in config.ALLOWED_EXTENSIONS


def validate_request_size(file: UploadFile) -> bool:
    """Validate file size against MAX_FILE_SIZE."""
    file.file.seek(0, os.SEEK_END)
    size = file.file.tell()
    file.file.seek(0)  # Reset file pointer
    return size <= config.MAX_FILE_SIZE

# Pydantic models for request/response validation


class QueryRequest(BaseModel):
    query: str


class HealthResponse(BaseModel):
    status: str
    message: str = None
    healthy: bool
    health: Dict[str, Any] = None


class AnswerResponse(BaseModel):
    answer: str
    success: bool
    error: str = None


class UploadResponse(BaseModel):
    success: bool
    message: str
    filename: str = None
    error: str = None


class IndexResponse(BaseModel):
    message: str
    version: str
    endpoints: Dict[str, str]


@router.get("/health", response_model=HealthResponse)
async def health_check(chatbot_agent=Depends(get_chatbot_agent)):
    """Health check endpoint for the chatbot service."""
    try:
        health_status = chatbot_agent.health_check()
        return {
            "status": "success",
            "health": health_status,
            "healthy": health_status["overall_health"]
        }
    except Exception as e:
        logger.error(f"Health check endpoint error: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "status": "error",
                "message": str(e),
                "healthy": False
            }
        )


@router.post("/answer", response_model=AnswerResponse)
async def answer_question(request: QueryRequest, chatbot_agent=Depends(get_chatbot_agent)):
    """
    Endpoint to receive a user question and return an answer using the chatbot agent.
    """
    try:
        query = request.query.strip()
        if not query:
            raise HTTPException(
                status_code=400,
                detail={
                    "answer": "Please provide a valid question.",
                    "success": False,
                    "error": "Empty query provided"
                }
            )

        result = chatbot_agent.answer_question(query)
        return {
            "answer": result["answer"],
            "success": True
        }
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in answer endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "answer": "An error occurred while processing your question. Please try again.",
                "success": False,
                "error": str(e)
            }
        )


@router.post("/uploadpdf", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...), chatbot_agent=Depends(get_chatbot_agent)):
    """
    Endpoint to upload and process a PDF file, adding its content to the knowledge base.
    """
    try:
        if not validate_request_size(file):
            raise HTTPException(
                status_code=413,
                detail={
                    "success": False,
                    "message": f"File too large. Maximum size is {config.MAX_FILE_SIZE // (1024*1024)}MB",
                    "error": "File size exceeded"
                }
            )

        if not file.filename:
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "message": "No file selected",
                    "error": "Empty filename"
                }
            )

        if not allowed_file(file.filename):
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "message": "Only PDF files are allowed",
                    "error": "Invalid file type"
                }
            )

        filename = secure_filename(file.filename)
        if not filename:
            raise HTTPException(
                status_code=400,
                detail={
                    "success": False,
                    "message": "Invalid filename",
                    "error": "Filename not secure"
                }
            )

        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_file.write(await file.read())
            temp_file_path = temp_file.name

        try:
            user_id = None
            if 'resume' in filename.lower() or 'cv' in filename.lower():
                user_id = Path(filename).stem

            success = chatbot_agent.upload_data(temp_file_path, user_id)

            if success:
                logger.info(f"Successfully processed PDF upload: {filename}")
                return {
                    "success": True,
                    "message": f"PDF '{filename}' uploaded and processed successfully",
                    "filename": filename
                }
            else:
                logger.warning(f"Failed to process PDF upload: {filename}")
                raise HTTPException(
                    status_code=500,
                    detail={
                        "success": False,
                        "message": "Failed to process the PDF file",
                        "error": "Processing failed"
                    }
                )

        finally:
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                logger.warning(
                    f"Failed to delete temporary file {temp_file_path}: {e}")

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in upload endpoint: {e}")
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": "An error occurred while processing your upload",
                "error": str(e)
            }
        )


@router.get("/", response_model=IndexResponse)
@router.head("/")
async def index():
    """Root endpoint for the API, providing basic information."""
    return {
        "message": "PDF Assistant Chatbot API",
        "version": "1.0.0",
        "endpoints": {
            "/health": "GET - Health check",
            "/answer": "POST - Answer questions",
            "/uploadpdf": "POST - Upload PDF files"
        }
    }
