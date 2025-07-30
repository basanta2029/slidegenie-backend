"""
Discussion slide generator for academic presentations.
"""
from typing import Any, Dict, List, Optional

from app.domain.schemas.generation import SlideContent
from app.services.slides.generators.base import BaseSlideGenerator, GeneratorInput


class DiscussionGenerator(BaseSlideGenerator):
    """Generator for discussion slides including implications, limitations, and analysis."""
    
    @property
    def section_type(self) -> str:
        """Return the section type."""
        return "discussion"
    
    @property
    def default_layout(self) -> str:
        """Return the default layout type."""
        return "content"
    
    def generate(self, input_data: GeneratorInput) -> List[SlideContent]:
        """
        Generate discussion slide(s).
        
        Expected content structure:
        {
            "interpretation": {
                "main_findings": [
                    "Finding 1: Our method achieves...",
                    "Finding 2: The approach scales..."
                ],
                "explanations": [
                    {
                        "finding": "95% accuracy improvement",
                        "explanation": "This improvement is due to...",
                        "evidence": "As shown in Figure 3..."
                    }
                ],
                "unexpected_results": [
                    {
                        "result": "Lower performance on Dataset C",
                        "possible_reasons": ["Reason 1", "Reason 2"],
                        "investigation": "Further analysis revealed..."
                    }
                ]
            },
            "implications": {
                "theoretical": [
                    "Supports theory X",
                    "Challenges assumption Y"
                ],
                "practical": [
                    "Enables new applications in...",
                    "Reduces computational cost by..."
                ],
                "broader_impact": [
                    "Could transform how we...",
                    "Opens possibilities for..."
                ]
            },
            "limitations": [
                {
                    "limitation": "Limited to supervised learning",
                    "severity": "moderate",
                    "workaround": "Could be extended to unsupervised...",
                    "future_work": "Plan to address in next phase"
                }
            ],
            "comparison_with_literature": {
                "agreements": [
                    {
                        "work": "Smith et al. 2023",
                        "agreement": "Confirms their finding about...",
                        "our_contribution": "We extend this by..."
                    }
                ],
                "disagreements": [
                    {
                        "work": "Jones et al. 2022",
                        "disagreement": "Our results contradict...",
                        "possible_reasons": ["Different datasets", "Updated methodology"]
                    }
                ]
            },
            "threats_to_validity": {
                "internal": [
                    "Potential selection bias in data",
                    "Limited hyperparameter tuning"
                ],
                "external": [
                    "Results may not generalize to...",
                    "Tested only on English text"
                ],
                "construct": [
                    "Metrics may not capture all aspects",
                    "Human evaluation was limited"
                ]
            },
            "robustness_analysis": {
                "sensitivity": {
                    "parameters": ["Learning rate", "Batch size"],
                    "results": "Method is robust to parameter changes"
                },
                "edge_cases": [
                    {
                        "case": "Very small datasets",
                        "performance": "Degraded but acceptable",
                        "mitigation": "Data augmentation helps"
                    }
                ]
            },
            "related_work_positioning": {
                "our_position": "First to combine X with Y",
                "advantages": ["Advantage 1", "Advantage 2"],
                "trade_offs": [
                    {
                        "aspect": "Speed vs Accuracy",
                        "our_choice": "Prioritized accuracy",
                        "justification": "Critical for this application"
                    }
                ]
            }
        }
        """
        self.validate_input(input_data)
        
        content = input_data.content
        options = input_data.options
        
        slides = []
        
        # Results interpretation
        if content.get("interpretation"):
            slides.extend(self._create_interpretation_slides(content["interpretation"], options))
        
        # Implications
        if content.get("implications"):
            slides.append(self._create_implications_slide(content["implications"], options))
        
        # Limitations
        if content.get("limitations"):
            slides.append(self._create_limitations_slide(content["limitations"], options))
        
        # Comparison with literature
        if content.get("comparison_with_literature"):
            slides.append(self._create_literature_comparison_slide(content["comparison_with_literature"], options))
        
        # Threats to validity
        if content.get("threats_to_validity"):
            slides.append(self._create_validity_slide(content["threats_to_validity"], options))
        
        # Robustness analysis
        if content.get("robustness_analysis"):
            slides.append(self._create_robustness_slide(content["robustness_analysis"], options))
        
        # Positioning relative to related work
        if content.get("related_work_positioning"):
            slides.append(self._create_positioning_slide(content["related_work_positioning"], options))
        
        return slides
    
    def _create_interpretation_slides(
        self,
        interpretation: Dict[str, Any],
        options: GeneratorInput
    ) -> List[SlideContent]:
        """Create slides for results interpretation."""
        slides = []
        
        # Main findings slide
        if interpretation.get("main_findings"):
            body = []
            
            # List main findings
            findings_items = []
            for i, finding in enumerate(interpretation["main_findings"]):
                findings_items.append({
                    "number": i + 1,
                    "finding": finding,
                    "style": {"emphasis": True}
                })
            
            body.append({
                "type": "findings_list",
                "findings": findings_items,
                "style": {
                    "showNumbers": True,
                    "spacing": "comfortable",
                    "bulletStyle": "star"
                }
            })
            
            # Add visual summary if appropriate
            if len(interpretation["main_findings"]) > 2:
                body.append(
                    self.create_visual_suggestion(
                        visual_type="findings_summary",
                        description="Visual summary of key findings",
                        data={"findings": interpretation["main_findings"]}
                    )
                )
            
            slides.append(self.create_slide(
                title="Key Findings",
                subtitle="What our results tell us",
                body=body,
                speaker_notes=self._generate_findings_notes(interpretation["main_findings"]),
                metadata={"section": "discussion", "subsection": "findings"}
            ))
        
        # Detailed explanations
        if interpretation.get("explanations"):
            for explanation in interpretation["explanations"]:
                explanation_slide = self._create_explanation_slide(explanation, options)
                slides.append(explanation_slide)
        
        # Unexpected results
        if interpretation.get("unexpected_results"):
            for unexpected in interpretation["unexpected_results"]:
                unexpected_slide = self._create_unexpected_slide(unexpected, options)
                slides.append(unexpected_slide)
        
        return slides
    
    def _create_explanation_slide(
        self,
        explanation: Dict[str, Any],
        options: GeneratorInput
    ) -> SlideContent:
        """Create slide explaining a specific finding."""
        body = []
        
        # Finding statement
        body.append({
            "type": "finding_statement",
            "content": explanation["finding"],
            "style": {
                "fontSize": "large",
                "fontWeight": "bold",
                "color": "primary",
                "alignment": "center",
                "marginBottom": "large"
            }
        })
        
        # Explanation
        if explanation.get("explanation"):
            body.append({
                "type": "heading",
                "content": "Why This Happened",
                "level": 3
            })
            body.append({
                "type": "text",
                "content": explanation["explanation"],
                "style": {"fontSize": "medium"}
            })
        
        # Supporting evidence
        if explanation.get("evidence"):
            body.append({
                "type": "heading",
                "content": "Evidence",
                "level": 3,
                "style": {"marginTop": "medium"}
            })
            body.append({
                "type": "evidence_box",
                "content": explanation["evidence"],
                "style": {
                    "backgroundColor": "info_light",
                    "borderLeft": "4px solid info",
                    "icon": "chart"
                }
            })
        
        # Mechanism or theory
        if explanation.get("mechanism"):
            body.append({
                "type": "heading",
                "content": "Underlying Mechanism",
                "level": 3,
                "style": {"marginTop": "medium"}
            })
            body.append({
                "type": "mechanism_diagram",
                "content": explanation["mechanism"],
                "style": {"showDiagram": True}
            })
        
        return self.create_slide(
            title="Understanding the Result",
            body=body,
            speaker_notes=self._generate_explanation_notes(explanation),
            metadata={"section": "discussion", "subsection": "explanation"}
        )
    
    def _create_unexpected_slide(
        self,
        unexpected: Dict[str, Any],
        options: GeneratorInput
    ) -> SlideContent:
        """Create slide for unexpected results."""
        body = []
        
        # Unexpected result highlight
        body.append({
            "type": "unexpected_box",
            "content": unexpected["result"],
            "style": {
                "backgroundColor": "warning_light",
                "borderColor": "warning",
                "icon": "question",
                "fontSize": "medium"
            }
        })
        
        # Possible reasons
        if unexpected.get("possible_reasons"):
            body.append({
                "type": "heading",
                "content": "Possible Explanations",
                "level": 3,
                "style": {"marginTop": "large"}
            })
            body.append({
                "type": "bullet_list",
                "items": unexpected["possible_reasons"],
                "style": {"bulletStyle": "question"}
            })
        
        # Investigation results
        if unexpected.get("investigation"):
            body.append({
                "type": "heading",
                "content": "Further Investigation",
                "level": 3,
                "style": {"marginTop": "medium"}
            })
            body.append({
                "type": "investigation_box",
                "content": unexpected["investigation"],
                "style": {
                    "backgroundColor": "success_light",
                    "icon": "magnifying_glass"
                }
            })
        
        # Lessons learned
        if unexpected.get("lessons"):
            body.append({
                "type": "lessons_list",
                "lessons": unexpected["lessons"],
                "style": {"marginTop": "medium"}
            })
        
        return self.create_slide(
            title="Unexpected Results",
            body=body,
            speaker_notes=self._generate_unexpected_notes(unexpected),
            metadata={"section": "discussion", "subsection": "unexpected"}
        )
    
    def _create_implications_slide(
        self,
        implications: Dict[str, Any],
        options: GeneratorInput
    ) -> SlideContent:
        """Create implications slide."""
        body = []
        
        # Theoretical implications
        if implications.get("theoretical"):
            body.append({
                "type": "implication_section",
                "title": "Theoretical Implications",
                "icon": "theory",
                "items": implications["theoretical"],
                "style": {"color": "primary"}
            })
        
        # Practical implications
        if implications.get("practical"):
            body.append({
                "type": "implication_section",
                "title": "Practical Implications",
                "icon": "application",
                "items": implications["practical"],
                "style": {
                    "color": "success",
                    "marginTop": "medium"
                }
            })
        
        # Broader impact
        if implications.get("broader_impact"):
            body.append({
                "type": "implication_section",
                "title": "Broader Impact",
                "icon": "globe",
                "items": implications["broader_impact"],
                "style": {
                    "color": "info",
                    "marginTop": "medium",
                    "emphasis": True
                }
            })
        
        # Visual representation
        if len([k for k in implications.keys() if implications.get(k)]) > 1:
            body.append(
                self.create_visual_suggestion(
                    visual_type="impact_diagram",
                    description="Diagram showing theoretical, practical, and broader impacts",
                    data=implications
                )
            )
        
        return self.create_slide(
            title="Implications of Our Work",
            body=body,
            speaker_notes=self._generate_implications_notes(implications),
            metadata={"section": "discussion", "subsection": "implications"}
        )
    
    def _create_limitations_slide(
        self,
        limitations: List[Dict[str, Any]],
        options: GeneratorInput
    ) -> SlideContent:
        """Create limitations slide."""
        body = []
        
        # Group by severity
        severe_limits = [l for l in limitations if l.get("severity") == "severe"]
        moderate_limits = [l for l in limitations if l.get("severity") == "moderate"]
        minor_limits = [l for l in limitations if l.get("severity") == "minor"]
        
        for category, limits, color in [
            ("Critical Limitations", severe_limits, "error"),
            ("Moderate Limitations", moderate_limits, "warning"),
            ("Minor Limitations", minor_limits, "info")
        ]:
            if limits:
                body.append({
                    "type": "limitation_category",
                    "title": category,
                    "color": color,
                    "style": {"marginTop": "medium" if body else None}
                })
                
                for limitation in limits:
                    limit_item = {
                        "limitation": limitation["limitation"],
                        "severity": limitation.get("severity", "moderate"),
                        "workaround": limitation.get("workaround"),
                        "future_work": limitation.get("future_work")
                    }
                    
                    body.append({
                        "type": "limitation_item",
                        "data": limit_item,
                        "style": {
                            "showWorkaround": bool(limitation.get("workaround")),
                            "showFuture": bool(limitation.get("future_work"))
                        }
                    })
        
        # Honesty statement
        body.append({
            "type": "honesty_note",
            "content": "We believe transparency about limitations strengthens our contribution.",
            "style": {
                "alignment": "center",
                "fontStyle": "italic",
                "marginTop": "large",
                "color": "muted"
            }
        })
        
        return self.create_slide(
            title="Limitations",
            subtitle="Honest assessment of our approach",
            body=body,
            speaker_notes=self._generate_limitations_notes(limitations),
            metadata={"section": "discussion", "subsection": "limitations"}
        )
    
    def _create_literature_comparison_slide(
        self,
        comparison: Dict[str, Any],
        options: GeneratorInput
    ) -> SlideContent:
        """Create literature comparison slide."""
        body = []
        
        # Agreements with literature
        if comparison.get("agreements"):
            body.append({
                "type": "heading",
                "content": "Our Results Confirm",
                "level": 3,
                "style": {"color": "success"}
            })
            
            for agreement in comparison["agreements"]:
                body.append({
                    "type": "agreement_item",
                    "work": agreement["work"],
                    "agreement": agreement["agreement"],
                    "our_contribution": agreement.get("our_contribution", ""),
                    "style": {"icon": "check", "color": "success"}
                })
        
        # Disagreements with literature
        if comparison.get("disagreements"):
            body.append({
                "type": "heading",
                "content": "Our Results Differ From",
                "level": 3,
                "style": {
                    "color": "warning",
                    "marginTop": "large"
                }
            })
            
            for disagreement in comparison["disagreements"]:
                body.append({
                    "type": "disagreement_item",
                    "work": disagreement["work"],
                    "disagreement": disagreement["disagreement"],
                    "possible_reasons": disagreement.get("possible_reasons", []),
                    "style": {"icon": "alert", "color": "warning"}
                })
        
        # Novel findings
        if comparison.get("novel_findings"):
            body.append({
                "type": "heading",
                "content": "Novel Findings",
                "level": 3,
                "style": {
                    "color": "primary",
                    "marginTop": "large"
                }
            })
            body.append({
                "type": "bullet_list",
                "items": comparison["novel_findings"],
                "style": {"bulletStyle": "star", "color": "primary"}
            })
        
        return self.create_slide(
            title="Relation to Literature",
            body=body,
            speaker_notes=self._generate_literature_comparison_notes(comparison),
            metadata={"section": "discussion", "subsection": "literature_comparison"}
        )
    
    def _create_validity_slide(
        self,
        threats: Dict[str, Any],
        options: GeneratorInput
    ) -> SlideContent:
        """Create threats to validity slide."""
        body = []
        
        # Internal validity
        if threats.get("internal"):
            body.append({
                "type": "validity_section",
                "title": "Internal Validity",
                "description": "Factors within our study that might affect results",
                "threats": threats["internal"],
                "color": "error",
                "icon": "internal"
            })
        
        # External validity
        if threats.get("external"):
            body.append({
                "type": "validity_section",
                "title": "External Validity",
                "description": "Generalizability of our findings",
                "threats": threats["external"],
                "color": "warning",
                "icon": "external",
                "style": {"marginTop": "medium"}
            })
        
        # Construct validity
        if threats.get("construct"):
            body.append({
                "type": "validity_section",
                "title": "Construct Validity",
                "description": "Whether we measured what we intended",
                "threats": threats["construct"],
                "color": "info",
                "icon": "construct",
                "style": {"marginTop": "medium"}
            })
        
        # Mitigation strategies
        if threats.get("mitigations"):
            body.append({
                "type": "heading",
                "content": "Mitigation Strategies",
                "level": 3,
                "style": {"marginTop": "large", "color": "success"}
            })
            body.append({
                "type": "mitigation_list",
                "strategies": threats["mitigations"],
                "style": {"bulletStyle": "shield"}
            })
        
        return self.create_slide(
            title="Threats to Validity",
            subtitle="Critical assessment of our methodology",
            body=body,
            speaker_notes=self._generate_validity_notes(threats),
            metadata={"section": "discussion", "subsection": "validity"}
        )
    
    def _create_robustness_slide(
        self,
        robustness: Dict[str, Any],
        options: GeneratorInput
    ) -> SlideContent:
        """Create robustness analysis slide."""
        body = []
        
        # Sensitivity analysis
        if robustness.get("sensitivity"):
            sensitivity = robustness["sensitivity"]
            body.append({
                "type": "heading",
                "content": "Parameter Sensitivity",
                "level": 3
            })
            
            body.append({
                "type": "sensitivity_analysis",
                "parameters": sensitivity.get("parameters", []),
                "results": sensitivity.get("results", ""),
                "style": {"showChart": True}
            })
        
        # Edge cases
        if robustness.get("edge_cases"):
            body.append({
                "type": "heading",
                "content": "Edge Case Analysis",
                "level": 3,
                "style": {"marginTop": "large"}
            })
            
            for case in robustness["edge_cases"]:
                body.append({
                    "type": "edge_case_item",
                    "case": case["case"],
                    "performance": case["performance"],
                    "mitigation": case.get("mitigation", ""),
                    "style": {"showMitigation": bool(case.get("mitigation"))}
                })
        
        # Stress testing
        if robustness.get("stress_tests"):
            body.append({
                "type": "heading",
                "content": "Stress Testing",
                "level": 3,
                "style": {"marginTop": "large"}
            })
            
            body.append({
                "type": "stress_test_results",
                "tests": robustness["stress_tests"],
                "style": {"layout": "grid"}
            })
        
        return self.create_slide(
            title="Robustness Analysis",
            subtitle="How well does our method handle variations?",
            body=body,
            speaker_notes=self._generate_robustness_notes(robustness),
            metadata={"section": "discussion", "subsection": "robustness"}
        )
    
    def _create_positioning_slide(
        self,
        positioning: Dict[str, Any],
        options: GeneratorInput
    ) -> SlideContent:
        """Create positioning slide."""
        body = []
        
        # Our unique position
        if positioning.get("our_position"):
            body.append({
                "type": "position_statement",
                "content": positioning["our_position"],
                "style": {
                    "fontSize": "large",
                    "fontWeight": "bold",
                    "color": "primary",
                    "alignment": "center",
                    "marginBottom": "large"
                }
            })
        
        # Advantages over existing work
        if positioning.get("advantages"):
            body.append({
                "type": "heading",
                "content": "Our Advantages",
                "level": 3,
                "style": {"color": "success"}
            })
            body.append({
                "type": "advantage_list",
                "advantages": positioning["advantages"],
                "style": {
                    "bulletStyle": "plus",
                    "color": "success"
                }
            })
        
        # Trade-offs we made
        if positioning.get("trade_offs"):
            body.append({
                "type": "heading",
                "content": "Design Trade-offs",
                "level": 3,
                "style": {
                    "marginTop": "large",
                    "color": "info"
                }
            })
            
            for trade_off in positioning["trade_offs"]:
                body.append({
                    "type": "trade_off_item",
                    "aspect": trade_off["aspect"],
                    "our_choice": trade_off["our_choice"],
                    "justification": trade_off.get("justification", ""),
                    "style": {"showJustification": bool(trade_off.get("justification"))}
                })
        
        # Positioning diagram
        if positioning.get("landscape"):
            body.append(
                self.create_visual_suggestion(
                    visual_type="positioning_map",
                    description="Map showing our approach relative to existing methods",
                    data=positioning["landscape"]
                )
            )
        
        return self.create_slide(
            title="Our Position in the Field",
            body=body,
            speaker_notes=self._generate_positioning_notes(positioning),
            metadata={"section": "discussion", "subsection": "positioning"}
        )
    
    def _generate_findings_notes(self, findings: List[str]) -> str:
        """Generate speaker notes for findings slide."""
        notes = []
        
        notes.append(f"Our analysis reveals {len(findings)} key findings.")
        notes.append("Let me walk through each one and explain its significance.")
        
        if len(findings) > 3:
            notes.append("These findings collectively paint a clear picture of our contribution.")
        
        return " ".join(notes)
    
    def _generate_explanation_notes(self, explanation: Dict[str, Any]) -> str:
        """Generate speaker notes for explanation slide."""
        notes = []
        
        notes.append("This result deserves a deeper explanation.")
        
        if explanation.get("evidence"):
            notes.append("The evidence strongly supports our interpretation.")
        
        if explanation.get("mechanism"):
            notes.append("Understanding the underlying mechanism helps us see why this works.")
        
        return " ".join(notes)
    
    def _generate_unexpected_notes(self, unexpected: Dict[str, Any]) -> str:
        """Generate speaker notes for unexpected results."""
        notes = []
        
        notes.append("This result was unexpected and required further investigation.")
        
        if unexpected.get("investigation"):
            notes.append("Our analysis helped us understand what happened.")
        
        notes.append("This highlights the importance of thorough evaluation.")
        
        return " ".join(notes)
    
    def _generate_implications_notes(self, implications: Dict[str, Any]) -> str:
        """Generate speaker notes for implications slide."""
        notes = []
        
        notes.append("Our work has implications across multiple dimensions.")
        
        if implications.get("theoretical"):
            notes.append("Theoretically, this advances our understanding of the field.")
        
        if implications.get("practical"):
            notes.append("Practically, this enables new applications and improvements.")
        
        if implications.get("broader_impact"):
            notes.append("The broader impact extends beyond our immediate domain.")
        
        return " ".join(notes)
    
    def _generate_limitations_notes(self, limitations: List[Dict[str, Any]]) -> str:
        """Generate speaker notes for limitations slide."""
        notes = []
        
        notes.append("It's important to be transparent about the limitations of our work.")
        notes.append(f"We've identified {len(limitations)} main limitations.")
        
        # Check for workarounds
        has_workarounds = any(l.get("workaround") for l in limitations)
        if has_workarounds:
            notes.append("For many of these, we've identified potential workarounds.")
        
        notes.append("These limitations guide our future research directions.")
        
        return " ".join(notes)
    
    def _generate_literature_comparison_notes(self, comparison: Dict[str, Any]) -> str:
        """Generate speaker notes for literature comparison."""
        notes = []
        
        notes.append("Our results relate to existing literature in interesting ways.")
        
        if comparison.get("agreements"):
            notes.append("We confirm several findings from previous work.")
        
        if comparison.get("disagreements"):
            notes.append("We also find some results that differ from previous studies.")
        
        notes.append("This positions our work clearly in the research landscape.")
        
        return " ".join(notes)
    
    def _generate_validity_notes(self, threats: Dict[str, Any]) -> str:
        """Generate speaker notes for validity slide."""
        notes = []
        
        notes.append("We've carefully considered threats to the validity of our results.")
        
        threat_types = [k for k in ["internal", "external", "construct"] if threats.get(k)]
        if threat_types:
            notes.append(f"We identified potential issues with {', '.join(threat_types)} validity.")
        
        if threats.get("mitigations"):
            notes.append("We've implemented strategies to mitigate these threats.")
        
        return " ".join(notes)
    
    def _generate_robustness_notes(self, robustness: Dict[str, Any]) -> str:
        """Generate speaker notes for robustness slide."""
        notes = []
        
        notes.append("We tested the robustness of our approach extensively.")
        
        if robustness.get("sensitivity"):
            notes.append("The method is robust to parameter variations.")
        
        if robustness.get("edge_cases"):
            notes.append("We also evaluated performance on edge cases.")
        
        return " ".join(notes)
    
    def _generate_positioning_notes(self, positioning: Dict[str, Any]) -> str:
        """Generate speaker notes for positioning slide."""
        notes = []
        
        notes.append("Let me position our work relative to the existing field.")
        
        if positioning.get("our_position"):
            notes.append("Our unique position gives us distinct advantages.")
        
        if positioning.get("trade_offs"):
            notes.append("We made deliberate trade-offs based on our application needs.")
        
        return " ".join(notes)