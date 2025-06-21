# System Architecture Documentation

## 1. Introduction/Overview

This document outlines the architecture of the PDF Assistant Chatbot backend. The system is a Flask-based Python application designed to process PDF documents, store their content in a vector database, and answer user questions based on this content using a Retrieval Augmented Generation (RAG) approach with Google Gemini and Pinecone.

The architecture emphasizes modularity, separating concerns into distinct components for request handling, core processing logic, external service interactions, and configuration management. This approach aims for maintainability, scalability, and clarity.

## 2. Core Components

The application is structured into several key components, primarily residing within the `src/backend` package:

### 2.1. Flask Application (`app.py`, `src/backend/__init__.py`)

-   **`app.py`**: This is the main executable script that starts the Flask development server. It imports the `create_app` application factory from the `backend` package.
-   **`src/backend/__init__.py`**: This package initializer is crucial for the application setup. It contains the `create_app()` factory function which:
    -   Creates an instance of the Flask application.
    -   Loads application configurations from `src.backend.config.Config`.
    -   Initializes the `ChatbotAgent` (which is an instance of `RAGAgent` from `src.backend.agents.rag_agent.py`).
    -   Initializes the `Orchestrator` (from `src.backend.services.orchestrator.py`) by injecting the `ChatbotAgent` instance.
    -   Makes the `Orchestrator` instance globally accessible within the Flask application context (typically as `current_app.chatbot_agent` or a similar attribute) for use by the route handlers.
    -   Registers API Blueprints, such as `chat_bp` (defined in `src.backend.routes.chat.py`), to organize routes.
    -   Configures application-level logging.

### 2.2. Routing (`src/backend/routes/chat.py`)

-   API endpoints are modularized using Flask Blueprints. The primary blueprint for chatbot functionalities is `chat_bp`.
-   This module is responsible for defining routes (e.g., `/`, `/health`, `/uploadpdf`, `/answer`) and mapping them to specific controller functions.
-   Controller functions handle incoming HTTP requests, perform initial validation (like checking for required parameters or file types), and then delegate the core processing logic to the `Orchestrator` service.
-   They also format the responses received from the service layer into JSON and set appropriate HTTP status codes before sending them back to the client.

### 2.3. Agent (`src/backend/agents/rag_agent.py`)

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

### 2.4. Services (`src/backend/services/orchestrator.py`)

-   The `Orchestrator` class serves as an abstraction layer between the API routes (HTTP request handlers) and the complex core logic within the `RAGAgent`.
-   **Primary Role**:
    -   It holds an instance of the `RAGAgent`.
    -   It exposes simplified methods (e.g., `process_query`, `ingest_document`, `get_service_health`) that the route handlers can call.
    -   It delegates these calls directly to the appropriate methods of the `RAGAgent`.
-   **Benefits & Extensibility**:
    -   Decouples route logic from the agent's internal implementation, making the system easier to maintain and modify.
    -   Provides a clear point for future enhancements, such as managing multiple types of agents, implementing more sophisticated request routing logic (e.g., based on query intent), or orchestrating multi-step workflows.

### 2.5. Configuration (`src/backend/config.py`)

-   The `Config` class is the central point for managing all application settings and configurations.
-   **Key Functions**:
    -   Loads configuration values from environment variables using `os.getenv()`. This is crucial for security (keeping API keys out of version control) and for adapting to different deployment environments (development, testing, production).
    -   Defines default values for configurations if corresponding environment variables are not set.
    -   Stores both Flask-specific settings (e.g., `FLASK_ENV`, `DEBUG`, `PORT`) and application-specific parameters (e.g., `GEMINI_API_KEY`, `PINECONE_API_KEY`, `PINECONE_INDEX_NAME`, `MAX_FILE_SIZE`, `ALLOWED_EXTENSIONS`).
    -   Includes a `validate_required_env_vars()` static method, which is proactively called during the `RAGAgent` initialization to ensure that all critical external service credentials are provided, preventing runtime failures due to missing configuration.

### 2.6. Utilities (`src/backend/utils/helper.py`)

-   This module is designated for common, reusable utility functions that might be needed across various parts of the application.
-   Examples could include specialized text processing functions, date/time helpers, or other miscellaneous logic that doesn't fit neatly into other components. (The specific content of `helper.py` was not part of this architectural review).

## 3. Directory Structure Overview

The project's codebase is organized as follows:

```plaintext
Chatbot_Pinecone_flask_backend/
├── .env                   # Local environment variables (gitignored)
├── .env.template          # Template for .env file
├── app.py                 # Main Flask application entry point for execution
├── requirements.txt       # Python package dependencies
├── start.sh               # Shell script for starting Gunicorn (production deployment)
├── src/                   # Main source code directory
│   └── backend/   # The core Python package for the chatbot application
│       ├── __init__.py    # Package initializer (contains create_app factory)
│       ├── agents/        # Houses different agent implementations
│       │   ├── base.py       # Defines a base class for agents
│       │   └── rag_agent.py  # Implements the RAG-based chatbot logic
│       ├── config.py      # Centralized application configuration
│       ├── routes/        # Defines API endpoints using Flask Blueprints
│       │   ├── __init__.py # Blueprint package initializer
│       │   └── chat.py    # Chat-related API endpoint definitions
│       ├── services/      # Service layer, including the Orchestrator
│       │   ├── __init__.py # Service package initializer
│       │   └── orchestrator.py # Orchestrates interactions with agent(s)
│       └── utils/         # Utility functions and helpers
│           ├── __init__.py # Utilities package initializer
│           └── helper.py    # Miscellaneous helper functions
├── tests/                 # Directory for automated tests (contents may vary)
└── README.md              # Main project documentation file
```

This structure promotes a clear separation of concerns, making the codebase easier to navigate, understand, and maintain.

