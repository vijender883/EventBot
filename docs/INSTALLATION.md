# Detailed Installation and Setup Guide

## 🛠️ Installation & Setup

### 1. Clone the Repository

```bash
# Make sure to clone the correct repository if the name changed, e.g.:
# git clone https://github.com/vijender883/Chatbot_Pinecone_FastAPI_backend
# cd Chatbot_Pinecone_FastAPI_backend
# For now, assuming the name is the same as the issue was raised on this repo:
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
# Backend Configuration (FastAPI)
APP_ENV=development # Set to 'production' when deploying (e.g., for Uvicorn settings)
PORT=8000           # Default port for FastAPI/Uvicorn, can be changed (e.g., to 5000)

# API Keys (Replace with your actual keys)
GEMINI_API_KEY="YOUR_GEMINI_API_KEY_HERE"
PINECONE_API_KEY="YOUR_PINECONE_API_KEY_HERE"

# Pinecone Configuration
PINECONE_INDEX_NAME="your_pinecone_index_name" # e.g., pdf-assistant-index
PINECONE_CLOUD="aws"                         # Your Pinecone cloud provider (e.g., aws, gcp)
PINECONE_REGION="us-east-1"                  # Your Pinecone index region (e.g., us-east-1)

# Optional: Logging Level
LOG_LEVEL=INFO # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL

# Frontend Configuration
ENDPOINT="http://localhost:8000" # URL for the backend API (default for FastAPI)
```
**Important**:
- Replace placeholder values with your actual credentials and configuration details.
- Ensure `PINECONE_INDEX_NAME`, `PINECONE_CLOUD`, and `PINECONE_REGION` in `.env` precisely match your Pinecone index settings.
- The `ENDPOINT` variable is used by the Streamlit frontend to connect to the backend API. The default `http://localhost:8000` assumes the backend is running locally on FastAPI's default port. Adjust if your backend is configured for a different port (e.g., 5000).
- The `.env` file is included in `.gitignore` and should not be committed to version control.

### 3. Verify Configuration

After setting up `.env` and activating your virtual environment, run this command from the project root to check if backend variables are loaded:

```bash
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(f\"Gemini Key Loaded: {bool(os.getenv('GEMINI_API_KEY'))}\"); print(f\"Pinecone Key Loaded: {bool(os.getenv('PINECONE_API_KEY'))}\"); print(f\"Pinecone Index: {os.getenv('PINECONE_INDEX_NAME')}\")"
```
This should output `True` for keys being loaded and display your Pinecone index name.

To check if the frontend `ENDPOINT` variable is loaded:
```bash
python -c "from dotenv import load_dotenv; import os; load_dotenv(); print(f\"Endpoint: {os.getenv('ENDPOINT')}\")"
```
This should display the endpoint URL, e.g., `Endpoint: http://localhost:8000`.

## 🚀 Running Locally

The application consists of two main parts: the FastAPI backend and the Streamlit frontend. Both need to be running to use the application. You can use the `Makefile` for convenience.

### 1. Start the Backend Server

With your virtual environment activated and `.env` file configured:

Using Makefile:
```bash
make run-backend
```
Alternatively, run directly with Uvicorn (assuming your FastAPI app instance is named `app` in `app.py`):
```bash
uvicorn app:app --reload --port ${PORT:-8000}
# The ${PORT:-8000} will use the PORT from .env or default to 8000
```
The backend server will typically start on `http://localhost:8000` (or the `PORT` specified in `.env`).

### 2. Start the Frontend Application

Once the backend server is running:

1.  **Ensure `ENDPOINT` is set**: The Streamlit frontend needs the `ENDPOINT` environment variable to point to your running backend. If you followed the `.env` configuration step and your backend is at `http://localhost:8000` (or your configured `PORT`), this should be correctly set.
2.  **Run the frontend**:

    Using Makefile:
    ```bash
    make run-frontend
    ```
    Alternatively, run directly:
    ```bash
    streamlit run src/frontend/streamlit_app.py
    ```
The Streamlit application will typically open in your web browser at `http://localhost:8501`. You can now upload PDFs and chat with the assistant through this interface.

### 3. Test the API (Optional)

Use `curl` or an API client like Postman to interact with the endpoints.

#### Health Check (`/health`)
```bash
curl http://localhost:${PORT:-8000}/health
# Replace ${PORT:-8000} with 5000 if you set PORT=5000 in .env
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
curl -X POST -F "file=@path/to/your_document.pdf" http://localhost:${PORT:-8000}/uploadpdf
# Replace ${PORT:-8000} with 5000 if you set PORT=5000 in .env
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
  http://localhost:${PORT:-8000}/answer
# Replace ${PORT:-8000} with 5000 if you set PORT=5000 in .env
```
Expected output (will vary based on the PDF content and query):
```json
{
  "answer": "The main subject of this document appears to be..."
}
```

