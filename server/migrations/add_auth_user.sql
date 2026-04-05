-- Migration: add AuthUser table
-- Run this against your Supabase/Postgres database if create_db_and_tables()
-- does not auto-create the table (e.g. the table already exists from a prior
-- SQLModel version that did not include AuthUser).

CREATE TABLE IF NOT EXISTS authuser (
    id              SERIAL PRIMARY KEY,
    email           VARCHAR UNIQUE NOT NULL,
    hashed_password VARCHAR NOT NULL,
    role            VARCHAR NOT NULL,          -- 'candidate' or 'recruiter'
    candidate_id    INTEGER REFERENCES candidate(id) ON DELETE SET NULL,
    company_id      INTEGER REFERENCES company(id) ON DELETE SET NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE INDEX IF NOT EXISTS idx_authuser_email ON authuser (email);
