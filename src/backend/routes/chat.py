import logging
from fastapi import APIRouter, HTTPException, UploadFile, File

from ..models import QueryRequest, AnswerResponse, UploadResponse, IndexResponse
from ..utils.upload_pdf import process_pdf_upload

# Configure logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# FastAPI router
router = APIRouter(tags=["pdf_processing"])


@router.get("/", response_model=IndexResponse)
@router.head("/")
async def index():
    """Root endpoint for the API."""
    logger.info("Accessed root endpoint")
    print("Accessed root endpoint")
    return {
        "message": "PDF Assistant Chatbot API",
        "version": "1.0.0",
        "endpoints": {
            "/": "GET, HEAD - Root endpoint",
            "/answer": "POST - Answer questions",
            "/uploadpdf": "POST - Upload PDF files"
        }
    }


@router.post("/answer", response_model=AnswerResponse)
async def answer_question(
    request: QueryRequest, 
    # Dependency injection will be handled by orchestrator.py
):
    """Endpoint to receive a user question and return an answer."""
    try:
        query = request.query.strip()
        if not query:
            logger.warning("Empty query provided")
            print("Error: Empty query provided")
            raise HTTPException(
                status_code=400,
                detail={
                    "answer": "Please provide a valid question.",
                    "success": False,
                    "error": "Empty query provided"
                }
            )
        
        # TODO: Import and use your orchestrator service here
        # from ..services.orchestrator import orchestrator
        # result = orchestrator.answer_question(query)
        
        # For now, return a placeholder response
        result = {"answer": "Please integrate with your orchestrator service"}
        
        logger.info(f"Answered query: {query}")
        print(f"Answered query: {query}")
        
        return {
            "answer": result["answer"],
            "success": True
        }
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Error in answer endpoint: {str(e)}")
        print(f"Error: Answer endpoint failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "answer": "An error occurred while processing your question.",
                "success": False,
                "error": str(e)
            }
        )


@router.post("/uploadpdf", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...)):
    """
    Upload and process a PDF file, storing text in Pinecone and tables in MySQL.
    
    This endpoint:
    1. Validates the uploaded file (size, type, etc.)
    2. Extracts text and tables from the PDF
    3. Stores text chunks as embeddings in Pinecone using Google Gemini
    4. Stores tables in MySQL database
    """
    try:
        result = await process_pdf_upload(file)
        logger.info(f"Successfully processed PDF: {result.get('filename', 'unknown')}")
        return result
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in upload endpoint: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": "An unexpected error occurred during PDF processing",
                "error": str(e)
            }
        )