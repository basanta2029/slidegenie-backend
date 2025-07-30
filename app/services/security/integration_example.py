"""
Example integration of security features with SlideGenie application.

This file demonstrates how to integrate:
- Security middleware with FastAPI
- Rate limiting and account lockout with auth endpoints
- Audit logging throughout the application
"""

from fastapi import FastAPI, Request, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from app.core.config import settings
from app.services.security import (
    SecurityMiddleware,
    RateLimitMiddleware,
    audit_logger,
    lockout_service,
    rate_limiter,
    SecurityEvent,
)


def integrate_security_middleware(app: FastAPI) -> None:
    """
    Integrate security middleware into FastAPI application.
    
    Add this to main.py after CORS middleware:
    """
    # Add security headers middleware
    app.add_middleware(
        SecurityMiddleware,
        enable_hsts=settings.is_production,
        enable_csp=True,
        enable_csrf=True,
        trusted_origins=[settings.FRONTEND_URL],
        audit_logger=audit_logger,
    )
    
    # Add rate limiting middleware
    app.add_middleware(
        RateLimitMiddleware,
        default_limit=100,  # 100 requests per minute
        default_window=60,
    )


# Example: Enhanced login endpoint with security features
async def secure_login_example(
    credentials: dict,
    request: Request,
    db = None,  # Database dependency
):
    """
    Example of login endpoint with full security integration.
    
    This shows how to integrate:
    - Account lockout checking
    - Failed attempt tracking
    - Audit logging
    - Rate limiting (handled by middleware)
    """
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("User-Agent")
    
    # 1. Check if account is locked
    lockout_status = await lockout_service.check_lockout_status(
        identifier=credentials["email"]
    )
    
    if lockout_status.is_locked:
        # Log the blocked attempt
        await audit_logger.log_event(
            event=SecurityEvent.LOGIN_FAILURE,
            user_id=credentials["email"],
            ip_address=client_ip,
            user_agent=user_agent,
            details={
                "reason": "account_locked",
                "lockout_until": lockout_status.lockout_until.isoformat() if lockout_status.lockout_until else None,
            }
        )
        
        raise HTTPException(
            status_code=status.HTTP_423_LOCKED,
            detail=f"Account is locked. {lockout_status.remaining_attempts} attempts remaining.",
        )
    
    try:
        # 2. Attempt authentication (your existing auth logic)
        # user = await authenticate_user(credentials)
        user = None  # Placeholder
        
        if not user:
            # 3. Record failed attempt
            lockout_info = await lockout_service.record_failed_attempt(
                identifier=credentials["email"],
                ip_address=client_ip,
                user_agent=user_agent,
                additional_context={
                    "login_type": "password",
                    "timestamp": request.headers.get("X-Request-ID"),
                }
            )
            
            # 4. Log failed login
            await audit_logger.log_event(
                event=SecurityEvent.LOGIN_FAILURE,
                user_id=credentials["email"],
                ip_address=client_ip,
                user_agent=user_agent,
                details={
                    "reason": "invalid_credentials",
                    "failed_attempts": lockout_info.failed_attempts,
                    "remaining_attempts": lockout_info.remaining_attempts,
                }
            )
            
            # Check if account was just locked
            if lockout_info.is_locked:
                raise HTTPException(
                    status_code=status.HTTP_423_LOCKED,
                    detail=f"Too many failed attempts. Account locked until {lockout_info.lockout_until}",
                )
            
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid credentials. {lockout_info.remaining_attempts} attempts remaining.",
            )
        
        # 5. Successful login - clear failed attempts
        await lockout_service.clear_failed_attempts(credentials["email"])
        
        # 6. Log successful login
        await audit_logger.log_event(
            event=SecurityEvent.LOGIN_SUCCESS,
            user_id=user.id,
            ip_address=client_ip,
            user_agent=user_agent,
            session_id=generate_session_id(),  # Your session ID logic
            details={
                "login_type": "password",
                "email": user.email,
            }
        )
        
        # 7. Generate tokens and return response
        # tokens = generate_tokens(user)
        # return AuthResponse(user=user, tokens=tokens)
        
    except HTTPException:
        raise
    except Exception as e:
        # Log system error
        await audit_logger.log_event(
            event=SecurityEvent.SYSTEM_ERROR,
            ip_address=client_ip,
            details={
                "error": str(e),
                "endpoint": "login",
            }
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed",
        )


# Example: Password reset with rate limiting
async def secure_password_reset_example(
    email: str,
    request: Request,
):
    """
    Example of password reset with security features.
    """
    client_ip = request.client.host if request.client else "unknown"
    
    # Check rate limit for password reset
    rate_result = await rate_limiter.check_rate_limit(
        identifier=f"ip:{client_ip}",
        endpoint="auth:reset_password",
    )
    
    if not rate_result.allowed:
        await audit_logger.log_event(
            event=SecurityEvent.RATE_LIMIT_EXCEEDED,
            ip_address=client_ip,
            details={
                "endpoint": "password_reset",
                "retry_after": rate_result.retry_after,
            }
        )
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Too many password reset requests. Try again in {rate_result.retry_after} seconds.",
        )
    
    # Log password reset request
    await audit_logger.log_event(
        event=SecurityEvent.PASSWORD_RESET_REQUEST,
        user_id=email,
        ip_address=client_ip,
        details={"email": email}
    )
    
    # Continue with password reset logic...


