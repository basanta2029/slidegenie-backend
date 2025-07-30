# SlideGenie Authentication API Documentation

## Overview

SlideGenie's authentication system provides secure, academic-focused authentication with support for traditional email/password login and OAuth providers (Google, Microsoft). The system includes advanced features like rate limiting, account lockout protection, and role-based access control (RBAC).

## Table of Contents

1. [Authentication Flow](#authentication-flow)
2. [API Endpoints](#api-endpoints)
3. [Request/Response Formats](#requestresponse-formats)
4. [Error Handling](#error-handling)
5. [Security Features](#security-features)
6. [Rate Limiting](#rate-limiting)
7. [Role-Based Access Control](#role-based-access-control)
8. [OAuth Integration](#oauth-integration)
9. [API Key Authentication](#api-key-authentication)
10. [Code Examples](#code-examples)

## Authentication Flow

### Standard Authentication Flow

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant AuthService
    participant Database
    participant EmailService

    Client->>API: POST /api/v1/auth/register
    API->>AuthService: Register user
    AuthService->>Database: Create user
    AuthService->>EmailService: Send verification email
    API-->>Client: 201 Created (tokens + user info)
    
    Note over Client: User verifies email
    
    Client->>API: GET /api/v1/auth/verify?token=xxx
    API->>AuthService: Verify email
    AuthService->>Database: Update user.is_verified
    API-->>Client: 200 OK
    
    Client->>API: POST /api/v1/auth/login
    API->>AuthService: Authenticate
    AuthService->>Database: Validate credentials
    API-->>Client: 200 OK (tokens + user info)
```

### OAuth Flow

```mermaid
sequenceDiagram
    participant Client
    participant API
    participant OAuth Provider
    participant AuthService

    Client->>API: GET /api/v1/auth/oauth/google
    API-->>Client: 302 Redirect to Google
    
    Client->>OAuth Provider: Authorize
    OAuth Provider-->>Client: Redirect with code
    
    Client->>API: GET /api/v1/auth/callback/google?code=xxx
    API->>OAuth Provider: Exchange code for tokens
    OAuth Provider-->>API: Access token + user info
    API->>AuthService: Create/update user
    API-->>Client: 200 OK (tokens + user info)
```

## API Endpoints

### Authentication Endpoints

#### 1. Register New User

```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "student@mit.edu",
  "password": "SecureP@ssw0rd123!",
  "first_name": "John",
  "last_name": "Doe",
  "institution": "MIT",
  "role": "student"
}
```

**Response:**
```json
{
  "user": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "email": "student@mit.edu",
    "first_name": "John",
    "last_name": "Doe",
    "institution": "MIT",
    "role": "student",
    "is_active": true,
    "is_verified": false,
    "created_at": "2024-01-15T10:30:00Z",
    "last_login": null
  },
  "tokens": {
    "access_token": "eyJhbGciOiJIUzI1NiIs...",
    "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
    "token_type": "Bearer",
    "expires_in": 1800
  },
  "session": {
    "session_id": "sess_1234567890",
    "created_at": "2024-01-15T10:30:00Z",
    "last_activity": "2024-01-15T10:30:00Z",
    "ip_address": "192.168.1.100",
    "user_agent": "Mozilla/5.0..."
  }
}
```

#### 2. Login

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "student@mit.edu",
  "password": "SecureP@ssw0rd123!"
}
```

**Response:** Same as registration response

#### 3. Refresh Access Token

```http
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Response:**
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIs...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIs...",
  "token_type": "Bearer",
  "expires_in": 1800
}
```

#### 4. Logout

```http
POST /api/v1/auth/logout
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "refresh_token": "eyJhbGciOiJIUzI1NiIs..."
}
```

**Response:**
```json
{
  "message": "Successfully logged out"
}
```

#### 5. Get Current User

```http
GET /api/v1/auth/me
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "email": "student@mit.edu",
  "first_name": "John",
  "last_name": "Doe",
  "institution": "MIT",
  "role": "student",
  "permissions": [
    "create:presentation",
    "read:presentation",
    "update:presentation",
    "delete:presentation"
  ],
  "is_active": true,
  "is_verified": true,
  "created_at": "2024-01-15T10:30:00Z",
  "last_login": "2024-01-15T14:20:00Z"
}
```

#### 6. Email Verification

```http
GET /api/v1/auth/verify?token=<verification_token>
```

**Response:**
```json
{
  "message": "Email verified successfully"
}
```

#### 7. Resend Verification Email

```http
POST /api/v1/auth/resend-verification
Content-Type: application/json

{
  "email": "student@mit.edu"
}
```

**Response:**
```json
{
  "message": "Verification email sent"
}
```

### OAuth Endpoints

#### 1. Initiate OAuth Flow

```http
GET /api/v1/auth/oauth/google
GET /api/v1/auth/oauth/microsoft
```

**Response:** 302 Redirect to OAuth provider

#### 2. OAuth Callback

```http
GET /api/v1/auth/callback/google?code=xxx&state=yyy
GET /api/v1/auth/callback/microsoft?code=xxx&state=yyy
```

**Response:** Same as login response

### Password Management

#### 1. Request Password Reset

```http
POST /api/v1/auth/password/reset-request
Content-Type: application/json

{
  "email": "student@mit.edu"
}
```

**Response:**
```json
{
  "message": "Password reset email sent"
}
```

#### 2. Reset Password

```http
POST /api/v1/auth/password/reset
Content-Type: application/json

{
  "token": "reset_token_here",
  "new_password": "NewSecureP@ssw0rd123!"
}
```

**Response:**
```json
{
  "message": "Password reset successfully"
}
```

### API Key Management

#### 1. Create API Key

```http
POST /api/v1/auth/api-keys
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "name": "Production API Key",
  "roles": ["api_user"],
  "expires_in_days": 90
}
```

**Response:**
```json
{
  "key_id": "key_550e8400-e29b-41d4",
  "key": "sk_live_AbCdEfGhIjKlMnOpQrStUvWxYz",
  "prefix": "sk_live_",
  "name": "Production API Key",
  "created_at": "2024-01-15T10:30:00Z",
  "expires_at": "2024-04-15T10:30:00Z"
}
```

#### 2. List API Keys

```http
GET /api/v1/auth/api-keys
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "api_keys": [
    {
      "key_id": "key_550e8400-e29b-41d4",
      "name": "Production API Key",
      "prefix": "sk_live_",
      "last_used": "2024-01-15T12:00:00Z",
      "created_at": "2024-01-15T10:30:00Z",
      "expires_at": "2024-04-15T10:30:00Z"
    }
  ]
}
```

#### 3. Revoke API Key

```http
DELETE /api/v1/auth/api-keys/:key_id
Authorization: Bearer <access_token>
```

**Response:**
```json
{
  "message": "API key revoked successfully"
}
```

## Request/Response Formats

### Common Headers

```http
Content-Type: application/json
Accept: application/json
Authorization: Bearer <token>
X-Request-ID: <unique-request-id>
X-Client-Version: 1.0.0
```

### Authentication Token Format

JWT tokens contain the following claims:

```json
{
  "sub": "550e8400-e29b-41d4-a716-446655440000",
  "email": "student@mit.edu",
  "roles": ["student"],
  "permissions": ["create:presentation", "read:presentation"],
  "institution": "MIT",
  "exp": 1705321800,
  "iat": 1705320000,
  "jti": "unique-token-id"
}
```

## Error Handling

### Error Response Format

```json
{
  "error": {
    "code": "AUTH_001",
    "message": "Invalid email or password",
    "field": "email",
    "details": {
      "attempts_remaining": 2
    }
  }
}
```

### Common Error Codes

| Code | Description | HTTP Status |
|------|-------------|-------------|
| AUTH_001 | Invalid credentials | 401 |
| AUTH_002 | User not found | 404 |
| AUTH_003 | User already exists | 409 |
| AUTH_004 | Email not verified | 403 |
| AUTH_005 | Invalid token | 401 |
| AUTH_006 | Token expired | 401 |
| AUTH_007 | Insufficient permissions | 403 |
| AUTH_010 | Account locked | 423 |
| SEC_001 | Rate limit exceeded | 429 |
| VAL_001 | Invalid email format | 400 |
| VAL_002 | Weak password | 400 |

## Security Features

### Password Requirements

- Minimum 12 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number
- At least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)

### Rate Limiting

| Endpoint | Limit | Window |
|----------|-------|--------|
| /auth/login | 5 requests | 15 minutes |
| /auth/register | 3 requests | 1 hour |
| /auth/password/reset-request | 3 requests | 1 hour |
| API endpoints (with key) | 1000 requests | 1 hour |

### Account Lockout

- 5 failed login attempts trigger a 30-minute lockout
- Failed attempts reset after successful login
- Lockout duration increases with repeated lockouts

### Security Headers

All responses include:

```http
X-Content-Type-Options: nosniff
X-Frame-Options: DENY
X-XSS-Protection: 1; mode=block
Strict-Transport-Security: max-age=31536000; includeSubDomains
Content-Security-Policy: default-src 'self'
```

## Role-Based Access Control

### Available Roles

| Role | Description | Level |
|------|-------------|-------|
| user | Basic user | 1 |
| student | Academic student | 2 |
| researcher | Academic researcher | 3 |
| faculty | Faculty member | 4 |
| professor | Professor | 5 |
| department_admin | Department administrator | 6 |
| institutional_admin | Institution administrator | 7 |
| admin | System administrator | 9 |

### Permission Examples

```json
{
  "student": [
    "create:presentation",
    "read:presentation",
    "update:presentation",
    "delete:presentation"
  ],
  "faculty": [
    "...all student permissions",
    "read:department",
    "manage:collaboration"
  ],
  "admin": [
    "...all permissions",
    "admin:system",
    "manage:users"
  ]
}
```

## OAuth Integration

### Google OAuth Configuration

1. Supported scopes: `openid`, `email`, `profile`
2. Academic domains automatically detected via `hd` parameter
3. Email verification required

### Microsoft OAuth Configuration

1. Supports work and school accounts
2. Automatic institution detection for .edu domains
3. Azure AD integration for enterprise SSO

## API Key Authentication

### Using API Keys

```http
GET /api/v1/presentations
Authorization: Bearer sk_live_AbCdEfGhIjKlMnOpQrStUvWxYz
```

### API Key Best Practices

1. Store keys securely (environment variables)
2. Rotate keys regularly (every 90 days)
3. Use different keys for different environments
4. Monitor key usage via audit logs

## Code Examples

### Python

```python
import requests

# Register
response = requests.post(
    "https://api.slidegenie.io/api/v1/auth/register",
    json={
        "email": "student@mit.edu",
        "password": "SecureP@ssw0rd123!",
        "first_name": "John",
        "last_name": "Doe"
    }
)
data = response.json()
access_token = data["tokens"]["access_token"]

# Make authenticated request
headers = {"Authorization": f"Bearer {access_token}"}
response = requests.get(
    "https://api.slidegenie.io/api/v1/auth/me",
    headers=headers
)
user = response.json()
```

### JavaScript/TypeScript

```typescript
// Register
const response = await fetch('https://api.slidegenie.io/api/v1/auth/register', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    email: 'student@mit.edu',
    password: 'SecureP@ssw0rd123!',
    first_name: 'John',
    last_name: 'Doe'
  })
});

const data = await response.json();
const accessToken = data.tokens.access_token;

// Make authenticated request
const userResponse = await fetch('https://api.slidegenie.io/api/v1/auth/me', {
  headers: { 'Authorization': `Bearer ${accessToken}` }
});
const user = await userResponse.json();
```

### cURL

```bash
# Register
curl -X POST https://api.slidegenie.io/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{
    "email": "student@mit.edu",
    "password": "SecureP@ssw0rd123!",
    "first_name": "John",
    "last_name": "Doe"
  }'

# Login
curl -X POST https://api.slidegenie.io/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{
    "email": "student@mit.edu",
    "password": "SecureP@ssw0rd123!"
  }'

# Get current user
curl -X GET https://api.slidegenie.io/api/v1/auth/me \
  -H "Authorization: Bearer <access_token>"
```

## Testing Authentication

### Test Endpoints

For development/testing, use these endpoints:

```
Base URL: https://api-test.slidegenie.io
Rate limits: Relaxed for testing
```

### Test Credentials

```json
{
  "student": {
    "email": "test.student@demo.edu",
    "password": "TestP@ssw0rd123!"
  },
  "faculty": {
    "email": "test.faculty@demo.edu",
    "password": "TestP@ssw0rd123!"
  }
}
```

### Postman Collection

Download our [Postman collection](https://api.slidegenie.io/docs/postman/auth-collection.json) for easy testing.

## Troubleshooting

### Common Issues

1. **"Invalid email or password"**
   - Ensure email is lowercase
   - Check for trailing spaces
   - Verify password meets requirements

2. **"Email not verified"**
   - Check spam folder for verification email
   - Use resend endpoint if needed

3. **"Rate limit exceeded"**
   - Wait for the specified retry-after period
   - Consider using API keys for higher limits

4. **"Token expired"**
   - Use refresh token to get new access token
   - Implement automatic token refresh in client

### Support

- API Status: https://status.slidegenie.io
- Developer Forum: https://forum.slidegenie.io
- Email: api-support@slidegenie.io