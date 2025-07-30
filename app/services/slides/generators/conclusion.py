"""
Conclusion slide generator for academic presentations.
"""
from typing import Any, Dict, List, Optional

from app.domain.schemas.generation import SlideContent
from app.services.slides.generators.base import BaseSlideGenerator, GeneratorInput


class ConclusionGenerator(BaseSlideGenerator):
    """Generator for conclusion slides including summary, future work, and final thoughts."""
    
    @property
    def section_type(self) -> str:
        """Return the section type."""
        return "conclusion"
    
    @property
    def default_layout(self) -> str:
        """Return the default layout type."""
        return "content"
    
    def generate(self, input_data: GeneratorInput) -> List[SlideContent]:
        """
        Generate conclusion slide(s).
        
        Expected content structure:
        {
            "summary": {
                "problem_addressed": "We addressed the challenge of...",
                "approach_summary": "Our approach combines X with Y to...",
                "key_results": [
                    "Achieved 95% accuracy on benchmark",
                    "Reduced computation time by 40%",
                    "Outperformed state-of-the-art methods"
                ],
                "main_contributions": [
                    "Novel architecture for...",
                    "Comprehensive evaluation showing...",
                    "Open-source implementation"
                ]
            },
            "achievements": {
                "research_questions_answered": [
                    {
                        "question": "RQ1: Can we improve accuracy?",
                        "answer": "Yes, we achieved 95% accuracy",
                        "evidence": "Demonstrated across 3 datasets"
                    }
                ],
                "objectives_met": [
                    {
                        "objective": "Design novel framework",
                        "status": "completed",
                        "outcome": "Framework shows 40% improvement"
                    }
                ],
                "hypotheses_validated": [
                    {
                        "hypothesis": "Combining X with Y improves performance",
                        "result": "confirmed",
                        "significance": "p < 0.001"
                    }
                ]
            },
            "impact": {
                "immediate": [
                    "Practitioners can now...",
                    "Researchers have new baseline"
                ],
                "long_term": [
                    "Could transform how we...",
                    "Opens path to..."
                ],
                "beneficiaries": ["Industry", "Academic community", "End users"]
            },
            "future_work": {
                "immediate_next_steps": [
                    "Extend to unsupervised learning",
                    "Evaluate on more diverse datasets"
                ],
                "long_term_vision": [
                    "Develop fully automated system",
                    "Apply to other domains"
                ],
                "open_questions": [
                    "How does this scale to very large datasets?",
                    "Can we reduce computational requirements further?"
                ]
            },
            "lessons_learned": [
                "Importance of thorough evaluation",
                "Value of combining different approaches",
                "Need for domain-specific adaptation"
            ],
            "call_to_action": {
                "researchers": "We encourage others to build upon this work",
                "practitioners": "Try our open-source implementation",
                "community": "Let's collaborate on the next challenges"
            },
            "acknowledgments": {
                "advisors": ["Prof. Smith", "Dr. Jones"],
                "collaborators": ["Research Team at University X"],
                "funding": "NSF Grant #12345",
                "resources": "Computational resources from XSEDE"
            },
            "final_message": "This work represents a significant step forward in addressing real-world challenges."
        }
        """
        self.validate_input(input_data)
        
        content = input_data.content
        options = input_data.options
        
        slides = []
        
        # Main summary slide
        if content.get("summary"):
            slides.append(self._create_summary_slide(content["summary"], options))
        
        # Achievements slide (research questions, objectives)
        if content.get("achievements"):
            slides.append(self._create_achievements_slide(content["achievements"], options))
        
        # Impact slide
        if content.get("impact"):
            slides.append(self._create_impact_slide(content["impact"], options))
        
        # Future work slide
        if content.get("future_work"):
            slides.append(self._create_future_work_slide(content["future_work"], options))
        
        # Lessons learned (if significant)
        if content.get("lessons_learned") and len(content["lessons_learned"]) > 2:
            slides.append(self._create_lessons_slide(content["lessons_learned"], options))
        
        # Call to action / closing slide
        closing_content = {
            "call_to_action": content.get("call_to_action"),
            "final_message": content.get("final_message"),
            "contact_info": content.get("contact_info")
        }
        slides.append(self._create_closing_slide(closing_content, options))
        
        # Acknowledgments slide (often separate)
        if content.get("acknowledgments"):
            slides.append(self._create_acknowledgments_slide(content["acknowledgments"], options))
        
        return slides
    
    def _create_summary_slide(
        self,
        summary: Dict[str, Any],
        options: GeneratorInput
    ) -> SlideContent:
        """Create main summary slide."""
        body = []
        
        # Problem statement recap
        if summary.get("problem_addressed"):
            body.append({
                "type": "problem_recap",
                "content": summary["problem_addressed"],
                "style": {
                    "backgroundColor": "grey_light",
                    "padding": "medium",
                    "fontSize": "medium"
                }
            })
        
        # Approach summary
        if summary.get("approach_summary"):
            body.append({
                "type": "heading",
                "content": "Our Approach",
                "level": 3,
                "style": {"marginTop": "large"}
            })
            body.append({
                "type": "text",
                "content": summary["approach_summary"],
                "style": {"fontSize": "medium"}
            })
        
        # Key results highlights
        if summary.get("key_results"):
            body.append({
                "type": "heading",
                "content": "Key Results",
                "level": 3,
                "style": {"marginTop": "large", "color": "success"}
            })
            
            result_items = []
            for result in summary["key_results"]:
                result_items.append({
                    "text": result,
                    "icon": "check",
                    "style": {"color": "success", "emphasis": True}
                })
            
            body.append({
                "type": "result_list",
                "items": result_items,
                "style": {"bulletStyle": "success"}
            })
        
        # Main contributions
        if summary.get("main_contributions"):
            body.append({
                "type": "heading",
                "content": "Contributions",
                "level": 3,
                "style": {"marginTop": "large", "color": "primary"}
            })
            
            contribution_items = []
            for i, contribution in enumerate(summary["main_contributions"]):
                contribution_items.append({
                    "number": i + 1,
                    "text": contribution,
                    "style": {"highlight": i < 2}  # Highlight top 2
                })
            
            body.append({
                "type": "contribution_list",
                "items": contribution_items,
                "style": {
                    "showNumbers": True,
                    "spacing": "comfortable"
                }
            })
        
        return self.create_slide(
            title="Summary",
            subtitle="What we accomplished",
            body=body,
            speaker_notes=self._generate_summary_notes(summary),
            metadata={"section": "conclusion", "subsection": "summary"}
        )
    
    def _create_achievements_slide(
        self,
        achievements: Dict[str, Any],
        options: GeneratorInput
    ) -> SlideContent:
        """Create achievements slide."""
        body = []
        
        # Research questions answered
        if achievements.get("research_questions_answered"):
            body.append({
                "type": "heading",
                "content": "Research Questions Answered",
                "level": 3,
                "style": {"color": "primary"}
            })
            
            for rq in achievements["research_questions_answered"]:
                body.append({
                    "type": "qa_item",
                    "question": rq["question"],
                    "answer": rq["answer"],
                    "evidence": rq.get("evidence", ""),
                    "style": {
                        "showEvidence": bool(rq.get("evidence")),
                        "marginBottom": "medium"
                    }
                })
        
        # Objectives met
        if achievements.get("objectives_met"):
            body.append({
                "type": "heading",
                "content": "Objectives Achieved",
                "level": 3,
                "style": {
                    "marginTop": "large",
                    "color": "success"
                }
            })
            
            obj_items = []
            for obj in achievements["objectives_met"]:
                status_icon = {
                    "completed": "check",
                    "partial": "partial",
                    "ongoing": "progress"
                }.get(obj.get("status", "completed"), "check")
                
                obj_items.append({
                    "objective": obj["objective"],
                    "status": obj.get("status", "completed"),
                    "outcome": obj.get("outcome", ""),
                    "icon": status_icon
                })
            
            body.append({
                "type": "objective_checklist",
                "items": obj_items,
                "style": {"showOutcomes": True}
            })
        
        # Hypotheses validated
        if achievements.get("hypotheses_validated"):
            body.append({
                "type": "heading",
                "content": "Hypotheses Tested",
                "level": 3,
                "style": {
                    "marginTop": "large",
                    "color": "info"
                }
            })
            
            for hyp in achievements["hypotheses_validated"]:
                result_color = {
                    "confirmed": "success",
                    "rejected": "error",
                    "partial": "warning"
                }.get(hyp.get("result", "confirmed"), "success")
                
                body.append({
                    "type": "hypothesis_result",
                    "hypothesis": hyp["hypothesis"],
                    "result": hyp.get("result", "confirmed"),
                    "significance": hyp.get("significance", ""),
                    "style": {
                        "color": result_color,
                        "showSignificance": bool(hyp.get("significance"))
                    }
                })
        
        return self.create_slide(
            title="Achievements",
            subtitle="Goals accomplished",
            body=body,
            speaker_notes=self._generate_achievements_notes(achievements),
            metadata={"section": "conclusion", "subsection": "achievements"}
        )
    
    def _create_impact_slide(
        self,
        impact: Dict[str, Any],
        options: GeneratorInput
    ) -> SlideContent:
        """Create impact slide."""
        body = []
        
        # Impact visualization
        if impact.get("immediate") or impact.get("long_term"):
            body.append(
                self.create_visual_suggestion(
                    visual_type="impact_timeline",
                    description="Timeline showing immediate and long-term impact",
                    data={
                        "immediate": impact.get("immediate", []),
                        "long_term": impact.get("long_term", [])
                    }
                )
            )
        
        # Immediate impact
        if impact.get("immediate"):
            body.append({
                "type": "impact_section",
                "title": "Immediate Impact",
                "items": impact["immediate"],
                "style": {
                    "color": "success",
                    "icon": "immediate",
                    "timeframe": "Now"
                }
            })
        
        # Long-term impact
        if impact.get("long_term"):
            body.append({
                "type": "impact_section",
                "title": "Long-term Vision",
                "items": impact["long_term"],
                "style": {
                    "color": "primary",
                    "icon": "future",
                    "timeframe": "Future",
                    "marginTop": "medium"
                }
            })
        
        # Beneficiaries
        if impact.get("beneficiaries"):
            body.append({
                "type": "heading",
                "content": "Who Benefits",
                "level": 3,
                "style": {"marginTop": "large"}
            })
            
            beneficiary_items = []
            for beneficiary in impact["beneficiaries"]:
                beneficiary_items.append({
                    "name": beneficiary,
                    "icon": self._get_beneficiary_icon(beneficiary)
                })
            
            body.append({
                "type": "beneficiary_grid",
                "items": beneficiary_items,
                "style": {"layout": "horizontal"}
            })
        
        return self.create_slide(
            title="Impact",
            subtitle="Making a difference",
            body=body,
            speaker_notes=self._generate_impact_notes(impact),
            metadata={"section": "conclusion", "subsection": "impact"}
        )
    
    def _create_future_work_slide(
        self,
        future_work: Dict[str, Any],
        options: GeneratorInput
    ) -> SlideContent:
        """Create future work slide."""
        body = []
        
        # Future work roadmap
        if future_work.get("immediate_next_steps") and future_work.get("long_term_vision"):
            body.append(
                self.create_visual_suggestion(
                    visual_type="roadmap",
                    description="Research roadmap showing next steps and long-term goals",
                    data={
                        "immediate": future_work["immediate_next_steps"],
                        "long_term": future_work["long_term_vision"]
                    }
                )
            )
        
        # Immediate next steps
        if future_work.get("immediate_next_steps"):
            body.append({
                "type": "future_section",
                "title": "Next Steps",
                "items": future_work["immediate_next_steps"],
                "style": {
                    "color": "warning",
                    "timeframe": "6-12 months",
                    "priority": "high"
                }
            })
        
        # Long-term vision
        if future_work.get("long_term_vision"):
            body.append({
                "type": "future_section",
                "title": "Long-term Vision",
                "items": future_work["long_term_vision"],
                "style": {
                    "color": "info",
                    "timeframe": "2-5 years",
                    "priority": "medium",
                    "marginTop": "medium"
                }
            })
        
        # Open questions
        if future_work.get("open_questions"):
            body.append({
                "type": "heading",
                "content": "Open Questions",
                "level": 3,
                "style": {"marginTop": "large"}
            })
            
            question_items = []
            for question in future_work["open_questions"]:
                question_items.append({
                    "question": question,
                    "difficulty": "high",  # Could be parameterized
                    "icon": "question"
                })
            
            body.append({
                "type": "question_list",
                "items": question_items,
                "style": {"bulletStyle": "question"}
            })
        
        # Collaboration opportunities
        if future_work.get("collaboration_opportunities"):
            body.append({
                "type": "collaboration_box",
                "content": "We welcome collaborations to address these challenges together!",
                "opportunities": future_work["collaboration_opportunities"],
                "style": {
                    "backgroundColor": "primary_light",
                    "marginTop": "large"
                }
            })
        
        return self.create_slide(
            title="Future Work",
            subtitle="Where do we go from here?",
            body=body,
            speaker_notes=self._generate_future_work_notes(future_work),
            metadata={"section": "conclusion", "subsection": "future_work"}
        )
    
    def _create_lessons_slide(
        self,
        lessons: List[str],
        options: GeneratorInput
    ) -> SlideContent:
        """Create lessons learned slide."""
        body = []
        
        # Lessons with icons
        lesson_items = []
        for lesson in lessons:
            lesson_type = self._classify_lesson(lesson)
            lesson_items.append({
                "lesson": lesson,
                "type": lesson_type,
                "icon": self._get_lesson_icon(lesson_type)
            })
        
        body.append({
            "type": "lesson_list",
            "items": lesson_items,
            "style": {
                "showIcons": True,
                "spacing": "comfortable"
            }
        })
        
        # Meta-lesson
        body.append({
            "type": "meta_lesson",
            "content": "Research is an iterative process of discovery, refinement, and validation.",
            "style": {
                "alignment": "center",
                "fontStyle": "italic",
                "marginTop": "large",
                "emphasis": True
            }
        })
        
        return self.create_slide(
            title="Lessons Learned",
            subtitle="What this journey taught us",
            body=body,
            speaker_notes=self._generate_lessons_notes(lessons),
            metadata={"section": "conclusion", "subsection": "lessons"}
        )
    
    def _create_closing_slide(
        self,
        closing_content: Dict[str, Any],
        options: GeneratorInput
    ) -> SlideContent:
        """Create final closing slide."""
        body = []
        
        # Final message
        if closing_content.get("final_message"):
            body.append({
                "type": "final_message",
                "content": closing_content["final_message"],
                "style": {
                    "fontSize": "large",
                    "fontWeight": "bold",
                    "alignment": "center",
                    "color": "primary",
                    "marginBottom": "large"
                }
            })
        
        # Call to action sections
        if closing_content.get("call_to_action"):
            cta = closing_content["call_to_action"]
            
            # For researchers
            if cta.get("researchers"):
                body.append({
                    "type": "cta_section",
                    "audience": "Researchers",
                    "message": cta["researchers"],
                    "icon": "research",
                    "style": {"color": "primary"}
                })
            
            # For practitioners
            if cta.get("practitioners"):
                body.append({
                    "type": "cta_section",
                    "audience": "Practitioners",
                    "message": cta["practitioners"],
                    "icon": "application",
                    "style": {
                        "color": "success",
                        "marginTop": "medium"
                    }
                })
            
            # For community
            if cta.get("community"):
                body.append({
                    "type": "cta_section",
                    "audience": "Community",
                    "message": cta["community"],
                    "icon": "community",
                    "style": {
                        "color": "info",
                        "marginTop": "medium"
                    }
                })
        
        # Contact information
        if closing_content.get("contact_info"):
            contact = closing_content["contact_info"]
            body.append({
                "type": "contact_info",
                "email": contact.get("email"),
                "website": contact.get("website"),
                "social": contact.get("social", {}),
                "style": {
                    "alignment": "center",
                    "marginTop": "large",
                    "fontSize": "small"
                }
            })
        
        # Thank you
        body.append({
            "type": "thank_you",
            "content": "Thank you for your attention!",
            "style": {
                "fontSize": "large",
                "fontWeight": "bold",
                "alignment": "center",
                "marginTop": "large",
                "color": "primary"
            }
        })
        
        return self.create_slide(
            title="Conclusion",
            body=body,
            layout="closing",
            speaker_notes=self._generate_closing_notes(closing_content),
            metadata={"section": "conclusion", "subsection": "closing"}
        )
    
    def _create_acknowledgments_slide(
        self,
        acknowledgments: Dict[str, Any],
        options: GeneratorInput
    ) -> SlideContent:
        """Create acknowledgments slide."""
        body = []
        
        # Advisors/supervisors
        if acknowledgments.get("advisors"):
            body.append({
                "type": "ack_section",
                "title": "Advisors",
                "people": acknowledgments["advisors"],
                "icon": "mentor",
                "style": {"color": "primary"}
            })
        
        # Collaborators
        if acknowledgments.get("collaborators"):
            body.append({
                "type": "ack_section",
                "title": "Collaborators",
                "people": acknowledgments["collaborators"],
                "icon": "team",
                "style": {
                    "color": "success",
                    "marginTop": "medium"
                }
            })
        
        # Funding
        if acknowledgments.get("funding"):
            body.append({
                "type": "funding_section",
                "title": "Funding Support",
                "content": acknowledgments["funding"],
                "icon": "funding",
                "style": {
                    "color": "info",
                    "marginTop": "medium"
                }
            })
        
        # Resources
        if acknowledgments.get("resources"):
            body.append({
                "type": "resources_section",
                "title": "Resources",
                "content": acknowledgments["resources"],
                "icon": "resources",
                "style": {
                    "color": "warning",
                    "marginTop": "medium"
                }
            })
        
        # Special thanks
        if acknowledgments.get("special_thanks"):
            body.append({
                "type": "special_thanks",
                "content": acknowledgments["special_thanks"],
                "style": {
                    "alignment": "center",
                    "fontStyle": "italic",
                    "marginTop": "large"
                }
            })
        
        return self.create_slide(
            title="Acknowledgments",
            body=body,
            speaker_notes="I'd like to thank everyone who made this work possible.",
            metadata={"section": "conclusion", "subsection": "acknowledgments"}
        )
    
    def _get_beneficiary_icon(self, beneficiary: str) -> str:
        """Get icon for beneficiary type."""
        beneficiary_lower = beneficiary.lower()
        
        if "industry" in beneficiary_lower or "business" in beneficiary_lower:
            return "industry"
        elif "research" in beneficiary_lower or "academic" in beneficiary_lower:
            return "research"
        elif "user" in beneficiary_lower or "people" in beneficiary_lower:
            return "users"
        elif "society" in beneficiary_lower or "public" in beneficiary_lower:
            return "society"
        else:
            return "group"
    
    def _classify_lesson(self, lesson: str) -> str:
        """Classify lesson type."""
        lesson_lower = lesson.lower()
        
        if "method" in lesson_lower or "approach" in lesson_lower:
            return "methodological"
        elif "evaluation" in lesson_lower or "experiment" in lesson_lower:
            return "experimental"
        elif "collaboration" in lesson_lower or "team" in lesson_lower:
            return "collaborative"
        elif "data" in lesson_lower:
            return "data"
        else:
            return "general"
    
    def _get_lesson_icon(self, lesson_type: str) -> str:
        """Get icon for lesson type."""
        icon_map = {
            "methodological": "method",
            "experimental": "experiment",
            "collaborative": "team",
            "data": "data",
            "general": "lightbulb"
        }
        return icon_map.get(lesson_type, "lightbulb")
    
    def _generate_summary_notes(self, summary: Dict[str, Any]) -> str:
        """Generate speaker notes for summary slide."""
        notes = []
        
        notes.append("Let me summarize what we've accomplished in this work.")
        
        if summary.get("key_results"):
            notes.append(f"We achieved {len(summary['key_results'])} key results.")
        
        if summary.get("main_contributions"):
            notes.append(f"Our {len(summary['main_contributions'])} main contributions advance the field.")
        
        return " ".join(notes)
    
    def _generate_achievements_notes(self, achievements: Dict[str, Any]) -> str:
        """Generate speaker notes for achievements slide."""
        notes = []
        
        notes.append("We successfully achieved our research goals.")
        
        if achievements.get("research_questions_answered"):
            rq_count = len(achievements["research_questions_answered"])
            notes.append(f"We answered all {rq_count} research questions we set out to address.")
        
        if achievements.get("objectives_met"):
            notes.append("Our objectives were met comprehensively.")
        
        return " ".join(notes)
    
    def _generate_impact_notes(self, impact: Dict[str, Any]) -> str:
        """Generate speaker notes for impact slide."""
        notes = []
        
        notes.append("The impact of this work extends beyond our immediate results.")
        
        if impact.get("immediate"):
            notes.append("We already see immediate applications and benefits.")
        
        if impact.get("long_term"):
            notes.append("The long-term potential is even more exciting.")
        
        return " ".join(notes)
    
    def _generate_future_work_notes(self, future_work: Dict[str, Any]) -> str:
        """Generate speaker notes for future work slide."""
        notes = []
        
        notes.append("This work opens up many exciting avenues for future research.")
        
        if future_work.get("immediate_next_steps"):
            notes.append("We have clear next steps to continue this line of work.")
        
        if future_work.get("open_questions"):
            notes.append("There are still important questions to explore.")
        
        return " ".join(notes)
    
    def _generate_lessons_notes(self, lessons: List[str]) -> str:
        """Generate speaker notes for lessons slide."""
        notes = []
        
        notes.append("This research journey taught us valuable lessons.")
        notes.append(f"I want to share {len(lessons)} key insights from our experience.")
        notes.append("These lessons will guide our future research.")
        
        return " ".join(notes)
    
    def _generate_closing_notes(self, closing_content: Dict[str, Any]) -> str:
        """Generate speaker notes for closing slide."""
        notes = []
        
        notes.append("In conclusion, this work makes significant contributions to the field.")
        
        if closing_content.get("call_to_action"):
            notes.append("I encourage you to engage with our work and build upon it.")
        
        notes.append("Thank you for your attention, and I look forward to your questions.")
        
        return " ".join(notes)