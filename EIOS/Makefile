.PHONY: setup check test test-unit test-contract test-integration test-cov lint types

setup:
	uv sync

# Runs the same gates as the pull-request pipeline (wired in T052).
check:
	uv run python -m tools.gates.local

test:
	uv run pytest -n auto -q

test-unit:
	uv run pytest tests/unit -n auto -q

test-contract:
	uv run pytest tests/contract -n auto -q

test-integration:
	uv run pytest tests/integration -n auto -q

test-cov:
	uv run pytest -n auto -q --cov

lint:
	uv run ruff check .
	uv run ruff format --check .

types:
	uv run mypy
