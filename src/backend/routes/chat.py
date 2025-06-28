# src/backend/routes/chat.py
import logging
import traceback
from fastapi import APIRouter, HTTPException, UploadFile, File, Request

from ..services.clear_data_service import clear_data_service
from ..models import QueryRequest, AnswerResponse, UploadResponse, IndexResponse, ClearDataResponse 

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
    return {
        "message": "PDF Assistant Chatbot API",
        "version": "1.0.0",
        "endpoints": {
            "/": "GET, HEAD - Root endpoint",
            "/answer": "POST - Answer questions",
            "/uploadpdf": "POST - Upload PDF files",
            "/health": "GET - Health check"
        }
    }


@router.get("/health")
async def health_check(fastapi_request: Request):
    """Health check endpoint to verify service status."""
    try:
        logger.info("Health check requested")
        
        # Check if orchestrator exists
        orchestrator = getattr(fastapi_request.app.state, 'orchestrator', None)
        logger.info(f"Orchestrator status: {'Available' if orchestrator else 'Not available'}")
        
        if orchestrator is None:
            return {
                "status": "unhealthy",
                "message": "Orchestrator not initialized",
                "timestamp": "2025-06-26",
                "services": {
                    "orchestrator": False,
                    "chatbot_agent": False,
                    "overall_health": False
                }
            }
        
        # Get health from orchestrator
        health_status = orchestrator.get_service_health()
        logger.info(f"Health status from orchestrator: {health_status}")
        
        return {
            "status": "healthy" if health_status.get("overall_health", False) else "degraded",
            "message": "Service operational" if health_status.get("overall_health", False) else "Service running with limited functionality",
            "timestamp": "2025-06-26",
            "services": health_status
        }
        
    except Exception as e:
        logger.error(f"Health check failed: {e}", exc_info=True)
        return {
            "status": "unhealthy",
            "message": f"Health check error: {str(e)}",
            "timestamp": "2025-06-26",
            "services": {
                "orchestrator": False,
                "chatbot_agent": False,
                "overall_health": False,
                "error": str(e)
            }
        }


@router.post("/answer", response_model=AnswerResponse)
async def answer_question(request: QueryRequest, fastapi_request: Request):
    """Endpoint to receive a user question and return an answer."""
    try:
        logger.info("Answer endpoint called")
        
        # Validate query
        query = request.query.strip()
        if not query:
            logger.warning("Empty query provided")
            raise HTTPException(
                status_code=400,
                detail={
                    "answer": "Please provide a valid question.",
                    "success": False,
                    "error": "Empty query provided"
                }
            )
        if request.pdf_uuid is None:
            logger.info(f"pdf_uuid from the request is None")
        logger.info(f"Processing query: {query[:100]}...")
        
        # Check orchestrator availability
        orchestrator = getattr(fastapi_request.app.state, 'orchestrator', None)
        logger.info(f"Orchestrator availability: {'Yes' if orchestrator else 'No'}")
        
        if orchestrator is None:
            logger.error("Orchestrator not available in app state")
            raise HTTPException(
                status_code=503,
                detail={
                    "answer": "Service temporarily unavailable. Application not properly initialized.",
                    "success": False,
                    "error": "Orchestrator not initialized"
                }
            )
        
        # Process query through orchestrator
        logger.info("Delegating query to orchestrator")
        pdf_uuid = request.pdf_uuid
        logger.info(f"Processing query with PDF UUID: {pdf_uuid}")
        try:
            result = orchestrator.process_query(query, pdf_uuid)
            logger.info(f"Orchestrator response: success={result.get('success', False)}")
        except Exception as e:
            logger.error(f"Orchestrator process_query failed: {e}", exc_info=True)
            raise HTTPException(
                status_code=500,
                detail={
                    "answer": "An error occurred while processing your question.",
                    "success": False,
                    "error": f"Orchestrator error: {str(e)}"
                }
            )
        
        # Validate orchestrator response
        if not isinstance(result, dict):
            logger.error(f"Invalid response type from orchestrator: {type(result)}")
            raise HTTPException(
                status_code=500,
                detail={
                    "answer": "Invalid response from service.",
                    "success": False,
                    "error": "Invalid response format"
                }
            )
        
        # Check if the operation was successful
        if not result.get("success", False):
            logger.warning(f"Orchestrator returned unsuccessful result: {result.get('error', 'Unknown error')}")
            # Return the error as a proper response rather than raising an exception
            return {
                "answer": result.get("answer", "An error occurred while processing your question."),
                "success": False,
                "error": result.get("error", "Unknown error")
            }
        
        logger.info("Successfully processed query")
        return {
            "answer": result.get("answer", "No answer provided"),
            "success": True,
            "error": None
        }
        
    except HTTPException as e:
        # Re-raise HTTP exceptions as-is
        logger.info(f"HTTP exception in answer endpoint: {e.status_code} - {e.detail}")
        raise e
    except Exception as e:
        # Catch any unexpected errors
        logger.error(f"Unexpected error in answer endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "answer": "An unexpected error occurred while processing your question.",
                "success": False,
                "error": f"Internal server error: {str(e)}"
            }
        )


