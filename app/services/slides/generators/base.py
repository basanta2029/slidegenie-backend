"""
Base slide generator class with common functionality.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, Union
from uuid import UUID

from pydantic import BaseModel, Field

from app.core.logging import get_logger
from app.domain.schemas.generation import SlideContent, Citation


logger = get_logger(__name__)


class GeneratorOptions(BaseModel):
    """Options for slide generation."""
    language: str = Field(default="en")
    academic_level: str = Field(default="research")  # undergraduate, graduate, research, professional
    presentation_type: str = Field(default="conference")  # conference, lecture, defense, seminar
    citation_style: str = Field(default="ieee")  # ieee, apa, mla, chicago
    include_speaker_notes: bool = Field(default=True)
    max_bullets_per_slide: int = Field(default=6)
    max_words_per_bullet: int = Field(default=25)
    emphasis_style: str = Field(default="bold")  # bold, italic, color
    
    class Config:
        extra = "allow"  # Allow additional fields for extensibility


class GeneratorInput(BaseModel):
    """Input data for slide generation."""
    content: Dict[str, Any] = Field(..., description="Structured content for the section")
    context: Dict[str, Any] = Field(default_factory=dict, description="Additional context")
    options: GeneratorOptions = Field(default_factory=GeneratorOptions)
    template_config: Dict[str, Any] = Field(default_factory=dict)


class BaseSlideGenerator(ABC):
    """Abstract base class for slide generators."""
    
    def __init__(self):
        """Initialize the generator."""
        self.logger = get_logger(self.__class__.__name__)
    
    @property
    @abstractmethod
    def section_type(self) -> str:
        """Return the section type this generator handles."""
        pass
    
    @property
    @abstractmethod
    def default_layout(self) -> str:
        """Return the default layout type for this section."""
        pass
    
    @abstractmethod
    def generate(self, input_data: GeneratorInput) -> List[SlideContent]:
        """
        Generate slides for the section.
        
        Args:
            input_data: Input data including content, context, and options
            
        Returns:
            List of generated slides
        """
        pass
    
    def validate_input(self, input_data: GeneratorInput) -> bool:
        """
        Validate input data for the generator.
        
        Args:
            input_data: Input data to validate
            
        Returns:
            True if valid, raises ValueError if not
        """
        if not input_data.content:
            raise ValueError(f"{self.section_type} generator requires content")
        return True
    
    def apply_formatting_rules(self, content: Dict[str, Any], options: GeneratorOptions) -> Dict[str, Any]:
        """
        Apply academic formatting rules to content.
        
        Args:
            content: Raw content to format
            options: Generator options
            
        Returns:
            Formatted content
        """
        # Apply common formatting rules
        if "body" in content:
            formatted_body = []
            for item in content["body"]:
                if item.get("type") == "bullet_list":
                    # Apply bullet point rules
                    formatted_items = []
                    for bullet in item.get("items", []):
                        # Limit words per bullet
                        words = bullet.split()
                        if len(words) > options.max_words_per_bullet:
                            # Split into multiple bullets
                            chunks = []
                            current_chunk = []
                            for word in words:
                                current_chunk.append(word)
                                if len(current_chunk) >= options.max_words_per_bullet:
                                    chunks.append(" ".join(current_chunk))
                                    current_chunk = []
                            if current_chunk:
                                chunks.append(" ".join(current_chunk))
                            formatted_items.extend(chunks)
                        else:
                            formatted_items.append(bullet)
                    
                    # Limit bullets per slide
                    if len(formatted_items) > options.max_bullets_per_slide:
                        # This should trigger slide splitting in the generator
                        item["items"] = formatted_items[:options.max_bullets_per_slide]
                        item["overflow_items"] = formatted_items[options.max_bullets_per_slide:]
                    else:
                        item["items"] = formatted_items
                
                formatted_body.append(item)
            
            content["body"] = formatted_body
        
        return content
    
    def create_slide(
        self,
        title: str,
        body: List[Dict[str, Any]],
        layout: Optional[str] = None,
        subtitle: Optional[str] = None,
        speaker_notes: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> SlideContent:
        """
        Create a slide with consistent structure.
        
        Args:
            title: Slide title
            body: Slide body content
            layout: Layout type (uses default if not specified)
            subtitle: Optional subtitle
            speaker_notes: Optional speaker notes
            metadata: Optional metadata
            
        Returns:
            SlideContent object
        """
        return SlideContent(
            title=title,
            subtitle=subtitle,
            body=body,
            layout=layout or self.default_layout,
            speaker_notes=speaker_notes,
            metadata=metadata or {}
        )
    
    def split_content_across_slides(
        self,
        title: str,
        items: List[Any],
        items_per_slide: int,
        item_formatter: callable,
        subtitle_prefix: Optional[str] = None
    ) -> List[SlideContent]:
        """
        Split content across multiple slides if needed.
        
        Args:
            title: Base title for slides
            items: Items to distribute
            items_per_slide: Maximum items per slide
            item_formatter: Function to format items for slide body
            subtitle_prefix: Optional prefix for continuation slides
            
        Returns:
            List of slides
        """
        slides = []
        
        for i in range(0, len(items), items_per_slide):
            chunk = items[i:i + items_per_slide]
            slide_num = (i // items_per_slide) + 1
            total_slides = (len(items) - 1) // items_per_slide + 1
            
            if total_slides > 1:
                slide_title = f"{title} ({slide_num}/{total_slides})"
                subtitle = f"{subtitle_prefix} - Part {slide_num}" if subtitle_prefix else None
            else:
                slide_title = title
                subtitle = subtitle_prefix
            
            slides.append(self.create_slide(
                title=slide_title,
                subtitle=subtitle,
                body=item_formatter(chunk)
            ))
        
        return slides
    
    def format_citations(self, citations: List[str], style: str = "inline") -> Dict[str, Any]:
        """
        Format citations according to academic style.
        
        Args:
            citations: List of citation keys
            style: Citation style (inline, footnote, endnote)
            
        Returns:
            Formatted citation content
        """
        return {
            "type": "citation",
            "keys": citations,
            "style": style
        }
    
    def create_visual_suggestion(
        self,
        visual_type: str,
        description: str,
        data: Optional[Dict[str, Any]] = None,
        caption: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Create a visual element suggestion.
        
        Args:
            visual_type: Type of visual (diagram, chart, image, etc.)
            description: Description of what should be visualized
            data: Optional data for the visualization
            caption: Optional caption
            
        Returns:
            Visual element content
        """
        return {
            "type": "visual_suggestion",
            "visual_type": visual_type,
            "description": description,
            "data": data or {},
            "caption": caption,
            "placeholder": True  # Indicates this needs to be replaced with actual visual
        }
    
    def estimate_speaking_time(self, slide: SlideContent, words_per_minute: int = 150) -> int:
        """
        Estimate speaking time for a slide in seconds.
        
        Args:
            slide: Slide content
            words_per_minute: Average speaking rate
            
        Returns:
            Estimated time in seconds
        """
        word_count = 0
        
        # Count words in title and subtitle
        if slide.title:
            word_count += len(slide.title.split())
        if slide.subtitle:
            word_count += len(slide.subtitle.split())
        
        # Count words in body
        for item in slide.body:
            if item.get("type") == "text":
                word_count += len(item.get("content", "").split())
            elif item.get("type") == "bullet_list":
                for bullet in item.get("items", []):
                    word_count += len(bullet.split())
            # Add extra time for visual elements
            elif item.get("type") in ["image", "chart", "diagram", "table"]:
                word_count += 30  # Assume 12 seconds for explaining a visual
        
        # Calculate time in seconds
        speaking_time = int((word_count / words_per_minute) * 60)
        
        # Add buffer time for transitions
        speaking_time += 5
        
        return max(speaking_time, 10)  # Minimum 10 seconds per slide