# [Project Logo Placeholder] PDF Assistant Chatbot

A PDF document assistant with a Flask-based backend and a Streamlit-based frontend. The backend integrates with Google Gemini AI and Pinecone vector database, allowing users to upload PDF files and ask questions about their content using natural language via the frontend interface.

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
    cd Chatbot_Pinecone_flask_backend
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

To run the Flask backend server:
```bash
make run-backend
# Alternatively: python app.py
```
The backend will typically start on `http://localhost:5000`.

### Running the Frontend

To run the Streamlit frontend application:
1.  Ensure the backend is running.
2.  Set the `ENDPOINT` environment variable if your backend is not on `http://localhost:5000`. For local development, you can add `ENDPOINT=http://localhost:5000` to your `.env` file.
```bash
make run-frontend
# Alternatively: streamlit run src/frontend/streamlit_app.py
```
The frontend will typically be available at `http://localhost:8501`.

## 📡 API Endpoints

The API routes are primarily defined in `src/backend/routes/chat.py`. The root `/` endpoint is in `app.py`.

| Endpoint     | Method | Description                                          | Request Body (Format)         | Success Response (JSON Example)                                                                                                |
|--------------|--------|------------------------------------------------------|-------------------------------|--------------------------------------------------------------------------------------------------------------------------------|
| `/`          | GET    | Basic API information and available endpoints.       | N/A                           | `{"message": "PDF Assistant Chatbot API", "version": "1.0.0", "endpoints": {"/health": "GET - Health check", ...}}` (from `chat.py` if routed, or `app.py`'s version) |
| `/health`    | GET    | Detailed health check of backend services.           | N/A                           | `{"status": "success", "health": {"gemini_api": true, ...}, "healthy": true}`                                                   |
| `/uploadpdf` | POST   | Uploads a PDF file for processing and vectorization. | FormData: `file` (PDF file)   | `{"success": true, "message": "PDF 'name.pdf' uploaded...", "filename": "name.pdf"}`                                           |
| `/answer`    | POST   | Asks a question about the processed PDF content.     | JSON: `{"query": "Your question?"}` | `{"answer": "AI generated answer."}`                                                                                           |

*Note: The root endpoint `/` defined in `app.py` provides a simple welcome message. The one in `chat.py` (if `chat_bp` is mounted at root) offers more detail. The table reflects the more detailed one for completeness.*

For deployment instructions, see the [Detailed Installation and Setup Guide](docs/INSTALLATION.md#-deploy-to-rendercom).

## 🔧 Development

### Project Structure
```
Chatbot_Pinecone_flask_backend/
├── .env                   # Local environment variables (gitignored)
├── .env.template          # Template for .env file
├── .git/                  # Git version control directory
├── .gitignore             # Specifies intentionally untracked files for Git
├── README.md              # This guide
├── Makefile               # Defines common tasks like running, testing, linting
├── app.py                 # Main Flask application entry point for the backend
├── requirements.txt       # Python package dependencies for both backend and frontend
├── requirements-dev.txt   # Development-specific dependencies (testing, linting)
├── start.sh               # Shell script for starting the backend application via Gunicorn
├── src/                   # Main source code directory
│   ├── backend/           # Source code for the Flask backend
│   │   ├── __init__.py
│   │   ├── agents/
│   │   │   ├── base.py
│   │   │   └── rag_agent.py
│   │   ├── config.py
│   │   ├── routes/
│   │   │   ├── __init__.py
│   │   │   └── chat.py
│   │   ├── services/
│   │   │   └── orchestrator.py
│   │   └── utils/
│   │       └── helper.py
│   └── frontend/          # Source code for the Streamlit frontend
│       └── streamlit_app.py # Main Streamlit application file
└── tests/                 # Automated tests (primarily for the backend)
    ├── conftest.py
    ├── test_agents/
    └── test_routes/
```

### Key Components

**Backend:**
-   **`app.py`**: Initializes the Flask app, registers blueprints, and defines the root (`/`) endpoint for the backend.
-   **`src/backend/routes/chat.py`**: Contains the Flask Blueprint (`chat_bp`) for core API endpoints: `/health`, `/uploadpdf`, and `/answer`.
-   **`src/backend/agents/rag_agent.py`**: Implements the core RAG (Retrieval Augmented Generation) logic, including PDF processing, vector embedding, and question answering using Gemini and Pinecone.
-   **`src/backend/services/orchestrator.py`**: Acts as a layer between API routes and the `RAGAgent`.
-   **`src/backend/config.py`**: Manages application configuration, loading settings from environment variables.

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
-   `FLASK_ENV`: Set to `development` or `production`.
-   `PORT`: Port for the backend server (defaults to `5000`).

**Frontend Variables:**
-   `ENDPOINT`: The URL of the backend API. For local development, this would typically be `http://localhost:5000`.

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
1.  Set `FLASK_ENV=development` in your `.env` file.
2.  Optionally, set `LOG_LEVEL=DEBUG` in `.env` for more detailed application logs.
3.  Run the app: `python app.py`.

## 📊 Monitoring

### Health Checks

The `/health` endpoint (see [API Endpoints](#-api-endpoints)) provides detailed status of backend components. Regularly polling this endpoint can help ensure system availability.

### Logs

-   **Local Development**: Logs are output to the console where `python app.py` is running. Adjust `LOG_LEVEL` in `.env` for desired verbosity.
-   **Render Deployment**: Access and monitor logs via the Render dashboard for your service. This is crucial for diagnosing issues in the production environment.

Key information to look for in logs:
-   Successful/failed PDF uploads and processing durations.
-   Question answering request details.
-   Errors from external services (Gemini, Pinecone).
-   Any unexpected application exceptions or tracebacks.

## 🔒 Security

-   **API Keys**: Handled via environment variables (`.env` locally, Render's environment settings). Never hardcode keys. Ensure `.env` is in `.gitignore`.
-   **File Uploads**:
    *   `werkzeug.utils.secure_filename` is used to sanitize filenames.
    *   File type and size are validated as per `ALLOWED_EXTENSIONS` and `MAX_FILE_SIZE` in the app configuration.
-   **Input Validation**: Basic validation for presence of query in `/answer` and file in `/uploadpdf`. Sensitive inputs should always be validated and sanitized.
-   **CORS**: `Flask-CORS` is initialized with `CORS(app)`, allowing all origins by default. For production, restrict this to your frontend's domain: `CORS(app, resources={r"/api/*": {"origins": "https://your.frontend.domain.com"}})` in `app.py`.
-   **Error Handling**: Endpoints use try-except blocks to return structured JSON error responses, avoiding exposure of raw stack traces.
-   **Dependency Management**: Keep `requirements.txt` up-to-date. Regularly audit dependencies for vulnerabilities using tools like `pip-audit` or GitHub's Dependabot.
-   **HTTPS**: Render automatically provides HTTPS for deployed services.

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