## 4. Data Flow / Process Flow

### 4.1. PDF Upload and Processing Flow

1.  **Client Request**: A user sends a `POST` request to the `/uploadpdf` endpoint, including a PDF file in `multipart/form-data`.
2.  **Routing (`routes/chat.py`)**: The `/uploadpdf` route handler:
    -   Receives the request.
    -   Validates the file (existence, name, type, size based on `Config`).
    -   Temporarily saves the valid PDF file to the server's filesystem.
3.  **Orchestration (`services/orchestrator.py`)**:
    -   The route handler calls `orchestrator.ingest_document()`, passing the path to the temporary file and any relevant metadata (like a `user_id` if the filename suggests it's a resume).
    -   The `Orchestrator` forwards this request to `rag_agent.upload_data()`.
4.  **Agent Processing (`agents/rag_agent.py` - `upload_data` method)**:
    -   **Parse PDF**: Loads text from the PDF using `PyPDFLoader`.
    -   **Chunk Text**: Splits the text into smaller chunks using `RecursiveCharacterTextSplitter`, adding metadata.
    -   **Generate Embeddings**: For each chunk, creates a vector embedding using `GoogleGenerativeAIEmbeddings`.
    -   **Store in Vector DB**: Upserts the text chunks and their embeddings into the Pinecone index via `PineconeVectorStore`.
5.  **HTTP Response**: The agent returns a success/failure status. This is propagated up through the `Orchestrator` to the route handler, which then sends a JSON response (e.g., `{"success": true, ...}`) to the client.

**Text-based Diagram (Upload Flow):**
```
Client --(POST /uploadpdf + PDF File)--> [Flask App: routes/chat.py]
  | (Temp File Path, User ID)
  v
[Orchestrator: ingest_document()]
  | (Temp File Path, User ID)
  v
[RAGAgent: upload_data()]
  | 1. Load PDF (PyPDFLoader)
  | 2. Split Text (RecursiveCharacterTextSplitter)
  | 3. For each chunk: Generate Embedding (GoogleGenerativeAIEmbeddings)
  | 4. Store Chunks & Embeddings in Pinecone (PineconeVectorStore)
  | (Success/Failure Status)
  v
[Orchestrator] --(Status)--> [Route Handler] --(JSON Response)--> Client
```

### 4.2. Question Answering Flow

1.  **Client Request**: A user sends a `POST` request to the `/answer` endpoint with a JSON payload: `{"query": "Your question here"}`.
2.  **Routing (`routes/chat.py`)**: The `/answer` route handler:
    -   Receives the request.
    -   Validates that the `query` is present and the request body is valid JSON.
3.  **Orchestration (`services/orchestrator.py`)**:
    -   The route handler calls `orchestrator.process_query()`, passing the user's query string.
    -   The `Orchestrator` forwards the query to `rag_agent.answer_question()`.
4.  **Agent Processing (`agents/rag_agent.py` - `answer_question` method)**:
    -   **Embed Query**: Generates a vector embedding for the user's query using `GoogleGenerativeAIEmbeddings` (often done implicitly by the vector store's search method).
    -   **Similarity Search**: Queries the Pinecone vector index (via `PineconeVectorStore`) to find text chunks whose embeddings are most similar to the query embedding. Retrieves top-k relevant chunks.
    -   **Formulate Context**: Combines the text of these retrieved chunks to create a consolidated context.
    -   **Prompt Engineering**: Constructs a prompt for the LLM using a predefined template, the retrieved context, and the original query.
    -   **Generate Answer**: Sends this prompt to the Google Gemini LLM (e.g., `gemini-2.0-flash`) to obtain a natural language answer.
    -   **Package Response**: Formats the LLM's answer and any relevant metadata (e.g., number of sources found) into a dictionary.
5.  **HTTP Response**: The agent returns this dictionary. The `Orchestrator` passes it to the route handler, which sends a JSON response (e.g., `{"answer": "..."}`) to the client.

**Text-based Diagram (Question Answering Flow):**
```
Client --(POST /answer + JSON Query)--> [Flask App: routes/chat.py]
  | (Query String)
  v
[Orchestrator: process_query()]
  | (Query String)
  v
[RAGAgent: answer_question()]
  | 1. Embed Query (GoogleGenerativeAIEmbeddings)
  | 2. Similarity Search in Pinecone (PineconeVectorStore) -> Retrieves relevant chunks
  | 3. Formulate Context from chunks
  | 4. Build Prompt (Template + Context + Query)
  | 5. Generate Answer (Gemini LLM)
  | (Response Dictionary)
  v
[Orchestrator] --(Response Dictionary)--> [Route Handler] --(JSON Response)--> Client
```

## 5. Configuration Management

-   Configuration is centralized in the `Config` class (`src/chatbot_backend/config.py`).
-   **Source**: Primarily loaded from environment variables (`os.getenv()`), allowing for different settings per environment (dev, prod) and keeping secrets out of the codebase.
-   **`.env` Files**: For local development, a `.env` file at the project root is used to set these environment variables. Flask's `python-dotenv` integration typically loads this automatically. This file is gitignored.
-   **Content**: Includes API keys (`GEMINI_API_KEY`, `PINECONE_API_KEY`), Pinecone connection details (`PINECONE_INDEX_NAME`, `PINECONE_CLOUD`, `PINECONE_REGION`), Flask settings (`FLASK_ENV`, `PORT`), and application parameters (`MAX_FILE_SIZE`).
-   **Validation**: `Config.validate_required_env_vars()` is called during `RAGAgent` initialization to ensure critical external service keys are present, raising an error if not.
-   **Access**: Configurations are made available to the Flask app via `app.config` (usually set up in `create_app`) and can also be imported directly from the `Config` class where needed.
