-- Rollback Migration: Remove OAuth support
-- Created: 2025-01-30
-- Description: Rolls back OAuth authentication support

-- Drop the oauth_account table (this will also drop the trigger and function)
DROP TABLE IF EXISTS oauth_account CASCADE;

-- Revert password_hash to NOT NULL
-- WARNING: This will fail if there are users without passwords
-- You may need to handle this case based on your requirements
ALTER TABLE "user" 
ALTER COLUMN password_hash SET NOT NULL;