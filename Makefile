# One-liners for installing, testing, linting, and formatting.
.PHONY: install test lint format clean flush-all run-backend run-frontend run-all venv venv3

# Define the project root as PYTHONPATH
# This ensures Python can find modules like 'src.backend'
export PYTHONPATH := $(shell pwd)

# Create virtual environment
venv:
	python -m venv venv
	@echo "Virtual environment 'venv' created. Activate with: source venv/bin/activate (Linux/macOS) or venv\\Scripts\\activate (Windows)"

venv3:
	python3 -m venv venv
	@echo "Virtual environment 'venv' created using python3. Activate with: source venv3/bin/activate (Linux/macOS) or venv3\\Scripts\\activate (Windows)"

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

# Run the FastAPI application
run-backend:
	@echo "Starting FastAPI backend server with Uvicorn..."
	@APP_ENV=development uvicorn app:app --reload --host 0.0.0.0 --port $${PORT:-5000}

# Run the Streamlit application
run-frontend:
	@echo "Starting Streamlit frontend application..."
	@streamlit run ./src/frontend/streamlit_app.py

# Run both backend and frontend concurrently for development
run-all:
	@echo "Starting backend and frontend servers..."
	@echo "Backend will run on http://localhost:$${PORT:-5000} (default script port is 5000, or as set in .env)"
	@echo "Frontend will run on http://localhost:8501 (default)"
	@echo "Make sure ENDPOINT in .env is set correctly (e.g., http://localhost:5000 or your configured backend port)"
	@echo "Press Ctrl+C to stop both servers."
	@trap 'kill $(BE_PID); kill $(FE_PID); exit' INT TERM
	@APP_ENV=development uvicorn app:app --reload --host 0.0.0.0 --port $${PORT:-5000} & BE_PID=$$!; \
	streamlit run ./src/frontend/streamlit_app.py & FE_PID=$$!; \
	wait $BE_PID; wait $FE_PID

commit:
	git pull origin dev
	git add .
	git commit -m "some changes"