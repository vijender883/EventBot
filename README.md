# EventBot

A PDF document assistant with a FastAPI-based backend and a Streamlit-based frontend. The backend integrates with Google Gemini AI, Pinecone vector database, and MySQL. It allows users to upload PDF files (extracting text for vector search and tables for structured data querying) and ask questions about their content using natural language via the frontend interface. Event bot(https://eventbot-pinecone-db.streamlit.app/)

## 📖 Table of Contents

- [🚀 Features](#-features)
- [🏛️ Logic Architecture](#️-logic-architecture)
- [📋 Prerequisites](#-prerequisites)
- [🛠️ Installation & Setup](docs/INSTALLATION.md)
- [🔑 API Keys Setup](docs/INSTALLATION.md#-api-keys-setup)
- [⚙️ Environment Configuration](docs/INSTALLATION.md#environment-configuration)
- [🚀 Running Locally](docs/INSTALLATION.md#-running-locally)
  - [Running the Backend](#running-the-backend)
  - [Running the Frontend](#running-the-frontend)
- [📡 API Endpoints](#-api-endpoints)
- [🌐 Deploy to Render.com](docs/INSTALLATION.md#-deploy-to-rendercom)
- [🔧 Development](#-development)
  - [Project Structure](#project-structure)
  - [Key Components](#key-components)
  - [Environment Variables](#environment-variables)
- [🧪 Running Tests](#-running-tests)
- [🛠️ Troubleshooting](#️-troubleshooting)
- [📊 Monitoring](#-monitoring)
- [🔒 Security](#-security)
- [📝 License](#-license)
- [🤝 Contributing](#-contributing)
- [📞 Support](#-support)

## 🚀 Features

- **Comprehensive PDF Document Processing**: Upload PDF files, extracting both text (for semantic search) and tables (for structured data storage in MySQL).
- **Hybrid AI-Powered Q&A**: Ask questions that can be answered by retrieving unstructured text (via RAG with Google Gemini & Pinecone) or querying structured table data.
- **Intelligent Response Combination**: An agentic system determines the best way to answer a query and combines information from different sources into a coherent response.
- **Vector Search**: Efficient document retrieval using Pinecone vector database for text segments.
- **Relational Data Storage**: Extracted tables from PDFs are stored in a MySQL database, enabling structured queries.
- **Streamlit Frontend**: User-friendly interface for uploading PDFs and interacting with the chatbot.
- **RESTful API**: Clean REST endpoints for the backend, consumed by the frontend.
- **Health Monitoring**: Built-in health checks and logging for the backend.
- **Agentic System with LangGraph**: Utilizes LangGraph for defining and running the multi-agent system (ManagerAgent, RAGAgent, CombinerAgent) for complex query processing.
- **Modular Design**: Clearly defined modules for agents, services, routing, and utilities.

## 🏛️ Logic Architecture

[Link to Logic Architecture Document will be added here once available]
_(Please see `docs/ARCHITECTURE.md` for a detailed system architecture description based on the codebase)._

## 📋 Prerequisites

- Python 3.8 or higher
- Google AI Studio account (for Gemini API key)
- Pinecone account (for Pinecone API key and index)
- MySQL compatible database (e.g., local MySQL, AWS RDS)
- Git

## 🛠️ Installation & Setup

For a quick start, follow these steps:

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/vijender883/EventBot
    cd EventBot
    ```

2.  **Create and Activate Virtual Environment:**
    *   **macOS/Linux:**
        ```bash
        python3 -m venv venv
        source venv/bin/activate
        ```
    *   **Windows (Command Prompt):**
        ```cmd
        python -m venv venv
        venv\Scripts\activate
        ```
    *For PowerShell or other shells, please refer to the detailed guide.*

3.  **Install Dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

For comprehensive instructions, including API key setup, environment configuration (especially `DATABASE_URL`), running the application, deployment, and troubleshooting, please see our [Detailed Installation and Setup Guide](docs/INSTALLATION.md).

### Running the Backend

To run the FastAPI backend server:
```bash
make run-backend
# Alternatively: uvicorn app:app --reload
```
The backend will typically start on `http://localhost:8000` (FastAPI's default) or `http://localhost:5000` if configured.

### Running the Frontend

To run the Streamlit frontend application:
1.  Ensure the backend is running.
2.  Set the `ENDPOINT` environment variable if your backend is not on `http://localhost:5000`. For local development, you can add `ENDPOINT=http://localhost:5000` (or your backend's port) to your `.env` file.
```bash
make run-frontend
# Alternatively: streamlit run src/frontend/streamlit_app.py
```
The frontend will typically be available at `http://localhost:8501`.

## 📡 API Endpoints

The API routes are primarily defined in `src/backend/routes/chat.py`. The root `/` endpoint is in `app.py`.

| Endpoint     | Method | Description                                          | Request Body (Format)         | Success Response (JSON Example)                                                                                                |
|--------------|--------|------------------------------------------------------|-------------------------------|--------------------------------------------------------------------------------------------------------------------------------|
| `/`          | GET    | Basic API information and available endpoints.       | N/A                           | `{"message": "PDF Assistant Chatbot API", "version": "1.0.0", "endpoints": {"/health": "GET - Health check", ...}}` (from `chat.py`) |
| `/health`    | GET    | Detailed health check of backend services.           | N/A                           | `{"status": "healthy", "services": {"manager_agent_health": {...}}, "overall_health": true}`                                   |
| `/uploadpdf` | POST   | Uploads a PDF file for processing, text vectorization (Pinecone), and table storage (MySQL). | FormData: `file` (PDF file)   | `{"success": true, "message": "PDF processed...", "filename": "name.pdf", "tables_stored": 1, "text_chunks_stored": 10}`            |
| `/answer`    | POST   | Asks a question about the processed PDF content.     | JSON: `{"query": "Your question?"}` | `{"answer": "AI generated answer.", "success": true, "error": null}`                                                                                           |

For deployment instructions, see the [Detailed Installation and Setup Guide](docs/INSTALLATION.md#-deploy-to-rendercom).

## 🔧 Development

### Project Structure
```
EventBot/
├── .env                           # Local environment variables (gitignored)
├── .env.template                  # Template for .env file
├── .git/                          # Git version control directory
├── .gitignore                     # Specifies intentionally untracked files for Git
├── README.md                      # This guide
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
│   │   │   └── rag_agent.py       # Implements the RAG-based chatbot logic (ChatbotAgent)
│   │   ├── config.py              # Centralized backend application configuration
│   │   ├── models.py              # Pydantic models for API requests/responses
│   │   ├── routes/                # Defines API endpoints
│   │   │   ├── __init__.py        # Router package initializer
│   │   │   └── chat.py            # Chat-related API endpoint definitions
│   │   ├── services/              # Service layer
│   │   │   ├── __init__.py        # Service package initializer
│   │   │   ├── embedding_service.py # Handles text embeddings and Pinecone storage
│   │   │   └── orchestrator.py    # Orchestrates interactions with ManagerAgent
│   │   ├── test_manager_agent.py  # Test script for ManagerAgent (currently in `src/backend/`, consider moving to `tests/`)
│   │   └── utils/                 # Backend utility functions and helpers
│   │       ├── __init__.py        # Utilities package initializer
│   │       ├── helper.py          # Miscellaneous helper functions
│   │       ├── pdf_processor.py   # PDF parsing and MySQL table storage
│   │       └── upload_pdf.py      # PDF upload handling utilities
│   └── frontend/                  # Source code for the Streamlit frontend
│       └── streamlit_app.py       # Main Streamlit application file
├── tests/                         # Directory for automated tests
│   ├── conftest.py
│   ├── test_agents/
│   │   └── test_rag_agent.py      # Example test for RAG agent
│   └── test_routes/
│       └── test_chat_routes.py    # Example test for chat routes
```

### Key Components

**Backend:**
-   **`app.py`**: Initializes the FastAPI app, loads configuration, sets up the `Orchestrator` (which initializes agents), and includes API routers.
-   **`src/backend/routes/chat.py`**: Defines API endpoints (`/health`, `/uploadpdf`, `/answer`) and delegates requests to appropriate handlers (e.g., `Orchestrator` for Q&A, `upload_pdf` util for uploads).
-   **`src/backend/services/orchestrator.py`**: Central coordinator that uses `ManagerAgent` for processing queries.
- **`src/backend/agents/manager_agent.py`**: Core agent using LangGraph. Analyzes queries, routes them to `TableAgent` for structured data queries or `ChatbotAgent` (RAG) for unstructured information, and then combines results using `CombinerAgent`.
- **`src/backend/agents/table_agent.py`**: Specialized agent for querying structured data from MySQL tables based on the query and PDF context.
- **`src/backend/agents/rag_agent.py` (Class `ChatbotAgent`)**: Specialized agent for RAG, performing similarity search in Pinecone and generating answers with Gemini based on unstructured text.
- **`src/backend/agents/combiner_agent.py`**: Merges responses from different sources (e.g., `TableAgent` and `ChatbotAgent`) into a single, coherent answer using an LLM.
-   **`src/backend/services/embedding_service.py`**: Manages text embedding generation (Gemini) and storage/retrieval in Pinecone.
- **`src/backend/utils/pdf_processor.py`**: Extracts text and tables from PDFs. Stores table data in MySQL and provides schema information.
-   **`src/backend/utils/upload_pdf.py`**: Handles the PDF upload process, coordinating `PDFProcessor` and `EmbeddingService`.
-   **`src/backend/config.py`**: Manages application configuration from environment variables.
-   **`src/backend/models.py`**: Contains Pydantic models for API request/response validation.

**Frontend:**
-   **`src/frontend/streamlit_app.py`**: A Streamlit application providing the user interface. It interacts with the backend API.

### Project Structure
```
EventBot/
├── .env                           # Local environment variables (gitignored)
├── .env.template                  # Template for .env file
├── .git/                          # Git version control directory
├── .gitignore                     # Specifies intentionally untracked files for Git
├── README.md                      # This guide
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
│   │   │   ├── embedding_service.py # Handles text embeddings and Pinecone storage
│   │   │   └── orchestrator.py    # Orchestrates interactions with ManagerAgent
│   │   ├── utils/                 # Backend utility functions and helpers
│   │   │   ├── __init__.py        # Utilities package initializer
│   │   │   ├── helper.py          # Miscellaneous helper functions
│   │   │   ├── pdf_processor.py   # PDF parsing and MySQL table storage
│   │   │   ├── schema_manager.py  # Manages table schemas (e.g., from table_schema.json)
│   │   │   ├── table_schema.json  # Stores inferred schemas for tables from PDFs
│   │   │   └── upload_pdf.py      # PDF upload handling utilities
│   └── frontend/                  # Source code for the Streamlit frontend
│       └── streamlit_app.py       # Main Streamlit application file
├── tests/                         # Directory for automated tests
│   ├── conftest.py
│   ├── test_agents/
│   │   └── test_rag_agent.py      # Example test for RAG agent
│   └── test_routes/
│       └── test_chat_routes.py    # Example test for chat routes
```
*Note: `src/backend/test_manager_agent.py` was present in the original structure; ideally, tests should reside in the `tests/` directory.*


### Environment Variables

The application uses environment variables for configuration. These are typically defined in a `.env` file in the project root for local development. See `.env.template` for a list of required variables.

**Backend Variables:**
-   `GEMINI_API_KEY`: Your Google Gemini API key.
-   `PINECONE_API_KEY`: Your Pinecone API key.
-   `PINECONE_INDEX_NAME`: The name of your Pinecone index.
-   `PINECONE_DIMENSION`: The dimension of vectors for Pinecone (e.g., 768 for `models/embedding-001`).
-   `PINECONE_CLOUD`: The cloud provider for your Pinecone index (e.g., `aws`).
-   `PINECONE_REGION`: The region of your Pinecone index (e.g., `us-east-1`).
-   `DATABASE_URL`: Connection string for your MySQL database (e.g., `mysql+mysqlconnector://user:password@host:port/database`). Critical for table storage and querying.
-   `APP_ENV`: Set to `development` or `production`.
-   `PORT`: Port for the backend server (defaults to `8000` or `5000`).
-   `LOG_LEVEL`: Optional, sets the logging level (e.g., `DEBUG`, `INFO`).

**Frontend Variables:**
-   `ENDPOINT`: The URL of the backend API (e.g., `http://localhost:5000`).

## 🧪 Running Tests

*(This section outlines general steps. Specific test setup might vary.)*

1.  **Install Test Dependencies**: If you haven't already, install development dependencies:
    ```bash
    pip install -r requirements-dev.txt
    ```
2.  **Configure Environment for Tests**: Ensure your `.env` file (or environment variables) are set up correctly, as tests might interact with external services if not properly mocked.
3.  **Run Tests**: Navigate to the project root directory and execute:
    ```bash
    pytest
    ```
    Pytest will automatically discover and run tests (typically files named `test_*.py` or `*_test.py` in the `tests/` directory).

Refer to the `tests/` directory and any specific test documentation or configuration files for more detailed instructions on running tests.

## 🛠️ Troubleshooting

For troubleshooting common installation and setup issues, refer to the [Detailed Installation and Setup Guide](docs/INSTALLATION.md#-troubleshooting).

### Debug Mode (Local Development)

For more verbose error output locally:
1.  Set `APP_ENV=development` in your `.env` file. This often enables FastAPI's debug mode.
2.  Optionally, set `LOG_LEVEL=DEBUG` in `.env` for more detailed application logs (our application uses this).
3.  Run the app (e.g., `uvicorn app:app --reload`).

## 📊 Monitoring

### Health Checks

The `/health` endpoint (see [API Endpoints](#-api-endpoints)) provides detailed status of backend components, including the different agents. Regularly polling this endpoint can help ensure system availability.

### Logs

-   **Local Development**: Logs are output to the console where `uvicorn app:app` is running. Adjust `LOG_LEVEL` in `.env` for desired verbosity (e.g., `INFO`, `DEBUG`).
-   **Render Deployment**: Access and monitor logs via the Render dashboard for your service. This is crucial for diagnosing issues in the production environment.

Key information to look for in logs:
-   Successful/failed PDF uploads and processing durations (including table and text chunk counts).
-   Question answering request details, including routing decisions by `ManagerAgent` and responses from `TableAgent` or `ChatbotAgent`.
-   Errors from external services (Gemini, Pinecone, MySQL).
-   Any unexpected application exceptions or tracebacks.

## 🔒 Security

-   **API Keys & Database Credentials**: Handled via environment variables (`.env` locally, Render's environment settings). Never hardcode credentials. Ensure `.env` is in `.gitignore`.
-   **File Uploads**:
    *   `werkzeug.utils.secure_filename` is used to sanitize filenames.
    *   File type and size are validated as per `ALLOWED_EXTENSIONS` and `MAX_FILE_SIZE` in the app configuration (`src/backend/config.py`).
-   **Input Validation**: Pydantic models (`src/backend/models.py`) are used for request validation in API endpoints.
-   **SQL Injection**:
    *   `TableAgent` uses an LLM to generate SQL queries. While this is powerful, it requires careful prompt engineering to prevent SQL injection. The current implementation relies on the LLM's ability to generate safe SQL based on schema and query descriptions.
    *   `PDFProcessor` when storing tables uses parameterized queries or ORM-like behavior if applicable, which is generally safer.
    *   **Recommendation**: Implement strict validation and sanitization of any table/column names or values derived from LLM output before using them in SQL queries, or use query builders that parameterize inputs.
-   **CORS**: FastAPI handles CORS through `CORSMiddleware`. Ensure it's configured securely, especially in production, by specifying allowed origins, methods, and headers. Example from `src/backend/__init__.py`:
    ```python
    from fastapi.middleware.cors import CORSMiddleware

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"], # Adjust for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    ```
-   **Error Handling**: FastAPI has built-in support for returning structured JSON error responses (e.g., using `HTTPException`) and allows for custom exception handlers. This helps avoid exposing raw stack traces.
-   **Dependency Management**: Keep `requirements.txt` and `requirements-dev.txt` up-to-date. Regularly audit dependencies for vulnerabilities using tools like `pip-audit` or GitHub's Dependabot.
-   **HTTPS**: Render automatically provides HTTPS for deployed services. For local development, consider using a reverse proxy like Caddy or Nginx if HTTPS is needed.

## 📝 License

This project is licensed under the MIT License. It's good practice to include a `LICENSE` file in the repository root with the full text of the MIT License.

## 🤝 Contributing

Contributions are welcome! Please adhere to the following process:

1.  **Fork the Repository**: Create your own fork on GitHub.
2.  **Create a Branch**: `git checkout -b feature/your-new-feature` or `bugfix/issue-description`.
3.  **Develop**: Make your changes.
4.  **Test**: Add and run tests for your changes using `pytest`. Ensure tests cover new functionality and don't break existing features.
5.  **Commit**: Write clear, concise commit messages.
6.  **Push**: Push your branch to your fork: `git push origin your-branch-name`.
7.  **Pull Request**: Open a PR against the `main` branch of the original repository. Clearly describe your changes and link any relevant issues. Ensure your PR passes any CI checks.

## 📞 Support

If you encounter issues or have questions:

-   **Check GitHub Issues**: See if your question or problem has already been addressed.
-   **Review Troubleshooting Section**: The [Detailed Installation and Setup Guide](docs/INSTALLATION.md#-troubleshooting) might have a solution.
-   **Create a New Issue**: If your issue is new, provide detailed information:
    *   Steps to reproduce.
    *   Expected vs. actual behavior.
    *   Error messages and relevant logs.
    *   Your environment (OS, Python version, relevant package versions).
-   For Render-specific deployment issues, consult the [Render documentation](https://render.com/docs).

---

**Happy coding! 🚀**