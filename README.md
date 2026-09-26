# homelab-postgres

PostgreSQL 18 and pgAdmin running in Docker on a Synology NAS, managed with Docker Compose.
Part of a self-hosted data platform I'm building to practise production-style database work.

The first project on the platform is **ActivityWatch → Postgres**: a pipeline that loads my own
computer-activity data into a layered database (raw → core → marts).

## Architecture

```
Laptop                                    Synology NAS (Docker)
┌──────────────┐                         ┌───────────────────────────────────┐
│ DBeaver      │── NAS:5433 ────────────►│ postgres container :5432          │
│              │                         │        ▲                          │
│ Browser      │── NAS:5050 ────────────►│ pgadmin container :80             │
└──────────────┘                         │   └── connects to "postgres:5432" │
     │                                   │       (internal Docker network)   │
     └── Tailscale (remote access) ─────►└───────────────────────────────────┘
```

### ActivityWatch data flow

```
LAPTOP                                       NAS
ActivityWatch (localhost:5600)
   │  REST API
   ▼
extract_load.py  ── Tailscale :5433 ──►  Postgres: activity database
(runs as etl user)                          └── raw schema  (data as received)
                                            └── core schema (3NF model, planned)
Alembic          ── Tailscale :5433 ──►  schema changes (runs as admin)
```

- **Pattern:** the laptop *pushes* data to the NAS. ActivityWatch only runs on the laptop and its API
  has no authentication, so it is never exposed to the network.
- **Code** goes to GitHub. **Data** goes only to Postgres. **Secrets** stay in `.env` files.

## Stack
- **PostgreSQL 18** (official Docker image)
- **pgAdmin 4** (web-based administration)
- **Docker Compose** (via Synology Container Manager)
- **Tailscale** for private remote access
- **Alembic** for versioned schema migrations
- **Python 3.12** (conda environment `homelab`) with `psycopg`, `requests`, `python-dotenv`

## Repository layout

```
homelab-postgres/
├── docker-compose.yml          ← Postgres + pgAdmin
├── .env.example                ← container settings (real .env not committed)
├── README.md
└── activitywatch/
    ├── bootstrap/
    │   └── 001_setup_db.sql    ← one-time: activity database, raw schema, etl role
    ├── migrations/             ← Alembic: all table changes, versioned
    │   ├── env.py
    │   └── versions/
    │       └── 0001_create_raw_tables.py
    ├── src/
    │   └── extract_load.py     ← pipeline (in progress)
    ├── alembic.ini
    ├── requirements.txt
    └── .env.example            ← pipeline settings (real .env not committed)
```

## Tools
| Tool | Where it runs | Used for |
|------|---------------|----------|
| **pgAdmin** | NAS, in the browser on port 5050 | Administration: roles, backups, monitoring |
| **DBeaver** | Laptop (desktop app) | Day-to-day querying and data exploration |
| **psql** | NAS (command line) | Quick checks, and running the bootstrap script |
| **Alembic** | Laptop (command line) | Creating and changing tables through versioned migrations |

## Setup

### 1. Platform (on the NAS)
1. Clone the repo onto the server
2. `cp .env.example .env` and fill in the values
3. Create the data folders (Synology's Docker doesn't create bind-mount folders automatically):
   ```bash
   mkdir data pgadmin
   sudo chown -R 5050:5050 pgadmin   # pgAdmin runs as user 5050 inside its container
   ```
4. `sudo docker compose up -d`
5. Check both containers are running: `sudo docker compose ps`

### 2. Activity database bootstrap (on the NAS, once)
Creates the `activity` database, the `raw` schema and the `etl` role. The password is typed at
run time, so it never appears in the file, the screen or shell history.
```bash
read -s -p "etl password: " ETL_PW; echo
sudo docker exec -i postgres psql -U <admin> -d mydb -v etl_password="$ETL_PW" \
    < activitywatch/bootstrap/001_setup_db.sql
```

### 3. Tables via Alembic (on the laptop)
```bash
conda create -n homelab python=3.12 -y
conda activate homelab
cd activitywatch
pip install -r requirements.txt
cp .env.example .env        # fill in DB host, admin and etl credentials
alembic upgrade head
```

## Connecting
| Client | Host | Port |
|--------|------|------|
| DBeaver / any SQL client | NAS LAN IP (at home) or Tailscale hostname (remote) | `5433` |
| pgAdmin (browser) | `http://<NAS IP>:5050` | `5050` |
| pgAdmin → Postgres (server registration) | `postgres` (Docker service name) | `5432` |
| psql on the NAS | `sudo docker exec -it postgres psql -U <user> -d <database>` | n/a |

## Databases and roles

| Database | Purpose |
|----------|---------|
| `mydb` | Sandbox for experiments |
| `activity` | ActivityWatch project |

| Role | Used by | Privileges on `raw` tables |
|------|---------|----------------------------|
| admin (`POSTGRES_USER`) | Me, and Alembic migrations | Everything (owner) |
| `etl` | The pipeline script | `SELECT`, `INSERT`, `UPDATE` only: no delete, truncate or DDL |

`etl` receives its privileges through `ALTER DEFAULT PRIVILEGES`, so every table Alembic creates
in `raw` is covered automatically. Verified with `\dp raw.*` → `etl=arw/<admin>`.

## Schema management
- **Bootstrap vs migrations:** creating the database and roles is server-level setup, done once with
  psql (`bootstrap/001_setup_db.sql`). Everything *inside* the database is an Alembic revision.
