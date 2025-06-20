# [Project Logo Placeholder] PDF Assistant Chatbot - Flask Backend

A Flask-based backend service that integrates with Google Gemini AI and Pinecone vector database to create an intelligent PDF document assistant. Users can upload PDF files and ask questions about their content using natural language.

## 📖 Table of Contents

- [🚀 Features](#-features)
- [📋 Prerequisites](#-prerequisites)
- [🛠️ Installation & Setup](#️-installation--setup)
  - [1. Clone the Repository](#1-clone-the-repository)
  - [2. Create and Activate Virtual Environment](#2-create-and-activate-virtual-environment)
  - [3. Install Dependencies](#3-install-dependencies)
- [🔑 API Keys Setup](#-api-keys-setup)
  - [Get Google Gemini API Key](#get-google-gemini-api-key)
  - [Get Pinecone API Key and Create Index](#get-pinecone-api-key-and-create-index)
- [⚙️ Environment Configuration](#️-environment-configuration)
  - [1. Create .env File](#1-create-env-file)
  - [2. Configure .env File](#2-configure-env-file)
  - [3. Verify Configuration](#3-verify-configuration)
- [🚀 Running Locally](#-running-locally)
  - [1. Start the Flask Server](#1-start-the-flask-server)
  - [2. Test the API](#2-test-the-api)
- [📡 API Endpoints](#-api-endpoints)
- [🌐 Deploy to Render.com](#-deploy-to-rendercom)
  - [1. Prepare for Deployment](#1-prepare-for-deployment)
  - [2. Create Render Account](#2-create-render-account)
  - [3. Create Web Service](#3-create-web-service)
  - [4. Configure Service](#4-configure-service)
  - [5. Set Environment Variables](#5-set-environment-variables)
  - [6. Deploy](#6-deploy)
  - [7. Test Deployment](#7-test-deployment)
- [🔧 Development](#-development)
  - [Project Structure](#project-structure)
  - [Key Components](#key-components)
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
- **RESTful API**: Clean REST endpoints for integration with frontend applications.
- **Health Monitoring**: Built-in health checks and logging.

## 📋 Prerequisites

- Python 3.8 or higher
- Google AI Studio account (for Gemini API key)
- Pinecone account (for Pinecone API key and index)
- Git

## 🛠️ Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/vijender883/Chatbot_Pinecone_flask_backend
cd Chatbot_Pinecone_flask_backend
```

### 2. Create and Activate Virtual Environment

Choose the commands appropriate for your operating system:

#### Windows Command Prompt
```cmd
python -m venv venv
venv\Scripts\activate
```

#### Windows PowerShell
```powershell
python -m venv venv
venv\Scripts\Activate.ps1
# If script execution is disabled, run:
# Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
# Then try activating again.
```

#### macOS/Linux
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

Once the virtual environment is activated:
```bash
pip install -r requirements.txt
```

## 🔑 API Keys Setup

### Get Google Gemini API Key

1.  **Visit Google AI Studio**: Navigate to [https://makersuite.google.com/app/apikey](https://makersuite.google.com/app/apikey) and sign in with your Google account.
2.  **Create API Key**: Click "Create API Key" and follow the prompts (e.g., "Create API key in new project").
3.  **Secure Your Key**: Copy the generated API key (it typically starts with `AIzaSy...`). Store it securely and never commit it to version control.

### Get Pinecone API Key and Create Index

1.  **Sign up for Pinecone**: Go to [https://www.pinecone.io/](https://www.pinecone.io/) and create a free account.
2.  **Get API Key**: After logging into the Pinecone console, navigate to the "API Keys" section and copy your API key (e.g., `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`).
3.  **Create a New Index** in the Pinecone console:
    *   **Index Name**: Choose a descriptive name (e.g., `pdf-assistant-index`). This exact name will be used in your `.env` file.
    *   **Dimensions**: Set to `768`. This is required for the `models/embedding-001` embedding model used by Gemini, which produces 768-dimensional vectors.
    *   **Metric**: Select `cosine` for similarity search.
    *   **Cloud Provider & Region**: Choose according to your preference (e.g., `AWS`, `us-east-1`). These details will also be needed for your `.env` file.
    *   Click "Create Index".

## ⚙️ Environment Configuration

### 1. Create .env File

In the project root directory, copy the template file to create your local environment configuration file:

```bash
cp .env.template .env
```
On Windows, use `copy` if `cp` is not available:
```bash
copy .env.template .env
```

### 2. Configure .env File

Open the `.env` file with a text editor and fill in your actual API keys and Pinecone details:

```env
# Flask Configuration
FLASK_ENV=development # Set to 'production' when deploying
PORT=5000             # Port the local server will run on

# API Keys (Replace with your actual keys)
GEMINI_API_KEY="YOUR_GEMINI_API_KEY_HERE"
PINECONE_API_KEY="YOUR_PINECONE_API_KEY_HERE"

# Pinecone Configuration
PINECONE_INDEX_NAME="your_pinecone_index_name" # e.g., pdf-assistant-index
PINECONE_CLOUD="aws"                         # Your Pinecone cloud provider (e.g., aws, gcp)
PINECONE_REGION="us-east-1"                  # Your Pinecone index region (e.g., us-east-1)

# Optional: Logging Level
LOG_LEVEL=INFO # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL
```
**Important**:
- Replace placeholder values with your actual credentials and configuration details.
- Ensure `PINECONE_INDEX_NAME`, `PINECONE_CLOUD`, and `PINECONE_REGION` in `.env` precisely match your Pinecone index settings.
- The `.env` file is included in `.gitignore` and should not be committed to version control.

### 3. Verify Configuration

After setting up `.env` and activating your virtual environment, run this command from the project root to check if variables are loaded:

```bash
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(f\"Gemini Key Loaded: {bool(os.getenv('GEMINI_API_KEY'))}\"); print(f\"Pinecone Key Loaded: {bool(os.getenv('PINECONE_API_KEY'))}\"); print(f\"Pinecone Index: {os.getenv('PINECONE_INDEX_NAME')}\")"
```
This should output `True` for keys being loaded and display your Pinecone index name.

## 🚀 Running Locally

### 1. Start the Flask Server

With your virtual environment activated and `.env` file configured:

```bash
python app.py
```
The server will typically start on `http://localhost:5000` (or the `PORT` specified in `.env`).

### 2. Test the API

Use `curl` or an API client like Postman to interact with the endpoints.

#### Health Check (`/health`)
```bash
curl http://localhost:5000/health
```
Expected successful output:
```json
{
  "status": "success",
  "health": {
    "gemini_api": true,
    "pinecone_connection": true,
    "embeddings": true,
    "vector_store": true,
    "overall_health": true
  },
  "healthy": true
}
```

#### Upload a PDF (`/uploadpdf`)
Replace `path/to/your_document.pdf` with an actual PDF file path.
```bash
curl -X POST -F "file=@path/to/your_document.pdf" http://localhost:5000/uploadpdf
```
Expected successful output:
```json
{
  "success": true,
  "message": "PDF 'your_document.pdf' uploaded and processed successfully",
  "filename": "your_document.pdf"
}
```

#### Ask a Question (`/answer`)
Ensure a PDF has been successfully uploaded and processed first.
```bash
curl -X POST \
  -H "Content-Type: application/json" \
  -d '{"query": "What is the main subject of this document?"}' \
  http://localhost:5000/answer
```
Expected output (will vary based on the PDF content and query):
```json
{
  "answer": "The main subject of this document appears to be..."
}
```

## 📡 API Endpoints

The API routes are primarily defined in `src/chatbot_backend/routes/chat.py`. The root `/` endpoint is in `app.py`.

| Endpoint     | Method | Description                                          | Request Body (Format)         | Success Response (JSON Example)                                                                                                |
|--------------|--------|------------------------------------------------------|-------------------------------|--------------------------------------------------------------------------------------------------------------------------------|
| `/`          | GET    | Basic API information and available endpoints.       | N/A                           | `{"message": "PDF Assistant Chatbot API", "version": "1.0.0", "endpoints": {"/health": "GET - Health check", ...}}` (from `chat.py` if routed, or `app.py`'s version) |
| `/health`    | GET    | Detailed health check of backend services.           | N/A                           | `{"status": "success", "health": {"gemini_api": true, ...}, "healthy": true}`                                                   |
| `/uploadpdf` | POST   | Uploads a PDF file for processing and vectorization. | FormData: `file` (PDF file)   | `{"success": true, "message": "PDF 'name.pdf' uploaded...", "filename": "name.pdf"}`                                           |
| `/answer`    | POST   | Asks a question about the processed PDF content.     | JSON: `{"query": "Your question?"}` | `{"answer": "AI generated answer."}`                                                                                           |

*Note: The root endpoint `/` defined in `app.py` provides a simple welcome message. The one in `chat.py` (if `chat_bp` is mounted at root) offers more detail. The table reflects the more detailed one for completeness.*

## 🌐 Deploy to Render.com

Render.com offers a convenient platform for deploying this Flask application.

### 1. Prepare for Deployment

1.  Ensure `requirements.txt` is up-to-date: `pip freeze > requirements.txt`.
2.  Make sure the `start.sh` script is executable. If you haven't done so:
    ```bash
    git update-index --chmod=+x start.sh
    ```
3.  Commit your latest changes and push them to your GitHub repository:
    ```bash
    git add .
    git commit -m "Prepare for Render deployment"
    git push origin main
    ```

### 2. Create Render Account

1.  Go to [render.com](https://render.com) and sign up (using GitHub is recommended).
2.  Connect your GitHub account to Render if you haven't already.

### 3. Create Web Service on Render

1.  From the Render dashboard, click "New +" → "Web Service".
2.  Connect your GitHub repository where the backend code is hosted.
3.  Select the specific repository.

### 4. Configure Service

-   **Name**: A unique name for your service (e.g., `pdf-assistant-backend`).
-   **Region**: Choose a region geographically close to your users.
-   **Branch**: `main` (or your primary deployment branch).
-   **Runtime**: `Python 3`. Render should auto-detect this.
-   **Build Command**: `pip install -r requirements.txt`. This is usually auto-detected.
-   **Start Command**: `./start.sh`. This script uses Gunicorn to run the Flask app.
    *Contents of `start.sh`:*
    ```bash
    #!/bin/bash
    set -e # Exit immediately if a command exits with a non-zero status
    export FLASK_ENV=production # Ensure Flask runs in production mode
    # Gunicorn command:
    # --bind 0.0.0.0:$PORT : Bind to all network interfaces on the port Render provides
    # --workers 2 : Adjust based on your Render plan's resources
    # --timeout 120 : Increase if PDF processing takes longer; be mindful of Render's limits
    # app:app : Points to the Flask app instance in app.py
    gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 app:app
    ```

### 5. Set Environment Variables

In your Render service's dashboard, navigate to the "Environment" section. Add the following environment variables, using your actual values:

-   `GEMINI_API_KEY`: `Your_Google_Gemini_API_Key`
-   `PINECONE_API_KEY`: `Your_Pinecone_API_Key`
-   `PINECONE_INDEX_NAME`: `Your_Pinecone_index_name`
-   `PINECONE_CLOUD`: `Your_Pinecone_cloud_provider` (e.g., `aws`)
-   `PINECONE_REGION`: `Your_Pinecone_region` (e.g., `us-east-1`)
-   `FLASK_ENV`: `production` (Reinforces the setting in `start.sh`)
-   `PYTHON_VERSION`: Optionally specify your Python version (e.g., `3.10.0`) if needed.

### 6. Deploy

1.  Click "Create Web Service".
2.  Render will begin the deployment process (pulling code, building, and starting the service). Monitor the deployment logs for any errors.
3.  Once deployed, your service will be accessible at a URL like `https://your-service-name.onrender.com`.

### 7. Test Deployment

Use `curl` or Postman to test your live service endpoints:
```bash
curl https://your-service-name.onrender.com/health
# Replace with your service name and a test PDF
curl -X POST -F "file=@path/to/your_document.pdf" https://your-service-name.onrender.com/uploadpdf
curl -X POST -H "Content-Type: application/json" \
  -d '{"query": "Summarize this document."}' \
  https://your-service-name.onrender.com/answer
```

## 🔧 Development

### Project Structure
```
Chatbot_Pinecone_flask_backend/
├── .env                   # Local environment variables (gitignored)
├── .env.template          # Template for .env file
├── .git/                  # Git version control directory
├── .gitignore             # Specifies intentionally untracked files for Git
├── README.md              # This guide
├── app.py                 # Main Flask application entry point, basic routes
├── requirements.txt       # Python package dependencies
├── start.sh               # Shell script for starting the application via Gunicorn
├── src/                   # Main source code directory
│   └── chatbot_backend/   # Primary package for the chatbot
│       ├── __init__.py
│       ├── core/          # Core logic (AI, PDF processing)
│       │   ├── __init__.py
│       │   └── event_bot.py # EventBot class for main operations
│       ├── routes/        # API route definitions
│       │   ├── __init__.py
│       │   └── chat.py    # Chat-related blueprints (upload, answer, health)
│       ├── services/      # External service integrations
│       │   ├── __init__.py
│       │   ├── gemini_service.py  # Google Gemini API interaction
│       │   └── pinecone_service.py # Pinecone vector DB interaction
│       └── utils/         # Utility functions and helpers
│           ├── __init__.py
│           ├── config_loader.py # Loads configuration from environment
│           └── helper.py        # Miscellaneous helper functions
└── tests/                 # Automated tests
    ├── __init__.py
    └── test_chat.py       # Example tests for chat functionalities (placeholder)
```

### Key Components

-   **`app.py`**: Initializes the Flask app, registers blueprints, and defines the root (`/`) endpoint.
-   **`src/chatbot_backend/routes/chat.py`**: Contains the Flask Blueprint (`chat_bp`) for core API endpoints: `/health`, `/uploadpdf`, and `/answer`.
-   **`src/chatbot_backend/core/event_bot.py`**: Houses the `EventBot` class, which orchestrates PDF processing (text extraction, chunking), vector embedding generation via Gemini, and question answering using the Pinecone index.
-   **`src/chatbot_backend/services/gemini_service.py`**: Provides a dedicated interface for communicating with the Google Gemini API (generating embeddings, conversational responses).
-   **`src/chatbot_backend/services/pinecone_service.py`**: Manages all interactions with Pinecone, including creating/accessing the index, and storing/querying document vectors.
-   **`src/chatbot_backend/utils/config_loader.py`**: Responsible for loading and providing access to configuration settings (API keys, Pinecone details) from environment variables.

## 🧪 Running Tests

*(This section outlines general steps. Specific test setup might vary.)*

This project should include automated tests to ensure reliability. Assuming `pytest` is the chosen test runner (a common choice for Python projects):

1.  **Activate Virtual Environment**: Ensure your `venv` is active.
2.  **Install Test Dependencies**: If not already included in `requirements.txt`, install pytest:
    ```bash
    pip install pytest
    ```
3.  **Run Tests**: Navigate to the project root directory and execute:
    ```bash
    pytest
    ```
    Pytest will automatically discover and run tests (typically files named `test_*.py` or `*_test.py` in the `tests/` directory).

Refer to the `tests/` directory and any specific test documentation or configuration files for more detailed instructions on running tests.

## 🛠️ Troubleshooting

### Common Issues

1.  **Import Errors / Module Not Found**:
    *   **Virtual Environment**: Confirm your virtual environment is activated (`source venv/bin/activate` or `venv\Scripts\activate`).
    *   **Dependencies**: Reinstall dependencies: `pip install -r requirements.txt`.
    *   **PYTHONPATH**: Usually handled by the virtual environment. Avoid manual `PYTHONPATH` modifications unless you have a specific reason.

2.  **API Key Issues (`GEMINI_API_KEY`, `PINECONE_API_KEY`)**:
    *   **`.env` File**: Ensure `.env` exists in the project root, is correctly named, and its content is accurate (no extra spaces/quotes around keys).
    *   **Verification**: Use the script in [Verify Configuration](#3-verify-configuration) to check if keys are loaded.

3.  **Pinecone Connection Problems**:
    *   **Configuration**: Double-check `PINECONE_INDEX_NAME`, `PINECONE_CLOUD`, and `PINECONE_REGION` in `.env` against your Pinecone console.
    *   **Index Status**: Verify the index exists and is healthy in Pinecone.
    *   **Service Outages**: Check Pinecone's official status page.

4.  **PDF Processing Fails (`/uploadpdf` errors)**:
    *   **File Validity**: Ensure the PDF is not corrupted.
    *   **Console Logs**: Check logs from `python app.py` for detailed error messages.
    *   **File Size/Type**: The application has checks for file size (`MAX_FILE_SIZE`) and type (`ALLOWED_EXTENSIONS`) defined in `app.py` and validated in `chat.py`.

5.  **`gunicorn` command not found (Render Deployment)**:
    *   Ensure `gunicorn` is in `requirements.txt`. If not, add it (`pip install gunicorn`, then `pip freeze > requirements.txt`) and redeploy.

6.  **Timeout Issues on Render (especially `/uploadpdf`)**:
    *   The `start.sh` script uses `--timeout 120` for Gunicorn. For very large PDFs, this might need to be increased. Be aware of Render's own request timeout limits (consult their documentation).
    *   For consistently long operations, consider implementing asynchronous background tasks.

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
-   **Review Troubleshooting Section**: This README's [Troubleshooting](#️-troubleshooting) section might have a solution.
-   **Create a New Issue**: If your issue is new, provide detailed information:
    *   Steps to reproduce.
    *   Expected vs. actual behavior.
    *   Error messages and relevant logs.
    *   Your environment (OS, Python version).
-   For Render-specific deployment issues, consult the [Render documentation](https://render.com/docs).

---

**Happy coding! 🚀**