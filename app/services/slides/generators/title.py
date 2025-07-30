"""
Title slide generator for academic presentations.
"""
from typing import Any, Dict, List, Optional

from app.domain.schemas.generation import SlideContent
from app.services.slides.generators.base import BaseSlideGenerator, GeneratorInput


class TitleSlideGenerator(BaseSlideGenerator):
    """Generator for title slides with academic formatting."""
    
    @property
    def section_type(self) -> str:
        """Return the section type."""
        return "title"
    
    @property
    def default_layout(self) -> str:
        """Return the default layout type."""
        return "title"
    
    def generate(self, input_data: GeneratorInput) -> List[SlideContent]:
        """
        Generate title slide(s).
        
        Expected content structure:
        {
            "title": "Presentation Title",
            "subtitle": "Optional Subtitle",
            "authors": [
                {
                    "name": "Author Name",
                    "affiliation": "Institution",
                    "email": "email@example.com",
                    "is_corresponding": true
                }
            ],
            "affiliations": [
                {
                    "id": "1",
                    "name": "University Name",
                    "department": "Department",
                    "address": "City, Country"
                }
            ],
            "conference": {
                "name": "Conference Name",
                "acronym": "CONF 2024",
                "date": "March 15-17, 2024",
                "location": "City, Country"
            },
            "metadata": {
                "doi": "10.1234/...",
                "funding": "Grant information",
                "date": "March 15, 2024"
            }
        }
        """
        self.validate_input(input_data)
        
        content = input_data.content
        options = input_data.options
        
        slides = []
        
        # Main title slide
        title_slide = self._create_main_title_slide(content, options)
        slides.append(title_slide)
        
        # Additional slides if needed
        if self._needs_author_slide(content):
            author_slide = self._create_author_slide(content, options)
            slides.append(author_slide)
        
        if self._needs_funding_slide(content):
            funding_slide = self._create_funding_slide(content, options)
            slides.append(funding_slide)
        
        return slides
    
    def _create_main_title_slide(self, content: Dict[str, Any], options: GeneratorInput) -> SlideContent:
        """Create the main title slide."""
        body = []
        
        # Format authors
        authors = content.get("authors", [])
        if authors:
            author_text = self._format_authors(authors, content.get("affiliations", []))
            body.append({
                "type": "authors",
                "content": author_text,
                "style": {
                    "fontSize": "medium",
                    "alignment": "center"
                }
            })
        
        # Add conference information
        conference = content.get("conference", {})
        if conference:
            conference_text = self._format_conference(conference)
            body.append({
                "type": "conference",
                "content": conference_text,
                "style": {
                    "fontSize": "small",
                    "alignment": "center",
                    "marginTop": "large"
                }
            })
        
        # Add date if no conference
        elif content.get("metadata", {}).get("date"):
            body.append({
                "type": "date",
                "content": content["metadata"]["date"],
                "style": {
                    "fontSize": "small",
                    "alignment": "center",
                    "marginTop": "large"
                }
            })
        
        # Add institutional logos if specified
        if content.get("logos"):
            body.append({
                "type": "logo_strip",
                "logos": content["logos"],
                "style": {
                    "position": "bottom",
                    "alignment": "center"
                }
            })
        
        speaker_notes = self._generate_speaker_notes(content, is_main=True)
        
        return self.create_slide(
            title=content.get("title", "Untitled Presentation"),
            subtitle=content.get("subtitle"),
            body=body,
            speaker_notes=speaker_notes,
            metadata={
                "is_title_slide": True,
                "presentation_type": options.presentation_type,
                "academic_level": options.academic_level
            }
        )
    
    def _create_author_slide(self, content: Dict[str, Any], options: GeneratorInput) -> SlideContent:
        """Create a separate slide for detailed author information."""
        authors = content.get("authors", [])
        affiliations = content.get("affiliations", [])
        
        body = []
        
        # Detailed author list
        author_list = []
        for author in authors:
            author_info = {
                "name": author["name"],
                "affiliation": author.get("affiliation", ""),
                "email": author.get("email", ""),
                "orcid": author.get("orcid", ""),
                "is_corresponding": author.get("is_corresponding", False),
                "contribution": author.get("contribution", "")
            }
            author_list.append(author_info)
        
        body.append({
            "type": "author_list",
            "authors": author_list,
            "style": {
                "format": "detailed",
                "includeEmail": True,
                "includeOrcid": True
            }
        })
        
        # Affiliation details
        if affiliations:
            body.append({
                "type": "affiliation_list",
                "affiliations": affiliations,
                "style": {
                    "format": "numbered",
                    "includeAddress": True
                }
            })
        
        return self.create_slide(
            title="Authors and Affiliations",
            body=body,
            layout="content",
            speaker_notes="Introduce all authors and their contributions to the work.",
            metadata={"is_author_slide": True}
        )
    
    def _create_funding_slide(self, content: Dict[str, Any], options: GeneratorInput) -> SlideContent:
        """Create a slide for funding and acknowledgments."""
        metadata = content.get("metadata", {})
        
        body = []
        
        # Funding information
        if metadata.get("funding"):
            body.append({
                "type": "heading",
                "content": "Funding",
                "level": 2
            })
            body.append({
                "type": "text",
                "content": metadata["funding"]
            })
        
        # Acknowledgments
        if metadata.get("acknowledgments"):
            body.append({
                "type": "heading",
                "content": "Acknowledgments",
                "level": 2
            })
            body.append({
                "type": "text",
                "content": metadata["acknowledgments"]
            })
        
        # Disclaimers
        if metadata.get("disclaimer"):
            body.append({
                "type": "text",
                "content": metadata["disclaimer"],
                "style": {"fontSize": "small", "fontStyle": "italic"}
            })
        
        return self.create_slide(
            title="Funding and Acknowledgments",
            body=body,
            layout="content",
            speaker_notes="Acknowledge funding sources and collaborators.",
            metadata={"is_funding_slide": True}
        )
    
    def _format_authors(self, authors: List[Dict[str, Any]], affiliations: List[Dict[str, Any]]) -> str:
        """Format author names with affiliations."""
        if not authors:
            return ""
        
        # Create affiliation mapping
        aff_map = {aff.get("id", str(i)): i + 1 for i, aff in enumerate(affiliations)}
        
        formatted_authors = []
        for author in authors:
            name = author["name"]
            
            # Add affiliation superscript
            if author.get("affiliation_ids"):
                aff_numbers = [str(aff_map.get(aid, "")) for aid in author["affiliation_ids"]]
                name += f"^{','.join(aff_numbers)}"
            elif author.get("affiliation"):
                # Find matching affiliation
                for aff_id, num in aff_map.items():
                    aff = affiliations[num - 1]
                    if aff.get("name") == author["affiliation"]:
                        name += f"^{num}"
                        break
            
            # Mark corresponding author
            if author.get("is_corresponding"):
                name += "*"
            
            formatted_authors.append(name)
        
        return ", ".join(formatted_authors)
    
    def _format_conference(self, conference: Dict[str, Any]) -> str:
        """Format conference information."""
        parts = []
        
        if conference.get("name"):
            parts.append(conference["name"])
        
        if conference.get("acronym"):
            parts.append(f"({conference['acronym']})")
        
        if conference.get("location"):
            parts.append(conference["location"])
        
        if conference.get("date"):
            parts.append(conference["date"])
        
        return " • ".join(parts)
    
    def _needs_author_slide(self, content: Dict[str, Any]) -> bool:
        """Determine if a separate author slide is needed."""
        authors = content.get("authors", [])
        
        # Need separate slide if:
        # - More than 5 authors
        # - Authors have detailed information (ORCID, contributions)
        # - Multiple complex affiliations
        
        if len(authors) > 5:
            return True
        
        if any(author.get("orcid") or author.get("contribution") for author in authors):
            return True
        
        if len(content.get("affiliations", [])) > 3:
            return True
        
        return False
    
    def _needs_funding_slide(self, content: Dict[str, Any]) -> bool:
        """Determine if a funding/acknowledgment slide is needed."""
        metadata = content.get("metadata", {})
        return bool(metadata.get("funding") or metadata.get("acknowledgments"))
    
    def _generate_speaker_notes(self, content: Dict[str, Any], is_main: bool = True) -> str:
        """Generate speaker notes for the title slide."""
        notes = []
        
        if is_main:
            notes.append(f"Welcome to my presentation on '{content.get('title', 'this topic')}'.")
            
            if content.get("conference"):
                conf = content["conference"]
                notes.append(f"I'm presenting at {conf.get('name', 'this conference')}.")
            
            # Count authors
            authors = content.get("authors", [])
            if len(authors) > 1:
                notes.append(f"This work was done in collaboration with {len(authors) - 1} co-authors.")
            
            # Note any special context
            if content.get("metadata", {}).get("presentation_type") == "defense":
                notes.append("This is my thesis defense presentation.")
            
        return " ".join(notes)