# SlideGenie Authentication System

## Overview

SlideGenie's authentication system provides secure user registration and login with special features for academic users. The system validates academic email addresses, provides email verification, and supports password reset functionality.

## Key Features

- **Academic Email Validation**: Automatic detection and validation of academic institution emails
- **JWT Token Authentication**: Secure token-based authentication with refresh tokens
- **Email Verification**: Required for academic email addresses
- **Password Reset**: Secure password reset flow with email confirmation
- **Token Blacklisting**: Secure logout with token revocation
- **Session Management**: Track active user sessions

## Authentication Flow

### 1. Registration

```http
POST /api/v1/auth/register
Content-Type: application/json

{
  "email": "john.doe@harvard.edu",
  "password": "SecurePassword123!",
  "first_name": "John",
  "last_name": "Doe",
  "institution": "Harvard University",  // Optional, auto-detected for academic emails
  "role": "researcher"  // Options: researcher, student, professor, admin
}
```

**Response:**
```json
{
  "user": {
    "id": "uuid",
    "email": "john.doe@harvard.edu",
    "first_name": "John",
    "last_name": "Doe",
    "institution": "Harvard University",
    "role": "researcher",
    "is_active": true,
    "is_verified": false,
    "created_at": "2024-01-01T00:00:00Z",
    "last_login": null
  },
  "tokens": {
    "access_token": "eyJ...",
    "refresh_token": "eyJ...",
    "token_type": "bearer",
    "expires_in": 3600,
    "refresh_expires_in": 604800
  },
  "session": {
    "session_id": "xxx",
    "user_id": "uuid",
    "created_at": "2024-01-01T00:00:00Z",
    "last_activity": "2024-01-01T00:00:00Z",
    "ip_address": "192.168.1.1",
    "user_agent": "Mozilla/5.0..."
  }
}
```

### 2. Login

```http
POST /api/v1/auth/login
Content-Type: application/json

{
  "email": "john.doe@harvard.edu",
  "password": "SecurePassword123!",
  "remember_me": false
}
```

**Note:** Academic email addresses must be verified before login.

### 3. Email Verification

After registration, users with academic emails receive a verification email:

```http
POST /api/v1/auth/verify-email
Content-Type: application/json

{
  "token": "verification_token_from_email"
}
```

### 4. Token Refresh

```http
POST /api/v1/auth/refresh
Content-Type: application/json

{
  "refresh_token": "eyJ..."
}
```

### 5. Logout

```http
POST /api/v1/auth/logout
Authorization: Bearer <access_token>
Content-Type: application/json

{
  "refresh_token": "eyJ..."  // Optional
}
```

## Academic Email Validation

### Check Email Domain

```http
GET /api/v1/academic/validate-domain?domain=harvard.edu
```

**Response:**
```json
{
  "domain": "harvard.edu",
  "is_academic": true,
  "institution": "Harvard University",
  "requires_verification": true
}
```

### Domain Autocomplete

```http
GET /api/v1/academic/suggest-domains?query=harv
```

**Response:**
```json
[
  "harvard.edu",
  "harvey.edu",
  "haverford.edu"
]
```

## Password Requirements

Passwords must meet the following criteria:
- Minimum 12 characters
- At least one uppercase letter
- At least one lowercase letter
- At least one number
- At least one special character (!@#$%^&*()_+-=[]{}|;:,.<>?)

## Password Reset

### 1. Request Reset

```http
POST /api/v1/auth/forgot-password
Content-Type: application/json

{
  "email": "john.doe@harvard.edu"
}
```

### 2. Reset Password

```http
POST /api/v1/auth/reset-password
Content-Type: application/json

{
  "token": "reset_token_from_email",
  "new_password": "NewSecurePassword123!"
}
```

## Security Features

### Token Security
- Access tokens expire in 1 hour
- Refresh tokens expire in 7 days
- Tokens are blacklisted on logout
- All tokens are invalidated on password reset

### Academic Institution Verification
- Academic emails (.edu, .ac.uk, etc.) are automatically detected
- Institution names are extracted from email domains
- Academic users must verify their email before accessing full features

### Rate Limiting
- Login attempts are rate-limited to prevent brute force attacks
- Password reset requests are limited per email
- Email verification resends are limited

## Error Handling

### Common Error Responses

**409 Conflict - Email Already Registered**
```json
{
  "detail": "Email already registered"
}
```

**401 Unauthorized - Invalid Credentials**
```json
{
  "detail": "Invalid email or password"
}
```

**403 Forbidden - Email Not Verified**
```json
{
  "detail": "Please verify your academic email address before logging in"
}
```

**400 Bad Request - Weak Password**
```json
{
  "detail": "Password must contain at least one uppercase letter"
}
```

## Token Structure

### Access Token Payload
```json
{
  "sub": "user_id",
  "email": "john.doe@harvard.edu",
  "roles": ["researcher"],
  "institution": "Harvard University",
  "type": "access",
  "session_id": "xxx",
  "iat": 1234567890,
  "exp": 1234571490,
  "jti": "unique_token_id"
}
```

## Implementation Details

### Services Used
- **TokenService**: JWT token generation and validation
- **AuthService**: User authentication and registration
- **EmailValidationService**: Academic email validation and notifications
- **AcademicEmailValidator**: Domain validation and institution detection
- **PasswordResetService**: Password reset functionality

### Database Models
- **User**: Stores user information including verification status
- **Session**: Tracks active user sessions (in Redis)
- **TokenBlacklist**: Stores revoked tokens (in Redis)

### Email Templates
- Verification email with institution branding
- Password reset email with secure link
- Welcome email for new users

## Best Practices

1. **Always use HTTPS** in production for all authentication endpoints
2. **Store tokens securely** in httpOnly cookies or secure storage
3. **Implement CSRF protection** for session-based authentication
4. **Monitor failed login attempts** and implement account lockout
5. **Use strong password policies** and consider 2FA for sensitive accounts
6. **Regularly rotate JWT secrets** and implement key rotation
7. **Log authentication events** for security auditing