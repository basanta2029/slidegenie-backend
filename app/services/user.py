"""
User service.
"""
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from sqlalchemy import select

import structlog

from app.core.security import get_password_hash
from app.domain.schemas.user import UserCreate, UserUpdate
from app.infrastructure.database.models import User, OAuthAccount
from app.repositories.user import UserRepository

logger = structlog.get_logger(__name__)


class UserService:
    """User service."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)
    
    async def create(
        self,
        user_create: UserCreate,
    ) -> User:
        """
        Create a new user.
        
        Args:
            user_create: User creation data
            
        Returns:
            Created user
        """
        # Hash password
        password_hash = get_password_hash(user_create.password)
        
        # Create user
        user_data = user_create.model_dump(exclude={"password"})
        user_data["password_hash"] = password_hash
        
        return await self.user_repo.create(user_data)
    
    async def get(
        self,
        user_id: UUID,
    ) -> Optional[User]:
        """
        Get user by ID.
        
        Args:
            user_id: User ID
            
        Returns:
            User if found
        """
        return await self.user_repo.get(user_id)
    
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
        return await self.user_repo.get_by_email(email)
    
    async def update(
        self,
        user_id: UUID,
        user_update: UserUpdate,
    ) -> Optional[User]:
        """
        Update user.
        
        Args:
            user_id: User ID
            user_update: Update data
            
        Returns:
            Updated user if found
        """
        update_data = user_update.model_dump(exclude_unset=True)
        return await self.user_repo.update(user_id, update_data)
    
    async def create_oauth_user(
        self,
        email: str,
        name: str,
        provider: str,
        provider_id: str,
        institution: Optional[str] = None,
        picture: Optional[str] = None,
    ) -> User:
        """
        Create a new user from OAuth provider.
        
        Args:
            email: User email
            name: User name
            provider: OAuth provider name
            provider_id: Provider-specific user ID
            institution: User's institution
            picture: Profile picture URL
            
        Returns:
            Created user
        """
        # Create user without password
        user_data = {
            "email": email,
            "full_name": name,
            "is_active": True,
            "is_verified": True,  # OAuth users are pre-verified
            "role": "user",
            "preferences": {
                "theme": "light",
                "notifications": {
                    "email": True,
                    "presentation_ready": True,
                    "weekly_summary": False,
                },
            },
        }
        
        user = await self.user_repo.create(user_data)
        
        # Create OAuth account link
        oauth_account = OAuthAccount(
            user_id=user.id,
            provider=provider,
            provider_account_id=provider_id,
            email=email,
            institution=institution,
            picture_url=picture,
        )
        
        self.db.add(oauth_account)
        await self.db.commit()
        
        logger.info(
            "oauth_user_created",
            user_id=str(user.id),
            email=email,
            provider=provider,
            institution=institution,
        )
        
        return user
    
    async def link_oauth_account(
        self,
        user_id: UUID,
        provider: str,
        provider_id: str,
        email: str,
        institution: Optional[str] = None,
        picture: Optional[str] = None,
    ) -> bool:
        """
        Link OAuth account to existing user.
        
        Args:
            user_id: User ID
            provider: OAuth provider name
            provider_id: Provider-specific user ID
            email: OAuth account email
            institution: Institution from OAuth
            picture: Profile picture URL
            
        Returns:
            Success status
        """
        try:
            # Check if already linked
            existing = await self.db.execute(
                select(OAuthAccount).where(
                    OAuthAccount.user_id == user_id,
                    OAuthAccount.provider == provider,
                )
            )
            if existing.scalar_one_or_none():
                logger.warning(
                    "oauth_account_already_linked",
                    user_id=str(user_id),
                    provider=provider,
                )
                return False
            
            # Create OAuth account link
            oauth_account = OAuthAccount(
                user_id=user_id,
                provider=provider,
                provider_account_id=provider_id,
                email=email,
                institution=institution,
                picture_url=picture,
            )
            
            self.db.add(oauth_account)
            await self.db.commit()
            
            logger.info(
                "oauth_account_linked",
                user_id=str(user_id),
                provider=provider,
                email=email,
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "oauth_account_link_error",
                user_id=str(user_id),
                provider=provider,
                error=str(e),
            )
            await self.db.rollback()
            return False
    
    async def unlink_oauth_account(
        self,
        user_id: UUID,
        provider: str,
    ) -> bool:
        """
        Unlink OAuth account from user.
        
        Args:
            user_id: User ID
            provider: OAuth provider name
            
        Returns:
            Success status
        """
        try:
            result = await self.db.execute(
                select(OAuthAccount).where(
                    OAuthAccount.user_id == user_id,
                    OAuthAccount.provider == provider,
                )
            )
            oauth_account = result.scalar_one_or_none()
            
            if not oauth_account:
                return False
            
            await self.db.delete(oauth_account)
            await self.db.commit()
            
            logger.info(
                "oauth_account_unlinked",
                user_id=str(user_id),
                provider=provider,
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "oauth_account_unlink_error",
                user_id=str(user_id),
                provider=provider,
                error=str(e),
            )
            await self.db.rollback()
            return False
    
    async def get_linked_oauth_providers(
        self,
        user_id: UUID,
    ) -> List[Dict[str, Any]]:
        """
        Get user's linked OAuth providers.
        
        Args:
            user_id: User ID
            
        Returns:
            List of linked OAuth accounts
        """
        try:
            result = await self.db.execute(
                select(OAuthAccount).where(OAuthAccount.user_id == user_id)
            )
            oauth_accounts = result.scalars().all()
            
            return [
                {
                    "provider": account.provider,
                    "email": account.email,
                    "linked_at": account.created_at.isoformat(),
                    "institution": account.institution,
                }
                for account in oauth_accounts
            ]
            
        except Exception as e:
            logger.error(
                "get_linked_providers_error",
                user_id=str(user_id),
                error=str(e),
            )
            return []
    
    async def update_oauth_tokens(
        self,
        user_id: UUID,
        provider: str,
        access_token: str,
        refresh_token: Optional[str] = None,
        expires_in: Optional[int] = None,
    ) -> bool:
        """
        Update OAuth tokens for user.
        
        Args:
            user_id: User ID
            provider: OAuth provider name
            access_token: New access token
            refresh_token: New refresh token
            expires_in: Token expiration in seconds
            
        Returns:
            Success status
        """
        try:
            result = await self.db.execute(
                select(OAuthAccount).where(
                    OAuthAccount.user_id == user_id,
                    OAuthAccount.provider == provider,
                )
            )
            oauth_account = result.scalar_one_or_none()
            
            if not oauth_account:
                return False
            
            # Update tokens
            oauth_account.access_token = access_token
            if refresh_token:
                oauth_account.refresh_token = refresh_token
            oauth_account.token_expires_at = (
                datetime.now(timezone.utc).timestamp() + expires_in
                if expires_in
                else None
            )
            oauth_account.updated_at = datetime.now(timezone.utc)
            
            await self.db.commit()
            
            logger.info(
                "oauth_tokens_updated",
                user_id=str(user_id),
                provider=provider,
                has_refresh_token=bool(refresh_token),
            )
            
            return True
            
        except Exception as e:
            logger.error(
                "oauth_tokens_update_error",
                user_id=str(user_id),
                provider=provider,
                error=str(e),
            )
            await self.db.rollback()
            return False