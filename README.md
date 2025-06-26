# PDF Assistant Chatbot

A PDF document assistant with a FastAPI-based backend and a Streamlit-based frontend. The backend integrates with Google Gemini AI and Pinecone vector database, allowing users to upload PDF files and ask questions about their content using natural language via the frontend interface.

*(Note: The live demo link `https://eventbot-pinecone-db.streamlit.app/` should be verified if it points to the current FastAPI version or an older Flask version. Assuming it's current for now.)*
Event bot: [https://eventbot-pinecone-db.streamlit.app/](https://eventbot-pinecone-db.streamlit.app/)

## 📖 Table of Contents

- [🚀 Features](#-features)
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

- **PDF Document Processing**: Upload and process PDF files into searchable vectors.
- **AI-Powered Q&A**: Ask questions about uploaded PDFs using Google Gemini AI.
- **Vector Search**: Efficient document retrieval using Pinecone vector database.
- **Resume Support**: Special handling for resume/CV documents (filename-based user ID extraction).
- **Streamlit Frontend**: User-friendly interface for uploading PDFs and interacting with the chatbot.
- **RESTful API**: Clean REST endpoints for the backend, consumed by the frontend.
- **Health Monitoring**: Built-in health checks and logging for the backend.

## 📋 Prerequisites

- Python 3.8 or higher
- Google AI Studio account (for Gemini API key)
- Pinecone account (for Pinecone API key and index)
- Git

## 🛠️ Installation & Setup

For a quick start, follow these steps:

1.  **Clone the Repository:**
    ```bash
    git clone https://github.com/vijender883/Chatbot_Pinecone_flask_backend
    # Or your fork's URL if you've forked it
    cd Chatbot_Pinecone_flask_backend
    # The directory name might be different if the repo name changes, e.g., PDF-Assistant-Chatbot
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

For comprehensive instructions, including API key setup, environment configuration, running the application, deployment, and troubleshooting, please see our [Detailed Installation and Setup Guide](docs/INSTALLATION.md).

### Running the Backend

To run the FastAPI backend server:
```bash
make run-backend
# Alternatively: uvicorn app:app --reload --host 0.0.0.0 --port 8000
# (or the port specified in your .env file, e.g., 5000)
```
The backend will typically start on `http://localhost:8000` (Uvicorn's default if not overridden by `PORT` in `.env`) or the port specified in your `.env` file (e.g., `http://localhost:5000`). Check your `.env` or `src/backend/config.py` for the exact port.

### Running the Frontend

To run the Streamlit frontend application:
1.  Ensure the backend is running.
2.  Set the `ENDPOINT` environment variable in your `.env` file to point to your running backend. For local development, if your backend is running on port 8000, this would be `ENDPOINT=http://localhost:8000`. If it's on port 5000, use `ENDPOINT=http://localhost:5000`.
```bash
make run-frontend
# Alternatively: streamlit run src/frontend/streamlit_app.py
```
The frontend will typically be available at `http://localhost:8501`.

## 📡 API Endpoints

The API routes are defined in `src/backend/routes/chat.py` and mounted under the `/api/chat` prefix (or similar, check `src/backend/__init__.py` or `app.py` for how `chat_router` is included). The application entry point `app.py` initializes the FastAPI app.

| Endpoint          | Method | Description                                          | Request Body (Pydantic Model) / FormData | Success Response (Pydantic Model / JSON Example)                                                                              |
|-------------------|--------|------------------------------------------------------|------------------------------------------|-------------------------------------------------------------------------------------------------------------------------------|
| `/api/chat/`      | GET    | Basic API information for the chat routes.           | N/A                                      | `{"message": "PDF Assistant Chatbot API", "version": "1.0.0", "docs": "/docs", ...}` (Actual response from `chat.py`'s index) |
| `/api/chat/health`| GET    | Detailed health check of backend services.           | N/A                                      | `HealthResponse` model: `{"status": "success", "health": {"gemini_api": true, ...}, "healthy": true}`                         |
| `/api/chat/uploadpdf`| POST | Uploads a PDF file for processing and vectorization. | FormData: `file: UploadFile`             | `UploadResponse` model: `{"success": true, "message": "PDF 'name.pdf' uploaded...", "filename": "name.pdf"}`               |
| `/api/chat/answer`| POST   | Asks a question about the processed PDF content.     | `AnswerRequest` model: `{"query": "Your question?"}` | `AnswerResponse` model: `{"answer": "AI generated answer."}`                                                                  |

*Note: The exact root path for the chat API (e.g., `/api/chat`) depends on how the `chat_router` is included in the main `FastAPI` app instance in `app.py` or `src/backend/__init__.py`. The table assumes a prefix like `/api/chat`. FastAPI also provides automatic interactive API documentation at `/docs` and ReDoc at `/redoc` relative to the application root.*

For deployment instructions, see the [Detailed Installation and Setup Guide](docs/INSTALLATION.md#-deploy-to-rendercom).

## 🔧 Development

### Project Structure
```
PDF-Assistant-Chatbot/ (or Chatbot_Pinecone_flask_backend/)
├── .env                   # Local environment variables (gitignored)
├── .env.template          # Template for .env file
├── .git/                  # Git version control directory
├── .gitignore             # Specifies intentionally untracked files for Git
├── README.md              # This guide
├── Makefile               # Defines common tasks like running, testing, linting
├── app.py                 # Main FastAPI application entry point
├── requirements.txt       # Python package dependencies
├── requirements-dev.txt   # Development-specific dependencies (testing, linting)
├── start.sh               # Shell script for starting the backend (e.g., Uvicorn with Gunicorn)
├── src/                   # Main source code directory
│   ├── backend/           # Source code for the FastAPI backend
│   │   ├── __init__.py    # Initializes backend, creates FastAPI app, includes routers
│   │   ├── agents/
│   │   │   ├── base.py
│   │   │   └── rag_agent.py
│   │   ├── config.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   └── chat.py    # Defines APIRouter for chat functionalities
│   │   ├── services/
│   │   │   └── orchestrator.py
│   │   └── utils/
│   │       └── helper.py
│   └── frontend/          # Source code for the Streamlit frontend
│       └── streamlit_app.py # Main Streamlit application file
└── tests/                 # Automated tests
    ├── conftest.py
    ├── test_agents/
    │   └── test_rag_agent.py
    └── test_routes/
        └── test_chat_routes.py
```

### Key Components

**Backend (FastAPI):**
-   **`app.py`**: Main application script. Creates the FastAPI app instance using `src.backend.create_app()`. Handles Uvicorn server startup.
-   **`src/backend/__init__.py`**: Contains `create_app()` factory function which initializes the FastAPI application, loads configuration, sets up the `ChatbotAgent`, `Orchestrator`, and includes API routers (like `chat_router` from `src.backend.routes.chat`).
-   **`src/backend/routes/chat.py`**: Defines an `APIRouter` for chat-related endpoints (`/health`, `/uploadpdf`, `/answer`). Uses Pydantic models for request/response validation.
-   **`src/backend/agents/rag_agent.py`**: Core RAG logic (PDF processing, embeddings, Pinecone interaction, Gemini LLM communication).
-   **`src/backend/services/orchestrator.py`**: Service layer, delegating calls from route handlers to the `ChatbotAgent`.
-   **`src/backend/config.py`**: Manages application configuration (environment variables, application settings).

**Frontend:**
-   **`src/frontend/streamlit_app.py`**: A Streamlit application providing the user interface. It interacts with the backend API to upload PDFs and get answers to questions.

### Environment Variables

The application uses environment variables for configuration. These are typically defined in a `.env` file in the project root for local development. See `.env.template` for a list of required variables.

**Backend Variables:**
-   `GEMINI_API_KEY`: Your Google Gemini API key.
-   `PINECONE_API_KEY`: Your Pinecone API key.
-   `PINECONE_INDEX_NAME`: The name of your Pinecone index.
-   `PINECONE_CLOUD`: The cloud provider for your Pinecone index (e.g., `aws`).
-   `PINECONE_REGION`: The region of your Pinecone index (e.g., `us-east-1`).
-   `DEBUG`: Set to `True` or `False` (boolean). Controls FastAPI's debug mode (influences auto-reloading with Uvicorn, detailed error pages). This replaces `APP_ENV` or `FLASK_ENV` for debug purposes.
-   `HOST`: Host address for the backend server (defaults to `0.0.0.0`).
-   `PORT`: Port for the backend server (defaults to `5000` as per `src/backend/config.py`, but Uvicorn's default is `8000` if not set). It's important to ensure consistency or clarify which default takes precedence if `PORT` isn't in `.env`.

**Frontend Variables:**
-   `ENDPOINT`: The URL of the backend API. For local development, if the backend runs on port 5000 (as per `config.py` default), this would be `http://localhost:5000/api/chat`. If backend is on port 8000, it would be `http://localhost:8000/api/chat`. *The path `/api/chat` should be included if the Streamlit app expects to hit the chat router directly.*

## 🧪 Running Tests

*(This section outlines general steps. Specific test setup might vary.)*

For information on installing test dependencies, see the [Detailed Installation and Setup Guide](docs/INSTALLATION.md#-running-tests).

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
1.  Set `DEBUG=True` in your `.env` file. This enables FastAPI's debug mode.
2.  The Uvicorn server run via `make run-backend` or `uvicorn app:app --reload` will typically show more detailed logs when debug mode is on.
3.  You can also adjust Python's standard logging levels within the application if needed, though `DEBUG=True` often provides sufficient detail for development.

## 📊 Monitoring

### Health Checks

The `/health` endpoint (see [API Endpoints](#-api-endpoints)) provides detailed status of backend components. Regularly polling this endpoint can help ensure system availability.

### Logs

-   **Local Development**: Logs are output to the console where the Uvicorn server (running `app:app`) is running. FastAPI and Uvicorn provide structured logging. The level of detail can be influenced by the `DEBUG` setting in `.env`.
-   **Render Deployment**: Access and monitor logs via the Render dashboard for your service. This is crucial for diagnosing issues in the deployed environment.

Key information to look for in logs:
-   Successful/failed PDF uploads and processing durations.
-   Question answering request details.
-   Errors from external services (Gemini, Pinecone).
-   Any unexpected application exceptions or tracebacks.

## 🔒 Security

-   **API Keys**: Handled via environment variables (`.env` locally, Render's environment settings). Never hardcode keys. Ensure `.env` is in `.gitignore`.
-   **File Uploads**:
    *   FastAPI's `UploadFile` object provides the filename. The application uses this filename but primarily relies on temporary file paths for processing. Direct persistent storage of user-uploaded filenames would require sanitization (e.g., using a library or custom logic if `werkzeug.utils.secure_filename` is not used).
    *   File type (`content_type` via `UploadFile.content_type`) and size (`UploadFile.size`) are validated within the `/uploadpdf` endpoint against `ALLOWED_EXTENSIONS` and `MAX_FILE_SIZE` from the `Config` class.
-   **Input Validation**: FastAPI leverages Pydantic models (e.g., `AnswerRequest`) for robust request body validation. Path and query parameters are also automatically validated by FastAPI based on type hints.
-   **CORS**: FastAPI handles Cross-Origin Resource Sharing (CORS) through `fastapi.middleware.cors.CORSMiddleware`. This is configured in `src/backend/__init__.py` (in the `create_app` function). The current configuration in the codebase is:
    ```python
    # In src/backend/__init__.py
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Allows all origins
        allow_credentials=True,
        allow_methods=["*"],  # Allows all methods
        allow_headers=["*"],  # Allows all headers
    )
    ```
    For production environments, `allow_origins` should be restricted to specific domains (e.g., `["https://your-frontend-domain.com"]`) instead of `["*"]`.
-   **Error Handling**: FastAPI has excellent built-in support for returning structured JSON error responses using `HTTPException`. Custom exception handlers can also be defined for more tailored error information, helping to avoid exposing raw stack traces or sensitive details.
-   **Dependency Management**: Keep `requirements.txt` and `requirements-dev.txt` up-to-date. Regularly audit dependencies for known vulnerabilities using tools like `pip-audit`, Snyk, GitHub's Dependabot, or similar services.
-   **HTTPS**: Render (or other typical deployment platforms) automatically provides HTTPS for deployed services by terminating SSL/TLS at the load balancer or reverse proxy. Ensure Uvicorn is configured to trust proxy headers if necessary (e.g., `forwarded_allow_ips`).

## 📝 License

This project is licensed under the MIT License. It's good practice to include a `LICENSE` file in the repository root with the full text of the MIT License.

## 🤝 Contributing

Contributions are welcome! Please adhere to the following process:

1.  **Fork the Repository**: Create your own fork on GitHub.
2.  **Create a Branch**: `git checkout -b feature/your-new-feature` or `bugfix/issue-description`.
3.  **Develop**: Make your changes.
4.  **Test**: Add and run tests for your changes using `pytest`.
5.  **Commit**: Write clear, concise commit messages.
6.  **Push**: Push your branch to your fork: `git push origin your-branch-name`.
7.  **Pull Request**: Open a PR against the `main` branch of the original repository. Clearly describe your changes and link any relevant issues.

## 📞 Support

If you encounter issues or have questions:

-   **Check GitHub Issues**: See if your question or problem has already been addressed.
-   **Review Troubleshooting Section**: The [Detailed Installation and Setup Guide](docs/INSTALLATION.md#-troubleshooting) might have a solution.
-   **Create a New Issue**: If your issue is new, provide detailed information:
    *   Steps to reproduce.
    *   Expected vs. actual behavior.
    *   Error messages and relevant logs.
    *   Your environment (OS, Python version).
-   For Render-specific deployment issues, consult the [Render documentation](https://render.com/docs).

---

**Happy coding! 🚀**