-- 001_setup_db.sql
-- One-time bootstrap: activity database, raw schema, etl user.
-- Run once with psql as the admin user. Tables are managed by Alembic.

\set ON_ERROR_STOP on

CREATE ROLE etl LOGIN PASSWORD :'etl_password';

CREATE DATABASE activity;
REVOKE CONNECT ON DATABASE activity FROM PUBLIC;
GRANT  CONNECT ON DATABASE activity TO etl;

\connect activity

CREATE SCHEMA raw;
GRANT USAGE ON SCHEMA raw TO etl;
ALTER DEFAULT PRIVILEGES IN SCHEMA raw
    GRANT SELECT, INSERT, UPDATE ON TABLES TO etl;