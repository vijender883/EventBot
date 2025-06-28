# System Architecture Documentation

## 1. Introduction/Overview

This document outlines the architecture of EventBot. The system comprises a FastAPI-based Python backend and a Streamlit-based Python frontend. The backend is designed to process PDF documents, extracting text for vector storage (Pinecone) and tables for relational storage (MySQL). It answers user questions using a sophisticated agentic system involving Retrieval Augmented Generation (RAG) with Google Gemini, table data querying, and intelligent response combination. The frontend provides a user interface for uploading PDFs and interacting with the chatbot.

The architecture emphasizes modularity, separating concerns into distinct components for the user interface, backend request handling, core processing logic (including multiple agents and services), external service interactions, and configuration management. This approach aims for maintainability, scalability, and clarity.

## 2. Core Components

The application is structured into several key components:

### 2.1. Frontend (Streamlit Application - `src/frontend/streamlit_app.py`)

-   **`src/frontend/streamlit_app.py`**: This is the main application file for the user interface, built using Streamlit.
-   **Key Responsibilities**:
    -   Provides a user-friendly interface for uploading PDF documents.
    -   Allows users to input questions in a chat-like interface.
    -   Communicates with the FastAPI backend API (via HTTP requests) to:
        -   Send PDF files for processing.
        -   Submit user queries and display the answers received from the backend.
    -   Manages UI state and user interactions.
    -   Requires the `ENDPOINT` environment variable to be set to the URL of the backend API.

### 2.2. Backend FastAPI Application (`app.py`, `src/backend/__init__.py`)

-   **`app.py`**: This is the main executable script that defines the FastAPI application instance. It's typically run with an ASGI server like Uvicorn. It initializes the `Orchestrator` and makes it available to the request lifecycle via `app.state`.
-   **`src/backend/__init__.py`**: Package initializer for the backend. FastAPI app setup in `app.py` involves:
    -   Creating an instance of the `FastAPI` application.
    -   Loading application configurations from `src.backend.config.Config`.
    -   Initializing the `Orchestrator`, which in turn initializes the `ManagerAgent` (and its sub-agents like `ChatbotAgent` and `CombinerAgent`) and other necessary services.
    -   Including API Routers, such as the one defined in `src.backend.routes.chat.py`.
    -   Configuring application-level logging and middleware (e.g., CORS).

### 2.3. Backend Routing (`src/backend/routes/chat.py`)

-   API endpoints are modularized using FastAPI's `APIRouter`. The primary router for chatbot functionalities is defined here.
-   This module is responsible for defining path operations (e.g., for `/`, `/health`, `/uploadpdf`, `/answer`) using decorators like `@router.get()` or `@router.post()`.
-   Path operation functions handle incoming HTTP requests, perform validation (FastAPI leverages Pydantic models from `src/backend/models.py`), and then delegate core logic.
    -   For `/answer`, it delegates to the `Orchestrator` instance (from `fastapi_request.app.state.orchestrator`).
    -   For `/uploadpdf`, it calls the `process_pdf_upload` utility function from `src/backend/utils/upload_pdf.py`.
-   FastAPI automatically handles response formatting (e.g., to JSON) and setting appropriate HTTP status codes.

### 2.4. Backend Models (`src/backend/models.py`)
-   **`src/backend/models.py`**: Defines Pydantic models used for API request validation and response serialization (e.g., `QueryRequest`, `AnswerResponse`, `UploadResponse`). This ensures data consistency and provides clear API contracts.

### 2.5. Backend Orchestration (`src/backend/services/orchestrator.py`)

-   The `Orchestrator` class serves as a high-level coordinator between the API routes and the backend's processing capabilities.
-   **Primary Role**:
    -   It initializes and holds an instance of the `ManagerAgent`.
    -   It exposes simplified methods like `process_query` (delegating to `ManagerAgent`) and `get_service_health` (aggregating health checks from agents).
    -   The `/uploadpdf` route bypasses direct orchestrator interaction for uploads, instead using utility functions that directly leverage `PDFProcessor` and `EmbeddingService`.
-   **Benefits & Extensibility**:
    -   Decouples route logic from the agent's internal implementation.
    -   Provides a clear point for managing different types of agents or more complex workflows if needed in the future.

### 2.6. Backend Agent System

