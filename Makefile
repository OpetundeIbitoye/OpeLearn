.PHONY: up down migrate revision ingest export test fmt

up:        ; docker compose up -d --build
down:      ; docker compose down
logs:      ; docker compose logs -f api worker
migrate:   ; docker compose exec api alembic upgrade head
revision:  ; docker compose exec api alembic revision --autogenerate -m "$(M)"
ingest:    ; docker compose exec api python -m scripts.ingest_corpus $(PATH)
export:    ; docker compose exec api python -m scripts.export_dataset
test:      ; docker compose exec api pytest -q
fmt:       ; ruff format backend && ruff check --fix backend
