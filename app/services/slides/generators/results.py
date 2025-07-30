"""
Results slide generator for academic presentations.
"""
from typing import Any, Dict, List, Optional

from app.domain.schemas.generation import SlideContent
from app.services.slides.generators.base import BaseSlideGenerator, GeneratorInput


class ResultsGenerator(BaseSlideGenerator):
    """Generator for results slides with visualizations and findings."""
    
    @property
    def section_type(self) -> str:
        """Return the section type."""
        return "results"
    
    @property
    def default_layout(self) -> str:
        """Return the default layout type."""
        return "content"
    
    def generate(self, input_data: GeneratorInput) -> List[SlideContent]:
        """
        Generate results slide(s).
        
        Expected content structure:
        {
            "experiments": [
                {
                    "name": "Experiment 1: Performance Evaluation",
                    "description": "Evaluate system performance",
                    "setup": {
                        "dataset": "Dataset A",
                        "parameters": {"param1": "value1"},
                        "baseline": "Method X"
                    },
                    "results": {
                        "metrics": {
                            "accuracy": 0.95,
                            "precision": 0.93,
                            "recall": 0.94,
                            "f1": 0.935
                        },
                        "chart_type": "bar",
                        "comparison": {
                            "our_method": {"accuracy": 0.95, "f1": 0.935},
                            "baseline": {"accuracy": 0.87, "f1": 0.865}
                        }
                    },
                    "key_findings": [
                        "Our method outperforms baseline by 8%",
                        "Significant improvement in edge cases"
                    ]
                }
            ],
            "overall_results": {
                "summary_table": {
                    "headers": ["Method", "Dataset A", "Dataset B", "Average"],
                    "rows": [
                        ["Our Method", "95.2%", "93.8%", "94.5%"],
                        ["Baseline 1", "87.1%", "85.9%", "86.5%"],
                        ["Baseline 2", "89.3%", "88.1%", "88.7%"]
                    ]
                },
                "best_results": [
                    {"metric": "Accuracy", "value": "95.2%", "dataset": "Dataset A"},
                    {"metric": "Speed", "value": "2.3x faster", "comparison": "vs Baseline"}
                ]
            },
            "visualizations": [
                {
                    "type": "performance_chart",
                    "title": "Performance Comparison",
                    "data": {...},
                    "insights": ["Clear performance advantage", "Consistent across datasets"]
                }
            ],
            "statistical_significance": {
                "tests": [
                    {
                        "name": "Paired t-test",
                        "p_value": 0.002,
                        "significant": true,
                        "interpretation": "Results are statistically significant"
                    }
                ]
            },
            "ablation_study": {
                "components": ["Component A", "Component B", "Component C"],
                "results": {
                    "full_system": 0.95,
                    "without_A": 0.88,
                    "without_B": 0.91,
                    "without_C": 0.93
                }
            },
            "case_studies": [
                {
                    "name": "Case Study 1",
                    "description": "Real-world application",
                    "before": "Previous result",
                    "after": "Our result",
                    "improvement": "45% reduction in errors"
                }
            ]
        }
        """
        self.validate_input(input_data)
        
        content = input_data.content
        options = input_data.options
        
        slides = []
        
        # Overall results summary
        if content.get("overall_results"):
            slides.append(self._create_summary_slide(content["overall_results"], options))
        
        # Individual experiment slides
        for experiment in content.get("experiments", []):
            exp_slides = self._create_experiment_slides(experiment, options)
            slides.extend(exp_slides)
        
        # Visualization slides
        for viz in content.get("visualizations", []):
            slides.append(self._create_visualization_slide(viz, options))
        
        # Statistical significance slide
        if content.get("statistical_significance"):
            slides.append(self._create_significance_slide(content["statistical_significance"], options))
        
        # Ablation study slide
        if content.get("ablation_study"):
            slides.append(self._create_ablation_slide(content["ablation_study"], options))
        
        # Case study slides
        if content.get("case_studies"):
            for case_study in content["case_studies"]:
                slides.append(self._create_case_study_slide(case_study, options))
        
        return slides
    
    def _create_summary_slide(
        self,
        overall_results: Dict[str, Any],
        options: GeneratorInput
    ) -> SlideContent:
        """Create overall results summary slide."""
        body = []
        
        # Best results highlights
        if overall_results.get("best_results"):
            highlights = []
            for result in overall_results["best_results"]:
                highlights.append({
                    "metric": result["metric"],
                    "value": result["value"],
                    "context": result.get("dataset") or result.get("comparison", ""),
                    "style": {"highlight": True}
                })
            
            body.append({
                "type": "result_highlights",
                "items": highlights,
                "style": {
                    "layout": "cards",
                    "colorScheme": "success"
                }
            })
        
        # Summary table
        if overall_results.get("summary_table"):
            table = overall_results["summary_table"]
            body.append({
                "type": "results_table",
                "headers": table["headers"],
                "rows": table["rows"],
                "style": {
                    "highlightBest": True,
                    "highlightRow": 0,  # Highlight our method
                    "compactMode": len(table["rows"]) > 5
                }
            })
        
        # Key takeaway
        if overall_results.get("key_takeaway"):
            body.append({
                "type": "takeaway_box",
                "content": overall_results["key_takeaway"],
                "style": {
                    "backgroundColor": "primary_light",
                    "fontSize": "medium",
                    "alignment": "center",
                    "marginTop": "large"
                }
            })
        
        return self.create_slide(
            title="Results Overview",
            subtitle="Performance across all experiments",
            body=body,
            speaker_notes=self._generate_summary_notes(overall_results),
            metadata={"section": "results", "subsection": "overview"}
        )
    
    def _create_experiment_slides(
        self,
        experiment: Dict[str, Any],
        options: GeneratorInput
    ) -> List[SlideContent]:
        """Create slides for a specific experiment."""
        slides = []
        
        # Main results slide
        body = []
        
        # Experiment description
        if experiment.get("description"):
            body.append({
                "type": "text",
                "content": experiment["description"],
                "style": {"fontSize": "medium", "marginBottom": "medium"}
            })
        
        # Results visualization
        results = experiment.get("results", {})
        if results.get("comparison"):
            body.append({
                "type": "comparison_chart",
                "data": results["comparison"],
                "chart_type": results.get("chart_type", "bar"),
                "style": {
                    "height": "medium",
                    "showValues": True,
                    "highlight": "our_method"
                }
            })
        elif results.get("metrics"):
            # Metrics display
            metric_items = []
            for metric, value in results["metrics"].items():
                metric_items.append({
                    "name": metric.title(),
                    "value": f"{value:.3f}" if isinstance(value, float) else str(value),
                    "improvement": results.get("improvements", {}).get(metric)
                })
            
            body.append({
                "type": "metrics_grid",
                "metrics": metric_items,
                "style": {
                    "columns": 2,
                    "showImprovement": True
                }
            })
        
        # Key findings
        if experiment.get("key_findings"):
            body.append({
                "type": "heading",
                "content": "Key Findings",
                "level": 3,
                "style": {"marginTop": "large"}
            })
            body.append({
                "type": "finding_list",
                "findings": experiment["key_findings"],
                "style": {
                    "bulletStyle": "arrow",
                    "emphasis": True
                }
            })
        
        slides.append(self.create_slide(
            title=experiment["name"],
            body=body,
            speaker_notes=self._generate_experiment_notes(experiment),
            metadata={"section": "results", "subsection": "experiment"}
        ))
        
        # Detailed setup slide if complex
        if self._needs_setup_slide(experiment):
            setup_slide = self._create_setup_slide(experiment, options)
            slides.insert(0, setup_slide)
        
        return slides
    
    def _create_visualization_slide(
        self,
        visualization: Dict[str, Any],
        options: GeneratorInput
    ) -> SlideContent:
        """Create a visualization-focused slide."""
        body = []
        
        # Main visualization
        body.append({
            "type": "visualization",
            "viz_type": visualization["type"],
            "data": visualization.get("data", {}),
            "title": visualization.get("title", ""),
            "style": {
                "height": "large",
                "interactive": visualization.get("interactive", False)
            }
        })
        
        # Insights
        if visualization.get("insights"):
            body.append({
                "type": "insight_bullets",
                "insights": visualization["insights"],
                "style": {
                    "position": "bottom",
                    "bulletStyle": "numbered",
                    "fontSize": "small"
                }
            })
        
        # Caption
        if visualization.get("caption"):
            body.append({
                "type": "caption",
                "content": visualization["caption"],
                "style": {
                    "alignment": "center",
                    "fontSize": "small",
                    "fontStyle": "italic"
                }
            })
        
        return self.create_slide(
            title=visualization.get("title", "Results Visualization"),
            body=body,
            layout="visualization",
            speaker_notes=self._generate_visualization_notes(visualization),
            metadata={"section": "results", "subsection": "visualization"}
        )
    
    def _create_significance_slide(
        self,
        significance: Dict[str, Any],
        options: GeneratorInput
    ) -> SlideContent:
        """Create statistical significance slide."""
        body = []
        
        # Test results
        body.append({
            "type": "heading",
            "content": "Statistical Validation",
            "level": 3
        })
        
        test_results = []
        for test in significance.get("tests", []):
            test_results.append({
                "test_name": test["name"],
                "p_value": f"p = {test['p_value']:.4f}",
                "significant": test["significant"],
                "interpretation": test.get("interpretation", ""),
                "confidence": test.get("confidence_level", "95%")
            })
        
        body.append({
            "type": "statistical_tests",
            "tests": test_results,
            "style": {
                "showSignificance": True,
                "highlightSignificant": True
            }
        })
        
        # Effect size if available
        if significance.get("effect_sizes"):
            body.append({
                "type": "heading",
                "content": "Effect Sizes",
                "level": 3,
                "style": {"marginTop": "medium"}
            })
            
            effect_items = []
            for effect in significance["effect_sizes"]:
                effect_items.append({
                    "measure": effect["measure"],
                    "value": effect["value"],
                    "interpretation": effect.get("interpretation", ""),
                    "magnitude": effect.get("magnitude", "medium")
                })
            
            body.append({
                "type": "effect_size_display",
                "effects": effect_items,
                "style": {"layout": "table"}
            })
        
        # Overall conclusion
        if significance.get("conclusion"):
            body.append({
                "type": "conclusion_box",
                "content": significance["conclusion"],
                "style": {
                    "backgroundColor": "success_light",
                    "marginTop": "large",
                    "icon": "check"
                }
            })
        
        return self.create_slide(
            title="Statistical Significance",
            body=body,
            speaker_notes=self._generate_significance_notes(significance),
            metadata={"section": "results", "subsection": "significance"}
        )
    
    def _create_ablation_slide(
        self,
        ablation: Dict[str, Any],
        options: GeneratorInput
    ) -> SlideContent:
        """Create ablation study slide."""
        body = []
        
        # Ablation results chart
        ablation_data = []
        results = ablation.get("results", {})
        
        for config, value in results.items():
            label = config.replace("_", " ").title()
            ablation_data.append({
                "configuration": label,
                "performance": value,
                "is_baseline": config == "full_system"
            })
        
        body.append({
            "type": "ablation_chart",
            "data": ablation_data,
            "style": {
                "chart_type": "waterfall",
                "showDelta": True,
                "baselineLabel": "Full System"
            }
        })
        
        # Component importance analysis
        if ablation.get("components"):
            importance = []
            full_performance = results.get("full_system", 1.0)
            
            for component in ablation["components"]:
                without_key = f"without_{component.replace(' ', '_')}"
                if without_key in results:
                    drop = full_performance - results[without_key]
                    importance.append({
                        "component": component,
                        "importance": f"{drop:.3f}",
                        "percentage": f"{(drop/full_performance)*100:.1f}%"
                    })
            
            if importance:
                body.append({
                    "type": "heading",
                    "content": "Component Importance",
                    "level": 3,
                    "style": {"marginTop": "large"}
                })
                body.append({
                    "type": "importance_ranking",
                    "items": sorted(importance, key=lambda x: float(x["importance"]), reverse=True),
                    "style": {"showBars": True}
                })
        
        # Key insights
        if ablation.get("insights"):
            body.append({
                "type": "ablation_insights",
                "insights": ablation["insights"],
                "style": {
                    "bulletStyle": "numbered",
                    "marginTop": "medium"
                }
            })
        
        return self.create_slide(
            title="Ablation Study",
            subtitle="Component contribution analysis",
            body=body,
            speaker_notes=self._generate_ablation_notes(ablation),
            metadata={"section": "results", "subsection": "ablation"}
        )
    
    def _create_case_study_slide(
        self,
        case_study: Dict[str, Any],
        options: GeneratorInput
    ) -> SlideContent:
        """Create case study slide."""
        body = []
        
        # Case description
        if case_study.get("description"):
            body.append({
                "type": "text",
                "content": case_study["description"],
                "style": {"fontSize": "medium", "marginBottom": "medium"}
            })
        
        # Before/After comparison
        if case_study.get("before") and case_study.get("after"):
            body.append({
                "type": "before_after",
                "before": {
                    "content": case_study["before"],
                    "label": "Previous Approach",
                    "visual": case_study.get("before_visual")
                },
                "after": {
                    "content": case_study["after"],
                    "label": "Our Approach",
                    "visual": case_study.get("after_visual")
                },
                "style": {
                    "layout": "side_by_side",
                    "showArrow": True
                }
            })
        
        # Improvement metrics
        if case_study.get("improvement"):
            body.append({
                "type": "improvement_highlight",
                "content": case_study["improvement"],
                "style": {
                    "fontSize": "large",
                    "color": "success",
                    "alignment": "center",
                    "marginTop": "medium",
                    "icon": "trending_up"
                }
            })
        
        # Details or specifics
        if case_study.get("details"):
            body.append({
                "type": "heading",
                "content": "Details",
                "level": 3,
                "style": {"marginTop": "medium"}
            })
            body.append({
                "type": "bullet_list",
                "items": case_study["details"]
            })
        
        # Real-world impact
        if case_study.get("impact"):
            body.append({
                "type": "impact_statement",
                "content": case_study["impact"],
                "style": {
                    "backgroundColor": "info_light",
                    "marginTop": "medium",
                    "icon": "impact"
                }
            })
        
        return self.create_slide(
            title=f"Case Study: {case_study['name']}",
            body=body,
            speaker_notes=self._generate_case_study_notes(case_study),
            metadata={"section": "results", "subsection": "case_study"}
        )
    
    def _create_setup_slide(
        self,
        experiment: Dict[str, Any],
        options: GeneratorInput
    ) -> SlideContent:
        """Create experimental setup slide."""
        body = []
        
        setup = experiment.get("setup", {})
        
        # Dataset information
        if setup.get("dataset"):
            body.append({
                "type": "setup_item",
                "label": "Dataset",
                "content": setup["dataset"],
                "icon": "database"
            })
        
        # Parameters
        if setup.get("parameters"):
            body.append({
                "type": "heading",
                "content": "Parameters",
                "level": 3,
                "style": {"marginTop": "medium"}
            })
            
            param_items = []
            for param, value in setup["parameters"].items():
                param_items.append(f"{param}: {value}")
            
            body.append({
                "type": "parameter_list",
                "items": param_items,
                "style": {"columns": 2, "monospace": True}
            })
        
        # Hardware/Environment
        if setup.get("environment"):
            body.append({
                "type": "environment_info",
                "data": setup["environment"],
                "style": {"marginTop": "medium"}
            })
        
        # Evaluation protocol
        if setup.get("protocol"):
            body.append({
                "type": "protocol_description",
                "content": setup["protocol"],
                "style": {
                    "backgroundColor": "grey_light",
                    "padding": "medium",
                    "marginTop": "medium"
                }
            })
        
        return self.create_slide(
            title=f"{experiment['name']} - Setup",
            body=body,
            speaker_notes=self._generate_setup_notes(setup),
            metadata={"section": "results", "subsection": "setup"}
        )
    
    def _needs_setup_slide(self, experiment: Dict[str, Any]) -> bool:
        """Determine if experiment needs a separate setup slide."""
        setup = experiment.get("setup", {})
        
        # Need setup slide if complex configuration
        if len(setup.get("parameters", {})) > 5:
            return True
        
        if setup.get("protocol") and len(setup["protocol"]) > 100:
            return True
        
        if setup.get("environment"):
            return True
        
        return False
    
    def _generate_summary_notes(self, overall_results: Dict[str, Any]) -> str:
        """Generate speaker notes for summary slide."""
        notes = []
        
        notes.append("Let me start with an overview of our results.")
        
        if overall_results.get("best_results"):
            notes.append(f"As you can see, we achieved significant improvements across multiple metrics.")
        
        if overall_results.get("summary_table"):
            notes.append("Our method consistently outperforms all baselines.")
        
        return " ".join(notes)
    
    def _generate_experiment_notes(self, experiment: Dict[str, Any]) -> str:
        """Generate speaker notes for experiment slides."""
        notes = []
        
        notes.append(f"For {experiment['name']}, we evaluated our approach comprehensively.")
        
        if experiment.get("key_findings"):
            notes.append(f"There are {len(experiment['key_findings'])} key findings from this experiment.")
        
        results = experiment.get("results", {})
        if results.get("comparison"):
            notes.append("The comparison clearly shows our method's advantages.")
        
        return " ".join(notes)
    
    def _generate_visualization_notes(self, visualization: Dict[str, Any]) -> str:
        """Generate speaker notes for visualization slides."""
        notes = []
        
        notes.append(f"This {visualization.get('type', 'visualization')} illustrates our results visually.")
        
        if visualization.get("insights"):
            notes.append(f"There are {len(visualization['insights'])} key insights to note here.")
        
        return " ".join(notes)
    
    def _generate_significance_notes(self, significance: Dict[str, Any]) -> str:
        """Generate speaker notes for significance slide."""
        notes = []
        
        notes.append("We validated our results using rigorous statistical tests.")
        
        significant_count = sum(1 for test in significance.get("tests", []) if test.get("significant"))
        if significant_count:
            notes.append(f"All {significant_count} tests show statistically significant improvements.")
        
        return " ".join(notes)
    
    def _generate_ablation_notes(self, ablation: Dict[str, Any]) -> str:
        """Generate speaker notes for ablation slide."""
        notes = []
        
        notes.append("The ablation study shows the contribution of each component.")
        
        # Find most important component
        results = ablation.get("results", {})
        if "full_system" in results:
            full_perf = results["full_system"]
            biggest_drop = 0
            key_component = ""
            
            for config, perf in results.items():
                if config.startswith("without_"):
                    drop = full_perf - perf
                    if drop > biggest_drop:
                        biggest_drop = drop
                        key_component = config.replace("without_", "").replace("_", " ")
            
            if key_component:
                notes.append(f"{key_component.title()} is the most critical component.")
        
        return " ".join(notes)
    
    def _generate_case_study_notes(self, case_study: Dict[str, Any]) -> str:
        """Generate speaker notes for case study slide."""
        notes = []
        
        notes.append(f"Let me show you a real-world example: {case_study['name']}.")
        
        if case_study.get("improvement"):
            notes.append(f"We achieved {case_study['improvement']} in this case.")
        
        if case_study.get("impact"):
            notes.append("This demonstrates the practical impact of our work.")
        
        return " ".join(notes)
    
    def _generate_setup_notes(self, setup: Dict[str, Any]) -> str:
        """Generate speaker notes for setup slide."""
        notes = []
        
        notes.append("Let me briefly explain the experimental setup.")
        
        if setup.get("dataset"):
            notes.append(f"We used {setup['dataset']} for evaluation.")
        
        if setup.get("parameters"):
            notes.append("These parameters were carefully chosen based on preliminary experiments.")
        
        return " ".join(notes)