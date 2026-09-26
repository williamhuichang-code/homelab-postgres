"""Extract ActivityWatch data and load it into the raw schema in Postgres.

Incremental: for each bucket, re-fetch events starting 1 hour before the
latest event already loaded (the "watermark").
Idempotent: upserts on primary keys, so re-running never duplicates rows.
"""
import os
from datetime import datetime, timedelta

import psycopg
import requests
from dotenv import load_dotenv
from psycopg.types.json import Jsonb

AW_API = "http://localhost:5600/api/0"
OVERLAP = timedelta(hours=1)

UPSERT_BUCKET = """
    INSERT INTO raw.aw_buckets (bucket_id, payload)
    VALUES (%s, %s)
    ON CONFLICT (bucket_id) DO UPDATE
    SET payload   = EXCLUDED.payload,
        loaded_at = now()
    WHERE raw.aw_buckets.payload IS DISTINCT FROM EXCLUDED.payload;
"""

UPSERT_EVENT = """
    INSERT INTO raw.aw_events (bucket_id, event_id, payload, ts)
    VALUES (%s, %s, %s, %s)
    ON CONFLICT (bucket_id, event_id) DO UPDATE
    SET payload        = EXCLUDED.payload,
        ts             = EXCLUDED.ts,
        last_loaded_at = now()
    WHERE raw.aw_events.payload IS DISTINCT FROM EXCLUDED.payload;
"""


def get_watermark(cur, bucket_id):
    """Latest event timestamp already loaded for this bucket (None if none)."""
    cur.execute("SELECT max(ts) FROM raw.aw_events WHERE bucket_id = %s", (bucket_id,))
    return cur.fetchone()[0]


def fetch_events(bucket_id, start):
    """Fetch events from ActivityWatch, optionally only from `start` onwards."""
    params = {"limit": -1}  # -1 = no limit
    if start is not None:
        params["start"] = start.isoformat()
    resp = requests.get(f"{AW_API}/buckets/{bucket_id}/events", params=params, timeout=60)
    resp.raise_for_status()
    return resp.json()


def main():
    load_dotenv()  # reads activitywatch/.env

    resp = requests.get(f"{AW_API}/buckets/", timeout=30)
    resp.raise_for_status()
    buckets = resp.json()

    with psycopg.connect(
        host=os.environ["DB_HOST"],
        port=os.environ["DB_PORT"],
        dbname=os.environ["DB_NAME"],
        user=os.environ["ETL_DB_USER"],
        password=os.environ["ETL_DB_PASSWORD"],
    ) as conn:
        with conn.cursor() as cur:
            for bucket_id, meta in buckets.items():
                cur.execute(UPSERT_BUCKET, (bucket_id, Jsonb(meta)))

                watermark = get_watermark(cur, bucket_id)
                start = watermark - OVERLAP if watermark else None

                events = fetch_events(bucket_id, start)
                rows = [
                    (bucket_id, e["id"], Jsonb(e), datetime.fromisoformat(e["timestamp"]))
                    for e in events
                ]
                if rows:
                    cur.executemany(UPSERT_EVENT, rows)

                conn.commit()
                print(f"{bucket_id}: {len(rows)} events fetched (from {start or 'beginning'})")


if __name__ == "__main__":
    main()