PG_DB ?= test
default: help

.PHONY: help
help:
	@grep -E '^[0-9a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | sort | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-30s\033[0m %s\n", $$1, $$2}'

.PHONY: format
format: ## run the Ruff formatter
	uv run ruff format

.PHONY: mypy
mypy: ## Run mypy for linting
	uv run mypy --config-file mypy.ini --explicit-package-bases .

.PHONY: migrate
migrate-dev: ## Run migrations for dev db
	docker compose up --build migration

.PHONY: test
test: db-clean migrate-test run-pytest ## 1. Clean, 2. Migrate, 3. Test

db-clean: ## Drop and recreate the public schema for test db
	@echo "--- 🧹 Cleaning Database ---"
	docker compose -f docker-compose.test.yaml up -d db_test
	# Wait for postgres to be ready before dropping
	docker compose -f docker-compose.test.yaml exec db_test sh -c 'until pg_isready -U $$PG_USER; do sleep 1; done'
	docker compose -f docker-compose.test.yaml exec db_test psql -U postgres -d $(PG_DB) -c "DROP SCHEMA public CASCADE; CREATE SCHEMA public;"

migrate-test: ## Run alembic migrations for test db
	@echo "--- 🚀 Running Migrations ---"
	docker compose -f docker-compose.test.yaml run --rm migrator_test

run-pytest: ## Run the tests
	@echo "--- 🧪 Running Pytest ---"
	docker compose -f docker-compose.test.yaml run --rm pytest