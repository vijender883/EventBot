# System Architecture Documentation

## 1. Introduction/Overview

This document outlines the architecture of EventBot. The system comprises a FastAPI-based Python backend and a Streamlit-based Python frontend. The backend processes PDF documents, extracting text for vector storage (Pinecone) and tables for relational storage (MySQL). It answers user questions using an agentic system involving Retrieval Augmented Generation (RAG) with Google Gemini, table data querying, and intelligent response combination. The frontend provides a user interface for uploading PDFs and interacting with the chatbot.

The architecture emphasizes modularity, separating concerns into distinct components for the user interface, backend request handling, core processing logic (including multiple agents and services), external service interactions, and configuration management. This approach aims for maintainability, scalability, and clarity.

## 2. Directory and File Structure Overview

The codebase is organized as follows:

```
EventBot/
├── app.py                         # Main FastAPI application entry point
├── clear_data_script.py           # Script for clearing data
├── docs/
│   ├── API.md
│   ├── ARCHITECTURE.md            # (this file)
│   ├── DEPLOYMENT.md
│   └── INSTALLATION.md
├── logs/                          # Log files
├── Makefile                       # Common tasks (run, test, lint)
├── README.md                      # Main documentation
├── requirements.txt               # Python dependencies
├── requirements-dev.txt           # Dev dependencies
├── scripts/
│   └── start.sh                   # Script to start backend
├── src/
│   ├── backend/
│   │   ├── __init__.py            # FastAPI app setup and service initialization
│   │   ├── agents/
│   │   │   ├── base.py            # Abstract base class for chatbot agents
│   │   │   ├── combiner_agent.py  # Combines responses from Table and RAG agents
│   │   │   ├── manager_agent.py   # Orchestrates query processing (LangGraph)
│   │   │   ├── rag_agent.py       # RAG-based chatbot logic (ChatbotAgent)
│   │   │   └── table_agent.py     # Handles SQL generation and execution for table data
│   │   ├── config.py              # Centralized backend configuration
│   │   ├── models.py              # Pydantic models for API requests/responses
│   │   ├── routes/
│   │   │   ├── __init__.py        # Router package initializer
│   │   │   └── chat.py            # API endpoints for chat, upload, health, etc.
│   │   ├── services/
│   │   │   ├── __init__.py        # Service package initializer
│   │   │   ├── clear_data_service.py # Service for clearing data from DB and Pinecone
│   │   │   ├── embedding_service.py  # Handles text embeddings and Pinecone storage
│   │   │   └── orchestrator.py    # Orchestrates interactions with ManagerAgent
│   │   ├── test_manager_agent.py  # Example/test script for ManagerAgent
│   │   └── utils/
│   │       ├── __init__.py        # Utilities package initializer
│   │       ├── helper.py          # Miscellaneous helper functions (e.g., error handlers)
│   │       ├── pdf_processor.py   # PDF parsing, MySQL table storage, schema saving
│   │       ├── schema_manager.py  # Manages table_schema.json (schema CRUD, docs)
│   │       ├── table_schema.json  # Stores inferred schemas for tables from PDFs
│   │       └── upload_pdf.py      # PDF upload handling, triggers extraction/storage
│   └── frontend/
│       └── streamlit_app.py       # Main Streamlit application file (UI)
├── tests/
│   ├── conftest.py
│   ├── test_agents/
│   │   └── test_rag_agent.py      # Test for RAG agent
│   └── test_routes/
│       └── test_chat_routes.py    # Test for chat routes
├── uploads/                       # Uploaded files (if any)
└── venv/                          # Python virtual environment
```

## 3. File-by-File Functionality

### Backend: `src/backend/`

- **`__init__.py`**: Initializes the FastAPI app, configures CORS, loads config, and sets up core services (ChatbotAgent, ManagerAgent, Orchestrator). Adds exception handlers and includes API routers.

#### Agents: `src/backend/agents/`
- **`base.py`**: Abstract base class for chatbot agents. Defines the interface for `answer_question` and `health_check` methods.
- **`combiner_agent.py`**: Combines responses from Table and RAG agents using Gemini LLM. Ensures a coherent, user-friendly answer.
- **`manager_agent.py`**: Central orchestrator using LangGraph. Analyzes queries, decides routing (table, RAG, or both), manages state, and invokes sub-agents. Handles workflow for multi-source Q&A.
- **`rag_agent.py`**: Implements the RAG (Retrieval Augmented Generation) agent. Handles vector search in Pinecone and uses Gemini for answer generation. Inherits from `BaseChatbotAgent`.
- **`table_agent.py`**: Handles SQL query generation (via Gemini) and execution on MySQL. Loads schema from `table_schema.json`, filters by PDF UUID, and formats results for the user.

