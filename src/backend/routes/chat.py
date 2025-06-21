# src/backend/routes/chat.py

import os
import tempfile
import logging
from pathlib import Path
from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, Request, Body
from pydantic import BaseModel
from typing import Dict, Any

from ..agents.rag_agent import ChatbotAgent
from ..config import Config


chat_router = APIRouter()
logger = logging.getLogger(__name__)

#pydantic models

class HealthResponse(BaseModel):
    status: str
    health: Dict[str, Any]
    healthy: bool

class AnswerRequest(BaseModel):
    query: str

class AnswerResponse(BaseModel):
    answer: str

class UploadResponse(BaseModel):
    success: bool
    message: str
    filename: str

class ErrorResponse(BaseModel):
    detail: str

# dependency injection

def get_chatbot_agent(request: Request) -> ChatbotAgent:
    """Dependency to get the chatbot agent instance from the app state."""
    agent = request.app.state.chatbot_agent
    if not agent:
        raise HTTPException(status_code=503, detail="Service temporarily unavailable: ChatbotAgent not initialized")
    return agent

def get_config(request: Request) -> Config:
    """Dependency to get the config instance from the app state."""
    return request.app.state.config

#helper functions

def allowed_file(filename: str, config: Config = Depends(get_config)):
    """Check if the uploaded file is allowed based on its extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in config.ALLOWED_EXTENSIONS

# api endpoints

@chat_router.get("/health", response_model=HealthResponse, tags=["Monitoring"])
def health_check(agent: ChatbotAgent = Depends(get_chatbot_agent)):
    """Health check endpoint for the chatbot service."""
    try:
        health_status = agent.health_check()
        return {
            "status": "success",
            "health": health_status,
            "healthy": health_status.get("overall_health", False)
        }
    except Exception as e:
        logger.error(f"Health check endpoint error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@chat_router.post("/answer", response_model=AnswerResponse, tags=["Chat"])
def answer_question(
    request_data: AnswerRequest,
    agent: ChatbotAgent = Depends(get_chatbot_agent)
):
    """
    Endpoint to receive a user question and return an answer.
    """
    try:
        if not request_data.query or not request_data.query.strip():
            raise HTTPException(status_code=400, detail="Empty query provided")
        
        result = agent.answer_question(request_data.query)
        return {"answer": result.get("answer", "No answer found.")}
    except HTTPException as http_exc:
        raise http_exc
    except Exception as e:
        logger.error(f"Error in answer endpoint: {e}")
        raise HTTPException(status_code=500, detail="I apologize, but I encountered an error while processing your question.")

@chat_router.post("/uploadpdf", response_model=UploadResponse, tags=["Data Management"])
async def upload_pdf(
    file: UploadFile = File(...),
    agent: ChatbotAgent = Depends(get_chatbot_agent),
    config: Config = Depends(get_config)
):
    """
    Endpoint to upload and process a PDF file.
    """
    if not file.filename:
        raise HTTPException(status_code=400, detail="No file selected")

    if not allowed_file(file.filename, config):
         raise HTTPException(status_code=400, detail="Only PDF files are allowed")

    # Secure filename is handled by UploadFile, but good to be aware.
    # The filename attribute is sanitized.
    filename = file.filename

    # Handle file size check
    # Note: A middleware is a better place for a robust size check.
    # This is a basic check.
    if file.size and file.size > config.MAX_FILE_SIZE:
        raise HTTPException(status_code=413, detail=f"File too large. Maximum size is {config.MAX_FILE_SIZE // (1024*1024)}MB")

    #save to a temporary file to be processed
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            content = await file.read()
            temp_file.write(content)
            temp_file_path = temp_file.name
    except Exception as e:
        logger.error(f"Failed to save uploaded file temporarily: {e}")
        raise HTTPException(status_code=500, detail="Could not save file for processing.")

    try:
        user_id = None
        if 'resume' in filename.lower() or 'cv' in filename.lower():
            user_id = Path(filename).stem
        
        success = agent.upload_data(temp_file_path, user_id)
        
        if success:
            logger.info(f"Successfully processed PDF upload: {filename}")
            return {
                "success": True,
                "message": f"PDF '{filename}' uploaded and processed successfully",
                "filename": filename
            }
        else:
            logger.warning(f"Failed to process PDF upload: {filename}")
            raise HTTPException(status_code=500, detail="Failed to process the PDF file")
            
    finally:
        #clean up
        try:
            os.unlink(temp_file_path)
        except Exception as e:
            logger.warning(f"Failed to delete temporary file {temp_file_path}: {e}")

@chat_router.get("/", tags=["General"])
def index():
    """Root endpoint for the API, providing basic information."""
    return {
        "message": "PDF Assistant Chatbot API",
        "version": "1.0.0",
        "docs": "/docs",
        "redoc": "/redoc",
        "endpoints": {
            "/health": "GET - Health check",
            "/answer": "POST - Answer questions",
            "/uploadpdf": "POST - Upload PDF files"
        }
    }