## 🌐 Deploy to Render.com

Render.com offers a convenient platform for deploying this FastAPI application.

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
-   **Start Command**: `./start.sh`. This script uses Gunicorn with Uvicorn workers to run the FastAPI app.
    *Example contents of `start.sh` for FastAPI:*
    ```bash
    #!/bin/bash
    set -e # Exit immediately if a command exits with a non-zero status
    export APP_ENV=production # Ensure app runs in production mode
    # Gunicorn command with Uvicorn workers:
    # --bind 0.0.0.0:$PORT : Bind to all network interfaces on the port Render provides
    # --workers <num_workers> : Adjust based on your Render plan's resources (e.g., 2 or (2*CPU_CORES)+1)
    # --worker-class uvicorn.workers.UvicornWorker : Use Uvicorn workers for ASGI
    # --timeout 120 : Increase if PDF processing takes longer; be mindful of Render's limits
    # app.main:app : Points to the FastAPI app instance (e.g., `app` in `app/main.py` or `app.py`)
    # Make sure your main FastAPI application file is app.py and the instance is `app`, or adjust app.main:app
    gunicorn --bind 0.0.0.0:$PORT --workers ${WORKERS:-2} --worker-class uvicorn.workers.UvicornWorker --timeout 120 app:app
    # Consider making WORKERS an environment variable.
    ```

### 5. Set Environment Variables

In your Render service's dashboard, navigate to the "Environment" section. Add the following environment variables, using your actual values:

-   `GEMINI_API_KEY`: `Your_Google_Gemini_API_Key`
-   `PINECONE_API_KEY`: `Your_Pinecone_API_Key`
-   `PINECONE_INDEX_NAME`: `Your_Pinecone_index_name`
-   `PINECONE_CLOUD`: `Your_Pinecone_cloud_provider` (e.g., `aws`)
-   `PINECONE_REGION`: `Your_Pinecone_region` (e.g., `us-east-1`)
-   `APP_ENV`: `production` (Reinforces the setting in `start.sh`)
-   `PORT`: Render will set this, but your `start.sh` uses it.
-   `WORKERS`: (Optional, if you made it configurable in `start.sh`, e.g., `2` or `4`)
-   `PYTHON_VERSION`: Optionally specify your Python version (e.g., `3.10.0`) if needed.

**Note on Frontend Deployment**: The above Render.com instructions are for deploying the FastAPI backend. Deploying the Streamlit frontend typically requires a separate service or a different setup. You might:
-   Deploy it as a separate Web Service on Render, configuring its start command as `streamlit run src/frontend/streamlit_app.py --server.port $PORT --server.headless true`. You'll also need to set the `ENDPOINT` environment variable for this frontend service to point to your deployed backend URL (e.g., `https://your-fastapi-backend.onrender.com`).
-   Use [Streamlit Community Cloud](https://streamlit.io/cloud) for deploying the frontend, which is often simpler for Streamlit apps.
-   Adapt the `start.sh` script and potentially use a process manager like `supervisor` if you intend to run both backend and frontend from the same service instance (more complex).

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

## 🧪 Running Tests

*(This section outlines general steps. Specific test setup might vary.)*

This project should include automated tests to ensure reliability. Assuming `pytest` is the chosen test runner (a common choice for Python projects):

1.  **Activate Virtual Environment**: Ensure your `venv` is active.
2.  **Install Test Dependencies**: If not already included in `requirements.txt`, install pytest:
    ```bash
    pip install pytest
    ```

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
    *   **Console Logs**: Check logs from your Uvicorn/Gunicorn process for detailed error messages.
    *   **File Size/Type**: The application has checks for file size (`MAX_FILE_SIZE`) and type (`ALLOWED_EXTENSIONS`) defined in the configuration and validated in `routes/chat.py` (likely using FastAPI's `UploadFile` attributes).

5.  **`gunicorn` or `uvicorn` command not found (Render Deployment)**:
    *   Ensure `gunicorn` and `uvicorn` are in `requirements.txt`. If not, add them (`pip install gunicorn uvicorn`, then `pip freeze > requirements.txt`) and redeploy.

6.  **Timeout Issues on Render (especially `/uploadpdf`)**:
    *   The `start.sh` script uses `--timeout 120` for Gunicorn. For very large PDFs, this might need to be increased. Be aware of Render's own request timeout limits (consult their documentation).
    *   For consistently long operations, consider implementing asynchronous background tasks.

### Debug Mode (Local Development)

For more verbose error output locally:
1.  Set `APP_ENV=development` in your `.env` file. (This usually triggers `debug=True` in FastAPI or Uvicorn's `--reload` flag implies it).
2.  Optionally, set `LOG_LEVEL=DEBUG` in `.env` for more detailed application logs.
3.  Run the app with Uvicorn: `uvicorn app:app --reload --port ${PORT:-8000}`.
