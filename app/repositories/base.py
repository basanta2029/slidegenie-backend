"""
Base repository implementation.
"""
from typing import Any, Dict, Generic, List, Optional, Type, TypeVar
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.base import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Base repository with common CRUD operations."""
    
    def __init__(
        self,
        model: Type[ModelType],
        db: AsyncSession,
    ):
        self.model = model
        self.db = db
    
    async def create(
        self,
        data: Dict[str, Any],
    ) -> ModelType:
        """
        Create a new record.
        
        Args:
            data: Record data
            
        Returns:
            Created record
        """
        db_obj = self.model(**data)
        self.db.add(db_obj)
        await self.db.commit()
        await self.db.refresh(db_obj)
        return db_obj
    
    async def get(
        self,
        id: UUID,
    ) -> Optional[ModelType]:
        """
        Get record by ID.
        
        Args:
            id: Record ID
            
        Returns:
            Record if found
        """
        stmt = select(self.model).where(self.model.id == id)
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_multi(
        self,
        *,
        skip: int = 0,
        limit: int = 100,
    ) -> List[ModelType]:
        """
        Get multiple records.
        
        Args:
            skip: Number of records to skip
            limit: Maximum number of records to return
            
        Returns:
            List of records
        """
        stmt = select(self.model).offset(skip).limit(limit)
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def update(
        self,
        id: UUID,
        data: Dict[str, Any],
    ) -> Optional[ModelType]:
        """
        Update a record.
        
        Args:
            id: Record ID
            data: Update data
            
        Returns:
            Updated record if found
        """
        db_obj = await self.get(id)
        if not db_obj:
            return None
        
        for field, value in data.items():
            setattr(db_obj, field, value)
        
        await self.db.commit()
        await self.db.refresh(db_obj)
        return db_obj
    
    async def delete(
        self,
        id: UUID,
    ) -> bool:
        """
        Delete a record.
        
        Args:
            id: Record ID
            
        Returns:
            True if deleted, False if not found
        """
        db_obj = await self.get(id)
        if not db_obj:
            return False
        
        await self.db.delete(db_obj)
        await self.db.commit()
        return True