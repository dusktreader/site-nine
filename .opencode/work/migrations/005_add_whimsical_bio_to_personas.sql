-- Migration 005: Add whimsical_bio field to personas table
-- Created: 2026-02-04
-- Purpose: Support lazy generation of whimsical persona bios during session-start

-- Add whimsical_bio column to personas table
ALTER TABLE personas ADD COLUMN whimsical_bio TEXT;

-- Note: Column is nullable to support lazy generation
-- When NULL, agents will generate bio on-the-fly and store it
