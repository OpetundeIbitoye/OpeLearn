"""Permanent cache for replayable external retrieval responses."""

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""CREATE TABLE external_cache (
        cache_key varchar(64) PRIMARY KEY,
        provider text NOT NULL,
        normalized_query text NOT NULL,
        raw_payload jsonb NOT NULL,
        fetched_at timestamptz NOT NULL DEFAULT now()
    )""")
    op.execute("CREATE INDEX ix_external_cache_provider ON external_cache(provider)")


def downgrade() -> None:
    op.execute("DROP TABLE external_cache")
