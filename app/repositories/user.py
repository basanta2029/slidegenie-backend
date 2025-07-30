"""
User repository.
"""
from typing import Any, Dict, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import User
from app.repositories.base import BaseRepository


class UserRepository(BaseRepository[User]):
    """User repository."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(User, db)
    
    async def get_by_email(
        self,
        email: str,
    ) -> Optional[User]:
        """
        Get user by email.
        
        Args:
            email: User email
            
        Returns:
            User if found
        """
        stmt = select(User).where(User.email == email)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_verification_token(
        self,
        token: str,
    ) -> Optional[User]:
        """
        Get user by verification token.
        
        Args:
            token: Verification token
            
        Returns:
            User if found
        """
        stmt = select(User).where(User.verification_token == token)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()