# src/backend/utils/upload_pdf.py

import logging
import os
import tempfile
from pathlib import Path
from fastapi import HTTPException, UploadFile
from werkzeug.utils import secure_filename

from ..utils.pdf_processor import PDFProcessor
from ..services.embedding_service import EmbeddingService
from ..config import config

logger = logging.getLogger(__name__)


def allowed_file(filename: str) -> bool:
    """Check if the uploaded file has an allowed extension."""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in config.ALLOWED_EXTENSIONS


def validate_file_size(file: UploadFile) -> bool:
    """Validate that the uploaded file size is within limits."""
    file.file.seek(0, os.SEEK_END)
    size = file.file.tell()
    file.file.seek(0)
    logger.info(f"File size: {size} bytes, Max allowed: {config.MAX_FILE_SIZE} bytes")
    print(f"File size: {size} bytes, Max allowed: {config.MAX_FILE_SIZE} bytes")
    return size <= config.MAX_FILE_SIZE


async def process_pdf_upload(file: UploadFile) -> dict:
    """
    Process uploaded PDF file: extract content, store tables in MySQL, 
    and store text embeddings in Pinecone.
    
    Returns:
        dict: Processing results with success status, message, and counts
    """
    filename = "unknown"  # Default value to avoid UnboundLocalError
    
    try:
        # Validate file size
        if not validate_file_size(file):
            logger.warning(f"File size exceeds limit: {config.MAX_FILE_SIZE // (1024*1024)}MB")
            print(f"Error: File size exceeds limit: {config.MAX_FILE_SIZE // (1024*1024)}MB")
            raise HTTPException(
                status_code=413, 
                detail={
                    "success": False,
                    "message": f"File size exceeds {config.MAX_FILE_SIZE // (1024*1024)}MB",
                    "error": "File too large"
                }
            )

        # Validate filename
        if not file.filename:
            logger.warning("No file selected")
            print("Error: No file selected")
            raise HTTPException(
                status_code=400, 
                detail={
                    "success": False,
                    "message": "No file selected",
                    "error": "Empty filename"
                }
            )

        # Validate file type
        if not allowed_file(file.filename):
            logger.warning(f"Invalid file type: {file.filename}")
            print(f"Error: Invalid file type: {file.filename}")
            raise HTTPException(
                status_code=400, 
                detail={
                    "success": False,
                    "message": "Only PDF files are allowed",
                    "error": "Invalid file type"
                }
            )

        filename = secure_filename(file.filename)
        logger.info(f"Processing uploaded file: {filename}")
        print(f"Processing uploaded file: {filename}")

        # Initialize processors
        pdf_processor = PDFProcessor()  # Will get database_url from config internally
        
        # Initialize embedding service
        config.validate_pinecone_config()
        config.validate_gemini_config()
        
        pinecone_config = {
            'api_key': config.PINECONE_API_KEY,
            'index_name': config.PINECONE_INDEX_NAME,
            'dimension': config.PINECONE_DIMENSION,
            'cloud': config.PINECONE_CLOUD,
            'region': config.PINECONE_REGION
        }
        embedding_service = EmbeddingService(config.GEMINI_API_KEY, pinecone_config)

        # Create temporary file
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            temp_file.write(await file.read())
            temp_file_path = temp_file.name
            logger.info(f"Temporary file created: {temp_file_path}")
            print(f"Temporary file created: {temp_file_path}")

        try:
            # Extract content from PDF
            content = pdf_processor.extract_content(temp_file_path)

            # Store text embeddings in Pinecone using Google Gemini
            text_chunks_stored = embedding_service.store_text_embeddings(
                content["text_chunks"], filename
            )

            # Store tables in MySQL
            tables_stored = 0
            for i, table in enumerate(content["tables"], 1):
                table_name = content["table_names"][i-1]
                logger.info(f"Attempting to store table {table_name}")
                print(f"Raw Table Data (first 3 rows): {table[:3] if table else 'Empty'}")
                if pdf_processor.store_table(table, table_name):
                    tables_stored += 1

            return {
                "success": True,
                "message": "PDF tables stored in MySQL and text stored in Pinecone successfully",
                "filename": filename,
                "tables_stored": tables_stored,
                "text_chunks_stored": text_chunks_stored
            }

        finally:
            # Clean up temporary file
            try:
                os.unlink(temp_file_path)
                logger.info(f"Deleted temporary file: {temp_file_path}")
                print(f"Deleted temporary file: {temp_file_path}")
            except Exception as e:
                logger.warning(f"Failed to delete temporary file {temp_file_path}: {str(e)}")
                print(f"Error: Failed to delete temporary file {temp_file_path}: {str(e)}")

    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Upload error: {str(e)}")
        print(f"Error: Failed to process PDF '{filename}': {str(e)}")
        raise HTTPException(
            status_code=500, 
            detail={
                "success": False,
                "message": "Failed to process PDF",
                "error": str(e)
            }
        )