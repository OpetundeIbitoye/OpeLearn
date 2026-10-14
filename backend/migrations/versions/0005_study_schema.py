"""Freeze the complete research instrument schema."""

from alembic import op

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("""CREATE TABLE participants (
        id uuid PRIMARY KEY, pseudonym varchar(32) NOT NULL UNIQUE,
        consent_version text, consented_at timestamptz, baseline_cluster text,
        assigned_arm varchar(2), assignment_seed integer, clustering_run_id uuid,
        created_at timestamptz NOT NULL DEFAULT now()
    )""")
    op.execute("""CREATE TABLE sessions (
        id uuid PRIMARY KEY, participant_id uuid NOT NULL REFERENCES participants(id),
        phase varchar(16) NOT NULL CHECK (phase IN ('baseline', 'treatment')),
        started_at timestamptz NOT NULL DEFAULT now(), ended_at timestamptz
    )""")
    op.execute("CREATE INDEX ix_sessions_participant_id ON sessions(participant_id)")
    op.execute("ALTER TABLE turns ADD COLUMN session_id uuid REFERENCES sessions(id)")
    op.execute("CREATE INDEX ix_turns_session_id ON turns(session_id)")
    op.execute("""CREATE TABLE retrieval_results (
        id uuid PRIMARY KEY, turn_id uuid NOT NULL REFERENCES turns(id),
        chunk_id uuid NOT NULL REFERENCES chunks(id), rank integer NOT NULL,
        dense_score double precision, sparse_score double precision,
        fused_score double precision NOT NULL, rerank_score double precision,
        query_variant text NOT NULL, created_at timestamptz NOT NULL DEFAULT now()
    )""")
    op.execute("CREATE INDEX ix_retrieval_results_turn_id ON retrieval_results(turn_id)")
    op.execute("""CREATE TABLE interaction_events (
        id uuid PRIMARY KEY, session_id uuid NOT NULL REFERENCES sessions(id),
        event_type text NOT NULL, payload jsonb NOT NULL,
        client_timestamp timestamptz NOT NULL, received_at timestamptz NOT NULL DEFAULT now()
    )""")
    op.execute("CREATE INDEX ix_interaction_events_session_id ON interaction_events(session_id)")
    op.execute("""CREATE TABLE survey_responses (
        id uuid PRIMARY KEY, session_id uuid NOT NULL REFERENCES sessions(id),
        instrument text NOT NULL, trigger varchar(16) NOT NULL,
        responses jsonb NOT NULL, submitted_at timestamptz NOT NULL DEFAULT now()
    )""")
    op.execute("CREATE INDEX ix_survey_responses_session_id ON survey_responses(session_id)")
    op.execute("""CREATE FUNCTION reject_study_event_mutation() RETURNS trigger LANGUAGE plpgsql AS $$
    BEGIN RAISE EXCEPTION 'interaction_events is append-only'; END $$""")
    op.execute("""CREATE TRIGGER interaction_events_append_only BEFORE UPDATE OR DELETE
        ON interaction_events FOR EACH ROW EXECUTE FUNCTION reject_study_event_mutation()""")


def downgrade() -> None:
    op.execute("DROP TRIGGER interaction_events_append_only ON interaction_events")
    op.execute("DROP FUNCTION reject_study_event_mutation()")
    op.execute("DROP TABLE survey_responses")
    op.execute("DROP TABLE interaction_events")
    op.execute("DROP TABLE retrieval_results")
    op.execute("ALTER TABLE turns DROP COLUMN session_id")
    op.execute("DROP TABLE sessions")
    op.execute("DROP TABLE participants")
