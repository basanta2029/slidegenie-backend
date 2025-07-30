"""
Outline/Agenda slide generator for academic presentations.
"""
from typing import Any, Dict, List, Optional

from app.domain.schemas.generation import SlideContent
from app.services.slides.generators.base import BaseSlideGenerator, GeneratorInput


class OutlineGenerator(BaseSlideGenerator):
    """Generator for outline/agenda slides."""
    
    @property
    def section_type(self) -> str:
        """Return the section type."""
        return "outline"
    
    @property
    def default_layout(self) -> str:
        """Return the default layout type."""
        return "outline"
    
    def generate(self, input_data: GeneratorInput) -> List[SlideContent]:
        """
        Generate outline/agenda slide(s).
        
        Expected content structure:
        {
            "sections": [
                {
                    "title": "Introduction",
                    "duration": 5,  # minutes
                    "subsections": ["Background", "Motivation", "Research Questions"],
                    "slide_range": [3, 8]
                },
                {
                    "title": "Methodology",
                    "duration": 10,
                    "subsections": ["Data Collection", "Analysis Framework"],
                    "slide_range": [9, 15]
                }
            ],
            "total_duration": 30,  # minutes
            "style": "numbered",  # numbered, bulleted, timeline
            "include_timing": true,
            "include_slide_numbers": true
        }
        """
        self.validate_input(input_data)
        
        content = input_data.content
        options = input_data.options
        
        slides = []
        
        # Determine outline style
        style = content.get("style", "numbered")
        sections = content.get("sections", [])
        
        if not sections:
            # Generate default outline if sections not provided
            sections = self._generate_default_sections(options.presentation_type)
        
        # Create outline slides based on style
        if style == "timeline":
            slides.extend(self._create_timeline_outline(sections, content, options))
        elif len(sections) > 8:
            # Split into multiple slides if too many sections
            slides.extend(self._create_multi_slide_outline(sections, content, options))
        else:
            slides.append(self._create_single_outline(sections, content, options))
        
        return slides
    
    def _create_single_outline(
        self,
        sections: List[Dict[str, Any]],
        content: Dict[str, Any],
        options: GeneratorInput
    ) -> SlideContent:
        """Create a single outline slide."""
        body = []
        
        # Main section list
        section_items = []
        for i, section in enumerate(sections):
            section_text = self._format_section_item(
                section, i + 1,
                content.get("style", "numbered"),
                content.get("include_timing", False),
                content.get("include_slide_numbers", False)
            )
            section_items.append(section_text)
        
        body.append({
            "type": "outline_list",
            "items": section_items,
            "style": {
                "listStyle": content.get("style", "numbered"),
                "spacing": "comfortable",
                "indentLevel": 0
            }
        })
        
        # Add total duration if specified
        if content.get("total_duration") and content.get("include_timing"):
            body.append({
                "type": "text",
                "content": f"Total Duration: {content['total_duration']} minutes",
                "style": {
                    "fontSize": "small",
                    "alignment": "right",
                    "marginTop": "medium",
                    "fontStyle": "italic"
                }
            })
        
        # Add navigation hint for interactive presentations
        if options.presentation_type in ["lecture", "seminar"]:
            body.append({
                "type": "text",
                "content": "Click on any section to jump directly to it",
                "style": {
                    "fontSize": "small",
                    "alignment": "center",
                    "marginTop": "large",
                    "color": "muted"
                }
            })
        
        speaker_notes = self._generate_outline_speaker_notes(sections, content)
        
        return self.create_slide(
            title=content.get("title", "Outline"),
            subtitle=content.get("subtitle", None),
            body=body,
            layout=self.default_layout,
            speaker_notes=speaker_notes,
            metadata={
                "is_outline_slide": True,
                "section_count": len(sections),
                "has_navigation": True
            }
        )
    
    def _create_multi_slide_outline(
        self,
        sections: List[Dict[str, Any]],
        content: Dict[str, Any],
        options: GeneratorInput
    ) -> List[SlideContent]:
        """Create multiple outline slides for long presentations."""
        slides = []
        sections_per_slide = 6
        
        # Overview slide
        overview = self._create_overview_slide(sections, content, options)
        slides.append(overview)
        
        # Detailed section slides
        for i in range(0, len(sections), sections_per_slide):
            section_chunk = sections[i:i + sections_per_slide]
            part_num = (i // sections_per_slide) + 1
            
            slide = self._create_single_outline(
                section_chunk,
                {**content, "title": f"Outline - Part {part_num}"},
                options
            )
            slides.append(slide)
        
        return slides
    
    def _create_timeline_outline(
        self,
        sections: List[Dict[str, Any]],
        content: Dict[str, Any],
        options: GeneratorInput
    ) -> List[SlideContent]:
        """Create a timeline-style outline."""
        body = []
        
        # Create timeline visualization
        timeline_data = []
        cumulative_time = 0
        
        for section in sections:
            duration = section.get("duration", 5)
            timeline_data.append({
                "title": section["title"],
                "start": cumulative_time,
                "duration": duration,
                "color": self._get_section_color(section["title"])
            })
            cumulative_time += duration
        
        body.append({
            "type": "timeline",
            "data": timeline_data,
            "total_duration": content.get("total_duration", cumulative_time),
            "style": {
                "orientation": "horizontal",
                "showLabels": True,
                "showDuration": content.get("include_timing", True)
            }
        })
        
        # Add section details below timeline
        if any(section.get("subsections") for section in sections):
            body.append({
                "type": "heading",
                "content": "Section Details",
                "level": 3,
                "style": {"marginTop": "large"}
            })
            
            details = []
            for section in sections:
                if section.get("subsections"):
                    details.append(f"{section['title']}: {', '.join(section['subsections'])}")
            
            body.append({
                "type": "bullet_list",
                "items": details,
                "style": {"fontSize": "small"}
            })
        
        return [self.create_slide(
            title="Presentation Timeline",
            body=body,
            layout="timeline",
            speaker_notes=self._generate_timeline_speaker_notes(sections, content)
        )]
    
    def _create_overview_slide(
        self,
        sections: List[Dict[str, Any]],
        content: Dict[str, Any],
        options: GeneratorInput
    ) -> SlideContent:
        """Create an overview slide for multi-part outlines."""
        body = []
        
        # Group sections into parts
        parts = []
        part_names = ["Introduction & Background", "Main Content", "Results & Conclusion"]
        sections_per_part = len(sections) // 3 + (1 if len(sections) % 3 else 0)
        
        for i, part_name in enumerate(part_names):
            start_idx = i * sections_per_part
            end_idx = min((i + 1) * sections_per_part, len(sections))
            if start_idx < len(sections):
                part_sections = sections[start_idx:end_idx]
                parts.append({
                    "name": part_name,
                    "sections": [s["title"] for s in part_sections],
                    "duration": sum(s.get("duration", 5) for s in part_sections)
                })
        
        # Create visual blocks for each part
        body.append({
            "type": "part_blocks",
            "parts": parts,
            "style": {
                "layout": "horizontal",
                "showDuration": content.get("include_timing", False)
            }
        })
        
        return self.create_slide(
            title="Presentation Overview",
            subtitle=f"{len(sections)} sections • {content.get('total_duration', 30)} minutes",
            body=body,
            layout="overview",
            speaker_notes="This presentation is organized into three main parts.",
            metadata={"is_overview_slide": True}
        )
    
    def _format_section_item(
        self,
        section: Dict[str, Any],
        number: int,
        style: str,
        include_timing: bool,
        include_slides: bool
    ) -> Dict[str, Any]:
        """Format a single section item for the outline."""
        # Build main text
        if style == "numbered":
            text = f"{number}. {section['title']}"
        elif style == "bulleted":
            text = section["title"]
        else:
            text = section["title"]
        
        # Add timing information
        if include_timing and section.get("duration"):
            text += f" ({section['duration']} min)"
        
        # Add slide range
        if include_slides and section.get("slide_range"):
            text += f" [slides {section['slide_range'][0]}-{section['slide_range'][1]}]"
        
        # Create item with subsections if present
        item = {
            "text": text,
            "level": 0,
            "style": {}
        }
        
        if section.get("subsections"):
            item["children"] = [
                {"text": subsection, "level": 1}
                for subsection in section["subsections"]
            ]
        
        # Add navigation link
        if section.get("slide_range"):
            item["link"] = {
                "type": "internal",
                "target": section["slide_range"][0]
            }
        
        return item
    
    def _generate_default_sections(self, presentation_type: str) -> List[Dict[str, Any]]:
        """Generate default sections based on presentation type."""
        if presentation_type == "conference":
            return [
                {"title": "Introduction", "duration": 3},
                {"title": "Related Work", "duration": 5},
                {"title": "Methodology", "duration": 7},
                {"title": "Results", "duration": 8},
                {"title": "Discussion", "duration": 5},
                {"title": "Conclusion", "duration": 2}
            ]
        elif presentation_type == "defense":
            return [
                {"title": "Introduction", "duration": 5},
                {"title": "Literature Review", "duration": 10},
                {"title": "Research Questions", "duration": 5},
                {"title": "Methodology", "duration": 15},
                {"title": "Results", "duration": 15},
                {"title": "Discussion", "duration": 10},
                {"title": "Contributions", "duration": 5},
                {"title": "Future Work", "duration": 5}
            ]
        elif presentation_type == "lecture":
            return [
                {"title": "Learning Objectives", "duration": 2},
                {"title": "Background", "duration": 10},
                {"title": "Core Concepts", "duration": 20},
                {"title": "Examples", "duration": 15},
                {"title": "Practice Problems", "duration": 10},
                {"title": "Summary", "duration": 3}
            ]
        else:  # seminar, workshop, etc.
            return [
                {"title": "Introduction", "duration": 5},
                {"title": "Main Topic", "duration": 20},
                {"title": "Discussion", "duration": 10},
                {"title": "Q&A", "duration": 10}
            ]
    
    def _get_section_color(self, section_title: str) -> str:
        """Get a color for the section based on its type."""
        color_map = {
            "introduction": "#4285F4",  # Blue
            "background": "#4285F4",
            "literature": "#EA4335",    # Red
            "related": "#EA4335",
            "method": "#34A853",        # Green
            "approach": "#34A853",
            "result": "#FBBC04",        # Yellow
            "finding": "#FBBC04",
            "discussion": "#9C27B0",    # Purple
            "conclusion": "#FF5722",    # Orange
            "future": "#795548"         # Brown
        }
        
        section_lower = section_title.lower()
        for keyword, color in color_map.items():
            if keyword in section_lower:
                return color
        
        return "#757575"  # Default grey
    
    def _generate_outline_speaker_notes(
        self,
        sections: List[Dict[str, Any]],
        content: Dict[str, Any]
    ) -> str:
        """Generate speaker notes for outline slides."""
        notes = []
        
        total_duration = content.get("total_duration", 30)
        notes.append(f"This presentation is structured into {len(sections)} main sections.")
        notes.append(f"The total presentation time is approximately {total_duration} minutes.")
        
        # Highlight key sections
        if any(s.get("duration", 0) > 10 for s in sections):
            long_sections = [s["title"] for s in sections if s.get("duration", 0) > 10]
            notes.append(f"The main focus areas are: {', '.join(long_sections)}.")
        
        # Add transition note
        notes.append("Let's begin with the first section.")
        
        return " ".join(notes)
    
    def _generate_timeline_speaker_notes(
        self,
        sections: List[Dict[str, Any]],
        content: Dict[str, Any]
    ) -> str:
        """Generate speaker notes for timeline slides."""
        notes = []
        
        notes.append("This timeline shows the flow and timing of our presentation.")
        
        # Calculate proportions
        total_time = sum(s.get("duration", 5) for s in sections)
        for section in sections:
            duration = section.get("duration", 5)
            percentage = (duration / total_time) * 100
            if percentage > 25:
                notes.append(f"Note that {section['title']} takes up {percentage:.0f}% of the presentation time.")
        
        notes.append("The timeline helps us stay on track and ensures we cover all topics adequately.")
        
        return " ".join(notes)