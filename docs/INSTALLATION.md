# Detailed Installation and Setup Guide

## 🛠️ Installation & Setup

### 1. Clone the Repository

```bash
git clone https://github.com/vijender883/EventBot
cd EventBot
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

### 2. API Keys Setup

#### Get Google Gemini API Key

1.  **Visit Google AI Studio**: Navigate to [https://makersuite.google.com/app/apikey](https://makersuite.google.com/app/apikey) and sign in with your Google account.
2.  **Create API Key**: Click "Create API Key" and follow the prompts (e.g., "Create API key in new project").
3.  **Secure Your Key**: Copy the generated API key (it typically starts with `AIzaSy...`). Store it securely and never commit it to version control.

#### Get Pinecone API Key and Create Index

1.  **Sign up for Pinecone**: Go to [https://www.pinecone.io/](https://www.pinecone.io/) and create a free account.
2.  **Get API Key**: After logging into the Pinecone console, navigate to the "API Keys" section and copy your API key (e.g., `xxxxxxxx-xxxx-xxxx-xxxx-xxxxxxxxxxxx`).
3.  **Create a New Index** in the Pinecone console:
    *   **Index Name**: Choose a descriptive name (e.g., `pdf-assistant-index`). This exact name will be used in your `.env` file.
    *   **Dimensions**: Set to `768`. This is required for the `models/embedding-001` embedding model used by Gemini, which produces 768-dimensional vectors.
    *   **Metric**: Select `cosine` for similarity search.
    *   **Cloud Provider & Region**: Choose according to your preference (e.g., `AWS`, `us-east-1`). These details will also be needed for your `.env` file.
    *   Click "Create Index".

### 2. Configure .env File

Open the `.env` file with a text editor and fill in your actual API keys and Pinecone details:

```env
# Backend Configuration (FastAPI)
APP_ENV=development # Set to 'production' when deploying (e.g., for Uvicorn settings)
PORT=8000           # Default port for FastAPI/Uvicorn, can be changed

# API Keys (Replace with your actual keys)
GEMINI_API_KEY="YOUR_GEMINI_API_KEY_HERE"
PINECONE_API_KEY="YOUR_PINECONE_API_KEY_HERE"

# Pinecone Configuration
PINECONE_INDEX_NAME="your_pinecone_index_name" # e.g., pdf-assistant-index
PINECONE_CLOUD="aws"                         # Your Pinecone cloud provider (e.g., aws, gcp)
PINECONE_REGION="us-east-1"                  # Your Pinecone index region (e.g., us-east-1)

# Optional: Logging Level for backend
LOG_LEVEL=INFO # Options: DEBUG, INFO, WARNING, ERROR, CRITICAL

# Database URL (Critical for table storage and querying)
DATABASE_URL="mysql+mysqlconnector://user:password@host:port/database" # Replace with your MySQL connection string

# Frontend Configuration
ENDPOINT="http://localhost:8000" # URL for the backend API (default for FastAPI if PORT=8000)
# Optional: Logging Level for frontend (Streamlit does not use this directly from .env in the same way)
# STREAMLIT_LOG_LEVEL=INFO
```
**Important**:
- Replace placeholder values with your actual credentials and configuration details.
- Ensure `PINECONE_INDEX_NAME`, `PINECONE_CLOUD`, and `PINECONE_REGION` in `.env` precisely match your Pinecone index settings.
- The `ENDPOINT` variable is used by the Streamlit frontend to connect to the backend API. The default `http://localhost:8000` assumes the backend is running locally on the `PORT` specified for it. Adjust if your backend is configured for a different port (e.g., 5000 and `ENDPOINT="http://localhost:5000"`).
- The `.env` file is included in `.gitignore` and should not be committed to version control.

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
uvicorn app:app --reload --port ${PORT:-8000} --log-level ${LOG_LEVEL:-info}
# The ${PORT:-8000} will use the PORT from .env or default to 8000
# The ${LOG_LEVEL:-info} will use LOG_LEVEL from .env or default to info
```
The backend server will typically start on `http://localhost:8000` (or the `PORT` specified in `.env`).

### 2. Start the Frontend Application

Once the backend server is running:

1.  **Ensure `ENDPOINT` is set**: The Streamlit frontend needs the `ENDPOINT` environment variable to point to your running backend. If you followed the `.env` configuration step, this should be correctly set.
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