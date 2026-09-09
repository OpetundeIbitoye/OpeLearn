"""Corpus tables and local hybrid retrieval indexes."""

from alembic import op

from app.corpus.embedding import embedding_dimension

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def upgrade() -> None:
    dimension = embedding_dimension()
    op.execute("""CREATE TABLE documents (
        id uuid PRIMARY KEY, sha256 varchar(64) NOT NULL UNIQUE,
        filename text NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
    )""")
    op.execute(f"""CREATE TABLE chunks (
        id uuid PRIMARY KEY, document_id uuid NOT NULL REFERENCES documents(id),
        ordinal integer NOT NULL, text text NOT NULL, section_heading text NOT NULL,
        page_number integer NOT NULL CHECK (page_number >= 1),
        token_count integer NOT NULL CHECK (token_count BETWEEN 1 AND 600),
        embedding_model text NOT NULL, embedding_revision text NOT NULL,
        embedding halfvec({dimension}) NOT NULL,
        search_vector tsvector NOT NULL DEFAULT '',
        UNIQUE(document_id, ordinal)
    )""")
    op.execute("""CREATE FUNCTION chunks_search_vector() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN NEW.search_vector := to_tsvector('english', NEW.text); RETURN NEW; END $$""")
    op.execute("""CREATE TRIGGER chunks_search_vector BEFORE INSERT OR UPDATE OF text ON chunks
               FOR EACH ROW EXECUTE FUNCTION chunks_search_vector()""")
    op.execute("CREATE INDEX ix_chunks_document_id ON chunks(document_id)")
    op.execute(
        "CREATE INDEX ix_chunks_embedding_hnsw ON chunks USING hnsw (embedding halfvec_cosine_ops)"
    )
    op.execute("CREATE INDEX ix_chunks_search_vector_gin ON chunks USING gin (search_vector)")


def downgrade() -> None:
    op.execute("DROP TABLE chunks")
    op.execute("DROP FUNCTION chunks_search_vector()")
    op.execute("DROP TABLE documents")
