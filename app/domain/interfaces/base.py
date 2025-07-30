"""
Base service interfaces for all SlideGenie services.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, TypeVar, Generic
from uuid import UUID

T = TypeVar('T')


class IService(ABC, Generic[T]):
    """Base interface for all services."""
    
    @abstractmethod
    async def create(self, data: Dict[str, Any]) -> T:
        """Create a new resource."""
        pass
    
    @abstractmethod
    async def get(self, id: UUID) -> Optional[T]:
        """Get a resource by ID."""
        pass
    
    @abstractmethod
    async def update(self, id: UUID, data: Dict[str, Any]) -> Optional[T]:
        """Update a resource."""
        pass
    
    @abstractmethod
    async def delete(self, id: UUID) -> bool:
        """Delete a resource."""
        pass
    
    @abstractmethod
    async def list(self, filters: Optional[Dict[str, Any]] = None, limit: int = 20, offset: int = 0) -> tuple[List[T], int]:
        """List resources with pagination."""
        pass


class IAsyncProcessor(ABC):
    """Interface for asynchronous processors."""
    
    @abstractmethod
    async def process(self, job_id: UUID, data: Dict[str, Any]) -> Dict[str, Any]:
        """Process a job asynchronously."""
        pass
    
    @abstractmethod
    async def get_progress(self, job_id: UUID) -> Dict[str, Any]:
        """Get processing progress."""
        pass
    
    @abstractmethod
    async def cancel(self, job_id: UUID) -> bool:
        """Cancel a running job."""
        pass


class IExporter(ABC):
    """Interface for export services."""
    
    @abstractmethod
    async def export(self, resource_id: UUID, format: str, options: Dict[str, Any]) -> bytes:
        """Export a resource to specified format."""
        pass
    
    @abstractmethod
    def supported_formats(self) -> List[str]:
        """Get list of supported export formats."""
        pass


class ISearchService(ABC):
    """Interface for search services."""
    
    @abstractmethod
    async def search(self, query: str, filters: Optional[Dict[str, Any]] = None, limit: int = 20) -> List[Any]:
        """Search for resources."""
        pass
    
    @abstractmethod
    async def index(self, resource_id: UUID, content: Dict[str, Any]) -> bool:
        """Index a resource for searching."""
        pass
    
    @abstractmethod
    async def remove_from_index(self, resource_id: UUID) -> bool:
        """Remove a resource from search index."""
        pass


class ICacheService(ABC):
    """Interface for caching services."""
    
    @abstractmethod
    async def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        pass
    
    @abstractmethod
    async def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache."""
        pass
    
    @abstractmethod
    async def delete(self, key: str) -> bool:
        """Delete value from cache."""
        pass
    
    @abstractmethod
    async def clear_pattern(self, pattern: str) -> int:
        """Clear all keys matching pattern."""
        pass