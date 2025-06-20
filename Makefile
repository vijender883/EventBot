# One-liners for installing, testing, linting, and formatting.
.PHONY: install test lint format clean run

# Define the project root as PYTHONPATH
# This ensures Python can find modules like 'src.chatbot_backend'
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
clean:
	find . -type f -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf venv

# Run the Flask application
run:
	python app.py

