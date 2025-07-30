"""
Template repository implementation.
"""
from typing import List, Optional, Dict, Any
from uuid import UUID

from sqlalchemy import select, and_, or_, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.database.models import Template, Institution
from app.repositories.base import BaseRepository


class TemplateRepository(BaseRepository[Template]):
    """Repository for template data access."""
    
    def __init__(self, db: AsyncSession):
        super().__init__(Template, db)
    
    async def get_active_templates(
        self,
        category: Optional[str] = None,
        academic_field: Optional[str] = None,
        conference_series: Optional[str] = None,
        include_premium: bool = True,
    ) -> List[Template]:
        """
        Get active templates with filters.
        
        Args:
            category: Template category
            academic_field: Academic field
            conference_series: Conference series
            include_premium: Include premium templates
            
        Returns:
            List of templates
        """
        conditions = [
            Template.is_active == True,
            Template.deleted_at.is_(None)
        ]
        
        if not include_premium:
            conditions.append(Template.is_premium == False)
        
        if category:
            conditions.append(Template.category == category)
        
        if academic_field:
            conditions.append(Template.academic_field == academic_field)
        
        if conference_series:
            conditions.append(Template.conference_series == conference_series)
        
        stmt = (
            select(Template)
            .where(and_(*conditions))
            .order_by(
                Template.is_official.desc(),
                Template.usage_count.desc(),
                Template.name
            )
        )
        
        result = await self.db.execute(stmt)
        return list(result.scalars())
    
    async def get_by_name(self, name: str) -> Optional[Template]:
        """
        Get template by name.
        
        Args:
            name: Template name
            
        Returns:
            Template or None
        """
        stmt = (
            select(Template)
            .where(
                and_(
                    Template.name == name,
                    Template.deleted_at.is_(None)
                )
            )
        )
        
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_user_templates(
        self,
        user_id: UUID,
        include_institutional: bool = True,
    ) -> List[Template]:
        """
        Get templates created by or available to a user.
        
        Args:
            user_id: User ID
            include_institutional: Include institutional templates
            
        Returns:
            List of templates
        """
        conditions = [
            Template.created_by_id == user_id,
            Template.deleted_at.is_(None)
        ]
        
        if include_institutional:
            # Get user's institution
            user_query = text("""
                SELECT institution FROM "user"
                WHERE id = :user_id AND deleted_at IS NULL
            """)
            result = await self.db.execute(user_query, {"user_id": user_id})
            institution_name = result.scalar()
            
            if institution_name:
                # Find institution ID
                inst_query = text("""
                    SELECT id FROM institution
                    WHERE name = :name AND deleted_at IS NULL
                    LIMIT 1
                """)
                inst_result = await self.db.execute(
                    inst_query,
                    {"name": institution_name}
                )
                institution_id = inst_result.scalar()
                
                if institution_id:
                    conditions[0] = or_(
                        Template.created_by_id == user_id,
                        Template.institution_id == institution_id
                    )
        
        stmt = (
            select(Template)
            .where(and_(*conditions))
            .order_by(Template.created_at.desc())
        )
        
        result = await self.db.execute(stmt)
        return list(result.scalars())
    
    async def increment_usage_count(self, template_id: UUID) -> None:
        """
        Increment template usage count.
        
        Args:
            template_id: Template ID
        """
        stmt = (
            update(Template)
            .where(Template.id == template_id)
            .values(usage_count=Template.usage_count + 1)
        )
        await self.db.execute(stmt)
    
    async def get_popular_templates(
        self,
        limit: int = 10,
        category: Optional[str] = None,
    ) -> List[Template]:
        """
        Get most popular templates.
        
        Args:
            limit: Maximum results
            category: Filter by category
            
        Returns:
            List of popular templates
        """
        conditions = [
            Template.is_active == True,
            Template.deleted_at.is_(None)
        ]
        
        if category:
            conditions.append(Template.category == category)
        
        stmt = (
            select(Template)
            .where(and_(*conditions))
            .order_by(Template.usage_count.desc())
            .limit(limit)
        )
        
        result = await self.db.execute(stmt)
        return list(result.scalars())
    
    async def search_templates(
        self,
        query: str,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Template]:
        """
        Search templates by name or description.
        
        Args:
            query: Search query
            filters: Additional filters
            
        Returns:
            List of matching templates
        """
        filters = filters or {}
        query_lower = f"%{query.lower()}%"
        
        conditions = [
            or_(
                func.lower(Template.name).like(query_lower),
                func.lower(Template.display_name).like(query_lower),
                func.lower(Template.description).like(query_lower)
            ),
            Template.is_active == True,
            Template.deleted_at.is_(None)
        ]
        
        # Apply filters
        if filters.get('category'):
            conditions.append(Template.category == filters['category'])
        
        if filters.get('academic_field'):
            conditions.append(Template.academic_field == filters['academic_field'])
        
        if filters.get('is_official') is not None:
            conditions.append(Template.is_official == filters['is_official'])
        
        stmt = (
            select(Template)
            .where(and_(*conditions))
            .order_by(Template.name)
        )
        
        result = await self.db.execute(stmt)
        return list(result.scalars())


# Import additional required modules
from sqlalchemy import update, text