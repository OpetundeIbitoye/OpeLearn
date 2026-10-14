"""Minimal append-only Phase 2 turn provenance."""

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""CREATE TABLE turns (
        id uuid PRIMARY KEY,
        query text NOT NULL,
        answer text NOT NULL,
        prompt text NOT NULL,
        prompt_hash text NOT NULL,
        embedding_model text NOT NULL,
        reranker_model text NOT NULL,
        generation_model text NOT NULL,
        arms_hash text NOT NULL,
        temperature double precision NOT NULL,
        latency_ms integer NOT NULL CHECK (latency_ms >= 0),
        input_tokens integer NOT NULL CHECK (input_tokens >= 0),
        output_tokens integer NOT NULL CHECK (output_tokens >= 0),
        created_at timestamptz NOT NULL DEFAULT now()
    )""")


def downgrade() -> None:
    op.execute("DROP TABLE turns")
