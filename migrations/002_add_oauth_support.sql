-- Migration: Add OAuth support
-- Created: 2025-01-30
-- Description: Adds OAuth authentication support with OAuthAccount table

-- Make password_hash nullable for OAuth users
ALTER TABLE "user" 
ALTER COLUMN password_hash DROP NOT NULL;

-- Create OAuthAccount table
CREATE TABLE oauth_account (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES "user"(id) ON DELETE CASCADE,
    
    -- OAuth provider info
    provider VARCHAR(50) NOT NULL,
    provider_account_id VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    
    -- Additional provider data
    institution VARCHAR(255),
    picture_url VARCHAR(500),
    access_token TEXT,
    refresh_token TEXT,
    token_expires_at DOUBLE PRECISION,
    
    -- Metadata
    raw_data JSONB DEFAULT '{}',
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT CURRENT_TIMESTAMP,
    deleted_at TIMESTAMP WITH TIME ZONE,
    
    -- Constraints
    CONSTRAINT _user_provider_uc UNIQUE (user_id, provider),
    CONSTRAINT _provider_account_uc UNIQUE (provider, provider_account_id)
);

-- Create indexes
CREATE INDEX idx_oauth_user_provider ON oauth_account(user_id, provider);
CREATE INDEX idx_oauth_deleted_at ON oauth_account(deleted_at);

-- Create updated_at trigger
CREATE OR REPLACE FUNCTION update_oauth_account_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER oauth_account_updated_at_trigger
BEFORE UPDATE ON oauth_account
FOR EACH ROW
EXECUTE FUNCTION update_oauth_account_updated_at();

-- Add comments
COMMENT ON TABLE oauth_account IS 'OAuth provider accounts linked to users';
COMMENT ON COLUMN oauth_account.provider IS 'OAuth provider name (google, microsoft, etc.)';
COMMENT ON COLUMN oauth_account.provider_account_id IS 'User ID from the OAuth provider';
COMMENT ON COLUMN oauth_account.token_expires_at IS 'Unix timestamp when the access token expires';
COMMENT ON COLUMN oauth_account.raw_data IS 'Provider-specific data in JSON format';

-- Grant permissions (adjust based on your database user setup)
-- GRANT SELECT, INSERT, UPDATE, DELETE ON oauth_account TO slidegenie_app;