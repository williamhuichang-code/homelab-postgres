"""create raw tables

Revision ID: 0001
Revises: 
Create Date: 2026-09-26 18:34:06.633688

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '0001'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        CREATE TABLE raw.aw_buckets (
            bucket_id   text PRIMARY KEY,
            payload     jsonb NOT NULL,
            loaded_at   timestamptz NOT NULL DEFAULT now()
        );
    """)
    op.execute("""
        CREATE TABLE raw.aw_events (
            bucket_id       text        NOT NULL,
            event_id        bigint      NOT NULL,
            payload         jsonb       NOT NULL,
            ts              timestamptz NOT NULL,
            first_loaded_at timestamptz NOT NULL DEFAULT now(),
            last_loaded_at  timestamptz NOT NULL DEFAULT now(),
            PRIMARY KEY (bucket_id, event_id)
        );
    """)
    op.execute("CREATE INDEX aw_events_bucket_ts_idx ON raw.aw_events (bucket_id, ts);")


def downgrade() -> None:
    op.execute("DROP TABLE raw.aw_events;")
    op.execute("DROP TABLE raw.aw_buckets;")
