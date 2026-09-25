# homelab-postgres

PostgreSQL 18 running in Docker on a Synology NAS, managed with Docker Compose.
Part of a self-hosted data platform I'm building to practise production-style database work.

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

## Stack
- PostgreSQL 18 (official Docker image)
- Docker Compose (via Synology Container Manager)
- Secrets kept in a `.env` file (not committed)

## Stack
- **PostgreSQL 18** (official Docker image)
- **pgAdmin 4** (web-based administration)
- **Docker Compose** (via Synology Container Manager)
- **Tailscale** for private remote access

## Tools
| Tool | Where it runs | Used for |
|------|---------------|----------|
| **pgAdmin** | NAS, in the browser on port 5050 | Administration: roles, backups, monitoring |
| **DBeaver** | Laptop (desktop app) | Day-to-day querying and data exploration |
| **psql** | NAS (command line) | Quick checks and scripting on the server |

## Setup
1. Clone the repo onto the server
2. `cp .env.example .env` and fill in the values
3. Create the data folders (Synology's Docker doesn't create bind-mount folders automatically):
```bash
   mkdir data pgadmin
   sudo chown -R 5050:5050 pgadmin   # pgAdmin runs as user 5050 inside its container
```
4. `sudo docker compose up -d`
5. Check both containers are running: `sudo docker compose ps`

## Connecting
| Client | Host | Port |
|--------|------|------|
| DBeaver / any SQL client | NAS LAN IP (at home) or Tailscale hostname (remote) | `5433` |
| pgAdmin (browser) | `http://<NAS IP>:5050` | `5050` |
| pgAdmin → Postgres (server registration) | `postgres` (Docker service name) | `5432` |
| psql on the NAS | `sudo docker exec -it postgres psql -U <user> -d <database>` | n/a |

Database name, user and password come from `.env`.

## Design decisions
- **Host port 5433:** Synology DSM runs its own built-in Postgres on port 5432, so this container is mapped to host port 5433 to avoid the conflict. Inside the container, Postgres still listens on 5432.
- **Internal vs external ports:** pgAdmin reaches Postgres over the internal Docker network by service name (`postgres:5432`). Only clients outside the NAS use the published port 5433.
- **UTC time zone:** timestamps are stored in UTC and converted only when displayed.
- **Persistent data:** the database (`./data`) and pgAdmin settings (`./pgadmin`) are bind mounts that survive container updates and are excluded from Git.

## Security
- **No public exposure:** ports 5433 and 5050 are never forwarded on the router. Exposing a database or admin tool directly to the internet invites constant automated scanning and password-guessing attacks.
- **Remote access via Tailscale:** remote connections go through Tailscale, an encrypted private network (WireGuard-based). Only devices logged into my Tailscale account can reach these services.
- **pgAdmin over HTTP:** acceptable only because it's reachable solely on the LAN and Tailscale, which already encrypts traffic.
- **Key expiry disabled on the server only:** the NAS stays connected permanently. Client devices such as laptops keep key expiry on, so a lost device loses access automatically.
- **Secrets outside Git:** credentials live only in `.env`, which is excluded by `.gitignore`. `.env.example` lists the variables needed.

## Troubleshooting
| Error | Cause | Fix |
|-------|-------|-----|
| `bind: address already in use` on 5432 | DSM's built-in Postgres uses 5432 (found with `sudo netstat -tlnp`) | Map the container to host port 5433 |
| `Bind mount failed: ... does not exist` | Synology's Docker doesn't auto-create bind-mount folders | `mkdir` the folder before starting |
| `Top-level object must be a mapping` | `docker-compose.yml` was committed empty | Save the file before committing; check with `git diff` |
| pgAdmin keeps restarting (permission denied) | pgAdmin runs as user 5050 and can't write to its folder | `sudo chown -R 5050:5050 pgadmin` |
| `ERR_CONNECTION_RESET` when opening pgAdmin | pgAdmin is still initialising on first start | Wait a minute, then reload |

## Roadmap
- [x] Postgres running in Docker, configured as code
- [x] Remote access via Tailscale
- [x] pgAdmin
- [x] SQL client (DBeaver) and psql
- [ ] Sample dataset
- [ ] Roles and permissions
- [ ] Schema migrations
- [ ] Data pipeline (Python ETL + dbt)
- [ ] Query performance tuning
- [ ] Automated backups and restore test
- [ ] BI dashboard (Metabase)