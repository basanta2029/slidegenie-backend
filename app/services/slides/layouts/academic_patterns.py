"""
Academic Design Patterns

Implements design patterns specifically tailored for academic presentations,
including proper citation placement, figure labeling, and scholarly layouts.
"""

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum

from .base import ElementPosition, ElementType, LayoutElement
from .grid import GridSystem, GridCell, GridAlignment


class AcademicElementType(Enum):
    """Academic-specific element types"""
    RESEARCH_QUESTION = "research_question"
    HYPOTHESIS = "hypothesis"
    METHODOLOGY = "methodology"
    RESULTS_TABLE = "results_table"
    EQUATION = "equation"
    THEOREM = "theorem"
    PROOF = "proof"
    FIGURE_WITH_CAPTION = "figure_with_caption"
    REFERENCE = "reference"
    ACKNOWLEDGMENT = "acknowledgment"
    AUTHOR_AFFILIATION = "author_affiliation"
    ABSTRACT = "abstract"


@dataclass
class AcademicStyle:
    """Style configuration for academic elements"""
    citation_style: str = "APA"  # APA, MLA, Chicago, IEEE
    equation_numbering: bool = True
    figure_numbering: bool = True
    table_numbering: bool = True
    theorem_numbering: bool = True
    bibliography_position: str = "bottom"  # bottom, separate_slide
    author_info_style: str = "grid"  # grid, list, institutional


