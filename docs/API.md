# PDF Assistant Chatbot API Documentation

## Introduction

The PDF Assistant Chatbot API allows clients to upload PDF documents for content processing and to ask natural language questions related to the information stored within those documents. The backend leverages Google Gemini for AI-driven language understanding and generation, and Pinecone as a vector database for efficient retrieval of relevant content.

This document provides detailed specifications for the available API endpoints, including request formats, response structures, and error handling.

---

## Common Information

-   **Base URL**:
    -   Local Development: `http://localhost:8000` (FastAPI default, can be configured via `.env` `PORT`, e.g., to `5000`)
    -   Production: This will be the URL provided by your deployment platform (e.g., `https://your-service-name.onrender.com`).
-   **Authentication**: The API does not currently implement explicit user-facing authentication. Security for external services (Google Gemini, Pinecone) is managed server-side via environment variables.
-   **Content Type**: For `POST` requests with a JSON body, `Content-Type: application/json` is required. For file uploads, `multipart/form-data` is used.
-   **Error Handling**: Errors are generally returned as JSON objects. Responses typically include a `success` (boolean) or `status` (string) field, and a `message` or `error` field detailing the issue. Standard HTTP status codes are used to indicate the overall outcome of the request.

---

## Endpoints

### 1. Root Endpoint

-   **Method**: `GET`
-   **Path**: `/`
-   **Description**: Provides basic information about the API, including its version and a list of primary endpoints. This route is defined within the `chat_bp` blueprint.
-   **Headers**: None required.
-   **Request Body**: None.
-   **Successful Response**:
    -   **Status Code**: `200 OK`
    -   **Body**:
        ```json
        {
          "message": "PDF Assistant Chatbot API",
          "version": "1.0.0",
          "endpoints": {
            "/health": "GET - Health check",
            "/answer": "POST - Answer questions",
            "/uploadpdf": "POST - Upload PDF files"
          }
        }
        ```
-   **Error Response**: Generally not applicable if the server is operational. In case of a severe server misconfiguration, a standard FastAPI JSON error response or a generic server error might be returned.
    -   **Status Code**: `500 Internal Server Error`
    -   **Body (Conceptual Example for unexpected error)**:
        ```json
        {
            "error": "Internal Server Error",
            "message": "The server encountered an unexpected condition."
        }
        ```
    *Note: `app.py` (or `main.py`) itself might define a very basic `GET /` route. However, if the APIRouter from `routes/chat.py` is included in the main app at the root, its more informative `/` route (documented here) will typically take precedence.*

---

### 2. Health Check

-   **Method**: `GET`
-   **Path**: `/health`
-   **Description**: Performs a comprehensive health check of the backend services. This includes verifying connectivity to Google Gemini and Pinecone, and ensuring the embedding model and vector store components are operational.
-   **Headers**: None required.
-   **Request Body**: None.
-   **Successful Response (All systems healthy)**:
    -   **Status Code**: `200 OK`
    -   **Body (Example based on `Orchestrator.get_service_health` and `ManagerAgent.health_check`)**:
        ```json
        {
            "orchestrator": true, // Indicates orchestrator itself is responsive
            "manager_agent": true, // Overall health of the manager agent
            "overall_health": true, // Top-level overall health
            "active_agent": "manager", // Indicates which agent type is active in orchestrator
            "manager_details": { // Detailed health from ManagerAgent
                "manager_agent": true,
                "llm_connection": true,
                "workflow_ready": true,
                "combiner_agent": true, // Health of sub-agents/components
                "chatbot_agent_available": true,
                "table_agent_available": true, // Assuming table_agent is also checked
                "overall_health": true // ManagerAgent's own overall_health
            }
        }
        ```
        *Note: The exact structure can vary based on which agent is active in the `Orchestrator` and the details included from its specific health check. The example above assumes `ManagerAgent` is active.*
-   **Degraded Service Response (One or more critical checks failed)**:
    -   **Status Code**: `503 Service Unavailable` (This is returned if `overall_health` is `false`)
    -   **Body Example (ManagerAgent or LLM connection failed)**:
        ```json
        {
          "orchestrator": true,
          "manager_agent": false, // Manager agent reported an issue
          "overall_health": false,
          "active_agent": "manager",
          "manager_details": {
            "manager_agent": true,
            "llm_connection": false, // Specific failure point
            "workflow_ready": true,
            "combiner_agent": true,
            "chatbot_agent_available": true,
            "table_agent_available": true,
            "overall_health": false
          }
        }
        ```
-   **Error Response (Exception during the health check process itself)**:
    -   **Status Code**: `500 Internal Server Error`
    -   **Body Example (Orchestrator failed to initialize agents)**:
        ```json
        {
          "status": "error",
          "message": "Orchestrator initialized without any agents - limited functionality.",
          "healthy": false // Or a more detailed error structure from FastAPI
        }
        ```

---

### 3. Upload PDF

-   **Method**: `POST`
-   **Path**: `/uploadpdf`
-   **Description**: Uploads a PDF file to the server. The server then processes this file by extracting its text and tables, generating vector embeddings from the text content, storing embeddings in Pinecone, and table data in MySQL. A unique `pdf_uuid` is generated and returned for context-specific querying.
-   **Headers**:
    -   `Content-Type`: `multipart/form-data` (Automatically set by HTTP clients for file uploads).
