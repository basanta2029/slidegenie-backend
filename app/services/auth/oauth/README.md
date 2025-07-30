# SlideGenie OAuth Integration

This module provides OAuth2 integration for SlideGenie with a focus on academic institutions.

## Features

- **Google OAuth**: Integration with Google Workspace for Education
- **Microsoft OAuth**: Integration with Microsoft 365 Education
- **Academic Focus**: Preference for .edu emails and academic institutions
- **Secure State Management**: CSRF protection with Redis-backed state management
- **Flexible Account Linking**: Users can link multiple OAuth providers

## Architecture

### Components

1. **Base Classes** (`base.py`)
   - `OAuthProviderInterface`: Abstract base class for OAuth providers
   - `OAuthUserInfo`: Standardized user information model
   - `OAuthTokens`: OAuth token management
   - `OAuthError`: OAuth-specific exceptions

2. **Providers**
   - `GoogleOAuthProvider`: Google OAuth implementation
   - `MicrosoftOAuthProvider`: Microsoft OAuth implementation

3. **State Management** (`state_manager.py`)
   - `OAuthStateManager`: Secure state token management with Redis
   - CSRF protection with cryptographically secure tokens
   - State expiration and cleanup

4. **API Endpoints** (`/app/api/v1/endpoints/oauth.py`)
   - Authorization initiation endpoints
   - Callback handling
   - Account linking/unlinking

## Usage

### Configuration

Add the following to your `.env` file:

```env
# Google OAuth
GOOGLE_CLIENT_ID=your-google-client-id
GOOGLE_CLIENT_SECRET=your-google-client-secret

# Microsoft OAuth
MICROSOFT_CLIENT_ID=your-microsoft-client-id
MICROSOFT_CLIENT_SECRET=your-microsoft-client-secret

# OAuth Settings
OAUTH_AUTO_CREATE_USERS=true
OAUTH_REDIRECT_TO_FRONTEND=true
API_BASE_URL=http://localhost:8000
FRONTEND_URL=http://localhost:3000
```

### Google OAuth Setup

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing
3. Enable Google+ API
4. Create OAuth 2.0 credentials
5. Add authorized redirect URIs:
   - `http://localhost:8000/api/v1/oauth/google/callback` (development)
   - `https://yourdomain.com/api/v1/oauth/google/callback` (production)

### Microsoft OAuth Setup

1. Go to [Azure Portal](https://portal.azure.com/)
2. Register a new application
3. Configure authentication:
   - Add Web platform
   - Add redirect URIs:
     - `http://localhost:8000/api/v1/oauth/microsoft/callback` (development)
     - `https://yourdomain.com/api/v1/oauth/microsoft/callback` (production)
4. Add API permissions:
   - Microsoft Graph: User.Read, EduRoster.ReadBasic

## API Endpoints

### Get OAuth Providers
```
GET /api/v1/oauth/providers
```

Returns list of configured OAuth providers.

### Google OAuth

**Initiate Authorization:**
```
GET /api/v1/oauth/google/authorize?action=login&frontend_redirect=/dashboard
```

Parameters:
- `action`: `login`, `signup`, or `link`
- `frontend_redirect`: Where to redirect after successful auth
- `redirect_uri`: Custom redirect URI (optional)

**Handle Callback:**
```
GET /api/v1/oauth/google/callback?code=...&state=...
```

### Microsoft OAuth

**Initiate Authorization:**
```
GET /api/v1/oauth/microsoft/authorize?action=login&tenant=common
```

Parameters:
- `action`: `login`, `signup`, or `link`
- `tenant`: Azure AD tenant (default: `common`)
- `frontend_redirect`: Where to redirect after successful auth

**Handle Callback:**
```
GET /api/v1/oauth/microsoft/callback?code=...&state=...
```

### Account Management

**Get Linked Accounts:**
```
GET /api/v1/oauth/linked-accounts
Authorization: Bearer <token>
```

**Unlink Provider:**
```
POST /api/v1/oauth/unlink/{provider}
Authorization: Bearer <token>
```

## Academic Institution Detection

The system automatically detects academic institutions through:

1. **Email Domain Analysis**
   - Checks for `.edu` domains
   - Maintains list of known academic domains

2. **OAuth Provider Data**
   - Google: `hd` parameter for Google Workspace domains
   - Microsoft: Tenant type and organization info

3. **Institution Mapping**
   - Maps common domains to full institution names
   - Stores institution information with user profile

## Security Features

1. **State Management**
   - Cryptographically secure state tokens
   - State expiration (10 minutes default)
   - IP address validation (optional)
   - One-time use enforcement

2. **Token Security**
   - Access tokens encrypted in database
   - Refresh tokens for long-term access
   - Automatic token refresh

3. **Account Security**
   - Prevents unlinking last authentication method
   - Requires password for critical operations
   - Email verification for OAuth accounts

## Error Handling

The module provides comprehensive error handling:

- `OAuthError`: Base exception for OAuth-related errors
- Detailed logging with structlog
- User-friendly error messages
- Graceful fallbacks

## Database Schema

### OAuthAccount Table

```sql
CREATE TABLE oauth_account (
    id UUID PRIMARY KEY,
    user_id UUID REFERENCES user(id),
    provider VARCHAR(50),
    provider_account_id VARCHAR(255),
    email VARCHAR(255),
    institution VARCHAR(255),
    access_token TEXT,
    refresh_token TEXT,
    token_expires_at FLOAT,
    raw_data JSONB,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    deleted_at TIMESTAMP
);
```

## Future Enhancements

1. **Additional Providers**
   - GitHub (for technical documentation)
   - LinkedIn (for professional networks)
   - ORCID (for researcher identification)

2. **Enhanced Academic Features**
   - Automatic institution verification
   - Academic email validation service
   - Integration with institutional SSO

3. **Advanced Security**
   - PKCE support for public clients
   - Token encryption at rest
   - Anomaly detection for suspicious logins