class AcademicDesignPatterns:
    """
    Design patterns for academic presentations
    
    Provides layouts and styling for:
    - Research presentations
    - Conference talks
    - Thesis defenses
    - Academic posters
    """
    
    def __init__(self, style: Optional[AcademicStyle] = None):
        self.style = style or AcademicStyle()
        self.grid = GridSystem()
        self._counters = {
            'figure': 0,
            'table': 0,
            'equation': 0,
            'theorem': 0
        }
    
    def create_title_slide_layout(self, 
                                 title: str,
                                 authors: List[Dict[str, str]],
                                 affiliations: List[str],
                                 conference: Optional[str] = None,
                                 date: Optional[str] = None) -> List[LayoutElement]:
        """
        Create academic title slide layout
        
        Args:
            title: Presentation title
            authors: List of author dicts with 'name', 'email', 'affiliation_id'
            affiliations: List of institution names
            conference: Conference name (optional)
            date: Presentation date (optional)
            
        Returns:
            List of positioned layout elements
        """
        elements = []
        
        # Title - top center, larger
        elements.append(LayoutElement(
            type=ElementType.TITLE,
            content=title,
            position=ElementPosition(x=0.1, y=0.15, width=0.8, height=0.15),
            style={'font_size': 'large', 'font_weight': 'bold', 'text_align': 'center'}
        ))
        
        # Authors grid or list
        if self.style.author_info_style == "grid":
            author_elements = self._create_author_grid(authors, affiliations)
        else:
            author_elements = self._create_author_list(authors, affiliations)
        
        elements.extend(author_elements)
        
        # Conference info
        if conference:
            elements.append(LayoutElement(
                type=ElementType.TEXT,
                content=conference,
                position=ElementPosition(x=0.1, y=0.75, width=0.8, height=0.05),
                style={'text_align': 'center', 'font_style': 'italic'}
            ))
        
        # Date
        if date:
            elements.append(LayoutElement(
                type=ElementType.TEXT,
                content=date,
                position=ElementPosition(x=0.1, y=0.82, width=0.8, height=0.05),
                style={'text_align': 'center'}
            ))
        
        # Institutional logos (placeholder positions)
        elements.append(LayoutElement(
            type=ElementType.LOGO,
            content="institution_logos",
            position=ElementPosition(x=0.05, y=0.90, width=0.90, height=0.08),
            style={'display': 'flex', 'justify_content': 'space-around'}
        ))
        
        return elements
    
    def _create_author_grid(self, authors: List[Dict[str, str]], 
                           affiliations: List[str]) -> List[LayoutElement]:
        """Create grid layout for authors"""
        elements = []
        
        # Calculate grid dimensions
        num_authors = len(authors)
        cols = min(3, num_authors)  # Max 3 columns
        rows = (num_authors + cols - 1) // cols
        
        # Create grid cells for authors
        author_cells = []
        for row in range(rows):
            for col in range(cols):
                if row * cols + col < num_authors:
                    author_cells.append(GridCell(
                        row=3 + row,
                        col=col * 4,
                        row_span=1,
                        col_span=4,
                        alignment=GridAlignment.CENTER
                    ))
        
        # Position authors
        for i, (author, cell) in enumerate(zip(authors, author_cells)):
            pos = self.grid.get_cell_position(cell)
            
            # Author name
            elements.append(LayoutElement(
                type=ElementType.TEXT,
                content=author['name'],
                position=ElementPosition(
                    x=pos.x,
                    y=pos.y,
                    width=pos.width,
                    height=pos.height * 0.6
                ),
                style={'text_align': 'center', 'font_weight': 'bold'}
            ))
            
            # Affiliation superscript
            if 'affiliation_id' in author:
                elements.append(LayoutElement(
                    type=ElementType.TEXT,
                    content=author['affiliation_id'],
                    position=ElementPosition(
                        x=pos.x + pos.width * 0.9,
                        y=pos.y,
                        width=pos.width * 0.1,
                        height=pos.height * 0.3
                    ),
                    style={'font_size': 'small', 'vertical_align': 'super'}
                ))
        
        # Affiliation list
        aff_y = 0.65
        for i, affiliation in enumerate(affiliations):
            elements.append(LayoutElement(
                type=ElementType.TEXT,
                content=f"{i+1}{affiliation}",
                position=ElementPosition(x=0.1, y=aff_y + i*0.03, width=0.8, height=0.03),
                style={'text_align': 'center', 'font_size': 'small'}
            ))
        
        return elements
    
    def _create_author_list(self, authors: List[Dict[str, str]], 
                           affiliations: List[str]) -> List[LayoutElement]:
        """Create list layout for authors"""
        elements = []
        
        # Simple centered list
        y_pos = 0.40
        for author in authors:
            elements.append(LayoutElement(
                type=ElementType.TEXT,
                content=author['name'],
                position=ElementPosition(x=0.1, y=y_pos, width=0.8, height=0.05),
                style={'text_align': 'center'}
            ))
            y_pos += 0.05
        
        # Affiliations
        y_pos += 0.05
        for affiliation in affiliations:
            elements.append(LayoutElement(
                type=ElementType.TEXT,
                content=affiliation,
                position=ElementPosition(x=0.1, y=y_pos, width=0.8, height=0.04),
                style={'text_align': 'center', 'font_size': 'small', 'font_style': 'italic'}
            ))
            y_pos += 0.04
        
        return elements
    
    def create_research_question_layout(self, 
                                      question: str,
                                      context: Optional[str] = None,
                                      hypotheses: Optional[List[str]] = None) -> List[LayoutElement]:
        """Create layout for research question slide"""
        elements = []
        
        # Section header
        elements.append(LayoutElement(
            type=ElementType.TITLE,
            content="Research Question",
            position=ElementPosition(x=0.1, y=0.1, width=0.8, height=0.10),
            style={'text_align': 'center', 'font_weight': 'bold'}
        ))
        
        # Context (if provided)
        y_pos = 0.25
        if context:
            elements.append(LayoutElement(
                type=ElementType.TEXT,
                content=context,
                position=ElementPosition(x=0.1, y=y_pos, width=0.8, height=0.15),
                style={'text_align': 'justify'}
            ))
            y_pos += 0.20
        
        # Main research question - highlighted
        elements.append(LayoutElement(
            type=AcademicElementType.RESEARCH_QUESTION,
            content=question,
            position=ElementPosition(x=0.05, y=y_pos, width=0.9, height=0.15),
            style={
                'text_align': 'center',
                'font_size': 'large',
                'font_style': 'italic',
                'background_color': 'highlight',
                'padding': '20px',
                'border_radius': '10px'
            }
        ))
        
        # Hypotheses (if provided)
        if hypotheses:
            y_pos += 0.25
            elements.append(LayoutElement(
                type=ElementType.SUBTITLE,
                content="Hypotheses:",
                position=ElementPosition(x=0.1, y=y_pos, width=0.8, height=0.05),
                style={'font_weight': 'bold'}
            ))
            
            y_pos += 0.07
            for i, hypothesis in enumerate(hypotheses):
                elements.append(LayoutElement(
                    type=ElementType.BULLET_LIST,
                    content=f"H{i+1}: {hypothesis}",
                    position=ElementPosition(x=0.15, y=y_pos, width=0.75, height=0.05),
                    style={'list_style': 'none'}
                ))
                y_pos += 0.06
        
        return elements
    
    def create_methodology_layout(self,
                                 methods: List[Dict[str, Any]],
                                 flow_diagram: Optional[str] = None) -> List[LayoutElement]:
        """Create methodology slide layout"""
        elements = []
        
        # Title
        elements.append(LayoutElement(
            type=ElementType.TITLE,
            content="Methodology",
            position=ElementPosition(x=0.1, y=0.05, width=0.8, height=0.08),
            style={'text_align': 'center', 'font_weight': 'bold'}
        ))
        
        if flow_diagram:
            # Flow diagram takes left side
            elements.append(LayoutElement(
                type=ElementType.DIAGRAM,
                content=flow_diagram,
                position=ElementPosition(x=0.05, y=0.15, width=0.45, height=0.75)
            ))
            
            # Methods list on right
            x_start = 0.55
            width = 0.40
        else:
            # Methods take full width
            x_start = 0.05
            width = 0.90
        
        # Methods list
        y_pos = 0.15
        for method in methods:
            # Method name
            elements.append(LayoutElement(
                type=ElementType.SUBTITLE,
                content=method['name'],
                position=ElementPosition(x=x_start, y=y_pos, width=width, height=0.05),
                style={'font_weight': 'bold'}
            ))
            y_pos += 0.06
            
            # Method details
            if 'details' in method:
                for detail in method['details']:
                    elements.append(LayoutElement(
                        type=ElementType.BULLET_LIST,
                        content=detail,
                        position=ElementPosition(x=x_start + 0.02, y=y_pos, width=width - 0.02, height=0.04),
                        style={'font_size': 'small'}
                    ))
                    y_pos += 0.045
            
            y_pos += 0.02  # spacing between methods
        
        return elements
    
    def create_results_layout(self,
                            findings: List[Dict[str, Any]],
                            include_stats: bool = True) -> List[LayoutElement]:
        """Create results slide layout"""
        elements = []
        
        # Title
        elements.append(LayoutElement(
            type=ElementType.TITLE,
            content="Results",
            position=ElementPosition(x=0.1, y=0.05, width=0.8, height=0.08),
            style={'text_align': 'center', 'font_weight': 'bold'}
        ))
        
        # Organize findings
        y_pos = 0.15
        for finding in findings:
            if finding.get('type') == 'table':
                # Results table
                self._counters['table'] += 1
                elements.append(LayoutElement(
                    type=AcademicElementType.RESULTS_TABLE,
                    content=finding['data'],
                    position=ElementPosition(x=0.1, y=y_pos, width=0.8, height=0.25)
                ))
                
                # Table caption
                elements.append(LayoutElement(
                    type=ElementType.TEXT,
                    content=f"Table {self._counters['table']}: {finding.get('caption', '')}",
                    position=ElementPosition(x=0.1, y=y_pos + 0.26, width=0.8, height=0.03),
                    style={'font_size': 'small', 'font_style': 'italic', 'text_align': 'center'}
                ))
                y_pos += 0.32
                
            elif finding.get('type') == 'figure':
                # Figure with caption
                self._counters['figure'] += 1
                elements.extend(self.create_figure_with_caption(
                    figure_content=finding['data'],
                    caption=finding.get('caption', ''),
                    position=ElementPosition(x=0.1, y=y_pos, width=0.8, height=0.35)
                ))
                y_pos += 0.40
                
            else:
                # Text finding
                elements.append(LayoutElement(
                    type=ElementType.BULLET_LIST,
                    content=finding.get('text', ''),
                    position=ElementPosition(x=0.1, y=y_pos, width=0.8, height=0.05)
                ))
                
                # Include statistics if available
                if include_stats and 'stats' in finding:
                    elements.append(LayoutElement(
                        type=ElementType.TEXT,
                        content=finding['stats'],
                        position=ElementPosition(x=0.15, y=y_pos + 0.05, width=0.75, height=0.03),
                        style={'font_size': 'small', 'font_family': 'monospace'}
                    ))
                    y_pos += 0.03
                
                y_pos += 0.07
        
        return elements
    
    def create_figure_with_caption(self,
                                 figure_content: Any,
                                 caption: str,
                                 position: ElementPosition,
                                 label: Optional[str] = None) -> List[LayoutElement]:
        """Create figure with proper academic caption"""
        elements = []
        
        if label is None:
            self._counters['figure'] += 1
            label = f"Figure {self._counters['figure']}"
        
        # Figure
        figure_height = position.height * 0.9
        elements.append(LayoutElement(
            type=ElementType.IMAGE,
            content=figure_content,
            position=ElementPosition(
                x=position.x,
                y=position.y,
                width=position.width,
                height=figure_height
            )
        ))
        
        # Caption
        elements.append(LayoutElement(
            type=ElementType.TEXT,
            content=f"{label}: {caption}",
            position=ElementPosition(
                x=position.x,
                y=position.y + figure_height + 0.01,
                width=position.width,
                height=position.height * 0.1
            ),
            style={'font_size': 'small', 'text_align': 'center', 'font_style': 'italic'}
        ))
        
        return elements
    
    def create_equation_layout(self,
                             equation: str,
                             description: Optional[str] = None,
                             derivation: Optional[List[str]] = None) -> List[LayoutElement]:
        """Create layout for mathematical equations"""
        elements = []
        
        self._counters['equation'] += 1
        eq_number = self._counters['equation']
        
        # Description (if provided)
        y_pos = 0.2
        if description:
            elements.append(LayoutElement(
                type=ElementType.TEXT,
                content=description,
                position=ElementPosition(x=0.1, y=y_pos, width=0.8, height=0.05),
                style={'text_align': 'center'}
            ))
            y_pos += 0.08
        
        # Main equation - centered and larger
        elements.append(LayoutElement(
            type=AcademicElementType.EQUATION,
            content=equation,
            position=ElementPosition(x=0.1, y=y_pos, width=0.7, height=0.15),
            style={'text_align': 'center', 'font_size': 'x-large', 'font_family': 'math'}
        ))
        
        # Equation number (right-aligned)
        if self.style.equation_numbering:
            elements.append(LayoutElement(
                type=ElementType.TEXT,
                content=f"({eq_number})",
                position=ElementPosition(x=0.85, y=y_pos + 0.05, width=0.1, height=0.05),
                style={'text_align': 'right'}
            ))
        
        # Derivation steps (if provided)
        if derivation:
            y_pos += 0.20
            elements.append(LayoutElement(
                type=ElementType.SUBTITLE,
                content="Derivation:",
                position=ElementPosition(x=0.1, y=y_pos, width=0.8, height=0.05),
                style={'font_weight': 'bold'}
            ))
            
            y_pos += 0.06
            for step in derivation:
                elements.append(LayoutElement(
                    type=ElementType.TEXT,
                    content=step,
                    position=ElementPosition(x=0.15, y=y_pos, width=0.7, height=0.05),
                    style={'font_family': 'math'}
                ))
                y_pos += 0.06
        
        return elements
    
    def create_citation_element(self,
                              citations: List[str],
                              style: Optional[str] = None) -> LayoutElement:
        """Create properly formatted citation element"""
        citation_style = style or self.style.citation_style
        
        # Format citations according to style
        formatted_citations = []
        for citation in citations:
            # Simple formatting - in practice, would use proper citation formatter
            if citation_style == "APA":
                formatted_citations.append(f"[{len(formatted_citations)+1}] {citation}")
            elif citation_style == "IEEE":
                formatted_citations.append(f"[{len(formatted_citations)+1}] {citation}")
            else:
                formatted_citations.append(citation)
        
        return LayoutElement(
            type=ElementType.CITATION,
            content="\n".join(formatted_citations),
            position=ElementPosition(x=0.05, y=0.90, width=0.90, height=0.08),
            style={'font_size': 'x-small', 'text_align': 'left'}
        )
    
    def reset_counters(self):
        """Reset figure, table, equation counters"""
        self._counters = {
            'figure': 0,
            'table': 0,
            'equation': 0,
            'theorem': 0
        }