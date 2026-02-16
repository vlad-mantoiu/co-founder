.PHONY: test test-domain test-api test-orchestration test-e2e test-cov lint

test:
	python -m pytest tests/ -v

test-domain:
	python -m pytest tests/domain/ -v

test-api:
	python -m pytest tests/api/ -v

test-orchestration:
	python -m pytest tests/orchestration/ -v

test-e2e:
	python -m pytest tests/e2e/ -v

test-cov:
	python -m pytest tests/ -v --cov=app --cov-report=term-missing

lint:
	ruff check app/ tests/
	ruff format --check app/ tests/
