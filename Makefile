.PHONY: help up down logs seed test backend-test frontend-dev lint fmt

help:
	@echo "NEXUS Intelligence Platform"
	@echo "  make up            Start the full development stack"
	@echo "  make down          Stop the stack"
	@echo "  make logs          Tail backend + frontend logs"
	@echo "  make seed          Re-run demo seed"
	@echo "  make test          Run backend tests"
	@echo "  make frontend-dev  Run Next.js locally (API via compose)"

up:
	docker compose up --build

down:
	docker compose down

logs:
	docker compose logs -f backend frontend

seed:
	docker compose exec backend python -m app.infrastructure.seed

test:
	docker compose exec backend pytest -q

backend-test:
	cd backend && python -m pytest -q

frontend-dev:
	cd frontend && npm run dev

lint:
	cd backend && ruff check app tests || true
	cd frontend && npx tsc --noEmit || true
