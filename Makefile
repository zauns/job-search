.PHONY: install test clean lint format setup-dev run

# Install dependencies
install:
	pip install -r requirements.txt

# Install in development mode
install-dev:
	pip install -e .
	pip install -r requirements.txt

# Run tests
test:
	pytest

# Run tests with coverage
test-cov:
	pytest --cov=job_matching_app --cov-report=html

# Clean up generated files
clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Lint code
lint:
	flake8 job_matching_app tests

# Format code
format:
	black job_matching_app tests
	isort job_matching_app tests

# Setup development environment
setup-dev: install-dev
	alembic upgrade head

# Run the application
run:
	python -m job_matching_app.main

# Initialize database
init-db:
	alembic upgrade head

# Create new migration
migrate:
	alembic revision --autogenerate -m "$(msg)"

# Apply migrations
upgrade:
	alembic upgrade head