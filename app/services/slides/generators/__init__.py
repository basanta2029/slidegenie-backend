"""
Slide generator classes for academic presentations.

This module provides generators for different types of academic slides,
each with specialized formatting and content organization.
"""
from typing import Dict, List

from .base import BaseSlideGenerator, GeneratorOptions, GeneratorInput
from .title import TitleSlideGenerator
from .outline import OutlineGenerator
from .introduction import IntroductionGenerator
from .literature import LiteratureReviewGenerator
from .methodology import MethodologyGenerator
from .results import ResultsGenerator
from .discussion import DiscussionGenerator
from .conclusion import ConclusionGenerator
from .references import ReferencesGenerator

# Registry of all available generators
GENERATOR_REGISTRY = {
    "title": TitleSlideGenerator,
    "outline": OutlineGenerator,
    "introduction": IntroductionGenerator,
    "literature_review": LiteratureReviewGenerator,
    "methodology": MethodologyGenerator,
    "results": ResultsGenerator,
    "discussion": DiscussionGenerator,
    "conclusion": ConclusionGenerator,
    "references": ReferencesGenerator,
}

# Alternative names for generators
GENERATOR_ALIASES = {
    "title_slide": "title",
    "agenda": "outline",
    "table_of_contents": "outline",
    "intro": "introduction",
    "background": "introduction",
    "related_work": "literature_review",
    "literature": "literature_review",
    "method": "methodology",
    "methods": "methodology",
    "approach": "methodology",
    "findings": "results",
    "evaluation": "results",
    "experiments": "results",
    "summary": "conclusion",
    "conclusions": "conclusion",
    "future_work": "conclusion",
    "bibliography": "references",
    "citations": "references",
}


def get_generator(section_type: str) -> BaseSlideGenerator:
    """
    Get a generator instance for the specified section type.
    
    Args:
        section_type: Type of section (e.g., 'introduction', 'results')
        
    Returns:
        Generator instance for the section
        
    Raises:
        ValueError: If section type is not recognized
    """
    # Normalize section type
    section_type = section_type.lower().strip()
    
    # Check aliases first
    if section_type in GENERATOR_ALIASES:
        section_type = GENERATOR_ALIASES[section_type]
    
    # Get generator class
    if section_type not in GENERATOR_REGISTRY:
        available = list(GENERATOR_REGISTRY.keys()) + list(GENERATOR_ALIASES.keys())
        raise ValueError(
            f"Unknown section type '{section_type}'. "
            f"Available types: {', '.join(sorted(available))}"
        )
    
    generator_class = GENERATOR_REGISTRY[section_type]
    return generator_class()


def list_available_generators() -> Dict[str, str]:
    """
    List all available generators with their descriptions.
    
    Returns:
        Dictionary mapping generator names to descriptions
    """
    descriptions = {
        "title": "Title slide with authors, affiliations, and conference info",
        "outline": "Table of contents/agenda with navigation",
        "introduction": "Background, motivation, and problem statement",
        "literature_review": "Related work with categorization and comparison",
        "methodology": "Approach, algorithms, and implementation details",
        "results": "Experimental findings with visualizations",
        "discussion": "Interpretation, implications, and limitations",
        "conclusion": "Summary, impact, and future work",
        "references": "Bibliography with proper academic formatting",
    }
    return descriptions


def create_generator_pipeline(section_types: List[str]) -> List[BaseSlideGenerator]:
    """
    Create a pipeline of generators for multiple sections.
    
    Args:
        section_types: List of section types in order
        
    Returns:
        List of generator instances
    """
    return [get_generator(section_type) for section_type in section_types]


# Standard academic presentation structure
STANDARD_ACADEMIC_STRUCTURE = [
    "title",
    "outline", 
    "introduction",
    "literature_review",
    "methodology",
    "results",
    "discussion",
    "conclusion",
    "references"
]

# Conference presentation structure (shorter)
CONFERENCE_STRUCTURE = [
    "title",
    "outline",
    "introduction", 
    "methodology",
    "results",
    "conclusion",
    "references"
]

# Thesis defense structure (comprehensive)
THESIS_DEFENSE_STRUCTURE = [
    "title",
    "outline",
    "introduction",
    "literature_review",
    "methodology",
    "results",
    "discussion",
    "conclusion",
    "references"
]

# Lecture structure
LECTURE_STRUCTURE = [
    "title",
    "outline",
    "introduction",
    "methodology",  # Main content
    "conclusion"
]

PRESENTATION_STRUCTURES = {
    "academic": STANDARD_ACADEMIC_STRUCTURE,
    "conference": CONFERENCE_STRUCTURE,
    "defense": THESIS_DEFENSE_STRUCTURE,
    "lecture": LECTURE_STRUCTURE,
}


def get_presentation_structure(presentation_type: str) -> List[str]:
    """
    Get the standard structure for a presentation type.
    
    Args:
        presentation_type: Type of presentation
        
    Returns:
        List of section types in order
    """
    return PRESENTATION_STRUCTURES.get(
        presentation_type.lower(),
        STANDARD_ACADEMIC_STRUCTURE
    )


__all__ = [
    "BaseSlideGenerator",
    "GeneratorOptions", 
    "GeneratorInput",
    "TitleSlideGenerator",
    "OutlineGenerator",
    "IntroductionGenerator",
    "LiteratureReviewGenerator", 
    "MethodologyGenerator",
    "ResultsGenerator",
    "DiscussionGenerator",
    "ConclusionGenerator",
    "ReferencesGenerator",
    "GENERATOR_REGISTRY",
    "GENERATOR_ALIASES",
    "get_generator",
    "list_available_generators",
    "create_generator_pipeline",
    "get_presentation_structure",
    "PRESENTATION_STRUCTURES",
]