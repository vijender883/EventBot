# src/chatbot_backend/utils/helper.py

import logging
from flask import jsonify, request, current_app # current_app for accessing app.config

logger = logging.getLogger(__name__)

# Common error handlers for Flask application
def not_found(error):
    """Handle 404 errors (resource not found)."""
    logger.warning(f"404 Not Found: {request.path}")
    return jsonify({
        "error": "Endpoint not found",
        "message": "The requested endpoint does not exist."
    }), 404

def method_not_allowed(error):
    """Handle 405 errors (HTTP method not allowed)."""
    logger.warning(f"405 Method Not Allowed: {request.method} {request.path}")
    return jsonify({
        "error": "Method not allowed",
        "message": "The HTTP method is not allowed for this endpoint."
    }), 405

def payload_too_large(error):
    """Handle 413 errors (payload too large)."""
    max_size_mb = current_app.config.get('MAX_FILE_SIZE', 0) // (1024 * 1024)
    logger.warning(f"413 Payload Too Large: {request.path} - Max size {max_size_mb}MB")
    return jsonify({
        "success": False,
        "message": f"File too large. Maximum size is {max_size_mb}MB",
        "error": "Payload too large."
    }), 413

# You can also move allowed_file and validate_request_size here if you want
# to keep all helper functions in one place, but they are currently scoped
# within the chat.py blueprint for direct access to current_app.config.
# If moved here, they would need to import current_app.

