# Deployment Guide

This document provides guidance on deploying the PDF Assistant Chatbot application, which consists of a Flask backend and a Streamlit frontend.

## Backend Deployment (Flask Application)

The Flask backend is designed to be deployed as a standard Python web application.

### Recommended Platform: Render.com

We provide detailed instructions for deploying the Flask backend to [Render.com](https://render.com) in the [Detailed Installation and Setup Guide](INSTALLATION.md#🌐-deploy-to-rendercom). This guide covers:
- Preparing your repository.
- Creating a Web Service on Render.
- Configuring build and start commands (using `gunicorn` via `start.sh`).
- Setting necessary environment variables for API keys and application settings.

### General Backend Deployment Considerations

If deploying to other platforms (e.g., AWS, Google Cloud, Heroku, self-hosted), consider the following:
-   **WSGI Server**: Use a production-grade WSGI server like Gunicorn (as configured in `start.sh`) or uWSGI. Do not use Flask's built-in development server in production.
-   **Environment Variables**: Ensure all required environment variables (API keys, database URLs, `FLASK_ENV=production`, etc.) are securely configured on your deployment platform. Refer to `.env.template` for a full list.
-   **Dependencies**: Install dependencies from `requirements.txt`.
-   **Database/Service Accessibility**: Ensure the deployed backend can reach external services like Google Gemini and Pinecone (check network rules, firewalls).
-   **HTTPS**: Configure HTTPS for secure communication. Most PaaS providers handle this automatically.
-   **Logging**: Configure appropriate logging for monitoring and troubleshooting.
-   **Static Files (if any)**: Configure serving of static files if your backend serves any directly (not applicable to this project as frontend is separate).

## Frontend Deployment (Streamlit Application)

The Streamlit frontend (`src/frontend/streamlit_app.py`) needs to be deployed as a separate web application.

### Key Requirement: `ENDPOINT` Environment Variable

The Streamlit application **must** have the `ENDPOINT` environment variable set to the URL of your deployed Flask backend API.
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

## Running Both Backend and Frontend

For a fully functional application, both the backend and frontend services must be deployed and running. The frontend must be configured to communicate with the backend via the `ENDPOINT` environment variable.