"""
Presentation and Slide Management service interfaces for Agent 2.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.domain.schemas.presentation import (
    PresentationCreate,
    PresentationUpdate,
    SlideCreate,
    SlideUpdate,
    CollaboratorAdd
)


class IPresentationService(ABC):
    """Interface for presentation management."""
    
    @abstractmethod
    async def create_presentation(
        self,
        user_id: UUID,
        data: PresentationCreate,
    ) -> Dict[str, Any]:
        """Create a new presentation."""
        pass
    
    @abstractmethod
    async def update_presentation(
        self,
        presentation_id: UUID,
        user_id: UUID,
        data: PresentationUpdate,
    ) -> Optional[Dict[str, Any]]:
        """Update presentation details."""
        pass
    
    @abstractmethod
    async def duplicate_presentation(
        self,
        presentation_id: UUID,
        user_id: UUID,
        new_title: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Duplicate an existing presentation."""
        pass
    
    @abstractmethod
    async def apply_template(
        self,
        presentation_id: UUID,
        template_id: UUID,
        preserve_content: bool = True,
    ) -> bool:
        """Apply template to presentation."""
        pass
    
    @abstractmethod
    async def get_presentation_statistics(
        self,
        presentation_id: UUID,
    ) -> Dict[str, Any]:
        """Get presentation statistics."""
        pass


class ISlideService(ABC):
    """Interface for slide management."""
    
    @abstractmethod
    async def create_slide(
        self,
        presentation_id: UUID,
        data: SlideCreate,
        position: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Create a new slide."""
        pass
    
    @abstractmethod
    async def update_slide(
        self,
        slide_id: UUID,
        data: SlideUpdate,
    ) -> Optional[Dict[str, Any]]:
        """Update slide content."""
        pass
    
    @abstractmethod
    async def reorder_slides(
        self,
        presentation_id: UUID,
        new_order: List[UUID],
    ) -> bool:
        """Reorder slides in presentation."""
        pass
    
    @abstractmethod
    async def duplicate_slide(
        self,
        slide_id: UUID,
        target_position: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Duplicate a slide."""
        pass
    
    @abstractmethod
    async def bulk_update_slides(
        self,
        presentation_id: UUID,
        updates: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        """Update multiple slides at once."""
        pass


class ICollaborationService(ABC):
    """Interface for presentation collaboration."""
    
    @abstractmethod
    async def add_collaborator(
        self,
        presentation_id: UUID,
        owner_id: UUID,
        collaborator: CollaboratorAdd,
    ) -> Dict[str, Any]:
        """Add collaborator to presentation."""
        pass
    
    @abstractmethod
    async def remove_collaborator(
        self,
        presentation_id: UUID,
        owner_id: UUID,
        collaborator_id: UUID,
    ) -> bool:
        """Remove collaborator from presentation."""
        pass
    
    @abstractmethod
    async def update_permissions(
        self,
        presentation_id: UUID,
        collaborator_id: UUID,
        permissions: List[str],
    ) -> bool:
        """Update collaborator permissions."""
        pass
    
    @abstractmethod
    async def get_collaborators(
        self,
        presentation_id: UUID,
    ) -> List[Dict[str, Any]]:
        """Get all collaborators for presentation."""
        pass
    
    @abstractmethod
    async def create_share_link(
        self,
        presentation_id: UUID,
        permissions: List[str],
        expires_in_days: Optional[int] = None,
    ) -> str:
        """Create shareable link."""
        pass


class IVersionControlService(ABC):
    """Interface for presentation version control."""
    
    @abstractmethod
    async def create_version(
        self,
        presentation_id: UUID,
        user_id: UUID,
        description: str,
    ) -> Dict[str, Any]:
        """Create a new version snapshot."""
        pass
    
    @abstractmethod
    async def list_versions(
        self,
        presentation_id: UUID,
    ) -> List[Dict[str, Any]]:
        """List all versions of presentation."""
        pass
    
    @abstractmethod
    async def restore_version(
        self,
        presentation_id: UUID,
        version_id: UUID,
        user_id: UUID,
    ) -> bool:
        """Restore presentation to specific version."""
        pass
    
    @abstractmethod
    async def compare_versions(
        self,
        presentation_id: UUID,
        version_a: UUID,
        version_b: UUID,
    ) -> Dict[str, Any]:
        """Compare two versions of presentation."""
        pass
    
    @abstractmethod
    async def get_version_diff(
        self,
        presentation_id: UUID,
        version_id: UUID,
    ) -> Dict[str, Any]:
        """Get changes in specific version."""
        pass


class ITemplateApplicationService(ABC):
    """Interface for template application logic."""
    
    @abstractmethod
    async def apply_theme(
        self,
        presentation_id: UUID,
        theme_config: Dict[str, Any],
    ) -> bool:
        """Apply theme configuration to presentation."""
        pass
    
    @abstractmethod
    async def apply_layout(
        self,
        slide_id: UUID,
        layout_type: str,
        preserve_content: bool = True,
    ) -> bool:
        """Apply layout to specific slide."""
        pass
    
    @abstractmethod
    async def bulk_apply_layouts(
        self,
        presentation_id: UUID,
        layout_mapping: Dict[UUID, str],
    ) -> Dict[UUID, bool]:
        """Apply layouts to multiple slides."""
        pass
    
    @abstractmethod
    async def migrate_content_to_layout(
        self,
        content: Dict[str, Any],
        from_layout: str,
        to_layout: str,
    ) -> Dict[str, Any]:
        """Migrate content between different layouts."""
        pass