# One-liners for installing, testing, linting, and formatting.
.PHONY: install test lint format clean flush-all run-backend run-frontend

# Define the project root as PYTHONPATH
# This ensures Python can find modules like 'src.backend'
export PYTHONPATH := $(shell pwd)

# Install dependencies for the main application
install:
	pip install -r requirements.txt
	pip install -r requirements-dev.txt

# Run tests
test:
	pytest

# Run linters and format checkers
lint:
	flake8 src/ tests/
	black --check src/ tests/
	isort --check-only src/ tests/

# Auto-format code
format:
	black src/ tests/
	isort src/ tests/

# Clean up build artifacts and cache
flush-all:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf venv

clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .pytest_cache
	rm -rf .coverage
	clear

# Run the Flask application
run-backend:
	python app.py

# Run the Streamlit application
run-frontend:
	streamlit run ./src/frontend/streamlit_app.py