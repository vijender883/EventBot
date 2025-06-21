# System Architecture Documentation

## 1. Introduction/Overview

This document outlines the architecture of the PDF Assistant Chatbot. The system comprises a Flask-based Python backend and a Streamlit-based Python frontend. The backend is designed to process PDF documents, store their content in a vector database (Pinecone), and answer user questions using a Retrieval Augmented Generation (RAG) approach with Google Gemini. The frontend provides a user interface for uploading PDFs and interacting with the chatbot.

The architecture emphasizes modularity, separating concerns into distinct components for the user interface, backend request handling, core processing logic, external service interactions, and configuration management. This approach aims for maintainability, scalability, and clarity.

## 2. Core Components

The application is structured into several key components:

### 2.1. Frontend (Streamlit Application - `src/frontend/streamlit_app.py`)

-   **`src/frontend/streamlit_app.py`**: This is the main application file for the user interface, built using Streamlit.
-   **Key Responsibilities**:
    -   Provides a user-friendly interface for uploading PDF documents.
    -   Allows users to input questions in a chat-like interface.
    -   Communicates with the Flask backend API (via HTTP requests) to:
        -   Send PDF files for processing.
        -   Submit user queries and display the answers received from the backend.
    -   Manages UI state and user interactions.
    -   Requires the `ENDPOINT` environment variable to be set to the URL of the backend API.

### 2.2. Backend Flask Application (`app.py`, `src/backend/__init__.py`)

-   **`app.py`**: This is the main executable script that starts the Flask development server. It imports the `create_app` application factory from the `backend` package.
-   **`src/backend/__init__.py`**: This package initializer is crucial for the application setup. It contains the `create_app()` factory function which:
    -   Creates an instance of the Flask application.
    -   Loads application configurations from `src.backend.config.Config`.
    -   Initializes the `ChatbotAgent` (which is an instance of `RAGAgent` from `src.backend.agents.rag_agent.py`).
    -   Initializes the `Orchestrator` (from `src.backend.services.orchestrator.py`) by injecting the `ChatbotAgent` instance.
    -   Makes the `Orchestrator` instance globally accessible within the Flask application context (typically as `current_app.chatbot_agent` or a similar attribute) for use by the route handlers.
    -   Registers API Blueprints, such as `chat_bp` (defined in `src.backend.routes.chat.py`), to organize routes.
    -   Configures application-level logging.

### 2.3. Backend Routing (`src/backend/routes/chat.py`)

-   API endpoints are modularized using Flask Blueprints. The primary blueprint for chatbot functionalities is `chat_bp`.
-   This module is responsible for defining routes (e.g., `/`, `/health`, `/uploadpdf`, `/answer`) and mapping them to specific controller functions.
-   Controller functions handle incoming HTTP requests, perform initial validation (like checking for required parameters or file types), and then delegate the core processing logic to the `Orchestrator` service.
-   They also format the responses received from the service layer into JSON and set appropriate HTTP status codes before sending them back to the client.

### 2.4. Backend Agent (`src/backend/agents/rag_agent.py`)

-   The `RAGAgent` class (referred to as `ChatbotAgent` in `__init__.py` after instantiation) is the heart of the chatbot's intelligence and processing capabilities. It extends `BaseChatbotAgent` (from `src/backend/agents/base.py`).
-   **Key Responsibilities**:
    -   **Initialization**:
        -   Establishes connections with external services: Google Gemini (for both Large Language Model capabilities and text embeddings) and Pinecone (for the vector database).
        -   Uses API keys and configuration parameters loaded from the `Config` class.
        -   Leverages Langchain library components for streamlined interaction: `GoogleGenerativeAIEmbeddings` for creating vector representations of text and `PineconeVectorStore` for interfacing with the Pinecone index.
    -   **PDF Processing (`upload_data` method)**:
        -   Accepts a PDF file path.
        -   Uses `PyPDFLoader` (from Langchain) to load and parse text content from the PDF.
        -   Employs `RecursiveCharacterTextSplitter` (from Langchain) to divide the extracted text into smaller, semantically coherent chunks suitable for embedding.
        -   Adds relevant metadata (e.g., `document_type`, `userId` for resumes) to each text chunk.
        -   Generates vector embeddings for each chunk using the configured Gemini embedding model (e.g., `models/embedding-001`).
        -   Stores these text chunks and their corresponding vector embeddings in the Pinecone vector index, making them searchable.
    -   **Retrieval Augmented Generation (RAG) for Question Answering (`answer_question` method)**:
        -   Receives a user's query.
        -   Generates an embedding for the query using the same Gemini embedding model.
        -   Performs a similarity search against the Pinecone vector index to retrieve the most relevant text chunks (context) based on vector proximity to the query embedding.
        -   Constructs a detailed prompt for the Gemini LLM (e.g., `gemini-2.0-flash`) using a predefined template. This prompt includes the retrieved context and the original user question, guiding the LLM to answer based on the provided information.
        -   Sends the prompt to the LLM and receives the generated natural language answer.
    -   **Health Checks (`health_check` method)**: Provides functionality to verify the operational status of its dependencies (Gemini API, Pinecone connection, embedding model, and vector store).

