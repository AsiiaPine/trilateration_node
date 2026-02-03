.PHONY: help test lint format install clean run

help:
	@echo "Available targets:"
	@echo "  make install    - Install dependencies"
	@echo "  make test       - Run tests"
	@echo "  make lint       - Run linters"
	@echo "  make format     - Format code with black"
	@echo "  make clean      - Clean build artifacts"
	@echo "  make run        - Run the main script"

install:
	pip install -r requirements.txt

test:
	pytest tests/ -v --cov=uwb_localizer --cov-report=html --cov-report=term

test-fast:
	pytest tests/ -v -x

lint:
	flake8 uwb_localizer/ tests/ main.py --max-line-length=120 --ignore=E501,W503
	pylint uwb_localizer/ tests/ main.py --disable=C0111,C0103 || true

format:
	black uwb_localizer/ tests/ main.py

clean:
	rm -rf build/ dist/ *.egg-info .pytest_cache .coverage htmlcov/ coverage.xml
	find . -type d -name __pycache__ -exec rm -r {} +
	find . -type f -name "*.pyc" -delete

run:
	python main.py
