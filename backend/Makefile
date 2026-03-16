.PHONY: dev ingest infra-init infra-up infra-down

## Start the API server in development mode
dev:
	uv run uvicorn docmind.api.main:app --reload --host 0.0.0.0 --port 8000

## Ingest a document: make ingest FILE=doc.pdf TITLE="My Doc"
ingest:
	uv run python scripts/ingest_file.py $(FILE) --title "$(TITLE)"

## First-time setup: start infrastructure and pull embedding model
infra-init:
	docker compose up -d
	docker compose exec ollama ollama pull nomic-embed-text:latest

## Start existing infrastructure containers (after first-time setup)
infra-up:
	docker compose up -d

## Stop infrastructure (keeps containers and volumes intact)
infra-down:
	docker compose stop
