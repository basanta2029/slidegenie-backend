"""
AI and Content Generation service interfaces for Agent 1.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from uuid import UUID

from app.domain.schemas.generation import (
    GenerationRequest,
    GenerationResponse,
    SlideContent,
    Citation
)


class IAIService(ABC):
    """Interface for AI model integration."""
    
    @abstractmethod
    async def generate_completion(
        self,
        prompt: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
    ) -> Dict[str, Any]:
        """Generate completion from AI model."""
        pass
    
    @abstractmethod
    async def generate_embeddings(self, text: str) -> List[float]:
        """Generate text embeddings."""
        pass
    
    @abstractmethod
    def estimate_tokens(self, text: str) -> int:
        """Estimate token count for text."""
        pass
    
    @abstractmethod
    def get_available_models(self) -> List[str]:
        """Get list of available AI models."""
        pass


class IContentGenerationService(ABC):
    """Interface for presentation content generation."""
    
    @abstractmethod
    async def generate_from_abstract(
        self,
        abstract: str,
        presentation_type: str,
        slide_count: int = 15,
        options: Optional[Dict[str, Any]] = None,
    ) -> GenerationResponse:
        """Generate presentation from abstract."""
        pass
    
    @abstractmethod
    async def generate_from_paper(
        self,
        paper_content: str,
        sections: List[str],
        options: Optional[Dict[str, Any]] = None,
    ) -> GenerationResponse:
        """Generate presentation from full paper."""
        pass
    
    @abstractmethod
    async def generate_slide_content(
        self,
        topic: str,
        slide_type: str,
        context: Optional[Dict[str, Any]] = None,
    ) -> SlideContent:
        """Generate content for a single slide."""
        pass
    
    @abstractmethod
    async def enhance_slide(
        self,
        slide_content: SlideContent,
        enhancement_type: str,
    ) -> SlideContent:
        """Enhance existing slide content."""
        pass


class ICitationExtractionService(ABC):
    """Interface for citation extraction and processing."""
    
    @abstractmethod
    async def extract_citations(self, text: str) -> List[Citation]:
        """Extract citations from text."""
        pass
    
    @abstractmethod
    async def parse_bibtex(self, bibtex_content: str) -> List[Dict[str, Any]]:
        """Parse BibTeX content."""
        pass
    
    @abstractmethod
    async def format_citation(
        self,
        citation_data: Dict[str, Any],
        style: str = "apa",
    ) -> str:
        """Format citation in specified style."""
        pass
    
    @abstractmethod
    async def lookup_doi(self, doi: str) -> Optional[Dict[str, Any]]:
        """Lookup citation data by DOI."""
        pass


class ILatexProcessingService(ABC):
    """Interface for LaTeX equation processing."""
    
    @abstractmethod
    async def parse_latex_equation(self, equation: str) -> Dict[str, Any]:
        """Parse LaTeX equation."""
        pass
    
    @abstractmethod
    async def render_equation(
        self,
        equation: str,
        format: str = "svg",
        size: Optional[str] = None,
    ) -> bytes:
        """Render LaTeX equation to image."""
        pass
    
    @abstractmethod
    async def extract_equations_from_text(self, text: str) -> List[str]:
        """Extract LaTeX equations from text."""
        pass
    
    @abstractmethod
    def validate_latex(self, equation: str) -> bool:
        """Validate LaTeX syntax."""
        pass


class IPromptEngineeringService(ABC):
    """Interface for academic prompt engineering."""
    
    @abstractmethod
    async def create_presentation_prompt(
        self,
        content_type: str,
        academic_field: str,
        requirements: Dict[str, Any],
    ) -> str:
        """Create optimized prompt for presentation generation."""
        pass
    
    @abstractmethod
    async def create_slide_prompt(
        self,
        slide_type: str,
        content: str,
        context: Dict[str, Any],
    ) -> str:
        """Create prompt for single slide generation."""
        pass
    
    @abstractmethod
    async def create_enhancement_prompt(
        self,
        content: str,
        enhancement_type: str,
        target_audience: str,
    ) -> str:
        """Create prompt for content enhancement."""
        pass