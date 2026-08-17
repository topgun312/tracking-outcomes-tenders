.PHONY: build up down logs migrate consumer api test lint

build:
	docker compose build

up:
	docker compose up -d

down:
	docker compose down

migrate:
	docker compose run --rm migrate

api:
	uv run uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload

consumer:
	uv run python -m src.broker.consumer

logs:
	docker compose logs -f

test:
	uv run pytest

lint:
	uv run isort src tests --check
	uv run black src tests --check
	uv run flake8 src tests