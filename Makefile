.PHONY: setup setup-full setup-dev setup-test dev test test-unit test-integration test-agents test-cov test-cov-html test-adk lint format clean

# Configuración y desarrollo
setup:
	poetry install --no-root --with dev,test

setup-full:
	poetry install --no-root --with dev,test,agents,clients,core,tools,telemetry

setup-dev:
	poetry install --no-root --with dev,test,agents,clients,core,tools

setup-test:
	poetry install --no-root --only test

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
	poetry run pytest --cov=core --cov=clients --cov=agents --cov=tools --cov=app

test-cov-html:
	poetry run pytest --cov=core --cov=clients --cov=agents --cov=tools --cov=app --cov-report=html
	@echo "Informe de cobertura generado en coverage_html_report/index.html"

# Calidad de código
lint:
	poetry run ruff check core clients agents tools app
	poetry run mypy core clients agents tools app

format:
	poetry run black core clients agents tools app
	poetry run isort core clients agents tools app

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