### 2.5. Backend Services (`src/backend/services/orchestrator.py`)

-   The `Orchestrator` class serves as an abstraction layer between the API routes (HTTP request handlers) and the complex core logic within the `RAGAgent`.
-   **Primary Role**:
    -   It holds an instance of the `RAGAgent`.
    -   It exposes simplified methods (e.g., `process_query`, `ingest_document`, `get_service_health`) that the route handlers can call.
    -   It delegates these calls directly to the appropriate methods of the `RAGAgent`.
-   **Benefits & Extensibility**:
    -   Decouples route logic from the agent's internal implementation, making the system easier to maintain and modify.
    -   Provides a clear point for future enhancements, such as managing multiple types of agents, implementing more sophisticated request routing logic (e.g., based on query intent), or orchestrating multi-step workflows.

### 2.6. Backend Configuration (`src/backend/config.py`)

-   The `Config` class is the central point for managing all application settings and configurations.
-   **Key Functions**:
    -   Loads configuration values from environment variables using `os.getenv()`. This is crucial for security (keeping API keys out of version control) and for adapting to different deployment environments (development, testing, production).
    -   Defines default values for configurations if corresponding environment variables are not set.
    -   Stores both Flask-specific settings (e.g., `FLASK_ENV`, `DEBUG`, `PORT`) and application-specific parameters (e.g., `GEMINI_API_KEY`, `PINECONE_API_KEY`, `PINECONE_INDEX_NAME`, `MAX_FILE_SIZE`, `ALLOWED_EXTENSIONS`).
    -   Includes a `validate_required_env_vars()` static method, which is proactively called during the `RAGAgent` initialization to ensure that all critical external service credentials are provided, preventing runtime failures due to missing configuration.

### 2.7. Backend Utilities (`src/backend/utils/helper.py`)

-   This module is designated for common, reusable utility functions that might be needed across various parts of the application.
-   Examples could include specialized text processing functions, date/time helpers, or other miscellaneous logic that doesn't fit neatly into other components. (The specific content of `helper.py` was not part of this architectural review).

## 3. Directory Structure Overview

The project's codebase is organized as follows:

```plaintext
Chatbot_Pinecone_flask_backend/
├── .env                           # Local environment variables (gitignored)
├── .env.template                  # Template for .env file
├── Makefile                       # Defines common tasks like running, testing, linting
├── app.py                         # Main Flask application entry point for the backend
├── requirements.txt               # Python package dependencies for both backend and frontend
├── requirements-dev.txt           # Development-specific dependencies (testing, linting)
├── start.sh                       # Shell script for starting the backend application via Gunicorn
├── src/                           # Main source code directory
│   ├── backend/                   # Source code for the Flask backend
│   │   ├── __init__.py            # Package initializer (contains create_app factory)
│   │   ├── agents/                # Houses different agent implementations
│   │   │   ├── base.py               # Defines a base class for agents
│   │   │   └── rag_agent.py          # Implements the RAG-based chatbot logic
│   │   ├── config.py              # Centralized backend application configuration
│   │   ├── routes/                # Defines API endpoints using Flask Blueprints
│   │   │   ├── __init__.py         # Blueprint package initializer
│   │   │   └── chat.py            # Chat-related API endpoint definitions
│   │   ├── services/              # Service layer, including the Orchestrator
│   │   │   ├── __init__.py         # Service package initializer
│   │   │   └── orchestrator.py     # Orchestrates interactions with agent(s)
│   │   └── utils/                 # Backend utility functions and helpers
│   │       ├── __init__.py         # Utilities package initializer
│   │       └── helper.py            # Miscellaneous helper functions
│   └── frontend/                  # Source code for the Streamlit frontend
│       └── streamlit_app.py         # Main Streamlit application file
├── tests/                         # Directory for automated tests (primarily for backend)
│   ├── conftest.py
│   ├── test_agents/
│   │   └── test_rag_agent.py
│   └── test_routes/
│       └── test_chat_routes.py
└── README.md                      # Main project documentation file
```

This structure promotes a clear separation of concerns between the frontend and backend, making the codebase easier to navigate, understand, and maintain.

## 4. Data Flow / Process Flow

The primary interactions involve the user (via the Streamlit frontend) and the Flask backend.

### 4.1. PDF Upload and Processing Flow

1.  **User Action (Frontend)**: User selects a PDF file and clicks "Upload" in the Streamlit UI (`streamlit_app.py`).
2.  **Frontend Request**: The Streamlit app sends a `POST` request to the backend's `/uploadpdf` endpoint (defined by `ENDPOINT` env var), with the PDF file in `multipart/form-data`.
3.  **Backend Routing (`routes/chat.py`)**: The `/uploadpdf` route handler in the Flask backend:
    -   Receives the request.
    -   Validates the file (existence, name, type, size based on `Config`).
    -   Temporarily saves the valid PDF file to the server's filesystem.
4.  **Backend Orchestration (`services/orchestrator.py`)**:
    -   The route handler calls `orchestrator.ingest_document()`, passing the path to the temporary file.
    -   The `Orchestrator` forwards this request to `rag_agent.upload_data()`.
