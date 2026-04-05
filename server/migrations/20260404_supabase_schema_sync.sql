-- Pomelo schema sync for existing Supabase/Postgres databases.
--
-- Apply this in the Supabase SQL editor to bring an older live database in line
-- with the current SQLModel schema. This migration is intentionally idempotent.
--
-- Note:
-- - If you already have duplicate swipes or matches, the UNIQUE constraints below
--   will fail until those duplicates are cleaned up.

ALTER TABLE "role"
ADD COLUMN IF NOT EXISTS max_swipes_per_day INTEGER NOT NULL DEFAULT 20;

ALTER TABLE "swipe"
ADD COLUMN IF NOT EXISTS keyword_score DOUBLE PRECISION;

ALTER TABLE "swipe"
ADD COLUMN IF NOT EXISTS keyword_reasoning TEXT;

ALTER TABLE "swipe"
ADD COLUMN IF NOT EXISTS keyword_approved BOOLEAN;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'uq_swipe_candidate_role'
    ) THEN
        ALTER TABLE "swipe"
        ADD CONSTRAINT uq_swipe_candidate_role UNIQUE (candidate_id, role_id);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'uq_match_candidate_role'
    ) THEN
        ALTER TABLE "match"
        ADD CONSTRAINT uq_match_candidate_role UNIQUE (candidate_id, role_id);
    END IF;
END $$;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1
        FROM pg_constraint
        WHERE conname = 'uq_match_swipe_id'
    ) THEN
        ALTER TABLE "match"
        ADD CONSTRAINT uq_match_swipe_id UNIQUE (swipe_id);
    END IF;
END $$;