The core logic for question answering is handled by a system of interconnected agents, primarily orchestrated by the `ManagerAgent` using LangGraph.

#### 2.6.1. Manager Agent (`src/backend/agents/manager_agent.py`)
-   The `ManagerAgent` is the central brain of the Q&A process. It uses LangGraph to define and execute a stateful workflow.
-   **Key Responsibilities**:
    -   Receives the user query and PDF context (UUID) from the `Orchestrator`.
    -   **Query Analysis (Manager Node)**: Uses a Gemini LLM to analyze the input query and available table schemas (loaded via `_load_table_schema` which reads `src/backend/utils/table_schema.json`, filtered by `pdf_uuid`). It determines if the query requires:
        -   Information primarily from structured tables ("table").
        -   Information primarily from unstructured text via RAG ("rag").
        -   Information from both sources ("both").
    -   **Conditional Routing**: Based on the analysis, it routes the query to:
        -   The `TableAgent` node if `needs_table` is true.
        -   The `ChatbotAgent` (RAG) node if `needs_rag` is true.
        -   If "both", it typically routes to `TableAgent` first, then `ChatbotAgent`.
    -   **State Management**: Passes relevant state (query, `pdf_uuid`, intermediate responses) between nodes.
    -   **Response Synthesis**: Routes processed information (table results, RAG results) to the `CombinerAgent` node.
    -   Initializes and uses instances of `TableAgent` (if available), `ChatbotAgent` (passed during its own initialization), and `CombinerAgent`.

#### 2.6.2. Table Agent (`src/backend/agents/table_agent.py`)
-   This agent is specialized in querying structured data stored in MySQL.
-   **Key Responsibilities**:
    -   Receives the query and `pdf_uuid` from the `ManagerAgent`.
    -   Loads the relevant table schemas for the given `pdf_uuid` (likely by interacting with `PDFProcessor` or `SchemaManager`).
    -   Uses a Gemini LLM to:
        -   Understand the query in the context of available table schemas.
        -   Generate an appropriate SQL query.
    -   Executes the SQL query against the MySQL database.
    -   Processes the SQL query results into a natural language response or structured data.
    -   Returns the response to the `ManagerAgent`.
-   *Note: The exact mechanism for schema loading and SQL execution is internal to `TableAgent` but it's designed to be context-aware based on the `pdf_uuid`.*

#### 2.6.3. Chatbot Agent (`src/backend/agents/rag_agent.py` - class `ChatbotAgent`)
-   This agent (formerly the primary RAG agent) is responsible for Retrieval Augmented Generation from unstructured text. It extends `BaseChatbotAgent`.
-   **Key Responsibilities**:
    -   **Initialization**: Connects to Google Gemini (LLM) and Pinecone (vector database). Uses `GoogleGenerativeAIEmbeddings` and `PineconeVectorStore` (from Langchain).
    -   **RAG for Question Answering (`answer_question` method)**:
        -   Receives a query and `pdf_uuid` (from the `ManagerAgent`).
        -   Performs similarity search against the Pinecone vector index, potentially filtering by `pdf_uuid` or using it to scope the search, to retrieve relevant text chunks. (The `EmbeddingService` handles the actual Pinecone interaction).
        -   Constructs a prompt with the retrieved context and the query.
        -   Sends the prompt to the Gemini LLM and returns the generated answer.
    -   It relies on `EmbeddingService` for Pinecone search operations if not directly implemented.

#### 2.6.4. Combiner Agent (`src/backend/agents/combiner_agent.py`)
-   This agent is responsible for intelligently merging responses from different sources (e.g., `TableAgent` results and `ChatbotAgent` results).
-   **Key Responsibilities**:
    -   Receives the original query, table response (if any), and RAG response (if any) from the `ManagerAgent`.
    -   Uses a Gemini LLM with a specific prompt to synthesize these inputs into a single, well-structured, and coherent final answer.
    -   Provides fallback mechanisms if one or more inputs are missing or if the LLM combination fails.

### 2.7. Backend Services