5.  **Backend Agent Processing (`agents/rag_agent.py` - `upload_data` method)**:
    -   **Parse PDF**: Loads text from the PDF using `PyPDFLoader`.
    -   **Chunk Text**: Splits the text into smaller chunks using `RecursiveCharacterTextSplitter`.
    -   **Generate Embeddings**: For each chunk, creates a vector embedding using `GoogleGenerativeAIEmbeddings`.
    -   **Store in Vector DB**: Upserts the text chunks and their embeddings into the Pinecone index via `PineconeVectorStore`.
6.  **Backend HTTP Response**: The agent returns a success/failure status. This is propagated up through the `Orchestrator` to the route handler, which then sends a JSON response (e.g., `{"success": true, ...}`) back to the Streamlit frontend.
7.  **Frontend Update**: The Streamlit app receives the response and updates the UI to inform the user of the upload status.

**Text-based Diagram (Upload Flow):**
```
User --(Uploads PDF)--> [Streamlit Frontend: streamlit_app.py]
  | (POST /uploadpdf + PDF File, via ENDPOINT)
  v
[Flask Backend: routes/chat.py]
  | (Temp File Path)
  v
[Backend Orchestrator: ingest_document()]
  | (Temp File Path)
  v
[Backend RAGAgent: upload_data()]
  | 1. Load PDF
  | 2. Split Text
  | 3. Generate Embeddings (Gemini)
  | 4. Store in Pinecone
  | (Success/Failure Status)
  v
[Backend Orchestrator] --(Status)--> [Backend Route Handler] --(JSON Response)--> [Streamlit Frontend] --(UI Update)--> User
```

### 4.2. Question Answering Flow

1.  **User Action (Frontend)**: User types a question into the chat input in the Streamlit UI and submits it.
2.  **Frontend Request**: The Streamlit app sends a `POST` request to the backend's `/answer` endpoint (defined by `ENDPOINT` env var) with a JSON payload: `{"query": "User's question"}`.
3.  **Backend Routing (`routes/chat.py`)**: The `/answer` route handler in the Flask backend:
    -   Receives the request.
    -   Validates that the `query` is present.
4.  **Backend Orchestration (`services/orchestrator.py`)**:
    -   The route handler calls `orchestrator.process_query()`, passing the user's query string.
    -   The `Orchestrator` forwards the query to `rag_agent.answer_question()`.
5.  **Backend Agent Processing (`agents/rag_agent.py` - `answer_question` method)**:
    -   **Embed Query**: Generates an embedding for the query (Gemini).
    -   **Similarity Search**: Queries Pinecone to find relevant text chunks.
    -   **Formulate Context**: Combines retrieved chunks.
    -   **Prompt Engineering**: Constructs a prompt for the LLM (Gemini).
    -   **Generate Answer**: Sends prompt to Gemini LLM.
6.  **Backend HTTP Response**: The agent returns the answer. This is propagated to the route handler, which sends a JSON response (e.g., `{"answer": "..."}`) back to the Streamlit frontend.
7.  **Frontend Update**: The Streamlit app receives the answer and displays it in the chat interface.

**Text-based Diagram (Question Answering Flow):**
```
User --(Asks Question)--> [Streamlit Frontend: streamlit_app.py]
  | (POST /answer + JSON Query, via ENDPOINT)
  v
[Flask Backend: routes/chat.py]
  | (Query String)
  v
[Backend Orchestrator: process_query()]
  | (Query String)
  v
[Backend RAGAgent: answer_question()]
  | 1. Embed Query (Gemini)
  | 2. Search Pinecone
  | 3. Formulate Context
  | 4. Build Prompt
  | 5. Generate Answer (Gemini LLM)
  | (Answer)
  v
[Backend Orchestrator] --(Answer)--> [Backend Route Handler] --(JSON Response)--> [Streamlit Frontend] --(Display Answer)--> User
```

## 5. Configuration Management

Configuration is managed via environment variables, facilitated by `.env` files for local development.

-   **Backend Configuration (`src/backend/config.py`)**:
    -   The `Config` class loads backend-specific settings (API keys for Gemini, Pinecone details, Flask settings) from environment variables.
    -   Refer to `.env.template` for variables like `GEMINI_API_KEY`, `PINECONE_API_KEY`, `PINECONE_INDEX_NAME`, `FLASK_ENV`, `PORT`.
-   **Frontend Configuration (`src/frontend/streamlit_app.py`)**:
    -   The Streamlit application primarily requires the `ENDPOINT` environment variable to know the address of the backend API (e.g., `ENDPOINT=http://localhost:5000`).
    -   This is also typically loaded from the `.env` file when running locally.
-   **`.env` Files**: A single `.env` file at the project root can store variables for both backend and frontend. This file is gitignored.
-   **Validation**: The backend's `Config.validate_required_env_vars()` ensures critical backend service keys are present. The frontend validates the `ENDPOINT` variable.
-   **Access**:
    -   Backend: Configurations are available via `app.config` or direct import from `Config`.
    -   Frontend: `os.getenv('ENDPOINT')` is used in `streamlit_app.py`.
