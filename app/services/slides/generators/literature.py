"""
Literature review slide generator for academic presentations.
"""
from typing import Any, Dict, List, Optional
from collections import defaultdict

from app.domain.schemas.generation import SlideContent
from app.services.slides.generators.base import BaseSlideGenerator, GeneratorInput


class LiteratureReviewGenerator(BaseSlideGenerator):
    """Generator for literature review/related work slides."""
    
    @property
    def section_type(self) -> str:
        """Return the section type."""
        return "literature_review"
    
    @property
    def default_layout(self) -> str:
        """Return the default layout type."""
        return "content"
    
    def generate(self, input_data: GeneratorInput) -> List[SlideContent]:
        """
        Generate literature review slide(s).
        
        Expected content structure:
        {
            "categories": [
                {
                    "name": "Machine Learning Approaches",
                    "works": [
                        {
                            "citation_key": "Smith2023",
                            "title": "Deep Learning for...",
                            "authors": ["Smith et al."],
                            "year": 2023,
                            "contribution": "Introduced novel architecture...",
                            "limitations": ["Limited to small datasets", "High computational cost"],
                            "relevance": "Directly related to our approach"
                        }
                    ]
                }
            ],
            "timeline": {
                "show": true,
                "start_year": 2018,
                "end_year": 2024
            },
            "comparison_table": {
                "criteria": ["Accuracy", "Speed", "Scalability"],
                "works": ["Smith2023", "Jones2022", "Our Work"]
            },
            "taxonomy": {
                "root": "Approaches",
                "branches": {
                    "Traditional": ["Rule-based", "Statistical"],
                    "Modern": ["Deep Learning", "Hybrid"]
                }
            },
            "key_insights": [
                "Most existing work focuses on...",
                "There is a clear gap in..."
            ]
        }
        """
        self.validate_input(input_data)
        
        content = input_data.content
        options = input_data.options
        
        slides = []
        
        # Overview slide if multiple categories
        if len(content.get("categories", [])) > 1:
            slides.append(self._create_overview_slide(content, options))
        
        # Category-specific slides
        for category in content.get("categories", []):
            category_slides = self._create_category_slides(category, content, options)
            slides.extend(category_slides)
        
        # Timeline slide if requested
        if content.get("timeline", {}).get("show"):
            slides.append(self._create_timeline_slide(content, options))
        
        # Comparison table slide
        if content.get("comparison_table"):
            slides.append(self._create_comparison_slide(content["comparison_table"], options))
        
        # Taxonomy slide
        if content.get("taxonomy"):
            slides.append(self._create_taxonomy_slide(content["taxonomy"], options))
        
        # Key insights/summary slide
        if content.get("key_insights"):
            slides.append(self._create_insights_slide(content["key_insights"], options))
        
        return slides
    
    def _create_overview_slide(
        self,
        content: Dict[str, Any],
        options: GeneratorInput
    ) -> SlideContent:
        """Create an overview slide for the literature review."""
        body = []
        
        # Categories overview
        categories = content.get("categories", [])
        
        # Visual representation of research areas
        body.append(
            self.create_visual_suggestion(
                visual_type="mind_map",
                description="Research areas and their relationships",
                data={
                    "categories": [cat["name"] for cat in categories],
                    "work_counts": [len(cat.get("works", [])) for cat in categories]
                }
            )
        )
        
        # Summary statistics
        total_works = sum(len(cat.get("works", [])) for cat in categories)
        year_range = self._get_year_range(content)
        
        stats = []
        stats.append({
            "value": str(total_works),
            "label": "Related Works Reviewed"
        })
        stats.append({
            "value": str(len(categories)),
            "label": "Research Areas"
        })
        if year_range:
            stats.append({
                "value": f"{year_range[0]}-{year_range[1]}",
                "label": "Time Span"
            })
        
        body.append({
            "type": "statistics_row",
            "items": stats,
            "style": {"marginTop": "large"}
        })
        
        # Category list with counts
        cat_items = []
        for cat in categories:
            work_count = len(cat.get("works", []))
            cat_items.append(f"{cat['name']} ({work_count} works)")
        
        body.append({
            "type": "bullet_list",
            "items": cat_items,
            "style": {"marginTop": "medium"}
        })
        
        return self.create_slide(
            title="Related Work Overview",
            body=body,
            speaker_notes=self._generate_overview_notes(content),
            metadata={"section": "literature_review", "subsection": "overview"}
        )
    
    def _create_category_slides(
        self,
        category: Dict[str, Any],
        content: Dict[str, Any],
        options: GeneratorInput
    ) -> List[SlideContent]:
        """Create slides for a specific category of related work."""
        slides = []
        works = category.get("works", [])
        
        # Group works if too many for one slide
        works_per_slide = 4
        
        for i in range(0, len(works), works_per_slide):
            work_chunk = works[i:i + works_per_slide]
            slide_num = (i // works_per_slide) + 1
            total_slides = (len(works) - 1) // works_per_slide + 1
            
            # Determine slide title
            if total_slides > 1:
                title = f"{category['name']} ({slide_num}/{total_slides})"
            else:
                title = category['name']
            
            body = self._format_works_for_slide(work_chunk, options)
            
            # Add category summary on last slide
            if slide_num == total_slides and category.get("summary"):
                body.append({
                    "type": "summary_box",
                    "content": category["summary"],
                    "style": {
                        "backgroundColor": "primary_light",
                        "marginTop": "large"
                    }
                })
            
            slides.append(self.create_slide(
                title=title,
                body=body,
                speaker_notes=self._generate_category_notes(category, work_chunk),
                metadata={
                    "section": "literature_review",
                    "subsection": category["name"],
                    "work_count": len(work_chunk)
                }
            ))
        
        return slides
    
    def _create_timeline_slide(
        self,
        content: Dict[str, Any],
        options: GeneratorInput
    ) -> SlideContent:
        """Create a timeline visualization of the literature."""
        body = []
        
        # Extract all works with years
        all_works = []
        for category in content.get("categories", []):
            for work in category.get("works", []):
                if work.get("year"):
                    all_works.append({
                        "citation_key": work["citation_key"],
                        "title": work.get("title", ""),
                        "year": work["year"],
                        "category": category["name"],
                        "milestone": work.get("is_milestone", False)
                    })
        
        # Sort by year
        all_works.sort(key=lambda x: x["year"])
        
        # Create timeline data
        timeline_data = {
            "works": all_works,
            "start_year": content.get("timeline", {}).get("start_year", min(w["year"] for w in all_works)),
            "end_year": content.get("timeline", {}).get("end_year", max(w["year"] for w in all_works)),
            "categories": list(set(w["category"] for w in all_works))
        }
        
        body.append({
            "type": "literature_timeline",
            "data": timeline_data,
            "style": {
                "orientation": "horizontal",
                "showMilestones": True,
                "groupByCategory": True
            }
        })
        
        # Add key developments text
        if content.get("timeline", {}).get("key_developments"):
            body.append({
                "type": "heading",
                "content": "Key Developments",
                "level": 3,
                "style": {"marginTop": "large"}
            })
            body.append({
                "type": "bullet_list",
                "items": content["timeline"]["key_developments"]
            })
        
        return self.create_slide(
            title="Evolution of the Field",
            subtitle=f"{timeline_data['start_year']} - {timeline_data['end_year']}",
            body=body,
            speaker_notes=self._generate_timeline_notes(all_works),
            metadata={"section": "literature_review", "subsection": "timeline"}
        )
    
    def _create_comparison_slide(
        self,
        comparison: Dict[str, Any],
        options: GeneratorInput
    ) -> SlideContent:
        """Create a comparison table slide."""
        body = []
        
        # Create comparison table
        headers = ["Approach"] + comparison["criteria"]
        rows = []
        
        for work in comparison["works"]:
            row = [work]
            for criterion in comparison["criteria"]:
                # Get the value for this criterion
                value = comparison.get("values", {}).get(work, {}).get(criterion, "—")
                row.append(value)
            rows.append(row)
        
        body.append({
            "type": "comparison_table",
            "headers": headers,
            "rows": rows,
            "style": {
                "highlightRow": len(rows) - 1 if "Our Work" in comparison["works"] else None,
                "colorScale": comparison.get("color_scale", False),
                "compactMode": len(rows) > 5
            }
        })
        
        # Add legend or notes if provided
        if comparison.get("legend"):
            body.append({
                "type": "legend",
                "items": comparison["legend"],
                "style": {"marginTop": "medium", "fontSize": "small"}
            })
        
        # Add key takeaways
        if comparison.get("takeaways"):
            body.append({
                "type": "heading",
                "content": "Key Takeaways",
                "level": 3,
                "style": {"marginTop": "large"}
            })
            body.append({
                "type": "bullet_list",
                "items": comparison["takeaways"],
                "style": {"bulletStyle": "checkmark"}
            })
        
        return self.create_slide(
            title="Comparison of Approaches",
            body=body,
            speaker_notes=self._generate_comparison_notes(comparison),
            metadata={"section": "literature_review", "subsection": "comparison"}
        )
    
    def _create_taxonomy_slide(
        self,
        taxonomy: Dict[str, Any],
        options: GeneratorInput
    ) -> SlideContent:
        """Create a taxonomy/classification slide."""
        body = []
        
        # Create hierarchical visualization
        body.append({
            "type": "taxonomy_tree",
            "data": taxonomy,
            "style": {
                "layout": "hierarchical",
                "showConnections": True,
                "nodeStyle": "rounded"
            }
        })
        
        # Add classification criteria if provided
        if taxonomy.get("criteria"):
            body.append({
                "type": "heading",
                "content": "Classification Criteria",
                "level": 3,
                "style": {"marginTop": "large"}
            })
            body.append({
                "type": "bullet_list",
                "items": taxonomy["criteria"]
            })
        
        # Position our work in the taxonomy
        if taxonomy.get("our_position"):
            body.append({
                "type": "highlight_box",
                "content": f"Our work: {taxonomy['our_position']}",
                "style": {
                    "backgroundColor": "success_light",
                    "marginTop": "medium"
                }
            })
        
        return self.create_slide(
            title="Taxonomy of Approaches",
            body=body,
            speaker_notes=self._generate_taxonomy_notes(taxonomy),
            metadata={"section": "literature_review", "subsection": "taxonomy"}
        )
    
    def _create_insights_slide(
        self,
        insights: List[str],
        options: GeneratorInput
    ) -> SlideContent:
        """Create a key insights/summary slide."""
        body = []
        
        # Format insights with emphasis
        insight_items = []
        for i, insight in enumerate(insights):
            # Identify insight type
            if "gap" in insight.lower() or "missing" in insight.lower():
                icon = "gap"
                style = "warning"
            elif "trend" in insight.lower() or "shift" in insight.lower():
                icon = "trend"
                style = "info"
            elif "consensus" in insight.lower() or "agree" in insight.lower():
                icon = "consensus"
                style = "success"
            else:
                icon = "insight"
                style = "primary"
            
            insight_items.append({
                "text": insight,
                "icon": icon,
                "style": style
            })
        
        body.append({
            "type": "insight_list",
            "items": insight_items,
            "style": {
                "spacing": "comfortable",
                "showIcons": True
            }
        })
        
        # Add transition to our work
        body.append({
            "type": "text",
            "content": "These insights motivate our approach, which addresses the identified gaps.",
            "style": {
                "fontSize": "medium",
                "fontStyle": "italic",
                "alignment": "center",
                "marginTop": "large",
                "emphasis": True
            }
        })
        
        return self.create_slide(
            title="Key Insights from Literature",
            body=body,
            speaker_notes=self._generate_insights_notes(insights),
            metadata={"section": "literature_review", "subsection": "insights"}
        )
    
    def _format_works_for_slide(
        self,
        works: List[Dict[str, Any]],
        options: GeneratorInput
    ) -> List[Dict[str, Any]]:
        """Format a list of works for display on a slide."""
        body = []
        
        for work in works:
            # Work entry
            work_content = []
            
            # Citation with title
            citation_text = f"[{work['citation_key']}] "
            if work.get("authors"):
                citation_text += f"{work['authors'][0]}"
                if work.get("year"):
                    citation_text += f" ({work['year']})"
            
            work_content.append({
                "type": "citation_header",
                "content": citation_text,
                "citation_key": work["citation_key"],
                "style": {"fontWeight": "bold"}
            })
            
            # Title if available
            if work.get("title"):
                work_content.append({
                    "type": "work_title",
                    "content": work["title"],
                    "style": {"fontStyle": "italic", "fontSize": "small"}
                })
            
            # Key contribution
            if work.get("contribution"):
                work_content.append({
                    "type": "contribution_text",
                    "content": f"✓ {work['contribution']}",
                    "style": {"color": "success", "marginLeft": "medium"}
                })
            
            # Limitations
            if work.get("limitations"):
                for limitation in work["limitations"][:2]:  # Show max 2 limitations
                    work_content.append({
                        "type": "limitation_text",
                        "content": f"✗ {limitation}",
                        "style": {"color": "error", "marginLeft": "medium", "fontSize": "small"}
                    })
            
            # Relevance to our work
            if work.get("relevance"):
                work_content.append({
                    "type": "relevance_text",
                    "content": f"→ {work['relevance']}",
                    "style": {"color": "primary", "marginLeft": "medium", "fontStyle": "italic"}
                })
            
            body.append({
                "type": "work_entry",
                "content": work_content,
                "style": {"marginBottom": "medium", "borderLeft": "3px solid #ccc", "paddingLeft": "medium"}
            })
        
        return body
    
    def _get_year_range(self, content: Dict[str, Any]) -> Optional[tuple]:
        """Get the year range from all works."""
        years = []
        for category in content.get("categories", []):
            for work in category.get("works", []):
                if work.get("year"):
                    years.append(work["year"])
        
        if years:
            return (min(years), max(years))
        return None
    
    def _generate_overview_notes(self, content: Dict[str, Any]) -> str:
        """Generate speaker notes for overview slide."""
        notes = []
        
        total_works = sum(len(cat.get("works", [])) for cat in content.get("categories", []))
        notes.append(f"I've reviewed {total_works} relevant works across {len(content.get('categories', []))} main areas.")
        
        notes.append("This comprehensive review reveals both the progress made and the gaps that remain.")
        
        return " ".join(notes)
    
    def _generate_category_notes(self, category: Dict[str, Any], works: List[Dict[str, Any]]) -> str:
        """Generate speaker notes for category slides."""
        notes = []
        
        notes.append(f"In the area of {category['name']}, several key works stand out.")
        
        # Highlight seminal works
        seminal = [w for w in works if w.get("is_seminal")]
        if seminal:
            notes.append(f"{seminal[0]['citation_key']} is particularly influential in this area.")
        
        # Note limitations pattern
        limitations = []
        for work in works:
            limitations.extend(work.get("limitations", []))
        
        if limitations:
            common_limitation = max(set(limitations), key=limitations.count)
            notes.append(f"A common limitation is {common_limitation.lower()}.")
        
        return " ".join(notes)
    
    def _generate_timeline_notes(self, works: List[Dict[str, Any]]) -> str:
        """Generate speaker notes for timeline slide."""
        notes = []
        
        notes.append("This timeline shows how the field has evolved over time.")
        
        # Identify periods of activity
        year_counts = defaultdict(int)
        for work in works:
            year_counts[work["year"]] += 1
        
        peak_year = max(year_counts, key=year_counts.get)
        notes.append(f"We see a peak of activity in {peak_year} with {year_counts[peak_year]} significant works.")
        
        return " ".join(notes)
    
    def _generate_comparison_notes(self, comparison: Dict[str, Any]) -> str:
        """Generate speaker notes for comparison slide."""
        notes = []
        
        notes.append(f"This comparison evaluates approaches across {len(comparison['criteria'])} key criteria.")
        
        if "Our Work" in comparison["works"]:
            notes.append("As highlighted, our approach addresses limitations of existing methods.")
        
        return " ".join(notes)
    
    def _generate_taxonomy_notes(self, taxonomy: Dict[str, Any]) -> str:
        """Generate speaker notes for taxonomy slide."""
        notes = []
        
        notes.append("This taxonomy helps us understand the landscape of approaches.")
        
        if taxonomy.get("our_position"):
            notes.append(f"Our work fits into the {taxonomy['our_position']} category.")
        
        return " ".join(notes)
    
    def _generate_insights_notes(self, insights: List[str]) -> str:
        """Generate speaker notes for insights slide."""
        notes = []
        
        notes.append(f"From this review, we can draw {len(insights)} key insights.")
        notes.append("These insights directly inform our research approach and contributions.")
        
        return " ".join(notes)