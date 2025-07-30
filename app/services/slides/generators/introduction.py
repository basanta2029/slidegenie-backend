"""
Introduction slide generator for academic presentations.
"""
from typing import Any, Dict, List, Optional

from app.domain.schemas.generation import SlideContent
from app.services.slides.generators.base import BaseSlideGenerator, GeneratorInput


class IntroductionGenerator(BaseSlideGenerator):
    """Generator for introduction slides including background, motivation, and problem statement."""
    
    @property
    def section_type(self) -> str:
        """Return the section type."""
        return "introduction"
    
    @property
    def default_layout(self) -> str:
        """Return the default layout type."""
        return "content"
    
    def generate(self, input_data: GeneratorInput) -> List[SlideContent]:
        """
        Generate introduction slide(s).
        
        Expected content structure:
        {
            "background": {
                "context": "General context of the research area",
                "importance": "Why this area is important",
                "current_state": "Current state of the field",
                "gaps": ["Gap 1", "Gap 2"],
                "statistics": [
                    {"value": "85%", "description": "of systems lack..."},
                    {"value": "$2.3B", "description": "market size"}
                ]
            },
            "motivation": {
                "problem_statement": "Clear statement of the problem",
                "why_now": "Why this problem needs solving now",
                "impact": "Potential impact of solving this problem",
                "beneficiaries": ["Researchers", "Industry", "Society"]
            },
            "research_questions": [
                "RQ1: How can we...",
                "RQ2: What is the impact of...",
                "RQ3: Can we develop..."
            ],
            "objectives": [
                "Objective 1: Design a novel...",
                "Objective 2: Evaluate the...",
                "Objective 3: Demonstrate..."
            ],
            "contributions": [
                "A novel framework for...",
                "Comprehensive evaluation showing...",
                "Open-source implementation"
            ],
            "thesis_statement": "In this work, we present..."
        }
        """
        self.validate_input(input_data)
        
        content = input_data.content
        options = input_data.options
        
        slides = []
        
        # Generate slides based on available content
        if content.get("background"):
            slides.extend(self._create_background_slides(content["background"], options))
        
        if content.get("motivation"):
            slides.append(self._create_motivation_slide(content["motivation"], options))
        
        if content.get("research_questions"):
            slides.append(self._create_research_questions_slide(content, options))
        
        if content.get("objectives"):
            slides.append(self._create_objectives_slide(content["objectives"], options))
        
        if content.get("contributions"):
            slides.append(self._create_contributions_slide(content["contributions"], options))
        
        # If minimal content, create a combined introduction slide
        if len(slides) == 0:
            slides.append(self._create_combined_intro_slide(content, options))
        
        return slides
    
    def _create_background_slides(
        self,
        background: Dict[str, Any],
        options: GeneratorInput
    ) -> List[SlideContent]:
        """Create background/context slides."""
        slides = []
        
        # Main background slide
        body = []
        
        if background.get("context"):
            body.append({
                "type": "text",
                "content": background["context"],
                "style": {"fontSize": "medium"}
            })
        
        if background.get("importance"):
            body.append({
                "type": "text",
                "content": background["importance"],
                "style": {"marginTop": "medium", "emphasis": True}
            })
        
        # Add statistics if available
        if background.get("statistics"):
            stat_items = []
            for stat in background["statistics"]:
                stat_items.append({
                    "type": "statistic",
                    "value": stat["value"],
                    "description": stat["description"],
                    "style": {"highlight": True}
                })
            
            body.append({
                "type": "statistics_row",
                "items": stat_items,
                "style": {"marginTop": "large"}
            })
        
        # Current state and gaps
        if background.get("current_state"):
            body.append({
                "type": "heading",
                "content": "Current State",
                "level": 3,
                "style": {"marginTop": "large"}
            })
            body.append({
                "type": "text",
                "content": background["current_state"]
            })
        
        if background.get("gaps"):
            body.append({
                "type": "heading",
                "content": "Research Gaps",
                "level": 3,
                "style": {"marginTop": "medium"}
            })
            body.append({
                "type": "bullet_list",
                "items": background["gaps"],
                "style": {"bulletStyle": "arrow"}
            })
        
        slides.append(self.create_slide(
            title="Background",
            body=body,
            speaker_notes=self._generate_background_notes(background),
            metadata={"section": "introduction", "subsection": "background"}
        ))
        
        # Create additional slide if there's a lot of content
        if len(body) > 5 and background.get("gaps"):
            gap_slide = self._create_research_gap_slide(background["gaps"], options)
            slides.append(gap_slide)
        
        return slides
    
    def _create_motivation_slide(
        self,
        motivation: Dict[str, Any],
        options: GeneratorInput
    ) -> SlideContent:
        """Create motivation slide."""
        body = []
        
        # Problem statement as main focus
        if motivation.get("problem_statement"):
            body.append({
                "type": "problem_box",
                "content": motivation["problem_statement"],
                "style": {
                    "backgroundColor": "error_light",
                    "borderColor": "error",
                    "padding": "large",
                    "fontSize": "medium"
                }
            })
        
        # Why now?
        if motivation.get("why_now"):
            body.append({
                "type": "heading",
                "content": "Why Address This Now?",
                "level": 3,
                "style": {"marginTop": "large"}
            })
            body.append({
                "type": "text",
                "content": motivation["why_now"]
            })
        
        # Impact and beneficiaries
        if motivation.get("impact") or motivation.get("beneficiaries"):
            impact_items = []
            
            if motivation.get("impact"):
                impact_items.append({
                    "title": "Potential Impact",
                    "content": motivation["impact"],
                    "icon": "impact"
                })
            
            if motivation.get("beneficiaries"):
                impact_items.append({
                    "title": "Who Benefits",
                    "content": ", ".join(motivation["beneficiaries"]),
                    "icon": "people"
                })
            
            body.append({
                "type": "impact_cards",
                "cards": impact_items,
                "style": {"marginTop": "large"}
            })
        
        return self.create_slide(
            title="Motivation",
            body=body,
            speaker_notes=self._generate_motivation_notes(motivation),
            metadata={"section": "introduction", "subsection": "motivation"}
        )
    
    def _create_research_questions_slide(
        self,
        content: Dict[str, Any],
        options: GeneratorInput
    ) -> SlideContent:
        """Create research questions slide."""
        body = []
        
        # Thesis statement if available
        if content.get("thesis_statement"):
            body.append({
                "type": "thesis_statement",
                "content": content["thesis_statement"],
                "style": {
                    "fontSize": "medium",
                    "fontStyle": "italic",
                    "alignment": "center",
                    "marginBottom": "large"
                }
            })
        
        # Research questions
        rq_items = []
        for i, question in enumerate(content["research_questions"]):
            rq_items.append({
                "type": "research_question",
                "number": i + 1,
                "question": question,
                "style": {"highlight": i == 0}  # Highlight first question
            })
        
        body.append({
            "type": "research_questions",
            "questions": rq_items,
            "style": {"spacing": "comfortable"}
        })
        
        # Add visual element suggestion
        if len(content["research_questions"]) > 2:
            body.append(
                self.create_visual_suggestion(
                    visual_type="diagram",
                    description="Research questions relationship diagram",
                    data={"questions": content["research_questions"]},
                    caption="Relationship between research questions"
                )
            )
        
        return self.create_slide(
            title="Research Questions",
            body=body,
            speaker_notes=self._generate_rq_notes(content["research_questions"]),
            metadata={"section": "introduction", "subsection": "research_questions"}
        )
    
    def _create_objectives_slide(
        self,
        objectives: List[str],
        options: GeneratorInput
    ) -> SlideContent:
        """Create objectives slide."""
        body = []
        
        # Format objectives with icons
        obj_items = []
        icons = ["target", "strategy", "implementation", "evaluation", "delivery"]
        
        for i, objective in enumerate(objectives):
            obj_items.append({
                "icon": icons[i % len(icons)],
                "text": objective,
                "style": {"indentLevel": 0}
            })
        
        body.append({
            "type": "objective_list",
            "items": obj_items,
            "style": {
                "listStyle": "numbered",
                "spacing": "comfortable",
                "showIcons": True
            }
        })
        
        # Add timeline if appropriate
        if options.presentation_type == "defense" and len(objectives) > 3:
            body.append({
                "type": "heading",
                "content": "Research Timeline",
                "level": 3,
                "style": {"marginTop": "large"}
            })
            body.append(
                self.create_visual_suggestion(
                    visual_type="timeline",
                    description="Project timeline showing when each objective will be addressed",
                    data={"objectives": objectives}
                )
            )
        
        return self.create_slide(
            title="Research Objectives",
            body=body,
            speaker_notes=self._generate_objectives_notes(objectives),
            metadata={"section": "introduction", "subsection": "objectives"}
        )
    
    def _create_contributions_slide(
        self,
        contributions: List[str],
        options: GeneratorInput
    ) -> SlideContent:
        """Create contributions slide."""
        body = []
        
        # Highlight main contributions
        contrib_items = []
        for i, contribution in enumerate(contributions):
            # Identify contribution type
            contrib_type = self._identify_contribution_type(contribution)
            
            contrib_items.append({
                "type": "contribution",
                "content": contribution,
                "category": contrib_type,
                "number": i + 1,
                "style": {
                    "highlight": i < 2,  # Highlight first two
                    "icon": self._get_contribution_icon(contrib_type)
                }
            })
        
        body.append({
            "type": "contribution_list",
            "items": contrib_items,
            "style": {
                "layout": "cards" if len(contributions) <= 4 else "list",
                "showNumbers": True,
                "showCategories": True
            }
        })
        
        # Add summary statement
        if len(contributions) > 3:
            body.append({
                "type": "text",
                "content": f"These {len(contributions)} contributions advance the state-of-the-art in multiple dimensions.",
                "style": {
                    "fontSize": "small",
                    "fontStyle": "italic",
                    "alignment": "center",
                    "marginTop": "large"
                }
            })
        
        return self.create_slide(
            title="Key Contributions",
            subtitle="What this work brings to the field",
            body=body,
            speaker_notes=self._generate_contributions_notes(contributions),
            metadata={"section": "introduction", "subsection": "contributions"}
        )
    
    def _create_research_gap_slide(
        self,
        gaps: List[str],
        options: GeneratorInput
    ) -> SlideContent:
        """Create a dedicated slide for research gaps."""
        body = []
        
        # Visual representation of gaps
        body.append(
            self.create_visual_suggestion(
                visual_type="gap_analysis",
                description="Visual showing current state vs desired state with gaps",
                data={"gaps": gaps}
            )
        )
        
        # Detailed gap list
        gap_items = []
        for gap in gaps:
            gap_items.append({
                "type": "gap_item",
                "content": gap,
                "style": {"bulletStyle": "warning"}
            })
        
        body.append({
            "type": "gap_list",
            "items": gap_items,
            "style": {"marginTop": "medium"}
        })
        
        return self.create_slide(
            title="Research Gaps",
            subtitle="What's missing in current approaches",
            body=body,
            speaker_notes="These gaps represent opportunities for significant contributions.",
            metadata={"section": "introduction", "subsection": "gaps"}
        )
    
    def _create_combined_intro_slide(
        self,
        content: Dict[str, Any],
        options: GeneratorInput
    ) -> SlideContent:
        """Create a combined introduction slide when content is minimal."""
        body = []
        
        # Add whatever content is available
        if content.get("problem_statement"):
            body.append({
                "type": "heading",
                "content": "Problem",
                "level": 3
            })
            body.append({
                "type": "text",
                "content": content["problem_statement"]
            })
        
        if content.get("approach"):
            body.append({
                "type": "heading",
                "content": "Our Approach",
                "level": 3,
                "style": {"marginTop": "medium"}
            })
            body.append({
                "type": "text",
                "content": content["approach"]
            })
        
        if content.get("goal"):
            body.append({
                "type": "heading",
                "content": "Goal",
                "level": 3,
                "style": {"marginTop": "medium"}
            })
            body.append({
                "type": "text",
                "content": content["goal"]
            })
        
        return self.create_slide(
            title="Introduction",
            body=body,
            speaker_notes="Let me introduce the problem we're addressing and our approach.",
            metadata={"section": "introduction"}
        )
    
    def _identify_contribution_type(self, contribution: str) -> str:
        """Identify the type of contribution."""
        lower_contrib = contribution.lower()
        
        if any(word in lower_contrib for word in ["framework", "model", "algorithm", "method"]):
            return "technical"
        elif any(word in lower_contrib for word in ["evaluation", "study", "analysis", "comparison"]):
            return "empirical"
        elif any(word in lower_contrib for word in ["tool", "system", "implementation", "software"]):
            return "practical"
        elif any(word in lower_contrib for word in ["theory", "proof", "formalization"]):
            return "theoretical"
        else:
            return "general"
    
    def _get_contribution_icon(self, contrib_type: str) -> str:
        """Get icon for contribution type."""
        icon_map = {
            "technical": "gear",
            "empirical": "chart",
            "practical": "code",
            "theoretical": "math",
            "general": "star"
        }
        return icon_map.get(contrib_type, "star")
    
    def _generate_background_notes(self, background: Dict[str, Any]) -> str:
        """Generate speaker notes for background slides."""
        notes = []
        
        notes.append("Let me start by providing some context for this work.")
        
        if background.get("statistics"):
            notes.append(f"As you can see from these statistics, this is a significant problem.")
        
        if background.get("gaps"):
            notes.append(f"Current approaches have {len(background['gaps'])} major limitations that we address.")
        
        return " ".join(notes)
    
    def _generate_motivation_notes(self, motivation: Dict[str, Any]) -> str:
        """Generate speaker notes for motivation slide."""
        notes = []
        
        notes.append("The core problem we're addressing is critical for several reasons.")
        
        if motivation.get("beneficiaries"):
            notes.append(f"Solving this will benefit {', '.join(motivation['beneficiaries'])}.")
        
        if motivation.get("why_now"):
            notes.append("The timing is particularly important because of recent developments.")
        
        return " ".join(notes)
    
    def _generate_rq_notes(self, questions: List[str]) -> str:
        """Generate speaker notes for research questions."""
        notes = []
        
        notes.append(f"Our research is guided by {len(questions)} key questions.")
        notes.append("Each question addresses a specific aspect of the problem.")
        
        if len(questions) > 1:
            notes.append("These questions are interrelated and build upon each other.")
        
        return " ".join(notes)
    
    def _generate_objectives_notes(self, objectives: List[str]) -> str:
        """Generate speaker notes for objectives."""
        notes = []
        
        notes.append(f"To answer our research questions, we have {len(objectives)} main objectives.")
        notes.append("Each objective represents a major component of the research.")
        
        return " ".join(notes)
    
    def _generate_contributions_notes(self, contributions: List[str]) -> str:
        """Generate speaker notes for contributions."""
        notes = []
        
        notes.append(f"This work makes {len(contributions)} key contributions to the field.")
        
        # Identify types
        types = set()
        for contrib in contributions:
            types.add(self._identify_contribution_type(contrib))
        
        if len(types) > 1:
            notes.append(f"These span {', '.join(types)} contributions.")
        
        notes.append("Let me highlight each contribution briefly.")
        
        return " ".join(notes)