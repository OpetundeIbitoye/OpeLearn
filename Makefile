DOCKER := $(or $(shell command -v docker),$(firstword $(wildcard /usr/local/bin/docker /usr/bin/docker /opt/homebrew/bin/docker /Applications/Docker.app/Contents/Resources/bin/docker)))
CORPUS_INPUT := $(if $(filter command line,$(origin PATH)),$(PATH),./sample_papers)

.PHONY: up down migrate revision ingest export test fmt

up:        ; docker compose up -d --build
down:      ; docker compose down
logs:      ; docker compose logs -f api worker
migrate:   ; docker compose exec api alembic upgrade head
revision:  ; docker compose exec api alembic revision --autogenerate -m "$(M)"
ingest:    ; PATH="$(dir $(DOCKER)):/usr/local/bin:/usr/bin:/bin" "$(DOCKER)" compose exec api python -m scripts.ingest_corpus "$(CORPUS_INPUT)"
export:    ; docker compose exec api python -m scripts.export_dataset
test:      ; docker compose exec api pytest -q
fmt:       ; ruff format backend && ruff check --fix backend
