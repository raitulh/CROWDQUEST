.PHONY: env up down logs test lint typecheck

env:
	python scripts/bootstrap_env.py

up:
	docker compose up --build -d

down:
	docker compose down

logs:
	docker compose logs -f --tail=200

test:
	cd apps/api && pytest -q

lint:
	cd apps/api && ruff check app tests

typecheck:
	cd apps/web && npm run typecheck