#### Configuration and Models
- **`config.py`**: Loads and validates environment variables for database, Pinecone, Gemini, and app settings. Provides a `Config` class and a global `config` instance.
- **`models.py`**: Pydantic models for API request/response validation (e.g., `QueryRequest`, `AnswerResponse`, `UploadResponse`). Ensures data consistency and clear API contracts.

#### Routing: `src/backend/routes/`
- **`__init__.py`**: Makes the `routes` directory a Python package.
- **`chat.py`**: Defines API endpoints for root (`/`), health check (`/health`), answering questions (`/answer`), PDF upload (`/uploadpdf`), clearing all data, and data summary. Delegates logic to orchestrator and utility functions.

#### Services: `src/backend/services/`
- **`__init__.py`**: Service package initializer.
- **`clear_data_service.py`**: Service for clearing all data from Pinecone and MySQL, and for summarizing current data.
- **`embedding_service.py`**: Handles creation and storage of text embeddings in Pinecone using Gemini. Provides methods for generating, storing, and searching embeddings.
- **`orchestrator.py`**: High-level coordinator between API routes and backend processing. Delegates queries to ManagerAgent and aggregates health checks.

#### Utilities: `src/backend/utils/`
- **`__init__.py`**: Provides initialization for core services (e.g., embedding service). Exports utility functions.
- **`helper.py`**: Miscellaneous helper functions, including custom error handlers for FastAPI.
- **`pdf_processor.py`**: Extracts text and tables from PDFs using `pdfplumber`. Infers table schemas with Gemini, stores tables in MySQL, and updates `table_schema.json` via `SchemaManager`.
- **`schema_manager.py`**: Manages the `table_schema.json` file. Provides CRUD for schemas, exports documentation, validates schemas, and supports CLI usage.
- **`table_schema.json`**: JSON file storing inferred schemas for all tables extracted from PDFs, keyed by table name and including PDF UUIDs.
- **`upload_pdf.py`**: Handles PDF upload logic. Validates file, saves temporarily, triggers extraction/storage, and manages embedding storage. Returns processing summary.

#### Test/Example
- **`test_manager_agent.py`**: Example script for testing the ManagerAgent with various queries. Demonstrates routing and health checks.

### Frontend: `src/frontend/`
- **`streamlit_app.py`**: Main Streamlit application. Provides UI for PDF upload, chat interface, error handling, and API communication. Manages session state, displays chat history, and handles user interactions.

## 4. Data Flow / Process Flow

### 4.1. PDF Upload and Processing Flow
1. **User Action (Frontend)**: User uploads a PDF via Streamlit UI.
2. **Frontend Request**: Sends a `POST` request to `/uploadpdf` with the PDF file.
3. **Backend Routing**: `/uploadpdf` endpoint in `chat.py` calls `process_pdf_upload` in `upload_pdf.py`.
4. **Processing**: `process_pdf_upload` validates, saves, and processes the PDF:
    - Uses `PDFProcessor` to extract text/tables, store tables in MySQL, and update schemas.
    - Uses `EmbeddingService` to store text embeddings in Pinecone.
5. **Response**: Returns a summary (including `pdf_uuid`) to the frontend.
6. **Frontend Update**: Stores `pdf_uuid` for future queries.

### 4.2. Question Answering Flow
1. **User Action (Frontend)**: User submits a question in the chat UI.
2. **Frontend Request**: Sends a `POST` request to `/answer` with the question and `pdf_uuid`.
3. **Backend Routing**: `/answer` endpoint in `chat.py` delegates to the orchestrator.
4. **Orchestration**: Orchestrator calls `ManagerAgent.process_query`, which:
    - Analyzes the query and schema.
    - Routes to TableAgent, RAG Agent, or both.
    - Combines responses using CombinerAgent.
5. **Response**: Returns the answer to the frontend for display.

## 5. Configuration Management

- **Backend**: All configuration is managed via environment variables, loaded by `config.py`. Includes database, Pinecone, Gemini, and app settings.
- **Frontend**: Uses the `ENDPOINT` environment variable to locate the backend API.
- **.env**: Stores environment variables for local development (gitignored).

## 6. Summary Table: File Locations and Roles

