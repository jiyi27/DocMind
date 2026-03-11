.PHONY: dev ingest infra-up infra-down

## Start the API server in development mode
dev:
	uv run uvicorn docmind.api.main:app --reload --host 0.0.0.0 --port 8000

## Ingest a document: make ingest FILE=doc.pdf TITLE="My Doc"
ingest:
	uv run python scripts/ingest_file.py $(FILE) --title "$(TITLE)"

## Start infrastructure (Qdrant + Ollama)
infra-up:
	docker compose up -d

## Stop infrastructure
infra-down:
	docker compose down