#### 2.7.1. Embedding Service (`src/backend/services/embedding_service.py`)
-   This service centralizes the logic for creating and storing text embeddings in Pinecone.
-   **Key Responsibilities**:
    -   Initializes connection to Google Gemini for embedding generation (`models/embedding-001`) and Pinecone for vector storage.
    -   Creates the Pinecone index if it doesn't exist.
    -   `generate_embeddings(texts)`: Generates embeddings for a list of text chunks using Gemini.
    -   `store_text_embeddings(text_chunks, filename, pdf_uuid)`: Generates embeddings for text chunks and stores them in Pinecone, including `filename` and `pdf_uuid` as metadata for filtering.
    -   `search_similar_text(query, top_k, pdf_uuid)`: Embeds a query and searches Pinecone for similar text chunks, potentially filtering by `pdf_uuid`. This is used by `ChatbotAgent`.

### 2.8. Backend Utilities

#### 2.8.1. PDF Processor (`src/backend/utils/pdf_processor.py`)
-   The `PDFProcessor` class handles the extraction of content from PDF files and storage of tabular data.
-   **Key Responsibilities**:
    -   Connects to a MySQL database (via `database_url` from config).
    -   `extract_content(pdf_path)`: Uses `pdfplumber` to extract text chunks and tables from a PDF. Handles multi-page tables.
    -   `infer_schema(table_data, table_name)`: Infers a database schema (column names and types) for an extracted table.
    -   `store_table(table_data, table_name, pdf_uuid)`: Creates a table in MySQL based on the inferred schema and inserts the extracted tabular data. It also associates the table with the `pdf_uuid`.
    -   **Schema Management**: After storing a table, it now also saves/updates the schema (table name, column details, `pdf_uuid`) to `src/backend/utils/table_schema.json` via `SchemaManager`.

#### 2.8.2. Schema Manager (`src/backend/utils/schema_manager.py`)
-   This utility is responsible for managing the `table_schema.json` file.
-   **Key Responsibilities**:
    -   `save_schema(table_name, schema_details, pdf_uuid)`: Adds or updates a table's schema in `table_schema.json`.
    -   `load_schema(pdf_uuid=None)`: Loads schemas from `table_schema.json`. If `pdf_uuid` is provided, it filters schemas for that specific PDF. This is used by `ManagerAgent` and potentially `TableAgent`.
    -   `delete_schema(table_name)`: Removes a table's schema (not currently implemented but good for future).

#### 2.8.3. PDF Upload Utilities (`src/backend/utils/upload_pdf.py`)
-   This module provides helper functions for the PDF upload process, used by the `/uploadpdf` route.
-   **Key Responsibilities (`process_pdf_upload` function)**:
    -   Generates a unique `pdf_uuid` for the uploaded PDF.
    -   Validates uploaded file (size, type, name).
    -   Uses `PDFProcessor` to:
        -   Extract text and tables from the PDF.
        -   Store the tables in MySQL, associating them with the `pdf_uuid`.
        -   Save the schemas of these tables to `table_schema.json` (via `PDFProcessor` calling `SchemaManager`), linked with `pdf_uuid`.
    -   Uses `EmbeddingService` to generate embeddings for the extracted text chunks and store them in Pinecone, associated with the `pdf_uuid`.
    -   Manages temporary file creation and cleanup.
    -   Returns the `pdf_uuid` in the response.

#### 2.8.4. General Helper (`src/backend/utils/helper.py`)
-   This module is designated for common, reusable utility functions that might be needed across various parts of the application (e.g., generating UUIDs).

### 2.9. Backend Configuration (`src/backend/config.py`)

-   The `Config` class is the central point for managing all application settings.
-   **Key Functions**:
    -   Loads configuration values from environment variables (e.g., API keys, database URLs, Pinecone details, `LOG_LEVEL`).
    -   Defines default values and validates required environment variables.
    -   Stores parameters like `GEMINI_API_KEY`, `PINECONE_API_KEY`, `PINECONE_INDEX_NAME`, `PINECONE_DIMENSION`, `PINECONE_CLOUD`, `PINECONE_REGION`, `DATABASE_URL`, `MAX_FILE_SIZE`, `ALLOWED_EXTENSIONS`, `LOG_LEVEL`.

## 3. Directory Structure Overview

The project's codebase is organized as follows (reflecting recent updates):