| File/Folder                                 | Location                                 | Functionality/Role                                                                                 |
|---------------------------------------------|------------------------------------------|---------------------------------------------------------------------------------------------------|
| app.py                                     | EventBot/app.py                          | FastAPI app entry point                                                                           |
| clear_data_script.py                        | EventBot/clear_data_script.py            | Script to clear all data                                                                          |
| docs/                                      | EventBot/docs/                           | Documentation                                                                                    |
| logs/                                      | EventBot/logs/                           | Log files                                                                                        |
| Makefile                                   | EventBot/Makefile                        | Common tasks                                                                                      |
| README.md                                  | EventBot/README.md                       | Main documentation                                                                               |
| requirements.txt                           | EventBot/requirements.txt                | Python dependencies                                                                              |
| requirements-dev.txt                       | EventBot/requirements-dev.txt            | Dev dependencies                                                                                 |
| scripts/start.sh                            | EventBot/scripts/start.sh                | Script to start backend                                                                           |
| src/backend/__init__.py                    | EventBot/src/backend/__init__.py         | FastAPI app setup, service initialization                                                         |
| src/backend/agents/base.py                 | EventBot/src/backend/agents/base.py      | Abstract base class for chatbot agents                                                            |
| src/backend/agents/combiner_agent.py       | EventBot/src/backend/agents/combiner_agent.py | Combines Table and RAG responses using Gemini LLM                                           |
| src/backend/agents/manager_agent.py        | EventBot/src/backend/agents/manager_agent.py | Orchestrates query processing (LangGraph)                                                   |
| src/backend/agents/rag_agent.py            | EventBot/src/backend/agents/rag_agent.py | RAG-based chatbot logic (ChatbotAgent)                                                            |
| src/backend/agents/table_agent.py          | EventBot/src/backend/agents/table_agent.py | Handles SQL generation/execution for table data                                             |
| src/backend/config.py                      | EventBot/src/backend/config.py           | Loads and validates environment variables                                                         |
| src/backend/models.py                      | EventBot/src/backend/models.py           | Pydantic models for API requests/responses                                                        |
| src/backend/routes/__init__.py             | EventBot/src/backend/routes/__init__.py  | Router package initializer                                                                        |
| src/backend/routes/chat.py                 | EventBot/src/backend/routes/chat.py      | API endpoints for chat, upload, health, etc.                                                     |
| src/backend/services/__init__.py           | EventBot/src/backend/services/__init__.py| Service package initializer                                                                       |
| src/backend/services/clear_data_service.py | EventBot/src/backend/services/clear_data_service.py | Service for clearing data from DB and Pinecone                                         |
| src/backend/services/embedding_service.py  | EventBot/src/backend/services/embedding_service.py | Handles text embeddings and Pinecone storage                                             |
| src/backend/services/orchestrator.py       | EventBot/src/backend/services/orchestrator.py | Orchestrates interactions with ManagerAgent                                               |
| src/backend/test_manager_agent.py          | EventBot/src/backend/test_manager_agent.py| Example/test script for ManagerAgent                                                              |
| src/backend/utils/__init__.py              | EventBot/src/backend/utils/__init__.py   | Utilities package initializer, embedding service init                                            |
| src/backend/utils/helper.py                | EventBot/src/backend/utils/helper.py     | Miscellaneous helper functions, error handlers                                                   |
| src/backend/utils/pdf_processor.py         | EventBot/src/backend/utils/pdf_processor.py | PDF parsing, MySQL table storage, schema saving                                            |
| src/backend/utils/schema_manager.py        | EventBot/src/backend/utils/schema_manager.py | Manages table_schema.json, schema CRUD, docs, CLI                                         |
| src/backend/utils/table_schema.json        | EventBot/src/backend/utils/table_schema.json | Stores inferred schemas for tables from PDFs                                              |
| src/backend/utils/upload_pdf.py            | EventBot/src/backend/utils/upload_pdf.py | PDF upload handling, triggers extraction/storage, manages embedding storage                      |
| src/frontend/streamlit_app.py              | EventBot/src/frontend/streamlit_app.py   | Main Streamlit application file (UI)                                                             |
| tests/                                     | EventBot/tests/                          | Automated tests                                                                                   |
| uploads/                                   | EventBot/uploads/                        | Uploaded files (if any)                                                                          |
| venv/                                      | EventBot/venv/                           | Python virtual environment                                                                       |

---

This documentation is up to date with the current codebase structure and describes the location and role of each file in the system.
