.PHONY: up down test lint migrate seed

up:
	docker compose --env-file infra/.env.example -f infra/docker-compose.yml up --build -d

down:
	docker compose --env-file infra/.env.example -f infra/docker-compose.yml down

test:
	docker compose --env-file infra/.env.example -f infra/docker-compose.yml run --rm backend pytest

lint:
	docker compose --env-file infra/.env.example -f infra/docker-compose.yml run --rm backend ruff check app tests
	docker compose --env-file infra/.env.example -f infra/docker-compose.yml run --rm frontend npm run lint
	docker compose --env-file infra/.env.example -f infra/docker-compose.yml run --rm frontend npm run typecheck

migrate:
	docker compose --env-file infra/.env.example -f infra/docker-compose.yml run --rm backend alembic upgrade head

seed:
	docker compose --env-file infra/.env.example -f infra/docker-compose.yml run --rm backend python -m app.seed

