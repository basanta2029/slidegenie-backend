"""Interface definitions for slide generation components.

These interfaces define the contracts that must be implemented by
the various slide generation subsystems.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Tuple, AsyncGenerator
from dataclasses import dataclass
from enum import Enum
from datetime import datetime


# Common data structures
@dataclass
class SlideContent:
    """Content for a single slide."""
    title: Optional[str] = None
    content: Optional[str] = None
    bullet_points: List[str] = None
    speaker_notes: Optional[str] = None
    layout_type: str = "content"
    visual_elements: List[Dict[str, Any]] = None
    metadata: Dict[str, Any] = None


@dataclass
class PresentationContent:
    """Complete presentation content."""
    title: str
    subtitle: Optional[str] = None
    author: Optional[str] = None
    date: Optional[datetime] = None
    slides: List[SlideContent] = None
    theme: Optional[str] = None
    metadata: Dict[str, Any] = None


@dataclass
class ValidationResult:
    """Result of validation check."""
    is_valid: bool
    errors: List[str] = None
    warnings: List[str] = None
    suggestions: List[str] = None


@dataclass
class QualityReport:
    """Quality assessment report."""
    overall_score: float
    readability_score: float
    consistency_score: float
    accessibility_score: float
    issues: List[Dict[str, Any]] = None
    recommendations: List[str] = None


@dataclass
class GenerationProgress:
    """Progress tracking for generation process."""
    current_step: str
    progress_percentage: float
    estimated_time_remaining: Optional[float] = None
    message: Optional[str] = None


# Generator interfaces
class ISlideGenerator(ABC):
    """Interface for slide generators."""
    
    @abstractmethod
    async def generate(
        self, 
        content: PresentationContent, 
        output_format: str,
        options: Optional[Dict[str, Any]] = None
    ) -> bytes:
        """Generate presentation in specified format."""
        pass
    
    @abstractmethod
    def supports_format(self, format: str) -> bool:
        """Check if generator supports the format."""
        pass
    
    @abstractmethod
    async def export_async(
        self,
        content: PresentationContent,
        output_format: str,
        stream: bool = False
    ) -> AsyncGenerator[bytes, None]:
        """Export presentation with optional streaming."""
        pass


# Layout interfaces
class ILayoutEngine(ABC):
    """Interface for layout engine."""
    
    @abstractmethod
    def get_available_layouts(self, style: str) -> List[str]:
        """Get available layouts for a style."""
        pass
    
    @abstractmethod
    def apply_layout(
        self,
        slide: SlideContent,
        layout_name: str,
        style_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Apply layout to slide content."""
        pass
    
    @abstractmethod
    def optimize_layout(
        self,
        slide: SlideContent,
        constraints: Optional[Dict[str, Any]] = None
    ) -> SlideContent:
        """Optimize slide layout based on content."""
        pass


# Rules interfaces
class IRule(ABC):
    """Interface for individual rules."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Rule name."""
        pass
    
    @property
    @abstractmethod
    def category(self) -> str:
        """Rule category (content, design, accessibility, etc.)."""
        pass
    
    @abstractmethod
    def validate(self, content: Any) -> ValidationResult:
        """Validate content against rule."""
        pass


class IRulesEngine(ABC):
    """Interface for rules engine."""
    
    @abstractmethod
    def add_rule(self, rule: IRule) -> None:
        """Add a validation rule."""
        pass
    
    @abstractmethod
    def validate_slide(self, slide: SlideContent) -> ValidationResult:
        """Validate a single slide."""
        pass
    
    @abstractmethod
    def validate_presentation(self, presentation: PresentationContent) -> ValidationResult:
        """Validate entire presentation."""
        pass
    
    @abstractmethod
    def get_rules_by_category(self, category: str) -> List[IRule]:
        """Get all rules in a category."""
        pass


# Quality interfaces
class IQualityChecker(ABC):
    """Interface for quality checkers."""
    
    @abstractmethod
    async def check_quality(
        self,
        presentation: PresentationContent,
        quality_level: str = "standard"
    ) -> QualityReport:
        """Check presentation quality."""
        pass
    
    @abstractmethod
    async def improve_quality(
        self,
        presentation: PresentationContent,
        target_score: float = 0.8
    ) -> Tuple[PresentationContent, QualityReport]:
        """Improve presentation quality."""
        pass
    
    @abstractmethod
    def get_quality_metrics(self) -> List[str]:
        """Get available quality metrics."""
        pass


# Orchestrator interfaces  
class IOrchestrator(ABC):
    """Interface for generation orchestrator."""
    
    @abstractmethod
    async def generate_presentation(
        self,
        input_content: str,
        config: Dict[str, Any],
        progress_callback: Optional[callable] = None
    ) -> PresentationContent:
        """Orchestrate the complete generation process."""
        pass
    
    @abstractmethod
    async def validate_input(self, input_content: str) -> ValidationResult:
        """Validate input before processing."""
        pass
    
    @abstractmethod
    def get_generation_status(self, job_id: str) -> Dict[str, Any]:
        """Get status of generation job."""
        pass
    
    @abstractmethod
    async def cancel_generation(self, job_id: str) -> bool:
        """Cancel an ongoing generation."""
        pass


# Factory interfaces
class IComponentFactory(ABC):
    """Factory for creating slide generation components."""
    
    @abstractmethod
    def create_generator(self, format: str) -> ISlideGenerator:
        """Create generator for specific format."""
        pass
    
    @abstractmethod
    def create_layout_engine(self, style: str) -> ILayoutEngine:
        """Create layout engine for style."""
        pass
    
    @abstractmethod
    def create_rules_engine(self, config: Dict[str, Any]) -> IRulesEngine:
        """Create rules engine with configuration."""
        pass
    
    @abstractmethod
    def create_quality_checker(self, level: str) -> IQualityChecker:
        """Create quality checker for level."""
        pass
    
    @abstractmethod
    def create_orchestrator(self, config: Dict[str, Any]) -> IOrchestrator:
        """Create orchestrator with configuration."""
        pass