-   **Request Body**:
    -   `file`: The PDF file to be uploaded. Sent as a part in the `multipart/form-data` request.
-   **Successful Response**:
    -   **Status Code**: `200 OK`
    -   **Body**:
        ```json
        {
          "success": true,
          "message": "PDF 'your_document_name.pdf' processed and data stored.",
          "filename": "your_document_name.pdf",
          "pdf_uuid": "unique-pdf-identifier-string",
          "tables_stored": 1,
          "text_chunks_stored": 10
        }
        ```
        *Note: `tables_stored` and `text_chunks_stored` indicate the number of tables found and stored in MySQL, and text segments vectorized and stored in Pinecone, respectively. `pdf_uuid` is essential for context-specific querying.*
-   **Error Responses**:
    -   **Status Code**: `400 Bad Request`
        -   *Reason: No file part in the request.*
            ```json
            {
              "success": false,
              "message": "No file provided",
              "error": "No file in request"
            }
            ```
        -   *Reason: No file selected by the user (empty filename string).*
            ```json
            {
              "success": false,
              "message": "No file selected",
              "error": "Empty filename"
            }
            ```
        -   *Reason: File type is not PDF (or not in `ALLOWED_EXTENSIONS`).*
            ```json
            {
              "success": false,
              "message": "Only PDF files are allowed",
              "error": "Invalid file type"
            }
            ```
        -   *Reason: Filename is considered insecure by `werkzeug.utils.secure_filename`.*
            ```json
            {
              "success": false,
              "message": "Invalid filename",
              "error": "Filename not secure"
            }
            ```
    -   **Status Code**: `413 Payload Too Large`
        -   *Reason: The uploaded file exceeds the server's configured `MAX_FILE_SIZE`.*
        -   **Body**:
            ```json
            {
              "success": false,
              "message": "File too large. Maximum size is 50MB", // Note: The exact size (e.g., 50MB) depends on the server configuration.
              "error": "File size exceeded"
            }
            ```
    -   **Status Code**: `500 Internal Server Error`
        -   *Reason: Core services (like `PDFProcessor`, `EmbeddingService`) not initialized, or an unexpected error occurred during PDF processing or storage.*
        -   **Body (Example: Service not initialized)**:
            ```json
            {
              "success": false,
              "message": "Service temporarily unavailable",
              "error": "Required service not initialized"
            }
            ```
        -   **Body (Example: PDF processing failure)**:
            ```json
            {
              "success": false,
              "message": "Failed to process the PDF file",
              "error": "Processing failed"
            }
            ```
        -   **Body (Example: Other unhandled exception)**:
            ```json
            {
              "success": false,
              "message": "An error occurred while processing your upload",
              "error": "<Specific error message string from the exception>"
            }
            ```

---

### 4. Ask Question

-   **Method**: `POST`
-   **Path**: `/answer`
-   **Description**: Submits a natural language question (query) related to the content of a specific, previously uploaded PDF document (identified by `pdf_uuid`). The API leverages its AI model and vector search capabilities to find relevant information and generate a coherent answer.
-   **Headers**:
    -   `Content-Type`: `application/json` (Required)
-   **Request Body**:
    -   **Structure**:
        ```json
        {
          "query": "Your question about the PDF content?",
          "pdf_uuid": "unique-pdf-identifier-string"
        }
        ```
    -   **Parameters**:
        -   `query` (string, required): The natural language question. It must be a non-empty string.
        -   `pdf_uuid` (string, required): The unique identifier for the PDF document this query pertains to. This UUID is returned upon successful PDF upload.
-   **Successful Response**:
    -   **Status Code**: `200 OK`
    -   **Body**:
        ```json
        {
          "answer": "The AI-generated answer based on the relevant document content.",
          "success": true,
          "error": null,
          "metadata": {
              "used_table": false, // Example: true if TableAgent was used
              "used_rag": true     // Example: true if RAGAgent was used
          }
        }
        ```
-   **Error Responses**:
    -   **Status Code**: `400 Bad Request`
        -   *Reason: Request body is not valid JSON or `Content-Type` header is not `application/json`.*
            ```json
            {
              "answer": "Invalid request format. Please provide a valid JSON request body.",
              "success": false,
              "error": "No JSON data provided"
            }
            ```
        -   *Reason: The `query` or `pdf_uuid` field is missing from the JSON body, is an empty string, or not a valid UUID format.*
            ```json
            {
              "answer": "Please provide a valid question and PDF UUID.",
              "success": false,
              "error": "Missing or invalid query or pdf_uuid"
            }
            ```
    -   **Status Code**: `500 Internal Server Error`
        -   *Reason: Core service (like `ManagerAgent` or its sub-agents) not initialized, or an error occurred during AI processing or question answering.*
        -   **Body (Example: Agent not initialized)**:
            ```json
            {
              "answer": "Service temporarily unavailable. Please try again later.",
              "success": false,
              "error": "Agent not initialized" // Or a more specific error from the backend
            }
            ```
        -   **Body (Example: General error during answer generation)**:
            ```json
            {
              "answer": "I apologize, but I encountered an error while processing your question. Please try again.",
              "success": false,
              "error": "<Specific error message string from the exception>"
            }
            ```

---
