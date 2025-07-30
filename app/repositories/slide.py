"""
Slide repository implementation.
"""
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import Slide, Presentation
from app.repositories.base import BaseRepository


class SlideRepository(BaseRepository[Slide]):
    """Repository for slide data access."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Slide, db)
    
    async def get_by_presentation(
        self,
        presentation_id: UUID,
        include_hidden: bool = False,
    ) -> List[Slide]:
        """
        Get all slides for a presentation.
        
        Args:
            presentation_id: Presentation ID
            include_hidden: Include hidden slides
            
        Returns:
            List of slides ordered by slide_number
        """
        conditions = [
            Slide.presentation_id == presentation_id,
            Slide.deleted_at.is_(None)
        ]
        
        if not include_hidden:
            conditions.append(Slide.is_hidden == False)
        
        stmt = (
            select(Slide)
            .where(and_(*conditions))
            .order_by(Slide.slide_number)
        )
        
        result = await self.db.execute(stmt)
        return list(result.scalars())
    
    async def get_slide(
        self,
        presentation_id: UUID,
        slide_number: int,
    ) -> Optional[Slide]:
        """
        Get a specific slide by presentation and number.
        
        Args:
            presentation_id: Presentation ID
            slide_number: Slide number
            
        Returns:
            Slide or None
        """
        stmt = (
            select(Slide)
            .where(
                and_(
                    Slide.presentation_id == presentation_id,
                    Slide.slide_number == slide_number,
                    Slide.deleted_at.is_(None)
                )
            )
        )
        
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def create_bulk(
        self,
        presentation_id: UUID,
        slides_data: List[Dict[str, Any]],
    ) -> List[Slide]:
        """
        Create multiple slides at once.
        
        Args:
            presentation_id: Presentation ID
            slides_data: List of slide data dictionaries
            
        Returns:
            List of created slides
        """
        slides = []
        for i, slide_data in enumerate(slides_data):
            slide_data['presentation_id'] = presentation_id
            if 'slide_number' not in slide_data:
                slide_data['slide_number'] = i + 1
            
            slide = Slide(**slide_data)
            self.db.add(slide)
            slides.append(slide)
        
        await self.db.flush()
        return slides
    
    async def reorder_slides(
        self,
        presentation_id: UUID,
        new_order: List[UUID],
    ) -> None:
        """
        Reorder slides within a presentation.
        
        Args:
            presentation_id: Presentation ID
            new_order: List of slide IDs in new order
        """
        for i, slide_id in enumerate(new_order):
            stmt = (
                update(Slide)
                .where(
                    and_(
                        Slide.id == slide_id,
                        Slide.presentation_id == presentation_id
                    )
                )
                .values(slide_number=i + 1)
            )
            await self.db.execute(stmt)
    
    async def duplicate_slide(
        self,
        slide_id: UUID,
        new_position: Optional[int] = None,
    ) -> Slide:
        """
        Duplicate a slide.
        
        Args:
            slide_id: Slide to duplicate
            new_position: Position for new slide (defaults to after original)
            
        Returns:
            New slide
        """
        # Get original slide
        original = await self.get(slide_id)
        if not original:
            raise ValueError(f"Slide {slide_id} not found")
        
        # Determine position
        if new_position is None:
            new_position = original.slide_number + 1
        
        # Shift subsequent slides
        await self._shift_slides(
            original.presentation_id,
            new_position,
            1
        )
        
        # Create duplicate
        new_slide_data = {
            'presentation_id': original.presentation_id,
            'slide_number': new_position,
            'content': original.content.copy() if original.content else {},
            'layout_type': original.layout_type,
            'title': f"{original.title} (Copy)" if original.title else None,
            'section': original.section,
            'speaker_notes': original.speaker_notes,
            'transitions': original.transitions.copy() if original.transitions else {},
            'animations': original.animations.copy() if original.animations else {},
            'duration_seconds': original.duration_seconds,
        }
        
        return await self.create(new_slide_data)
    
    async def delete_slide(
        self,
        slide_id: UUID,
        reorder: bool = True,
    ) -> bool:
        """
        Delete a slide and optionally reorder remaining slides.
        
        Args:
            slide_id: Slide ID
            reorder: Whether to reorder remaining slides
            
        Returns:
            Success status
        """
        slide = await self.get(slide_id)
        if not slide:
            return False
        
        # Soft delete
        success = await self.delete(slide_id)
        
        if success and reorder:
            # Shift subsequent slides
            await self._shift_slides(
                slide.presentation_id,
                slide.slide_number + 1,
                -1
            )
        
        return success
    
    async def search_slides(
        self,
        presentation_id: UUID,
        query: str,
        search_in: List[str] = ['title', 'content', 'speaker_notes'],
    ) -> List[Slide]:
        """
        Search slides within a presentation.
        
        Args:
            presentation_id: Presentation ID
            query: Search query
            search_in: Fields to search in
            
        Returns:
            List of matching slides
        """
        conditions = [
            Slide.presentation_id == presentation_id,
            Slide.deleted_at.is_(None)
        ]
        
        search_conditions = []
        query_lower = f"%{query.lower()}%"
        
        if 'title' in search_in:
            search_conditions.append(
                func.lower(Slide.title).like(query_lower)
            )
        
        if 'speaker_notes' in search_in:
            search_conditions.append(
                func.lower(Slide.speaker_notes).like(query_lower)
            )
        
        if 'content' in search_in:
            # Search in JSONB content
            search_conditions.append(
                func.jsonb_to_tsvector(
                    'english',
                    Slide.content,
                    '["string"]'
                ).match(func.plainto_tsquery('english', query))
            )
        
        if search_conditions:
            conditions.append(or_(*search_conditions))
        
        stmt = (
            select(Slide)
            .where(and_(*conditions))
            .order_by(Slide.slide_number)
        )
        
        result = await self.db.execute(stmt)
        return list(result.scalars())
    
    async def get_statistics(
        self,
        presentation_id: UUID,
    ) -> Dict[str, Any]:
        """
        Get statistics about slides in a presentation.
        
        Args:
            presentation_id: Presentation ID
            
        Returns:
            Dictionary with statistics
        """
        # Base condition
        base_condition = and_(
            Slide.presentation_id == presentation_id,
            Slide.deleted_at.is_(None),
            Slide.is_hidden == False
        )
        
        # Count queries
        stats_query = select(
            func.count(Slide.id).label('total_slides'),
            func.sum(Slide.word_count).label('total_words'),
            func.sum(Slide.figure_count).label('total_figures'),
            func.sum(Slide.duration_seconds).label('total_duration'),
            func.count(Slide.id).filter(Slide.contains_equations == True).label('slides_with_equations'),
            func.count(Slide.id).filter(Slide.contains_code == True).label('slides_with_code'),
            func.count(Slide.id).filter(Slide.contains_citations == True).label('slides_with_citations'),
        ).where(base_condition)
        
        result = await self.db.execute(stats_query)
        row = result.one()
        
        return {
            'total_slides': row.total_slides or 0,
            'total_words': row.total_words or 0,
            'total_figures': row.total_figures or 0,
            'total_duration_seconds': row.total_duration or 0,
            'estimated_duration_minutes': (row.total_duration or 0) / 60,
            'slides_with_equations': row.slides_with_equations or 0,
            'slides_with_code': row.slides_with_code or 0,
            'slides_with_citations': row.slides_with_citations or 0,
        }
    
    async def _shift_slides(
        self,
        presentation_id: UUID,
        from_position: int,
        shift_by: int,
    ) -> None:
        """
        Shift slide numbers within a presentation.
        
        Args:
            presentation_id: Presentation ID
            from_position: Starting position
            shift_by: Amount to shift (positive or negative)
        """
        if shift_by == 0:
            return
        
        stmt = (
            update(Slide)
            .where(
                and_(
                    Slide.presentation_id == presentation_id,
                    Slide.slide_number >= from_position,
                    Slide.deleted_at.is_(None)
                )
            )
            .values(slide_number=Slide.slide_number + shift_by)
        )
        
        await self.db.execute(stmt)
    
    async def update_slide_count(self, presentation_id: UUID) -> None:
        """
        Update the slide count in the presentation.
        
        Args:
            presentation_id: Presentation ID
        """
        count_query = (
            select(func.count(Slide.id))
            .where(
                and_(
                    Slide.presentation_id == presentation_id,
                    Slide.deleted_at.is_(None),
                    Slide.is_hidden == False
                )
            )
        )
        
        result = await self.db.execute(count_query)
        count = result.scalar() or 0
        
        update_stmt = (
            update(Presentation)
            .where(Presentation.id == presentation_id)
            .values(slide_count=count)
        )
        
        await self.db.execute(update_stmt)


# Import additional required modules
from sqlalchemy import update, or_