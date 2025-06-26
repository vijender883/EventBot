# src/backend/models.py
"""
Pydantic models for API requests and responses.

This module defines the data models used throughout the FastAPI application
for request validation and response serialization.
"""

from typing import Dict, Optional
from pydantic import BaseModel


class QueryRequest(BaseModel):
    """Request model for chat queries."""
    query: str

    class Config:
        json_schema_extra = {
            "example": {
                "query": "What information is available in the uploaded PDF?"
            }
        }


class AnswerResponse(BaseModel):
    """Response model for chat answers."""
    answer: str
    success: bool
    error: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "answer": "Based on the uploaded PDF...",
                "success": True,
                "error": None
            }
        }


class UploadResponse(BaseModel):
    """Response model for PDF upload operations."""
    success: bool
    message: str
    filename: Optional[str] = None
    tables_stored: Optional[int] = None
    text_chunks_stored: Optional[int] = None
    error: Optional[str] = None

    class Config:
        json_schema_extra = {
            "example": {
                "success": True,
                "message": "PDF processed successfully",
                "filename": "document.pdf",
                "tables_stored": 3,
                "text_chunks_stored": 45,
                "error": None
            }
        }


class IndexResponse(BaseModel):
    """Response model for the root endpoint."""
    message: str
    version: str
    endpoints: Dict[str, str]

    class Config:
        json_schema_extra = {
            "example": {
                "message": "PDF Assistant Chatbot API",
                "version": "1.0.0",
                "endpoints": {
                    "/": "GET, HEAD - Root endpoint",
                    "/answer": "POST - Answer questions",
                    "/uploadpdf": "POST - Upload PDF files"
                }
            }
        }