```plaintext
EventBot/
├── .env                           # Local environment variables (gitignored)
├── .env.template                  # Template for .env file
├── Makefile                       # Defines common tasks like running, testing, linting
├── app.py                         # Main FastAPI application entry point
├── requirements.txt               # Python package dependencies
├── requirements-dev.txt           # Development-specific dependencies
├── start.sh                       # Script for starting backend
├── src/                           # Main source code directory
│   ├── backend/                   # Source code for the FastAPI backend
│   │   ├── __init__.py            # Package initializer
│   │   ├── agents/                # Houses different agent implementations
│   │   │   ├── base.py            # Defines a base class for agents
│   │   │   ├── combiner_agent.py  # Agent for combining responses
│   │   │   ├── manager_agent.py   # Agent for orchestrating query processing (uses LangGraph)
│   │   │   ├── rag_agent.py       # Implements the RAG-based chatbot logic (ChatbotAgent)
│   │   │   └── table_agent.py     # Agent for querying structured table data
│   │   ├── config.py              # Centralized backend application configuration
│   │   ├── models.py              # Pydantic models for API requests/responses
│   │   ├── routes/                # Defines API endpoints
│   │   │   ├── __init__.py        # Router package initializer
│   │   │   └── chat.py            # Chat-related API endpoint definitions
│   │   ├── services/              # Service layer
│   │   │   ├── __init__.py        # Service package initializer
│   │   │   ├── clear_data_service.py # Service for clearing data from DB and Vector Store
│   │   │   ├── embedding_service.py # Handles text embeddings and Pinecone storage
│   │   │   └── orchestrator.py    # Orchestrates interactions with ManagerAgent
│   │   └── utils/                 # Backend utility functions and helpers
│   │       ├── __init__.py        # Utilities package initializer
│   │       ├── helper.py          # Miscellaneous helper functions (e.g., generate_uuid)
│   │       ├── pdf_processor.py   # PDF parsing, MySQL table storage, and schema saving via SchemaManager
│   │       ├── schema_manager.py  # Manages table_schema.json
│   │       ├── table_schema.json  # Stores inferred schemas for tables from PDFs, linked by pdf_uuid
│   │       └── upload_pdf.py      # PDF upload handling utilities, generates pdf_uuid
│   └── frontend/                  # Source code for the Streamlit frontend
│       └── streamlit_app.py       # Main Streamlit application file
├── tests/                         # Directory for automated tests
│   ├── conftest.py
│   ├── test_agents/
│   │   └── test_rag_agent.py      # Example test for RAG agent
│   └── test_routes/
│       └── test_chat_routes.py    # Example test for chat routes
└── README.md                      # Main project documentation file
```
*Note: The file `src/backend/test_manager_agent.py` was noted in previous versions; tests should ideally reside in the `tests/` directory. The structure above reflects the addition of `table_agent.py`, `schema_manager.py`, `table_schema.json` and `clear_data_service.py`.*

This structure promotes a clear separation of concerns between the frontend and backend, making the codebase easier to navigate, understand, and maintain.

## 4. Data Flow / Process Flow

The primary interactions involve the user (via the Streamlit frontend) and the FastAPI backend.

### 4.1. PDF Upload and Processing Flow

1.  **User Action (Frontend)**: User selects a PDF file and clicks "Upload" in the Streamlit UI (`streamlit_app.py`).
2.  **Frontend Request**: The Streamlit app sends a `POST` request to the backend's `/uploadpdf` endpoint (defined by `ENDPOINT` env var), with the PDF file in `multipart/form-data`.
3.  **Backend Routing (`routes/chat.py`)**: The `/uploadpdf` path operation function:
    -   Receives the `UploadFile`.
    -   Calls `process_pdf_upload` from `src/backend/utils/upload_pdf.py`.
4.  **PDF Upload Utility (`utils/upload_pdf.py` - `process_pdf_upload` function)**:
    -   Generates a unique `pdf_uuid` using `helper.generate_uuid()`.
    -   Validates the file (name, type, size based on `Config`).
    -   Saves the PDF to a temporary file.
    -   **Instantiates `PDFProcessor` and `EmbeddingService`**.
    -   Calls `pdf_processor.extract_content()`:
        -   Uses `pdfplumber` to parse text and tables from the PDF.
    -   For each extracted table:
        -   Calls `pdf_processor.store_table(table_data, table_name, pdf_uuid)`: Infers schema, creates a table in MySQL, inserts data, and importantly, calls `SchemaManager.save_schema()` to record the table's schema along with the `pdf_uuid` in `table_schema.json`.
    -   For extracted text chunks:
        -   Calls `embedding_service.store_text_embeddings(chunks, filename, pdf_uuid)`: Generates embeddings using Gemini and upserts text chunks and embeddings into Pinecone, tagging them with `pdf_uuid` metadata.
    -   Cleans up the temporary file.
