"""
Academic Features and Reference Management service interfaces for Agent 3.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from uuid import UUID


class IReferenceManagementService(ABC):
    """Interface for reference and citation management."""
    
    @abstractmethod
    async def import_bibtex(
        self,
        presentation_id: UUID,
        bibtex_content: str,
    ) -> List[Dict[str, Any]]:
        """Import references from BibTeX."""
        pass
    
    @abstractmethod
    async def export_bibtex(
        self,
        presentation_id: UUID,
        citation_keys: Optional[List[str]] = None,
    ) -> str:
        """Export references to BibTeX."""
        pass
    
    @abstractmethod
    async def format_citations(
        self,
        citations: List[Dict[str, Any]],
        style: str = "apa",
    ) -> List[str]:
        """Format citations in specified style."""
        pass
    
    @abstractmethod
    async def deduplicate_references(
        self,
        presentation_id: UUID,
    ) -> Dict[str, Any]:
        """Deduplicate references in presentation."""
        pass
    
    @abstractmethod
    async def update_citation_usage(
        self,
        presentation_id: UUID,
    ) -> Dict[str, List[int]]:
        """Update citation usage across slides."""
        pass


class IAcademicLookupService(ABC):
    """Interface for academic database lookups."""
    
    @abstractmethod
    async def lookup_by_doi(self, doi: str) -> Optional[Dict[str, Any]]:
        """Lookup paper by DOI."""
        pass
    
    @abstractmethod
    async def lookup_by_pmid(self, pmid: str) -> Optional[Dict[str, Any]]:
        """Lookup paper by PubMed ID."""
        pass
    
    @abstractmethod
    async def lookup_by_arxiv(self, arxiv_id: str) -> Optional[Dict[str, Any]]:
        """Lookup paper by arXiv ID."""
        pass
    
    @abstractmethod
    async def search_crossref(
        self,
        query: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Search CrossRef database."""
        pass
    
    @abstractmethod
    async def search_pubmed(
        self,
        query: str,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """Search PubMed database."""
        pass


class ITemplateManagementService(ABC):
    """Interface for academic template management."""
    
    @abstractmethod
    async def create_custom_template(
        self,
        user_id: UUID,
        name: str,
        config: Dict[str, Any],
        base_template_id: Optional[UUID] = None,
    ) -> Dict[str, Any]:
        """Create custom template."""
        pass
    
    @abstractmethod
    async def update_template(
        self,
        template_id: UUID,
        user_id: UUID,
        updates: Dict[str, Any],
    ) -> Optional[Dict[str, Any]]:
        """Update template configuration."""
        pass
    
    @abstractmethod
    async def share_template(
        self,
        template_id: UUID,
        visibility: str = "public",
        institutions: Optional[List[UUID]] = None,
    ) -> bool:
        """Share template with others."""
        pass
    
    @abstractmethod
    async def get_conference_templates(
        self,
        conference_series: str,
    ) -> List[Dict[str, Any]]:
        """Get templates for specific conference."""
        pass
    
    @abstractmethod
    async def validate_template_compliance(
        self,
        presentation_id: UUID,
        template_id: UUID,
    ) -> Dict[str, Any]:
        """Validate presentation against template requirements."""
        pass


class IInstitutionBrandingService(ABC):
    """Interface for institutional branding."""
    
    @abstractmethod
    async def apply_institution_branding(
        self,
        presentation_id: UUID,
        institution_id: UUID,
    ) -> bool:
        """Apply institutional branding to presentation."""
        pass
    
    @abstractmethod
    async def create_institution_template(
        self,
        institution_id: UUID,
        base_template_id: UUID,
        branding: Dict[str, Any],
    ) -> Dict[str, Any]:
        """Create institution-specific template."""
        pass
    
    @abstractmethod
    async def validate_branding_compliance(
        self,
        presentation_id: UUID,
        institution_id: UUID,
    ) -> Dict[str, Any]:
        """Validate branding compliance."""
        pass


class ITemplateMarketplaceService(ABC):
    """Interface for template marketplace."""
    
    @abstractmethod
    async def list_marketplace_templates(
        self,
        filters: Optional[Dict[str, Any]] = None,
        sort_by: str = "popularity",
        limit: int = 20,
        offset: int = 0,
    ) -> tuple[List[Dict[str, Any]], int]:
        """List marketplace templates."""
        pass
    
    @abstractmethod
    async def purchase_template(
        self,
        user_id: UUID,
        template_id: UUID,
        payment_token: str,
    ) -> Dict[str, Any]:
        """Purchase premium template."""
        pass
    
    @abstractmethod
    async def rate_template(
        self,
        user_id: UUID,
        template_id: UUID,
        rating: int,
        review: Optional[str] = None,
    ) -> bool:
        """Rate and review template."""
        pass
    
    @abstractmethod
    async def get_template_analytics(
        self,
        template_id: UUID,
        creator_id: UUID,
    ) -> Dict[str, Any]:
        """Get template usage analytics."""
        pass