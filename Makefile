.PHONY: dev-backend dev-frontend infra-init infra-up infra-down

## Start only the backend API server
dev-backend:
	cd backend && uv run uvicorn docmind.api.main:app --reload --host 0.0.0.0 --port 8000

## Start only the frontend dev server
dev-frontend:
	cd frontend && pnpm run dev

## First-time setup: start infrastructure, pull embedding model, and sync Python dependencies
infra-init:
	docker compose up -d
	docker compose exec ollama ollama pull nomic-embed-text:latest
	cd backend && uv sync

## Start existing infrastructure containers (after first-time setup)
infra-up:
	docker compose up -d

## Stop infrastructure (keeps containers and volumes intact)
infra-down:
	docker compose stop
