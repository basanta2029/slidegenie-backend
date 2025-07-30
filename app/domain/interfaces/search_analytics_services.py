"""
Search and Analytics service interfaces for Agent 6.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID
from datetime import datetime, date


class ISearchService(ABC):
    """Interface for full-text and semantic search."""
    
    @abstractmethod
    async def search_presentations(
        self,
        query: str,
        user_id: Optional[UUID] = None,
        filters: Optional[Dict[str, Any]] = None,
        limit: int = 20,
        offset: int = 0,
    ) -> Tuple[List[Dict[str, Any]], int]:
        """Search presentations with full-text search."""
        pass
    
    @abstractmethod
    async def semantic_search(
        self,
        query: str,
        user_id: Optional[UUID] = None,
        threshold: float = 0.7,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Semantic search using embeddings."""
        pass
    
    @abstractmethod
    async def search_within_presentation(
        self,
        presentation_id: UUID,
        query: str,
        search_in: List[str] = ['slides', 'notes', 'references'],
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Search within a specific presentation."""
        pass
    
    @abstractmethod
    async def get_similar_presentations(
        self,
        presentation_id: UUID,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Find similar presentations."""
        pass
    
    @abstractmethod
    async def update_search_index(
        self,
        presentation_id: UUID,
    ) -> bool:
        """Update search index for presentation."""
        pass


class IEmbeddingService(ABC):
    """Interface for vector embedding operations."""
    
    @abstractmethod
    async def generate_presentation_embedding(
        self,
        presentation_id: UUID,
        embedding_type: str = "combined",
    ) -> List[float]:
        """Generate embedding for presentation."""
        pass
    
    @abstractmethod
    async def update_embeddings(
        self,
        presentation_id: UUID,
    ) -> Dict[str, bool]:
        """Update all embeddings for presentation."""
        pass
    
    @abstractmethod
    async def find_nearest_neighbors(
        self,
        embedding: List[float],
        limit: int = 10,
        filters: Optional[Dict[str, Any]] = None,
    ) -> List[Tuple[UUID, float]]:
        """Find nearest neighbors by embedding."""
        pass
    
    @abstractmethod
    async def cluster_presentations(
        self,
        user_id: Optional[UUID] = None,
        n_clusters: int = 10,
    ) -> Dict[int, List[UUID]]:
        """Cluster presentations by similarity."""
        pass


class IAnalyticsService(ABC):
    """Interface for usage analytics."""
    
    @abstractmethod
    async def track_event(
        self,
        event_type: str,
        user_id: UUID,
        metadata: Dict[str, Any],
    ) -> bool:
        """Track analytics event."""
        pass
    
    @abstractmethod
    async def get_user_analytics(
        self,
        user_id: UUID,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """Get user analytics summary."""
        pass
    
    @abstractmethod
    async def get_presentation_analytics(
        self,
        presentation_id: UUID,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """Get presentation analytics."""
        pass
    
    @abstractmethod
    async def get_system_analytics(
        self,
        from_date: Optional[date] = None,
        to_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """Get system-wide analytics."""
        pass
    
    @abstractmethod
    async def export_analytics_report(
        self,
        report_type: str,
        filters: Dict[str, Any],
        format: str = "csv",
    ) -> bytes:
        """Export analytics report."""
        pass


class IUsageMetricsService(ABC):
    """Interface for usage metrics tracking."""
    
    @abstractmethod
    async def track_api_usage(
        self,
        endpoint: str,
        user_id: UUID,
        response_time_ms: float,
        status_code: int,
    ) -> bool:
        """Track API endpoint usage."""
        pass
    
    @abstractmethod
    async def track_generation_metrics(
        self,
        job_id: UUID,
        metrics: Dict[str, Any],
    ) -> bool:
        """Track generation job metrics."""
        pass
    
    @abstractmethod
    async def get_usage_summary(
        self,
        user_id: UUID,
        period: str = "month",
    ) -> Dict[str, Any]:
        """Get usage summary for billing."""
        pass
    
    @abstractmethod
    async def get_resource_usage(
        self,
        user_id: UUID,
    ) -> Dict[str, Any]:
        """Get resource usage (storage, API calls, etc)."""
        pass


class ITaggingService(ABC):
    """Interface for content tagging and categorization."""
    
    @abstractmethod
    async def auto_tag_presentation(
        self,
        presentation_id: UUID,
    ) -> List[str]:
        """Automatically tag presentation based on content."""
        pass
    
    @abstractmethod
    async def suggest_tags(
        self,
        content: str,
        existing_tags: List[str],
        limit: int = 10,
    ) -> List[str]:
        """Suggest tags based on content."""
        pass
    
    @abstractmethod
    async def get_trending_tags(
        self,
        category: Optional[str] = None,
        limit: int = 20,
    ) -> List[Dict[str, Any]]:
        """Get trending tags."""
        pass
    
    @abstractmethod
    async def get_related_tags(
        self,
        tag: str,
        limit: int = 10,
    ) -> List[str]:
        """Get related tags."""
        pass


class ICostAnalysisService(ABC):
    """Interface for cost analysis and tracking."""
    
    @abstractmethod
    async def track_ai_usage(
        self,
        user_id: UUID,
        model: str,
        tokens_used: int,
        cost_cents: float,
    ) -> bool:
        """Track AI model usage and cost."""
        pass
    
    @abstractmethod
    async def get_user_costs(
        self,
        user_id: UUID,
        from_date: date,
        to_date: date,
    ) -> Dict[str, Any]:
        """Get user cost breakdown."""
        pass
    
    @abstractmethod
    async def get_cost_projections(
        self,
        user_id: UUID,
        period: str = "month",
    ) -> Dict[str, Any]:
        """Get cost projections based on usage."""
        pass
    
    @abstractmethod
    async def optimize_costs(
        self,
        user_id: UUID,
    ) -> Dict[str, Any]:
        """Get cost optimization recommendations."""
        pass