# Example: OAuth login with security
async def secure_oauth_login_example(
    provider: str,
    oauth_data: dict,
    request: Request,
):
    """
    Example of OAuth login with security features.
    """
    client_ip = request.client.host if request.client else "unknown"
    user_agent = request.headers.get("User-Agent")
    
    # Log OAuth attempt
    await audit_logger.log_event(
        event=SecurityEvent.OAUTH_LOGIN_ATTEMPT,
        ip_address=client_ip,
        user_agent=user_agent,
        details={
            "provider": provider,
            "oauth_id": oauth_data.get("id"),
        }
    )
    
    try:
        # Your OAuth logic here
        # user = await process_oauth_login(provider, oauth_data)
        
        # Log success
        await audit_logger.log_event(
            event=SecurityEvent.OAUTH_LOGIN_SUCCESS,
            user_id=user.id,
            ip_address=client_ip,
            details={
                "provider": provider,
                "email": user.email,
            }
        )
        
    except Exception as e:
        # Log failure
        await audit_logger.log_event(
            event=SecurityEvent.OAUTH_LOGIN_FAILURE,
            ip_address=client_ip,
            details={
                "provider": provider,
                "error": str(e),
            }
        )
        raise


# Example: API key authentication with audit logging
security = HTTPBearer()

async def api_key_auth_example(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    request: Request = None,
):
    """
    Example of API key authentication with security features.
    """
    client_ip = request.client.host if request.client else "unknown"
    api_key = credentials.credentials
    
    # Validate API key (your logic)
    # api_key_data = await validate_api_key(api_key)
    
    if not api_key_data:
        await audit_logger.log_event(
            event=SecurityEvent.INVALID_API_KEY,
            ip_address=client_ip,
            details={"api_key_prefix": api_key[:8] + "..."}
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid API key",
        )
    
    # Log API key usage
    await audit_logger.log_event(
        event=SecurityEvent.API_KEY_USED,
        user_id=api_key_data.user_id,
        ip_address=client_ip,
        details={
            "api_key_id": api_key_data.id,
            "key_name": api_key_data.name,
        }
    )
    
    return api_key_data


# Example: Administrative action with audit logging
async def admin_action_example(
    action: str,
    target_user_id: str,
    admin_user_id: str,
    request: Request,
):
    """
    Example of administrative action with audit logging.
    """
    client_ip = request.client.host if request.client else "unknown"
    
    # Map actions to events
    event_map = {
        "suspend": SecurityEvent.USER_SUSPENDED,
        "activate": SecurityEvent.USER_ACTIVATED,
        "delete": SecurityEvent.USER_DELETED,
        "update": SecurityEvent.USER_UPDATED,
    }
    
    # Log the administrative action
    await audit_logger.log_event(
        event=event_map.get(action, SecurityEvent.USER_UPDATED),
        user_id=admin_user_id,
        ip_address=client_ip,
        details={
            "action": action,
            "target_user_id": target_user_id,
            "admin_user_id": admin_user_id,
        }
    )
    
    # Perform the action...


# Example: Monitoring and alerting
async def security_monitoring_example():
    """
    Example of using audit logs for security monitoring.
    """
    # Get security metrics for the last hour
    metrics = await audit_logger.get_security_metrics(hours=1)
    
    # Check for anomalies
    if metrics["failed_logins"] > 100:
        # Send alert about potential brute force attack
        pass
    
    if metrics["account_lockouts"] > 20:
        # Send alert about unusual lockout activity
        pass
    
    if len(metrics["critical_events"]) > 0:
        # Send immediate alert for critical events
        for event in metrics["critical_events"]:
            print(f"CRITICAL: {event['event']} at {event['timestamp']}")
    
    # Get specific user activity
    user_activity = await audit_logger.get_user_activity(
        user_id="user123",
        days=7,
    )
    
    if user_activity["suspicious_activity"]:
        # Flag user for review
        pass
    
    return metrics


# Example: Custom rate limiting for specific operations
async def custom_rate_limit_example(
    user_id: str,
    operation: str,
):
    """
    Example of custom rate limiting for specific operations.
    """
    # Check custom rate limit
    result = await rate_limiter.check_rate_limit(
        identifier=f"user:{user_id}:operation:{operation}",
        limit=10,  # 10 operations
        window=3600,  # per hour
    )
    
    if not result.allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail=f"Rate limit exceeded for {operation}",
            headers={
                "X-RateLimit-Limit": str(result.limit),
                "X-RateLimit-Remaining": str(result.remaining),
                "X-RateLimit-Reset": result.reset_time.isoformat(),
                "Retry-After": str(result.retry_after),
            }
        )
    
    # Proceed with operation...


def generate_session_id() -> str:
    """Generate a unique session ID."""
    import secrets
    return secrets.token_urlsafe(32)