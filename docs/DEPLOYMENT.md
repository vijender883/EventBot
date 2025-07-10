# Deployment Guide

This document provides guidance on deploying the PDF Assistant Chatbot application, which consists of a FastAPI backend and a Streamlit frontend.

## Backend Deployment (FastAPI Application)

The FastAPI backend is designed to be deployed as a standard Python ASGI application.

### Recommended Platform: Render.com

We provide detailed instructions for deploying the FastAPI backend to [Render.com](https://render.com) in the [Detailed Installation and Setup Guide](INSTALLATION.md#🌐-deploy-to-rendercom). This guide covers:
- Preparing your repository.
- Creating a Web Service on Render.
- Configuring build and start commands (e.g., using Uvicorn with Gunicorn workers via `start.sh`).
- Setting necessary environment variables for API keys and application settings.

### General Backend Deployment Considerations

If deploying to other platforms (e.g., AWS, Google Cloud, Heroku, self-hosted), consider the following:
-   **ASGI Server**: Use a production-grade ASGI server like Uvicorn, potentially managed by Gunicorn for multiple worker processes. Do not use Uvicorn's development server (`--reload`) in production directly without a process manager.
-   **Environment Variables**: Ensure all required environment variables (API keys, database URLs, `APP_ENV=production`, etc.) are securely configured on your deployment platform. Refer to `.env.template` for a full list.
-   **Dependencies**: Install dependencies from `requirements.txt`.
-   **Database/Service Accessibility**: Ensure the deployed backend can reach external services like Google Gemini and Pinecone (check network rules, firewalls).
-   **HTTPS**: Configure HTTPS for secure communication. Most PaaS providers handle this automatically.
-   **Logging**: Configure appropriate logging for monitoring and troubleshooting.
-   **Static Files (if any)**: Configure serving of static files if your backend serves any directly (not applicable to this project as frontend is separate).

## Frontend Deployment (Streamlit Application)

The Streamlit frontend (`src/frontend/streamlit_app.py`) needs to be deployed as a separate web application.

### Key Requirement: `ENDPOINT` Environment Variable

The Streamlit application **must** have the `ENDPOINT` environment variable set to the URL of your deployed FastAPI backend API.
For example, if your backend is deployed to `https://my-pdf-backend.onrender.com`, then the Streamlit application needs `ENDPOINT=https://my-pdf-backend.onrender.com`.

### Deployment Options for Streamlit

1.  **Streamlit Community Cloud**:
    *   [Streamlit Community Cloud](https://streamlit.io/cloud) is a free service offered by Streamlit for deploying public Streamlit apps directly from GitHub repositories.
    *   It's generally the easiest way to get a Streamlit app running.
    *   You will need to configure the `ENDPOINT` environment variable in the Streamlit Cloud settings for your app.

2.  **Render.com (Separate Web Service)**:
    *   You can deploy the Streamlit app as a separate Web Service on Render.
    *   **Runtime**: Python 3.
    *   **Build Command**: `pip install -r requirements.txt`.
    *   **Start Command**: `streamlit run src/frontend/streamlit_app.py --server.port $PORT --server.headless true`
        *   `--server.port $PORT` allows Render to assign the port.
        *   `--server.headless true` is recommended for deployment.
    *   **Environment Variables**: Set the `ENDPOINT` variable to your backend's URL.

3.  **Other Platforms (Heroku, Docker, VMs)**:
    *   **Docker**: You can containerize the Streamlit application. A `Dockerfile` would typically look like:
        ```dockerfile
        FROM python:3.9-slim
        WORKDIR /app
        COPY requirements.txt .
        RUN pip install --no-cache-dir -r requirements.txt
        COPY src/frontend /app/src/frontend
        # Ensure ENDPOINT is set when running the container
        CMD ["streamlit", "run", "src/frontend/streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
        ```
        You would then build and run this Docker image on your chosen platform, ensuring the `ENDPOINT` environment variable is passed to the container.
    *   **Virtual Machines / Bare Metal**: You can run the Streamlit app using `streamlit run src/frontend/streamlit_app.py` behind a reverse proxy like Nginx or Caddy for HTTPS and robust serving.

### General Frontend Deployment Considerations

-   **Dependencies**: Ensure all dependencies from `requirements.txt` are installed in the frontend's deployment environment.
-   **Resource Allocation**: Streamlit apps can be memory-intensive depending on usage. Monitor and allocate resources accordingly.
-   **HTTPS**: Ensure the deployed frontend is served over HTTPS.

## Deploying to Render.com

The following steps outline how to deploy the FastAPI backend to [Render.com](https://render.com):

1. **Prepare for Deployment**
    - Ensure `requirements.txt` is up-to-date: `pip freeze > requirements.txt`.
    - Make sure the `start.sh` script is executable. If you haven't done so:
      ```bash
      git update-index --chmod=+x start.sh
      ```
    - Commit your latest changes and push them to your GitHub repository:
      ```bash
      git add .
      git commit -m "Prepare for Render deployment"
      git push origin main
      ```

2. **Create Render Account**
    - Go to [render.com](https://render.com) and sign up (using GitHub is recommended).
    - Connect your GitHub account to Render if you haven't already.

3. **Create Web Service on Render**
    - From the Render dashboard, click "New +" → "Web Service".
    - Connect your GitHub repository where the backend code is hosted.
    - Select the specific repository.

4. **Configure Service**
    - **Name**: A unique name for your service (e.g., `pdf-assistant-backend`).
    - **Region**: Choose a region geographically close to your users.
    - **Branch**: `main` (or your primary deployment branch).
    - **Runtime**: `Python 3`. Render should auto-detect this.
    - **Build Command**: `pip install -r requirements.txt`. This is usually auto-detected.
    - **Start Command**: `./start.sh`. This script uses Gunicorn with Uvicorn workers to run the FastAPI app.
      *Example contents of `start.sh` for FastAPI (ensure it matches your project's `start.sh`):*
      ```bash
      #!/bin/bash
      set -e # Exit immediately if a command exits with a non-zero status
      export APP_ENV=${APP_ENV:-production} # Ensure app runs in production mode, allow override
      export LOG_LEVEL=${LOG_LEVEL:-info} # Set default log level, allow override
      # Gunicorn command with Uvicorn workers:
      # --bind 0.0.0.0:$PORT : Bind to all network interfaces on the port Render provides
      # --workers <num_workers> : Adjust based on your Render plan's resources (e.g., 2 or (2*CPU_CORES)+1)
      # --worker-class uvicorn.workers.UvicornWorker : Use Uvicorn workers for ASGI
      # --timeout 120 : Increase if PDF processing takes longer; be mindful of Render's limits
      # --log-level $LOG_LEVEL : Pass log level to Gunicorn/Uvicorn
      # app:app : Points to the FastAPI app instance (e.g., `app` in `app.py`)
      gunicorn --bind 0.0.0.0:$PORT \
               --workers ${WORKERS:-2} \
               --worker-class uvicorn.workers.UvicornWorker \
               --timeout ${GUNICORN_TIMEOUT:-120} \
               --log-level $LOG_LEVEL \
               app:app
      ```

5. **Set Environment Variables**
    - In your Render service's dashboard, navigate to the "Environment" section. Add the following environment variables, using your actual values:
        - `GEMINI_API_KEY`: `Your_Google_Gemini_API_Key`
        - `PINECONE_API_KEY`: `Your_Pinecone_API_Key`
        - `PINECONE_INDEX_NAME`: `Your_Pinecone_index_name`
        - `PINECONE_CLOUD`: `Your_Pinecone_cloud_provider` (e.g., `aws`)
        - `PINECONE_REGION`: `Your_Pinecone_region` (e.g., `us-east-1`)
        - `DATABASE_URL`: `Your_MySQL_connection_string`
        - `APP_ENV`: `production` (Reinforces the setting in `start.sh`)
        - `LOG_LEVEL`: `info` (or `debug` for more verbose logging during troubleshooting)
        - `PORT`: Render will set this, but your `start.sh` uses it.
        - `WORKERS`: (Optional, if you made it configurable in `start.sh`, e.g., `2` or `4`)
        - `GUNICORN_TIMEOUT`: (Optional, e.g., `120` or `300` if you have long running requests)
        - `PYTHON_VERSION`: Optionally specify your Python version (e.g., `3.10.0`) if needed.

    **Note on Frontend Deployment**: The above Render.com instructions are for deploying the FastAPI backend. Deploying the Streamlit frontend typically requires a separate service or a different setup. You might:
    - Deploy it as a separate Web Service on Render, configuring its start command as `streamlit run src/frontend/streamlit_app.py --server.port $PORT --server.headless true`. You'll also need to set the `ENDPOINT` environment variable for this frontend service to point to your deployed backend URL (e.g., `https://your-fastapi-backend.onrender.com`).
    - Use [Streamlit Community Cloud](https://streamlit.io/cloud) for deploying the frontend, which is often simpler for Streamlit apps.
    - Adapt the `start.sh` script and potentially use a process manager like `supervisor` if you intend to run both backend and frontend from the same service instance (more complex).

6. **Deploy**
    - Click "Create Web Service".
    - Render will begin the deployment process (pulling code, building, and starting the service). Monitor the deployment logs for any errors.
    - Once deployed, your service will be accessible at a URL like `https://your-service-name.onrender.com`.

7. **Test Deployment**
    - Use `curl` or Postman to test your live service endpoints:
      ```bash
      curl https://your-service-name.onrender.com/health
      # Replace with your service name and a test PDF
      curl -X POST -F "file=@path/to/your_document.pdf" https://your-service-name.onrender.com/uploadpdf
      # After getting pdf_uuid from above:
      curl -X POST -H "Content-Type: application/json" \
        -d '{"query": "Summarize this document.", "pdf_uuid": "your_pdf_uuid_from_upload"}' \
        https://your-service-name.onrender.com/answer
      ```

## Running Both Backend and Frontend

For a fully functional application, both the backend and frontend services must be deployed and running. The frontend must be configured to communicate with the backend via the `ENDPOINT` environment variable.