.PHONY: install dev api ui test test-api test-ui check

# One port for both halves: the API binds it, the UI dev server proxies to it.
API_PORT ?= 8000
export API_URL = http://127.0.0.1:$(API_PORT)

# The API and the UI dev server together, in one terminal; Ctrl-C stops both.
dev:
	@trap 'kill 0' EXIT INT TERM; $(MAKE) api & $(MAKE) ui & wait

install:
	uv sync --all-groups
	npm --prefix frontend install

api:
	uv run uvicorn icm_platform.app:app --reload --port $(API_PORT)

ui:
	npm --prefix frontend run dev

test: test-api test-ui

test-api:
	uv run pytest

test-ui:
	npm --prefix frontend test

check:
	uv run ruff check .
	uv run ty check src tests
	npm --prefix frontend run typecheck
