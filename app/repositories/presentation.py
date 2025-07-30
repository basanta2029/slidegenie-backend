"""
Presentation repository with advanced search capabilities.
"""
from typing import Any, Dict, List, Optional
from uuid import UUID

from sqlalchemy import and_, or_, select, func
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload

from app.infrastructure.database.models import (
    Presentation, 
    Slide, 
    Reference,
    User,
    Template,
    Tag,
    presentation_tags,
    presentation_authors
)
from app.repositories.base import BaseRepository


class PresentationRepository(BaseRepository[Presentation]):
    """Repository for presentation data access with search capabilities."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Presentation, db)
    
    async def get_with_slides(self, presentation_id: UUID) -> Optional[Presentation]:
        """
        Get presentation with all slides loaded.
        
        Args:
            presentation_id: Presentation ID
            
        Returns:
            Presentation with slides or None
        """
        stmt = (
            select(Presentation)
            .where(Presentation.id == presentation_id)
            .where(Presentation.deleted_at.is_(None))
            .options(selectinload(Presentation.slides))
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_full_presentation(self, presentation_id: UUID) -> Optional[Presentation]:
        """
        Get presentation with all related data loaded.
        
        Args:
            presentation_id: Presentation ID
            
        Returns:
            Presentation with all relationships loaded
        """
        stmt = (
            select(Presentation)
            .where(Presentation.id == presentation_id)
            .where(Presentation.deleted_at.is_(None))
            .options(
                selectinload(Presentation.slides),
                selectinload(Presentation.references),
                selectinload(Presentation.authors),
                joinedload(Presentation.owner),
                joinedload(Presentation.template),
                selectinload(Presentation.tags),
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def search(
        self,
        query: str,
        user_id: Optional[UUID] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[List[Presentation], int]:
        """
        Search presentations with full-text search.
        
        Args:
            query: Search query
            user_id: Filter by user ID
            filters: Additional filters
            limit: Maximum results
            offset: Results offset
            
        Returns:
            Tuple of (presentations, total_count)
        """
        filters = filters or {}
        
        # Base query
        base_stmt = select(Presentation).where(Presentation.deleted_at.is_(None))
        
        # Add search condition
        if query:
            search_condition = func.to_tsquery('english', query)
            base_stmt = base_stmt.where(
                Presentation.search_vector.match(search_condition)
            )
        
        # Add user filter
        if user_id:
            base_stmt = base_stmt.where(
                or_(
                    Presentation.owner_id == user_id,
                    Presentation.authors.any(User.id == user_id)
                )
            )
        
        # Add other filters
        if filters.get('presentation_type'):
            base_stmt = base_stmt.where(
                Presentation.presentation_type == filters['presentation_type']
            )
        
        if filters.get('field_of_study'):
            base_stmt = base_stmt.where(
                Presentation.field_of_study == filters['field_of_study']
            )
        
        if filters.get('conference_name'):
            base_stmt = base_stmt.where(
                Presentation.conference_name.ilike(f"%{filters['conference_name']}%")
            )
        
        if filters.get('status'):
            base_stmt = base_stmt.where(
                Presentation.status == filters['status']
            )
        
        if filters.get('is_public') is not None:
            base_stmt = base_stmt.where(
                Presentation.is_public == filters['is_public']
            )
        
        if filters.get('tags'):
            # Filter by tags
            tag_names = filters['tags']
            base_stmt = base_stmt.join(presentation_tags).join(Tag).where(
                Tag.name.in_(tag_names)
            )
        
        # Count total results
        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total_result = await self.db.execute(count_stmt)
        total_count = total_result.scalar() or 0
        
        # Get paginated results with relevance ranking
        if query:
            ranked_stmt = (
                base_stmt
                .order_by(
                    func.ts_rank(Presentation.search_vector, search_condition).desc(),
                    Presentation.updated_at.desc()
                )
                .limit(limit)
                .offset(offset)
                .options(
                    selectinload(Presentation.tags),
                    joinedload(Presentation.owner),
                    joinedload(Presentation.template)
                )
            )
        else:
            ranked_stmt = (
                base_stmt
                .order_by(Presentation.updated_at.desc())
                .limit(limit)
                .offset(offset)
                .options(
                    selectinload(Presentation.tags),
                    joinedload(Presentation.owner),
                    joinedload(Presentation.template)
                )
            )
        
        result = await self.db.execute(ranked_stmt)
        presentations = list(result.scalars().unique())
        
        return presentations, total_count
    
    async def find_similar(
        self,
        presentation_id: UUID,
        limit: int = 10,
    ) -> List[Presentation]:
        """
        Find similar presentations using vector similarity.
        
        Args:
            presentation_id: Reference presentation ID
            limit: Maximum results
            
        Returns:
            List of similar presentations
        """
        # Get embedding for reference presentation
        embedding_query = text("""
            SELECT embedding
            FROM presentationembedding
            WHERE presentation_id = :presentation_id
            AND embedding_type = 'combined'
            ORDER BY generated_at DESC
            LIMIT 1
        """)
        
        result = await self.db.execute(
            embedding_query,
            {"presentation_id": presentation_id}
        )
        embedding = result.scalar()
        
        if not embedding:
            return []
        
        # Find similar presentations
        similarity_query = text("""
            SELECT DISTINCT p.*
            FROM presentation p
            INNER JOIN presentationembedding pe ON p.id = pe.presentation_id
            WHERE p.id != :presentation_id
            AND p.deleted_at IS NULL
            AND pe.embedding_type = 'combined'
            ORDER BY pe.embedding <-> :embedding
            LIMIT :limit
        """)
        
        result = await self.db.execute(
            similarity_query,
            {
                "presentation_id": presentation_id,
                "embedding": embedding,
                "limit": limit
            }
        )
        
        return list(result.scalars())
    
    async def get_user_presentations(
        self,
        user_id: UUID,
        include_collaborations: bool = True,
        status: Optional[str] = None,
        limit: int = 50,
        offset: int = 0,
    ) -> tuple[List[Presentation], int]:
        """
        Get presentations for a specific user.
        
        Args:
            user_id: User ID
            include_collaborations: Include presentations where user is author
            status: Filter by status
            limit: Maximum results
            offset: Results offset
            
        Returns:
            Tuple of (presentations, total_count)
        """
        # Base query
        conditions = [
            Presentation.owner_id == user_id,
            Presentation.deleted_at.is_(None)
        ]
        
        if include_collaborations:
            conditions[0] = or_(
                Presentation.owner_id == user_id,
                Presentation.authors.any(User.id == user_id)
            )
        
        if status:
            conditions.append(Presentation.status == status)
        
        base_stmt = select(Presentation).where(and_(*conditions))
        
        # Count total
        count_stmt = select(func.count()).select_from(base_stmt.subquery())
        total_result = await self.db.execute(count_stmt)
        total_count = total_result.scalar() or 0
        
        # Get results
        stmt = (
            base_stmt
            .order_by(Presentation.updated_at.desc())
            .limit(limit)
            .offset(offset)
            .options(
                selectinload(Presentation.tags),
                joinedload(Presentation.template)
            )
        )
        
        result = await self.db.execute(stmt)
        presentations = list(result.scalars().unique())
        
        return presentations, total_count
    
    async def increment_view_count(self, presentation_id: UUID) -> None:
        """
        Increment view count for a presentation.
        
        Args:
            presentation_id: Presentation ID
        """
        stmt = (
            update(Presentation)
            .where(Presentation.id == presentation_id)
            .values(
                view_count=Presentation.view_count + 1,
                last_accessed=func.now()
            )
        )
        await self.db.execute(stmt)
    
    async def get_by_share_token(self, share_token: str) -> Optional[Presentation]:
        """
        Get presentation by share token.
        
        Args:
            share_token: Share token
            
        Returns:
            Presentation or None
        """
        stmt = (
            select(Presentation)
            .where(Presentation.share_token == share_token)
            .where(Presentation.deleted_at.is_(None))
            .options(
                selectinload(Presentation.slides),
                joinedload(Presentation.owner),
                joinedload(Presentation.template)
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def create_version(
        self,
        presentation_id: UUID,
        changed_by_id: UUID,
        change_summary: str,
    ) -> None:
        """
        Create a version snapshot of the presentation.
        
        Args:
            presentation_id: Presentation ID
            changed_by_id: User who made changes
            change_summary: Summary of changes
        """
        # Get current presentation with slides
        presentation = await self.get_with_slides(presentation_id)
        if not presentation:
            return
        
        # Get current version number
        version_query = text("""
            SELECT COALESCE(MAX(version_number), 0) + 1
            FROM presentationversion
            WHERE presentation_id = :presentation_id
        """)
        result = await self.db.execute(
            version_query,
            {"presentation_id": presentation_id}
        )
        version_number = result.scalar()
        
        # Create snapshot
        snapshot = {
            "slides": [
                {
                    "slide_number": slide.slide_number,
                    "content": slide.content,
                    "layout_type": slide.layout_type,
                    "title": slide.title,
                }
                for slide in sorted(presentation.slides, key=lambda s: s.slide_number)
            ],
            "metadata": {
                "slide_count": presentation.slide_count,
                "template_id": str(presentation.template_id) if presentation.template_id else None,
                "theme_config": presentation.theme_config,
            }
        }
        
        # Insert version record
        insert_query = text("""
            INSERT INTO presentationversion 
            (id, presentation_id, version_number, title, content_snapshot, change_summary, changed_by_id)
            VALUES 
            (:id, :presentation_id, :version_number, :title, :content_snapshot, :change_summary, :changed_by_id)
        """)
        
        await self.db.execute(
            insert_query,
            {
                "id": str(uuid.uuid4()),
                "presentation_id": presentation_id,
                "version_number": version_number,
                "title": presentation.title,
                "content_snapshot": json.dumps(snapshot),
                "change_summary": change_summary,
                "changed_by_id": changed_by_id,
            }
        )
        
        # Update presentation version number
        await self.update(
            presentation_id,
            {"version": version_number}
        )


# Import additional required modules
from sqlalchemy import update, text
import json
import uuid