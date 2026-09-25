# homelab-postgres

PostgreSQL 18 running in Docker on a Synology NAS, managed with Docker Compose.
Part of a self-hosted data platform I'm building to practise production-style database work.

## Stack
- PostgreSQL 18 (official Docker image)
- Docker Compose (via Synology Container Manager)
- Secrets kept in a `.env` file (not committed)

## Setup
1. Clone the repo onto the server
2. `cp .env.example .env` and fill in the values
3. `mkdir data` (required on Synology: its Docker doesn't create bind-mount folders automatically)
4. `sudo docker compose up -d`
5. Check it's running: `sudo docker compose ps`

## Connecting
| Setting  | Value                       |
|----------|-----------------------------|
| Host     | NAS IP address              |
| Port     | `5433`                      |
| Database | `POSTGRES_DB` from `.env`   |
| User     | `POSTGRES_USER` from `.env` |

From the server itself:
`sudo docker exec -it postgres psql -U <user> -d <database>`

## Design decisions
- **Host port 5433:** Synology DSM runs its own built-in Postgres on port 5432, so this container is mapped to host port 5433 to avoid the conflict. Inside the container, Postgres still listens on 5432.
- **UTC time zone:** timestamps are stored in UTC and converted only when displayed.
- **Persistent data:** the database lives in `./data`, a bind mount that survives container updates and is excluded from Git.

## Security
- **No public exposure:** port 5433 is never forwarded on the router. Exposing a database directly to the internet invites constant automated scanning and password-guessing attacks.
- **Remote access via Tailscale:** remote connections go through Tailscale, an encrypted private network (WireGuard-based). Only devices logged into my Tailscale account can reach the database.
- **Key expiry disabled on the server only:** the NAS stays connected permanently. Client devices such as laptops keep key expiry on, so a lost device loses access automatically.
- **Secrets outside Git:** credentials live only in `.env`, which is excluded by `.gitignore`.

## Troubleshooting
| Error | Cause | Fix |
|-------|-------|-----|
| `bind: address already in use` on 5432 | DSM's built-in Postgres uses 5432 (found with `sudo netstat -tlnp \| grep 5432`) | Map the container to host port 5433 |
| `Bind mount failed: ... data does not exist` | Synology's Docker doesn't auto-create bind-mount folders | `mkdir data` before starting |
| `Top-level object must be a mapping` | `docker-compose.yml` was committed empty | Save the file before committing; check with `git diff` |

## Roadmap
- [x] Postgres running in
- [ ] pgAdmin
- [ ] Roles and permissions
- [ ] Sample dataset
- [ ] Automated backups