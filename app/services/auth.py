"""
Authentication service.
"""
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import decode_token, verify_password
from app.infrastructure.database.models import User
from app.repositories.user import UserRepository


class AuthService:
    """Authentication service."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
    
    async def authenticate(
        self,
        email: str,
        password: str,
    ) -> Optional[User]:
        """
        Authenticate user with email and password.
        
        Args:
            email: User email
            password: Plain text password
            
        Returns:
            User if authenticated, None otherwise
        """
        user = await self.user_repo.get_by_email(email)
        if not user:
            return None
        
        if not verify_password(password, user.password_hash):
            return None
        
        return user
    
    async def verify_refresh_token(
        self,
        token: str,
    ) -> Optional[User]:
        """
        Verify refresh token and return user.
        
        Args:
            token: Refresh token
            
        Returns:
            User if token is valid, None otherwise
        """
        payload = decode_token(token)
        if not payload:
            return None
        
        if payload.get("type") != "refresh":
            return None
        
        user_id = payload.get("sub")
        if not user_id:
            return None
        
        return await self.user_repo.get(user_id)