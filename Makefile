.PHONY: test
test:
	.\venv\Scripts\python.exe -m pytest tests/ -v

.PHONY: test-unit
test-unit:
	.\venv\Scripts\python.exe -m pytest tests/unit -v

.PHONY: test-integration
test-integration:
	.\venv\Scripts\python.exe -m pytest tests/integration -v

.PHONY: test-cov
test-cov:
	.\venv\Scripts\python.exe -m pytest tests/ --cov=app --cov-report=term-missing

.PHONY: test-db
test-db:
	psql -U postgres -c "CREATE DATABASE \"NOCTRADB_test\" OWNER postgres;"