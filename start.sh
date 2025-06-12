#!/bin/bash
# Render.com start script

# Create necessary directories
mkdir -p uploads
mkdir -p logs

# Start the application with gunicorn
exec gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --access-logfile - --error-logfile - app:app