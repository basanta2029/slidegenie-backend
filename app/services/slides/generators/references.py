"""
References slide generator for academic presentations.
"""
from typing import Any, Dict, List, Optional
import re

from app.domain.schemas.generation import SlideContent
from app.services.slides.generators.base import BaseSlideGenerator, GeneratorInput


class ReferencesGenerator(BaseSlideGenerator):
    """Generator for reference/bibliography slides with proper formatting."""
    
    @property
    def section_type(self) -> str:
        """Return the section type."""
        return "references"
    
    @property
    def default_layout(self) -> str:
        """Return the default layout type."""
        return "references"
    
    def generate(self, input_data: GeneratorInput) -> List[SlideContent]:
        """
        Generate reference slide(s).
        
        Expected content structure:
        {
            "references": [
                {
                    "citation_key": "Smith2023",
                    "type": "article",
                    "authors": ["Smith, J.", "Doe, A."],
                    "title": "Novel Approach to Machine Learning",
                    "venue": "Journal of AI Research",
                    "year": 2023,
                    "volume": 15,
                    "pages": "123-145",
                    "doi": "10.1234/jair.2023.15.123",
                    "url": "https://example.com/paper",
                    "cited_count": 3,
                    "importance": "high"  # high, medium, low
                }
            ],
            "style": "ieee",  # ieee, apa, mla, chicago, acm
            "categorize": true,  # Group by type or importance
            "show_urls": false,
            "show_doi": true,
            "compact_mode": false,
            "max_per_slide": 15,
            "highlight_key_refs": true
        }
        """
        self.validate_input(input_data)
        
        content = input_data.content
        options = input_data.options
        
        references = content.get("references", [])
        if not references:
            return []
        
        style = content.get("style", options.citation_style)
        max_per_slide = content.get("max_per_slide", 15)
        
        slides = []
        
        # Sort and organize references
        organized_refs = self._organize_references(references, content)
        
        # Create slides based on organization
        if content.get("categorize") and len(organized_refs) > 1:
            # Create categorized slides
            for category, refs in organized_refs.items():
                category_slides = self._create_category_slides(
                    category, refs, style, max_per_slide, content
                )
                slides.extend(category_slides)
        else:
            # Create simple reference slides
            all_refs = []
            for refs_list in organized_refs.values():
                all_refs.extend(refs_list)
            
            ref_slides = self._create_reference_slides(
                all_refs, style, max_per_slide, content
            )
            slides.extend(ref_slides)
        
        return slides
    
    def _organize_references(
        self,
        references: List[Dict[str, Any]],
        content: Dict[str, Any]
    ) -> Dict[str, List[Dict[str, Any]]]:
        """Organize references by category or keep as single list."""
        if not content.get("categorize"):
            return {"all": sorted(references, key=self._sort_key)}
        
        # Categorize by type
        categories = {
            "Journal Articles": [],
            "Conference Papers": [],
            "Books": [],
            "Web Resources": [],
            "Other": []
        }
        
        for ref in references:
            ref_type = ref.get("type", "article").lower()
            
            if ref_type in ["article", "journal"]:
                categories["Journal Articles"].append(ref)
            elif ref_type in ["inproceedings", "conference", "proceedings"]:
                categories["Conference Papers"].append(ref)
            elif ref_type in ["book", "inbook", "incollection"]:
                categories["Books"].append(ref)
            elif ref_type in ["misc", "online", "webpage"]:
                categories["Web Resources"].append(ref)
            else:
                categories["Other"].append(ref)
        
        # Remove empty categories and sort within each
        organized = {}
        for category, refs in categories.items():
            if refs:
                organized[category] = sorted(refs, key=self._sort_key)
        
        return organized
    
    def _create_category_slides(
        self,
        category: str,
        references: List[Dict[str, Any]],
        style: str,
        max_per_slide: int,
        content: Dict[str, Any]
    ) -> List[SlideContent]:
        """Create slides for a specific reference category."""
        slides = []
        
        # Split into chunks if too many references
        for i in range(0, len(references), max_per_slide):
            chunk = references[i:i + max_per_slide]
            
            # Determine slide title
            if len(references) > max_per_slide:
                slide_num = (i // max_per_slide) + 1
                total_slides = (len(references) - 1) // max_per_slide + 1
                title = f"{category} ({slide_num}/{total_slides})"
            else:
                title = category
            
            slide = self._create_single_reference_slide(
                title, chunk, style, content
            )
            slides.append(slide)
        
        return slides
    
    def _create_reference_slides(
        self,
        references: List[Dict[str, Any]],
        style: str,
        max_per_slide: int,
        content: Dict[str, Any]
    ) -> List[SlideContent]:
        """Create reference slides without categorization."""
        slides = []
        
        for i in range(0, len(references), max_per_slide):
            chunk = references[i:i + max_per_slide]
            
            # Determine slide title
            if len(references) > max_per_slide:
                slide_num = (i // max_per_slide) + 1
                total_slides = (len(references) - 1) // max_per_slide + 1
                title = f"References ({slide_num}/{total_slides})"
            else:
                title = "References"
            
            slide = self._create_single_reference_slide(
                title, chunk, style, content
            )
            slides.append(slide)
        
        return slides
    
    def _create_single_reference_slide(
        self,
        title: str,
        references: List[Dict[str, Any]],
        style: str,
        content: Dict[str, Any]
    ) -> SlideContent:
        """Create a single reference slide."""
        body = []
        
        # Format references according to style
        ref_items = []
        for i, ref in enumerate(references):
            formatted_ref = self._format_reference(ref, style, content)
            
            # Add highlighting for key references
            is_key = (
                content.get("highlight_key_refs") and 
                ref.get("importance") == "high"
            )
            
            ref_items.append({
                "number": i + 1,
                "citation_key": ref.get("citation_key", ""),
                "formatted_text": formatted_ref,
                "is_key_reference": is_key,
                "cited_count": ref.get("cited_count", 0),
                "doi": ref.get("doi"),
                "url": ref.get("url"),
                "style": {
                    "highlight": is_key,
                    "fontSize": "small" if content.get("compact_mode") else "medium"
                }
            })
        
        body.append({
            "type": "reference_list",
            "references": ref_items,
            "style": {
                "citation_style": style,
                "show_numbers": True,
                "show_doi": content.get("show_doi", True),
                "show_urls": content.get("show_urls", False),
                "compact_mode": content.get("compact_mode", False),
                "line_spacing": "tight" if content.get("compact_mode") else "normal"
            }
        })
        
        # Add reference count
        if len(references) > 5:
            body.append({
                "type": "reference_count",
                "content": f"{len(references)} references",
                "style": {
                    "alignment": "right",
                    "fontSize": "small",
                    "color": "muted",
                    "marginTop": "small"
                }
            })
        
        return self.create_slide(
            title=title,
            body=body,
            layout=self.default_layout,
            speaker_notes=self._generate_references_notes(references),
            metadata={
                "section": "references",
                "reference_count": len(references),
                "citation_style": style
            }
        )
    
    def _format_reference(
        self,
        ref: Dict[str, Any],
        style: str,
        content: Dict[str, Any]
    ) -> str:
        """Format a single reference according to the specified style."""
        if style.lower() == "ieee":
            return self._format_ieee(ref)
        elif style.lower() == "apa":
            return self._format_apa(ref)
        elif style.lower() == "mla":
            return self._format_mla(ref)
        elif style.lower() == "chicago":
            return self._format_chicago(ref)
        elif style.lower() == "acm":
            return self._format_acm(ref)
        else:
            return self._format_ieee(ref)  # Default fallback
    
    def _format_ieee(self, ref: Dict[str, Any]) -> str:
        """Format reference in IEEE style."""
        parts = []
        
        # Authors
        authors = ref.get("authors", [])
        if authors:
            if len(authors) == 1:
                parts.append(self._format_author_ieee(authors[0]))
            elif len(authors) <= 3:
                formatted_authors = [self._format_author_ieee(auth) for auth in authors]
                parts.append(", ".join(formatted_authors[:-1]) + " and " + formatted_authors[-1])
            else:
                parts.append(self._format_author_ieee(authors[0]) + " et al.")
        
        # Title
        title = ref.get("title", "")
        if title:
            if ref.get("type") == "article":
                parts.append(f'"{title},"')
            else:
                parts.append(f"{title},")
        
        # Venue
        venue = ref.get("venue", "")
        if venue:
            if ref.get("type") == "article":
                parts.append(f"*{venue}*,")
            else:
                parts.append(f"in *{venue}*,")
        
        # Volume and pages
        volume = ref.get("volume")
        pages = ref.get("pages")
        if volume:
            vol_str = f"vol. {volume}"
            if pages:
                vol_str += f", pp. {pages},"
            else:
                vol_str += ","
            parts.append(vol_str)
        elif pages:
            parts.append(f"pp. {pages},")
        
        # Year
        year = ref.get("year")
        if year:
            parts.append(f"{year}.")
        
        # DOI
        doi = ref.get("doi")
        if doi:
            parts.append(f"doi: {doi}")
        
        return " ".join(parts)
    
    def _format_apa(self, ref: Dict[str, Any]) -> str:
        """Format reference in APA style."""
        parts = []
        
        # Authors
        authors = ref.get("authors", [])
        if authors:
            formatted_authors = [self._format_author_apa(auth) for auth in authors]
            if len(formatted_authors) == 1:
                parts.append(formatted_authors[0])
            else:
                parts.append(", ".join(formatted_authors[:-1]) + ", & " + formatted_authors[-1])
        
        # Year
        year = ref.get("year")
        if year:
            parts.append(f"({year}).")
        else:
            parts.append("(n.d.).")
        
        # Title
        title = ref.get("title", "")
        if title:
            if ref.get("type") == "article":
                parts.append(f"{title}.")
            else:
                parts.append(f"*{title}*.")
        
        # Venue
        venue = ref.get("venue", "")
        if venue:
            if ref.get("type") == "article":
                venue_str = f"*{venue}*"
                volume = ref.get("volume")
                pages = ref.get("pages")
                if volume:
                    venue_str += f", {volume}"
                if pages:
                    venue_str += f", {pages}"
                parts.append(venue_str + ".")
            else:
                parts.append(f"*{venue}*.")
        
        # DOI
        doi = ref.get("doi")
        if doi:
            parts.append(f"https://doi.org/{doi}")
        
        return " ".join(parts)
    
    def _format_mla(self, ref: Dict[str, Any]) -> str:
        """Format reference in MLA style."""
        parts = []
        
        # Authors
        authors = ref.get("authors", [])
        if authors:
            first_author = self._format_author_mla(authors[0], first=True)
            if len(authors) == 1:
                parts.append(first_author)
            elif len(authors) == 2:
                second_author = self._format_author_mla(authors[1])
                parts.append(f"{first_author}, and {second_author}")
            else:
                parts.append(f"{first_author}, et al.")
        
        # Title
        title = ref.get("title", "")
        if title:
            if ref.get("type") == "article":
                parts.append(f'"{title}."')
            else:
                parts.append(f"*{title}*.")
        
        # Venue
        venue = ref.get("venue", "")
        volume = ref.get("volume")
        year = ref.get("year")
        pages = ref.get("pages")
        
        if venue:
            venue_str = f"*{venue}*"
            if volume:
                venue_str += f", vol. {volume}"
            if year:
                venue_str += f", {year}"
            if pages:
                venue_str += f", pp. {pages}"
            parts.append(venue_str + ".")
        
        # URL/DOI
        doi = ref.get("doi")
        url = ref.get("url")
        if doi:
            parts.append(f"doi:{doi}")
        elif url:
            parts.append(f"Web. {url}")
        
        return " ".join(parts)
    
    def _format_chicago(self, ref: Dict[str, Any]) -> str:
        """Format reference in Chicago style."""
        parts = []
        
        # Authors
        authors = ref.get("authors", [])
        if authors:
            first_author = self._format_author_chicago(authors[0], first=True)
            if len(authors) == 1:
                parts.append(first_author)
            else:
                other_authors = [self._format_author_chicago(auth) for auth in authors[1:]]
                parts.append(f"{first_author}, " + ", ".join(other_authors))
        
        # Title
        title = ref.get("title", "")
        venue = ref.get("venue", "")
        
        if title and venue:
            if ref.get("type") == "article":
                parts.append(f'"{title}." *{venue}*')
            else:
                parts.append(f"*{title}*. {venue}")
        elif title:
            parts.append(f"*{title}*")
        
        # Publication details
        pub_details = []
        volume = ref.get("volume")
        if volume:
            pub_details.append(f"vol. {volume}")
        
        year = ref.get("year")
        if year:
            pub_details.append(f"{year}")
        
        pages = ref.get("pages")
        if pages:
            pub_details.append(f"{pages}")
        
        if pub_details:
            parts.append("(" + ", ".join(pub_details) + ")")
        
        # DOI
        doi = ref.get("doi")
        if doi:
            parts.append(f"https://doi.org/{doi}")
        
        return " ".join(parts) + "."
    
    def _format_acm(self, ref: Dict[str, Any]) -> str:
        """Format reference in ACM style."""
        parts = []
        
        # Authors
        authors = ref.get("authors", [])
        if authors:
            formatted_authors = [self._format_author_acm(auth) for auth in authors]
            parts.append(", ".join(formatted_authors))
        
        # Year
        year = ref.get("year")
        if year:
            parts.append(f"{year}.")
        
        # Title
        title = ref.get("title", "")
        if title:
            parts.append(f"{title}.")
        
        # Venue
        venue = ref.get("venue", "")
        if venue:
            if ref.get("type") == "inproceedings":
                parts.append(f"In *{venue}*")
            else:
                parts.append(f"*{venue}*")
        
        # Pages
        pages = ref.get("pages")
        if pages:
            parts.append(f"({pages})")
        
        # DOI
        doi = ref.get("doi")
        if doi:
            parts.append(f"DOI: https://doi.org/{doi}")
        
        return " ".join(parts)
    
    def _format_author_ieee(self, author: str) -> str:
        """Format author name for IEEE style."""
        return self._format_author_first_initial(author)
    
    def _format_author_apa(self, author: str) -> str:
        """Format author name for APA style."""
        return self._format_author_first_initial(author)
    
    def _format_author_mla(self, author: str, first: bool = False) -> str:
        """Format author name for MLA style."""
        if first:
            return self._format_author_last_first(author)
        else:
            return self._format_author_first_last(author)
    
    def _format_author_chicago(self, author: str, first: bool = False) -> str:
        """Format author name for Chicago style."""
        if first:
            return self._format_author_last_first(author)
        else:
            return self._format_author_first_last(author)
    
    def _format_author_acm(self, author: str) -> str:
        """Format author name for ACM style."""
        return self._format_author_first_last(author)
    
    def _format_author_first_initial(self, author: str) -> str:
        """Format: J. Smith"""
        if "," in author:
            # "Smith, John" -> "J. Smith"
            last, first = author.split(",", 1)
            first = first.strip()
            if first:
                return f"{first[0]}. {last.strip()}"
            return last.strip()
        else:
            # "John Smith" -> "J. Smith"
            parts = author.strip().split()
            if len(parts) >= 2:
                return f"{parts[0][0]}. {' '.join(parts[1:])}"
            return author
    
    def _format_author_last_first(self, author: str) -> str:
        """Format: Smith, John"""
        if "," in author:
            return author  # Already in correct format
        else:
            parts = author.strip().split()
            if len(parts) >= 2:
                return f"{parts[-1]}, {' '.join(parts[:-1])}"
            return author
    
    def _format_author_first_last(self, author: str) -> str:
        """Format: John Smith"""
        if "," in author:
            # "Smith, John" -> "John Smith"
            last, first = author.split(",", 1)
            return f"{first.strip()} {last.strip()}"
        else:
            return author  # Already in correct format
    
    def _sort_key(self, ref: Dict[str, Any]) -> tuple:
        """Generate sort key for reference."""
        # Sort by first author last name, then year, then title
        authors = ref.get("authors", [])
        first_author = authors[0] if authors else "zzz"
        
        # Extract last name
        if "," in first_author:
            last_name = first_author.split(",")[0].strip()
        else:
            parts = first_author.split()
            last_name = parts[-1] if parts else "zzz"
        
        year = ref.get("year", 9999)
        title = ref.get("title", "")
        
        return (last_name.lower(), year, title.lower())
    
    def _generate_references_notes(self, references: List[Dict[str, Any]]) -> str:
        """Generate speaker notes for reference slides."""
        notes = []
        
        notes.append(f"Here are the {len(references)} references for this section.")
        
        # Count key references
        key_refs = [r for r in references if r.get("importance") == "high"]
        if key_refs:
            notes.append(f"I've highlighted {len(key_refs)} particularly important references.")
        
        # Note high citation counts
        highly_cited = [r for r in references if r.get("cited_count", 0) > 100]
        if highly_cited:
            notes.append("Several of these are highly cited works in the field.")
        
        if len(references) > 10:
            notes.append("The full bibliography demonstrates the extensive related work in this area.")
        
        return " ".join(notes)