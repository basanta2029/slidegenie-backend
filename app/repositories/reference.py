"""
Reference repository for managing citations.
"""
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy import select, and_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import Reference
from app.repositories.base import BaseRepository


class ReferenceRepository(BaseRepository[Reference]):
    """Repository for reference/citation data access."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Reference, db)
    
    async def get_by_presentation(
        self,
        presentation_id: UUID,
    ) -> List[Reference]:
        """
        Get all references for a presentation.
        
        Args:
            presentation_id: Presentation ID
            
        Returns:
            List of references
        """
        stmt = (
            select(Reference)
            .where(
                and_(
                    Reference.presentation_id == presentation_id,
                    Reference.deleted_at.is_(None)
                )
            )
            .order_by(Reference.citation_key)
        )
        
        result = await self.db.execute(stmt)
        return list(result.scalars())
    
    async def get_by_citation_key(
        self,
        presentation_id: UUID,
        citation_key: str,
    ) -> Optional[Reference]:
        """
        Get reference by citation key.
        
        Args:
            presentation_id: Presentation ID
            citation_key: Citation key
            
        Returns:
            Reference or None
        """
        stmt = (
            select(Reference)
            .where(
                and_(
                    Reference.presentation_id == presentation_id,
                    Reference.citation_key == citation_key,
                    Reference.deleted_at.is_(None)
                )
            )
        )
        
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def create_or_update(
        self,
        presentation_id: UUID,
        citation_key: str,
        data: Dict[str, Any],
    ) -> Reference:
        """
        Create or update a reference.
        
        Args:
            presentation_id: Presentation ID
            citation_key: Citation key
            data: Reference data
            
        Returns:
            Created or updated reference
        """
        existing = await self.get_by_citation_key(presentation_id, citation_key)
        
        if existing:
            return await self.update(existing.id, data)
        else:
            data['presentation_id'] = presentation_id
            data['citation_key'] = citation_key
            return await self.create(data)
    
    async def bulk_import(
        self,
        presentation_id: UUID,
        references: List[Dict[str, Any]],
    ) -> List[Reference]:
        """
        Bulk import references.
        
        Args:
            presentation_id: Presentation ID
            references: List of reference data
            
        Returns:
            List of created/updated references
        """
        result = []
        
        for ref_data in references:
            citation_key = ref_data.get('citation_key')
            if not citation_key:
                continue
            
            ref = await self.create_or_update(
                presentation_id,
                citation_key,
                ref_data
            )
            result.append(ref)
        
        return result
    
    async def find_by_doi(
        self,
        doi: str,
        presentation_id: Optional[UUID] = None,
    ) -> List[Reference]:
        """
        Find references by DOI.
        
        Args:
            doi: DOI to search for
            presentation_id: Limit to specific presentation
            
        Returns:
            List of references
        """
        conditions = [
            Reference.doi == doi,
            Reference.deleted_at.is_(None)
        ]
        
        if presentation_id:
            conditions.append(Reference.presentation_id == presentation_id)
        
        stmt = select(Reference).where(and_(*conditions))
        result = await self.db.execute(stmt)
        return list(result.scalars())
    
    async def update_usage_count(
        self,
        reference_id: UUID,
        slide_numbers: List[int],
    ) -> None:
        """
        Update usage count and slide numbers for a reference.
        
        Args:
            reference_id: Reference ID
            slide_numbers: List of slide numbers using this reference
        """
        await self.update(
            reference_id,
            {
                'usage_count': len(slide_numbers),
                'slide_numbers': slide_numbers
            }
        )
    
    async def get_unused_references(
        self,
        presentation_id: UUID,
    ) -> List[Reference]:
        """
        Get references not used in any slides.
        
        Args:
            presentation_id: Presentation ID
            
        Returns:
            List of unused references
        """
        stmt = (
            select(Reference)
            .where(
                and_(
                    Reference.presentation_id == presentation_id,
                    Reference.usage_count == 0,
                    Reference.deleted_at.is_(None)
                )
            )
            .order_by(Reference.citation_key)
        )
        
        result = await self.db.execute(stmt)
        return list(result.scalars())