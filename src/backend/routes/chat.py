# src/backend/routes/chat.py

import os
import tempfile
import logging
from pathlib import Path
from flask import Blueprint, request, jsonify, current_app

# Create a Blueprint for chat-related routes
chat_bp = Blueprint('chat_bp', __name__)
logger = logging.getLogger(__name__)

# Helper functions (can be moved to utils if needed elsewhere)
def allowed_file(filename):
    """Check if the uploaded file is allowed based on its extension."""
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']

def validate_request_size():
    """Validate request content length against MAX_FILE_SIZE."""
    if request.content_length and request.content_length > current_app.config['MAX_FILE_SIZE']:
        return False
    return True

@chat_bp.route('/health', methods=['GET'])
def health_check():
    """Health check endpoint for the chatbot service."""
    try:
        chatbot_agent = current_app.chatbot_agent
        if not chatbot_agent:
            logger.error("ChatbotAgent is not initialized during health check.")
            return jsonify({
                "status": "error",
                "message": "ChatbotAgent not initialized",
                "healthy": False
            }), 500
        
        health_status = chatbot_agent.health_check()
        
        return jsonify({
            "status": "success",
            "health": health_status,
            "healthy": health_status["overall_health"]
        }), 200 if health_status["overall_health"] else 503
        
    except Exception as e:
        logger.error(f"Health check endpoint error: {e}")
        return jsonify({
            "status": "error",
            "message": str(e),
            "healthy": False
        }), 500

@chat_bp.route('/answer', methods=['POST'])
def answer_question():
    """
    Endpoint to receive a user question and return an answer using the chatbot agent.
    """
    try:
        chatbot_agent = current_app.chatbot_agent
        if not chatbot_agent:
            return jsonify({
                "answer": "Service temporarily unavailable. Please try again later.",
                "success": False,
                "error": "ChatbotAgent not initialized"
            }), 500
        
        data = request.get_json()
        if not data:
            return jsonify({
                "answer": "Invalid request format. Please provide a valid JSON request.",
                "success": False,
                "error": "No JSON data provided"
            }), 400
        
        query = data.get('query', '').strip()
        if not query:
            return jsonify({
                "answer": "Please provide a valid question.",
                "success": False,
                "error": "Empty query provided"
            }), 400
        
        result = chatbot_agent.answer_question(query)
        
        return jsonify({
            "answer": result["answer"]
        }), 200
        
    except Exception as e:
        logger.error(f"Error in answer endpoint: {e}")
        return jsonify({
            "answer": "I apologize, but I encountered an error while processing your question. Please try again.",
            "success": False,
            "error": str(e)
        }), 500

@chat_bp.route('/uploadpdf', methods=['POST'])
def upload_pdf():
    """
    Endpoint to upload and process a PDF file, adding its content to the knowledge base.
    """
    try:
        chatbot_agent = current_app.chatbot_agent
        if not chatbot_agent:
            return jsonify({
                "success": False,
                "message": "Service temporarily unavailable",
                "error": "ChatbotAgent not initialized"
            }), 500
        
        if not validate_request_size():
            return jsonify({
                "success": False,
                "message": f"File too large. Maximum size is {current_app.config['MAX_FILE_SIZE'] // (1024*1024)}MB",
                "error": "File size exceeded"
            }), 413
        
        if 'file' not in request.files:
            return jsonify({
                "success": False,
                "message": "No file provided",
                "error": "No file in request"
            }), 400
        
        file = request.files['file']
        
        if file.filename == '':
            return jsonify({
                "success": False,
                "message": "No file selected",
                "error": "Empty filename"
            }), 400
        
        if not allowed_file(file.filename):
            return jsonify({
                "success": False,
                "message": "Only PDF files are allowed",
                "error": "Invalid file type"
            }), 400
        
        # Using secure_filename is important for security, but it's typically handled
        # when saving to a known safe path. For temporary files, the naming is random.
        # Still good practice to know it exists.
        from werkzeug.utils import secure_filename
        filename = secure_filename(file.filename)
        if not filename:
            return jsonify({
                "success": False,
                "message": "Invalid filename",
                "error": "Filename not secure"
            }), 400
        
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as temp_file:
            file.save(temp_file.name)
            temp_file_path = temp_file.name
        
        try:
            user_id = None
            if 'resume' in filename.lower() or 'cv' in filename.lower():
                user_id = Path(filename).stem
            
            success = chatbot_agent.upload_pdf(temp_file_path, user_id)
            
            if success:
                logger.info(f"Successfully processed PDF upload: {filename}")
                return jsonify({
                    "success": True,
                    "message": f"PDF '{filename}' uploaded and processed successfully",
                    "filename": filename
                }), 200
            else:
                logger.warning(f"Failed to process PDF upload: {filename}")
                return jsonify({
                    "success": False,
                    "message": "Failed to process the PDF file",
                    "error": "Processing failed"
                }), 500
                
        finally:
            try:
                os.unlink(temp_file_path)
            except Exception as e:
                logger.warning(f"Failed to delete temporary file {temp_file_path}: {e}")
        
    except Exception as e:
        logger.error(f"Error in upload endpoint: {e}")
        return jsonify({
            "success": False,
            "message": "An error occurred while processing your upload",
            "error": str(e)
        }), 500

@chat_bp.route('/', methods=['GET'])
def index():
    """Root endpoint for the API, providing basic information."""
    return jsonify({
        "message": "PDF Assistant Chatbot API",
        "version": "1.0.0",
        "endpoints": {
            "/health": "GET - Health check",
            "/answer": "POST - Answer questions",
            "/uploadpdf": "POST - Upload PDF files"
        }
    })

