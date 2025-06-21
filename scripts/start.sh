#!/bin/bash
# Render.com start script

# Create necessary directories
mkdir -p uploads
mkdir -p logs

# Start the application with gunicorn and uvicorn workers
# Ensure APP_ENV is set to production in the deployment environment if necessary
# WORKERS environment variable can be set by the deployment platform, defaults to 2 if not set.
exec gunicorn --bind 0.0.0.0:$PORT --workers ${WORKERS:-2} --worker-class uvicorn.workers.UvicornWorker --timeout 120 --access-logfile - --error-logfile - app:app