5.  **Backend HTTP Response**: The `process_pdf_upload` function returns a JSON response (e.g., `{"success": true, "filename": "doc.pdf", "pdf_uuid": "unique-id", "tables_stored": 2, "text_chunks_stored": 50}`) via the route handler to the Streamlit frontend. The `pdf_uuid` is crucial for subsequent Q&A.
6.  **Frontend Update**: The Streamlit app receives the response, stores the `pdf_uuid` (e.g., in session state), and updates the UI.

**Text-based Diagram (Upload Flow):**
```
User --(Uploads PDF)--> [Streamlit Frontend: streamlit_app.py]
  | (POST /uploadpdf + PDF File, via ENDPOINT)
  v
[FastAPI Backend: routes/chat.py - /uploadpdf endpoint]
  | (UploadFile)
  v
[Backend Util: utils/upload_pdf.py - process_pdf_upload()]
  | 1. Generate pdf_uuid
  | 2. Validate File, Create Temp File
  | 3. Instantiate PDFProcessor, EmbeddingService, SchemaManager (via PDFProcessor)
  | 4. Call pdf_processor.extract_content(temp_file_path) --> (Text Chunks, Tables)
  | 5. For each Table:
  |    Call pdf_processor.store_table(table_data, table_name, pdf_uuid)
  |      --> Stores in MySQL
  |      --> Calls schema_manager.save_schema(..., pdf_uuid) --> (Updates table_schema.json)
  | 6. For Text Chunks:
  |    Call embedding_service.store_text_embeddings(chunks, filename, pdf_uuid) --> (Store in Pinecone with pdf_uuid)
  | 7. Cleanup Temp File
  | (JSON Response: success, counts, pdf_uuid)
  v
[FastAPI Backend: routes/chat.py] --(JSON Response)--> [Streamlit Frontend (stores pdf_uuid)] --(UI Update)--> User
```

### 4.2. Question Answering Flow

1.  **User Action (Frontend)**: User types a question into the chat input in the Streamlit UI and submits it. The frontend retrieves the `pdf_uuid` associated with the current document/session.
2.  **Frontend Request**: The Streamlit app sends a `POST` request to the backend's `/answer` endpoint with a JSON payload: `{"query": "User's question", "pdf_uuid": "active_pdf_uuid"}` (defined by `QueryRequest` model).
3.  **Backend Routing (`routes/chat.py`)**: The `/answer` path operation function:
    -   Receives the request, validates against `QueryRequest` (which now includes `pdf_uuid`).
    -   Retrieves the `Orchestrator` instance from `fastapi_request.app.state.orchestrator`.
    -   Calls `orchestrator.process_query()`, passing the user's query string and the `pdf_uuid`.
4.  **Backend Orchestration (`services/orchestrator.py` - `process_query` method)**:
    -   Delegates the query and `pdf_uuid` to `manager_agent.process_query(query, pdf_uuid)`.
5.  **Manager Agent Processing (`agents/manager_agent.py` - `process_query` method)**:
    -   Initializes `AgentState` with `query` and `pdf_uuid`.
    -   Uses LangGraph workflow:
        -   **Manager Node**:
            -   Calls `_load_table_schema(pdf_uuid)` to get schemas relevant to the specific PDF from `table_schema.json` (via `SchemaManager`).
            -   Analyzes query using an LLM against these specific schemas to determine if it needs "table", "rag", or "both". Sets state flags (`needs_table`, `needs_rag`).
        -   **Conditional Routing**:
            -   If `needs_table`: Routes to **Table Node**.
                -   **Table Node**: Invokes `table_agent.process_query(state.query, state.pdf_uuid)`. `TableAgent` uses the `pdf_uuid` to fetch relevant schemas (again, if needed, or relies on schemas passed by Manager) and generate/execute SQL against MySQL. Returns `table_response`.
            -   If `needs_rag` (either directly or after table processing if "both"): Routes to **RAG Node**.
                -   **RAG Node**: Calls `chatbot_agent.answer_question(state.query, pdf_uuid=state.pdf_uuid)`. `ChatbotAgent` uses `EmbeddingService` to search Pinecone, filtering by `pdf_uuid` for context-specific RAG. Returns `rag_response`.
        -   **Combiner Node**: Calls `combiner_agent.combine_responses(original_query, table_response, rag_response)`.
            -   `CombinerAgent` uses an LLM to synthesize a final answer.
    -   Returns the combined answer and metadata.
