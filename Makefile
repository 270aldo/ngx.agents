.PHONY: setup dev test test-unit test-integration test-agents test-cov test-cov-html test-adk lint format clean

# Configuración y desarrollo
setup:
	poetry install --with dev,test

dev:
	poetry run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000

# Pruebas
test:
	poetry run pytest

test-unit:
	poetry run pytest -m unit

test-integration:
	poetry run pytest -m integration

test-agents:
	poetry run pytest -m agents

# Pruebas específicas
test-adk:
	./scripts/test_adk_integration.sh

# Cobertura de código
test-cov:
	poetry run pytest --cov=core --cov=clients --cov=agents --cov=tools --cov=api

test-cov-html:
	poetry run pytest --cov=core --cov=clients --cov=agents --cov=tools --cov=api --cov-report=html
	@echo "Informe de cobertura generado en coverage_html_report/index.html"

# Calidad de código
lint:
	poetry run flake8 core clients agents tools api

format:
	poetry run black core clients agents tools api

# Limpieza
clean:
	rm -rf .pytest_cache
	rm -rf .coverage
	rm -rf coverage_html_report
	rm -rf __pycache__
	rm -rf */__pycache__
	rm -rf */*/__pycache__
	rm -rf */*/*/__pycache__
	find . -name "*.pyc" -delete
	find . -name "*.pyo" -delete
	find . -name "*.pyd" -delete
	find . -name ".DS_Store" -delete