@router.post("/uploadpdf", response_model=UploadResponse)
async def upload_pdf(file: UploadFile = File(...), fastapi_request: Request = None):
    """
    Upload and process a PDF file, storing text in Pinecone and tables in MySQL.
    """
    try:
        logger.info("PDF upload endpoint called")
        
        # Import and use upload function
        from ..utils.upload_pdf import process_pdf_upload
        result = await process_pdf_upload(file)
        logger.info(f"Successfully processed PDF UUID: {result.get('pdf_uuid')}")
        logger.info(f"Successfully processed PDF: {result.get('filename', 'unknown')}")
        return result
        
    except HTTPException as e:
        raise e
    except Exception as e:
        logger.error(f"Unexpected error in upload endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": "An unexpected error occurred during PDF processing",
                "error": str(e)
            }
        )
    
@router.post("/clearalldata", response_model=ClearDataResponse)
async def clear_all_data_endpoint(fastapi_request: Request):
    """
    Clear all data from both Pinecone index and MySQL database.
    
    ⚠️  WARNING: This permanently deletes ALL data and cannot be undone!
    """
    try:
        logger.info("Clear all data endpoint called")
        
        # Get data summary before clearing
        logger.info("Getting data summary before clearing")
        pre_summary = await clear_data_service.get_data_summary()
        logger.info(f"Pre-clear summary: Pinecone vectors={pre_summary['pinecone']['vector_count']}, MySQL tables={pre_summary['mysql']['table_count']}")
        
        # Perform the clearing operation
        result = await clear_data_service.clear_all_data()
        
        # Get data summary after clearing
        logger.info("Getting data summary after clearing")
        post_summary = await clear_data_service.get_data_summary()
        logger.info(f"Post-clear summary: Pinecone vectors={post_summary['pinecone']['vector_count']}, MySQL tables={post_summary['mysql']['table_count']}")
        
        # Add summaries to result
        result["pre_clear_summary"] = pre_summary
        result["post_clear_summary"] = post_summary
        
        if result["success"]:
            logger.info("Successfully cleared all data")
        else:
            logger.error(f"Data clearing failed: {result['summary']}")
        
        return result
        
    except Exception as e:
        logger.error(f"Unexpected error in clear all data endpoint: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": "An unexpected error occurred while clearing data",
                "summary": f"Internal server error: {str(e)}",
                "operations": {
                    "pinecone": {"success": False, "message": f"Error: {str(e)}", "details": {}},
                    "mysql": {"success": False, "message": f"Error: {str(e)}", "details": {}}
                }
            }
        )


@router.get("/datasummary")
async def get_data_summary_endpoint():
    """
    Get a summary of current data in both Pinecone and MySQL.
    Useful for checking what data exists before clearing.
    """
    try:
        logger.info("Data summary endpoint called")
        
        summary = await clear_data_service.get_data_summary()
        
        # Add some additional metadata
        response = {
            "success": True,
            "message": "Data summary retrieved successfully",
            "data": summary,
            "timestamp": "2025-06-27",  # You might want to use actual timestamp
            "totals": {
                "pinecone_vectors": summary["pinecone"]["vector_count"] if summary["pinecone"]["available"] else 0,
                "mysql_tables": summary["mysql"]["table_count"] if summary["mysql"]["available"] else 0
            }
        }
        
        logger.info(f"Data summary: {response['totals']}")
        return response
        
    except Exception as e:
        logger.error(f"Error getting data summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail={
                "success": False,
                "message": f"Error retrieving data summary: {str(e)}",
                "data": None
            }
        )