6.  **Backend HTTP Response**: The `Orchestrator` returns the result from `ManagerAgent`. The route handler sends a JSON response (e.g., `{"answer": "...", "success": true, "metadata": {"used_table": true, "used_rag": false}}`) back to the Streamlit frontend.
7.  **Frontend Update**: The Streamlit app receives the answer and displays it in the chat interface.

**Text-based Diagram (Question Answering Flow):**
```
User --(Asks Question)--> [Streamlit Frontend: streamlit_app.py (retrieves pdf_uuid)]
  | (POST /answer + JSON Query {query, pdf_uuid}, via ENDPOINT)
  v
[FastAPI Backend: routes/chat.py - /answer endpoint]
  | (Query String, pdf_uuid from QueryRequest)
  | (Retrieves Orchestrator from app.state)
  v
[Backend Orchestrator: process_query(query, pdf_uuid)]
  | (Query String, pdf_uuid)
  v
[Manager Agent: process_query(query, pdf_uuid) via LangGraph Workflow]
  | 0. Initial State: {query, pdf_uuid}
  | 1. Manager Node:
  |    a. _load_table_schema(pdf_uuid) --> (Fetches relevant schemas from table_schema.json via SchemaManager)
  |    b. Analyze query (LLM) with PDF-specific schemas -> needs_table? needs_rag?
  | 2. Conditional Routing:
  |    |--(if table_needed)--> [Table Node: table_agent.process_query(query, pdf_uuid)]
  |    |                         | a. (TableAgent potentially re-fetches/uses schema for pdf_uuid)
  |    |                         | b. Generate & Execute SQL on MySQL
  |    |                         `--> table_response
  |    |--(if rag_needed)-----> [RAG Node: chatbot_agent.answer_question(query, pdf_uuid)]
  |    |                          | a. Embed Query
  |    |                          | b. Search Pinecone (via EmbeddingService, filtering by pdf_uuid)
  |    |                          | c. Build Prompt, Get LLM Answer (Gemini)
  |    |                          `--> rag_response
  | 3. Combiner Node: combiner_agent.combine_responses(query, table_resp, rag_resp) (LLM) --> final_answer
  | (Final Answer & Metadata)
  v
[Backend Orchestrator] --(Answer)--> [Backend Path Operation Function] --(JSON Response from AnswerResponse)--> [Streamlit Frontend] --(Display Answer)--> User
```

## 5. Configuration Management

Configuration is managed via environment variables, facilitated by `.env` files for local development. The `src/backend/config.py` module centralizes access to these.

-   **Backend Configuration (`src/backend/config.py`)**:
    -   The `Config` class loads settings (API keys, Pinecone details, database URL, `APP_ENV`, `PORT`, `LOG_LEVEL`, etc.) from environment variables.
    -   Refer to `.env.template` for variables like `GEMINI_API_KEY`, `PINECONE_API_KEY`, `PINECONE_INDEX_NAME`, `PINECONE_DIMENSION`, `PINECONE_CLOUD`, `PINECONE_REGION`, `DATABASE_URL`, `MAX_FILE_SIZE`, `ALLOWED_EXTENSIONS`, `LOG_LEVEL`.
    -   `DATABASE_URL` is a crucial variable for connecting to the MySQL database used by `PDFProcessor` and `TableAgent`.
-   **Frontend Configuration (`src/frontend/streamlit_app.py`)**:
    -   Primarily requires the `ENDPOINT` environment variable for the backend API URL.
-   **`.env` Files**: A single `.env` file at the project root can store variables for both backend and frontend. This file is gitignored.
-   **Validation**: The backend's `Config` class includes methods or leverages Pydantic to validate that critical environment variables are provided.
-   **Access**:
    -   Backend: Configurations are imported from `src.backend.config` (e.g., `from ..config import config`).
    -   Frontend: `os.getenv('ENDPOINT')` is used in `streamlit_app.py`.