- **Versioned migrations with Alembic:** each change is a numbered revision with `upgrade()` and
  `downgrade()`, written in plain SQL. The database records its current version in `alembic_version`.
- **Rollback tested:** `alembic downgrade -1` / `alembic upgrade head` on the empty tables.

| Revision | Change |
|----------|--------|
| `0001` | `raw.aw_buckets` and `raw.aw_events` |

## ActivityWatch data model

**Layers:** `raw` (exactly as received) → `core` (my own 3NF model, planned) → marts (later).

**Raw tables**
- `raw.aw_buckets`: one row per data source; the full bucket JSON in `payload`.
- `raw.aw_events`: one row per event; the full event JSON in `payload`, plus a typed `ts` copy used
  only for the incremental-load watermark. Primary key `(bucket_id, event_id)`.

**Buckets collected:** window (app and title), AFK (active/away), Chrome web tabs.

**Load strategy (planned for `extract_load.py`)**
- *Incremental:* fetch only events newer than the latest loaded `ts`, minus a 1-hour overlap.
- *Idempotent:* upsert on the primary key, so re-runs never duplicate rows.
- *Overlap:* the most recent event keeps growing in duration; re-fetching the last hour captures its final value.

**Data-quality findings from exploring the source**
- **Mislabelled timestamps:** bucket `created` is local time (UTC+8) labelled as UTC; event timestamps are true UTC.
- **Overlapping AFK events:** two `afk` events can share a start time with different durations; summing durations naively double-counts time.
- **Duplicate web bucket:** `aw-watcher-web-chrome` (no hostname) holds a single event from the extension install.
- **Non-continuous IDs:** event IDs skip numbers because ActivityWatch merges repeated heartbeats; IDs appear to be shared across buckets.
- **Empty window titles** occur briefly while windows open.

Raw keeps all of this untouched; cleaning rules belong in `core`.

## Design decisions
- **Host port 5433:** Synology DSM runs its own built-in Postgres on port 5432, so this container is mapped to host port 5433 to avoid the conflict. Inside the container, Postgres still listens on 5432.
- **Internal vs external ports:** pgAdmin reaches Postgres over the internal Docker network by service name (`postgres:5432`). Only clients outside the NAS use the published port 5433.
- **UTC time zone:** timestamps are stored in UTC and converted only when displayed.
- **Persistent data:** the database (`./data`) and pgAdmin settings (`./pgadmin`) are bind mounts that survive container updates and are excluded from Git.
- **Push, not pull:** ActivityWatch data originates on the laptop, so the laptop pushes it to the NAS (the same pattern as device agents in industry).
- **Raw payload kept verbatim:** the original JSON, including timestamp strings, is stored as `jsonb` so the core model can be redesigned without re-fetching.

## Security
- **No public exposure:** ports 5433 and 5050 are never forwarded on the router.
- **Remote access via Tailscale:** an encrypted private network (WireGuard-based); only my devices can reach these services.
- **pgAdmin over HTTP:** acceptable only because it's reachable solely on the LAN and Tailscale.
- **Key expiry disabled on the server only:** client devices keep key expiry on, so a lost device loses access automatically.
- **Least privilege:** the pipeline logs in as `etl`, which cannot delete data or change the schema.
- **Secrets outside Git:** credentials live only in `.env` files; passwords for new roles are passed to psql as variables at run time.
- **Trusted local connections:** the official Postgres image trusts connections from inside the container (`127.0.0.1`), so password tests must connect through port 5433 to be meaningful.

## Troubleshooting
| Error | Cause | Fix |
|-------|-------|-----|
| `bind: address already in use` on 5432 | DSM's built-in Postgres uses 5432 (found with `sudo netstat -tlnp`) | Map the container to host port 5433 |
| `Bind mount failed: ... does not exist` | Synology's Docker doesn't auto-create bind-mount folders | `mkdir` the folder before starting |
| `Top-level object must be a mapping` | `docker-compose.yml` was committed empty | Save the file before committing; check with `git diff` |
| pgAdmin keeps restarting (permission denied) | pgAdmin runs as user 5050 and can't write to its folder | `sudo chown -R 5050:5050 pgadmin` |
| `ERR_CONNECTION_RESET` when opening pgAdmin | pgAdmin is still initialising on first start | Wait a minute, then reload |
| `syntax error at or near ":"` in the bootstrap | psql variable name mismatch (`-v elt_password` vs `:'etl_password'`); undefined variables are left in the SQL as-is | Pass the exact variable name with `-v` |
| Password test shows `Password Used: false` | Connection from inside the container is trusted | Test through `-h <NAS IP> -p 5433` |
| `'py' is not recognized` / VS Code "No Python found" | Python installed via conda, not the python.org launcher | Use a conda env (`conda activate homelab`) and select it as the VS Code interpreter |

## Roadmap
- [x] Postgres running in Docker, configured as code
- [x] Remote access via Tailscale
- [x] pgAdmin
- [x] SQL client (DBeaver) and psql
- [x] Real data source chosen: ActivityWatch (window, AFK and web buckets explored)
- [x] Roles and permissions: admin and least-privilege `etl` role
- [x] Schema migrations with Alembic (revision 0001, rollback tested)
- [ ] Data pipeline: `extract_load.py` (incremental, idempotent)
- [ ] Hourly scheduling with Windows Task Scheduler
- [ ] Core layer: 3NF model built from raw
- [ ] Read-only `analyst` role
- [ ] Query performance tuning
- [ ] Automated backups and restore test
- [ ] BI dashboard (Metabase)
