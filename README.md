# homelab-postgres

PostgreSQL 18 running in Docker on a Synology NAS, managed with Docker Compose.
Part of a self-hosted data platform I'm building to practise production-style database work.

## Stack
- PostgreSQL 18 (official Docker image)
- Docker Compose (via Synology Container Manager)
- Secrets kept in a `.env` file (not committed)

## Setup
1. Clone the repo
2. `cp .env.example .env` and fill in the values
3. `docker compose up -d`

## Design decisions
- **UTC time zone:** timestamps are stored in UTC and converted only when displayed
- **Secrets outside Git:** credentials live only in `.env`, which `.gitignore` excludes
- **Persistent data:** the database is stored in `./data`, a bind mount that survives container updates

## Roadmap
- [ ] pgAdmin
- [ ] Roles and permissions
- [ ] Sample dataset
- [ ] Automated backups