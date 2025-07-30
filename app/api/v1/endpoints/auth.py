"""
Authentication endpoints with academic email validation.
"""
from typing import Any, Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status, Header
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.dependencies import get_current_user
from app.core.exceptions import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
    EmailNotVerifiedError,
    InvalidTokenError,
    UserNotFoundError,
)
from app.domain.schemas.auth import (
    AuthResponse,
    EmailVerification,
    PasswordReset,
    PasswordResetConfirm,
    TokenPair,
    TokenRefresh,
    UserLogin,
    UserRegistration,
)
from app.infrastructure.database.base import get_db
from app.infrastructure.database.models import User as UserModel
from app.services.auth.auth_service import AuthService
from app.services.auth.password_service import PasswordResetService

router = APIRouter()


@router.post("/register", response_model=AuthResponse)
async def register(
    user_data: UserRegistration,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Register a new user with academic email validation.
    
    - Validates email format and domain
    - Checks for academic institution (.edu domains)
    - Sends verification email
    - Returns user profile and authentication tokens
    """
    auth_service = AuthService(db)
    
    try:
        # Get client info
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("User-Agent")
        
        # Register user
        auth_response = await auth_service.register(
            user_data=user_data,
            request_ip=client_ip,
            user_agent=user_agent,
        )
        
        return auth_response
        
    except UserAlreadyExistsError:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Email already registered",
        )
    except InvalidCredentialsError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Registration failed",
        )


@router.post("/login", response_model=AuthResponse)
async def login(
    credentials: UserLogin,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Login with email and password.
    
    - Validates credentials
    - Checks email verification for academic emails
    - Returns authentication tokens and user profile
    """
    auth_service = AuthService(db)
    
    try:
        # Get client info
        client_ip = request.client.host if request.client else None
        user_agent = request.headers.get("User-Agent")
        
        # Authenticate user
        auth_response = await auth_service.login(
            credentials=credentials,
            request_ip=client_ip,
            user_agent=user_agent,
        )
        
        return auth_response
        
    except InvalidCredentialsError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except EmailNotVerifiedError as e:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Login failed",
        )


@router.post("/refresh", response_model=TokenPair)
async def refresh_tokens(
    token_data: TokenRefresh,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Refresh access token using refresh token.
    
    - Validates refresh token
    - Returns new token pair
    - Old refresh token is blacklisted
    """
    auth_service = AuthService(db)
    
    try:
        # Get client info
        client_ip = request.client.host if request.client else None
        
        # Refresh tokens
        new_tokens = await auth_service.refresh_tokens(
            refresh_token=token_data.refresh_token,
            request_ip=client_ip,
        )
        
        return new_tokens
        
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid refresh token",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Token refresh failed",
        )


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(
    authorization: str = Header(...),
    refresh_token: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
) -> None:
    """
    Logout user and blacklist tokens.
    
    - Blacklists access token (from Authorization header)
    - Optionally blacklists refresh token
    - Returns 204 No Content on success
    """
    auth_service = AuthService(db)
    
    try:
        # Extract token from header
        if not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid authorization header",
            )
        
        access_token = authorization[7:]  # Remove "Bearer " prefix
        
        # Logout user
        await auth_service.logout(
            access_token=access_token,
            refresh_token=refresh_token,
        )
        
    except Exception as e:
        # Log error but don't expose details
        # Logout should appear successful even on error
        pass


@router.post("/verify-email", response_model=dict)
async def verify_email(
    verification_data: EmailVerification,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Verify user's email address.
    
    - Validates verification token
    - Marks email as verified
    - Enables full account access
    """
    auth_service = AuthService(db)
    
    try:
        # Verify email
        success = await auth_service.verify_email(
            verification_token=verification_data.token,
        )
        
        if success:
            return {"message": "Email verified successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Email verification failed",
            )
            
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired verification token",
        )
    except UserNotFoundError:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Email verification failed",
        )


@router.post("/resend-verification", response_model=dict)
async def resend_verification_email(
    email: str,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Resend email verification link.
    
    - Generates new verification token if needed
    - Sends verification email
    - Rate limited to prevent abuse
    """
    auth_service = AuthService(db)
    
    try:
        # Resend verification email
        success = await auth_service.resend_verification_email(email=email)
        
        if success:
            return {"message": "Verification email sent"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to send verification email",
            )
            
    except UserNotFoundError:
        # Don't reveal if email exists
        return {"message": "If the email exists, a verification link has been sent"}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to send verification email",
        )


@router.post("/forgot-password", response_model=dict)
async def forgot_password(
    reset_request: PasswordReset,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Request password reset.
    
    - Validates email exists
    - Generates reset token
    - Sends password reset email
    """
    password_service = PasswordResetService(db)
    
    try:
        # Request password reset
        success = await password_service.request_password_reset(
            email=reset_request.email,
        )
        
        # Always return success to prevent email enumeration
        return {"message": "If the email exists, a password reset link has been sent"}
        
    except Exception as e:
        # Don't expose errors
        return {"message": "If the email exists, a password reset link has been sent"}


@router.post("/reset-password", response_model=dict)
async def reset_password(
    reset_data: PasswordResetConfirm,
    db: AsyncSession = Depends(get_db),
) -> Any:
    """
    Reset password with token.
    
    - Validates reset token
    - Updates user password
    - Invalidates all existing tokens
    """
    password_service = PasswordResetService(db)
    
    try:
        # Reset password
        success = await password_service.reset_password(
            token=reset_data.token,
            new_password=reset_data.new_password,
        )
        
        if success:
            return {"message": "Password reset successfully"}
        else:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Password reset failed",
            )
            
    except InvalidTokenError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid or expired reset token",
        )
    except InvalidCredentialsError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Password reset failed",
        )


@router.get("/me", response_model=dict)
async def get_current_user(
    current_user: UserModel = Depends(get_current_user),
) -> Any:
    """
    Get current authenticated user.
    
    Returns user profile information.
    """
    return {
        "id": str(current_user.id),
        "email": current_user.email,
        "full_name": current_user.full_name,
        "institution": current_user.institution,
        "role": current_user.role,
        "is_active": current_user.is_active,
        "is_verified": current_user.is_verified,
        "created_at": current_user.created_at.isoformat(),
        "last_login": current_user.last_login.isoformat() if current_user.last_login else None,
    }