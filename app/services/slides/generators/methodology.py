"""
Methodology slide generator for academic presentations.
"""
from typing import Any, Dict, List, Optional

from app.domain.schemas.generation import SlideContent
from app.services.slides.generators.base import BaseSlideGenerator, GeneratorInput


class MethodologyGenerator(BaseSlideGenerator):
    """Generator for methodology/approach slides with technical details and diagrams."""
    
    @property
    def section_type(self) -> str:
        """Return the section type."""
        return "methodology"
    
    @property
    def default_layout(self) -> str:
        """Return the default layout type."""
        return "content"
    
    def generate(self, input_data: GeneratorInput) -> List[SlideContent]:
        """
        Generate methodology slide(s).
        
        Expected content structure:
        {
            "overview": {
                "approach_name": "Novel Framework Name",
                "description": "High-level description",
                "key_innovation": "What makes this approach novel",
                "architecture_diagram": true
            },
            "components": [
                {
                    "name": "Data Processing Module",
                    "description": "Handles input preprocessing",
                    "techniques": ["Normalization", "Feature extraction"],
                    "algorithms": ["Algorithm 1", "Algorithm 2"],
                    "complexity": "O(n log n)"
                }
            ],
            "pipeline": {
                "steps": [
                    {
                        "name": "Step 1: Data Collection",
                        "description": "Collect data from sources",
                        "inputs": ["Raw data"],
                        "outputs": ["Cleaned data"],
                        "tools": ["Python", "Pandas"]
                    }
                ],
                "diagram": true
            },
            "algorithms": [
                {
                    "name": "Algorithm Name",
                    "pseudocode": ["line 1", "line 2"],
                    "complexity": {
                        "time": "O(n²)",
                        "space": "O(n)"
                    },
                    "novelty": "What's new about this"
                }
            ],
            "implementation": {
                "technologies": ["Python", "TensorFlow", "Docker"],
                "architecture": "Microservices",
                "deployment": "Cloud-based",
                "code_snippets": [
                    {
                        "description": "Core algorithm",
                        "language": "python",
                        "code": "def process():\n    pass"
                    }
                ]
            },
            "evaluation_method": {
                "metrics": ["Accuracy", "F1-score", "Runtime"],
                "baselines": ["Method A", "Method B"],
                "datasets": ["Dataset 1", "Dataset 2"],
                "statistical_tests": ["t-test", "ANOVA"]
            }
        }
        """
        self.validate_input(input_data)
        
        content = input_data.content
        options = input_data.options
        
        slides = []
        
        # Overview slide
        if content.get("overview"):
            slides.append(self._create_overview_slide(content["overview"], options))
        
        # Architecture diagram slide
        if content.get("overview", {}).get("architecture_diagram"):
            slides.append(self._create_architecture_slide(content, options))
        
        # Component slides
        if content.get("components"):
            component_slides = self._create_component_slides(content["components"], options)
            slides.extend(component_slides)
        
        # Pipeline slides
        if content.get("pipeline"):
            pipeline_slides = self._create_pipeline_slides(content["pipeline"], options)
            slides.extend(pipeline_slides)
        
        # Algorithm slides
        if content.get("algorithms"):
            for algorithm in content["algorithms"]:
                slides.append(self._create_algorithm_slide(algorithm, options))
        
        # Implementation details slide
        if content.get("implementation"):
            slides.append(self._create_implementation_slide(content["implementation"], options))
        
        # Evaluation methodology slide
        if content.get("evaluation_method"):
            slides.append(self._create_evaluation_method_slide(content["evaluation_method"], options))
        
        return slides
    
    def _create_overview_slide(
        self,
        overview: Dict[str, Any],
        options: GeneratorInput
    ) -> SlideContent:
        """Create methodology overview slide."""
        body = []
        
        # Approach name and description
        if overview.get("description"):
            body.append({
                "type": "text",
                "content": overview["description"],
                "style": {"fontSize": "medium", "marginBottom": "medium"}
            })
        
        # Key innovation highlight
        if overview.get("key_innovation"):
            body.append({
                "type": "innovation_box",
                "content": overview["key_innovation"],
                "style": {
                    "backgroundColor": "primary_light",
                    "borderLeft": "4px solid primary",
                    "padding": "medium",
                    "icon": "lightbulb"
                }
            })
        
        # Main characteristics
        if overview.get("characteristics"):
            body.append({
                "type": "heading",
                "content": "Key Characteristics",
                "level": 3,
                "style": {"marginTop": "large"}
            })
            body.append({
                "type": "characteristic_list",
                "items": overview["characteristics"],
                "style": {
                    "showIcons": True,
                    "iconStyle": "checkmark"
                }
            })
        
        # Advantages
        if overview.get("advantages"):
            body.append({
                "type": "heading",
                "content": "Advantages",
                "level": 3,
                "style": {"marginTop": "medium"}
            })
            body.append({
                "type": "bullet_list",
                "items": overview["advantages"],
                "style": {"bulletStyle": "plus", "color": "success"}
            })
        
        return self.create_slide(
            title=overview.get("approach_name", "Our Methodology"),
            subtitle="Overview",
            body=body,
            speaker_notes=self._generate_overview_notes(overview),
            metadata={"section": "methodology", "subsection": "overview"}
        )
    
    def _create_architecture_slide(
        self,
        content: Dict[str, Any],
        options: GeneratorInput
    ) -> SlideContent:
        """Create system architecture slide."""
        body = []
        
        # Architecture diagram
        body.append(
            self.create_visual_suggestion(
                visual_type="architecture_diagram",
                description="System architecture showing all components and data flow",
                data={
                    "components": [c["name"] for c in content.get("components", [])],
                    "connections": content.get("connections", []),
                    "layers": content.get("layers", [])
                },
                caption="System Architecture"
            )
        )
        
        # Component legend
        if content.get("components"):
            legend_items = []
            for comp in content["components"]:
                legend_items.append({
                    "name": comp["name"],
                    "description": comp.get("brief_description", ""),
                    "color": comp.get("color", "#4285F4")
                })
            
            body.append({
                "type": "component_legend",
                "items": legend_items,
                "style": {
                    "layout": "grid",
                    "columns": 2,
                    "marginTop": "medium"
                }
            })
        
        return self.create_slide(
            title="System Architecture",
            body=body,
            layout="diagram",
            speaker_notes=self._generate_architecture_notes(content),
            metadata={"section": "methodology", "subsection": "architecture"}
        )
    
    def _create_component_slides(
        self,
        components: List[Dict[str, Any]],
        options: GeneratorInput
    ) -> List[SlideContent]:
        """Create slides for individual components."""
        slides = []
        
        # Group related components
        components_per_slide = 2
        
        for i in range(0, len(components), components_per_slide):
            component_chunk = components[i:i + components_per_slide]
            
            body = []
            
            for component in component_chunk:
                # Component header
                body.append({
                    "type": "component_header",
                    "name": component["name"],
                    "style": {
                        "fontSize": "large",
                        "fontWeight": "bold",
                        "color": "primary",
                        "marginTop": "medium" if component != component_chunk[0] else None
                    }
                })
                
                # Description
                if component.get("description"):
                    body.append({
                        "type": "text",
                        "content": component["description"],
                        "style": {"marginBottom": "small"}
                    })
                
                # Techniques/Algorithms used
                if component.get("techniques"):
                    body.append({
                        "type": "technique_list",
                        "title": "Techniques",
                        "items": component["techniques"],
                        "style": {"inline": True, "tagStyle": True}
                    })
                
                if component.get("algorithms"):
                    body.append({
                        "type": "algorithm_list",
                        "title": "Algorithms",
                        "items": component["algorithms"],
                        "style": {"inline": True, "tagStyle": True}
                    })
                
                # Complexity if specified
                if component.get("complexity"):
                    body.append({
                        "type": "complexity_note",
                        "content": f"Complexity: {component['complexity']}",
                        "style": {"fontSize": "small", "fontFamily": "monospace"}
                    })
                
                # Visual representation if available
                if component.get("diagram"):
                    body.append(
                        self.create_visual_suggestion(
                            visual_type="component_diagram",
                            description=f"Detailed view of {component['name']}",
                            data=component.get("diagram_data", {})
                        )
                    )
            
            slide_title = "System Components"
            if len(components) > components_per_slide:
                slide_num = (i // components_per_slide) + 1
                total_slides = (len(components) - 1) // components_per_slide + 1
                slide_title += f" ({slide_num}/{total_slides})"
            
            slides.append(self.create_slide(
                title=slide_title,
                body=body,
                speaker_notes=self._generate_component_notes(component_chunk),
                metadata={"section": "methodology", "subsection": "components"}
            ))
        
        return slides
    
    def _create_pipeline_slides(
        self,
        pipeline: Dict[str, Any],
        options: GeneratorInput
    ) -> List[SlideContent]:
        """Create pipeline/workflow slides."""
        slides = []
        
        # Overview diagram
        if pipeline.get("diagram"):
            body = []
            
            body.append(
                self.create_visual_suggestion(
                    visual_type="pipeline_diagram",
                    description="End-to-end pipeline showing data flow",
                    data={
                        "steps": [s["name"] for s in pipeline.get("steps", [])],
                        "connections": pipeline.get("connections", [])
                    },
                    caption="Processing Pipeline"
                )
            )
            
            slides.append(self.create_slide(
                title="Processing Pipeline",
                body=body,
                layout="diagram",
                speaker_notes=self._generate_pipeline_overview_notes(pipeline),
                metadata={"section": "methodology", "subsection": "pipeline"}
            ))
        
        # Detailed step slides
        steps = pipeline.get("steps", [])
        steps_per_slide = 3
        
        for i in range(0, len(steps), steps_per_slide):
            step_chunk = steps[i:i + steps_per_slide]
            
            body = []
            
            for j, step in enumerate(step_chunk):
                # Step header with number
                body.append({
                    "type": "step_header",
                    "number": i + j + 1,
                    "name": step["name"],
                    "style": {
                        "fontSize": "medium",
                        "fontWeight": "bold",
                        "showNumber": True
                    }
                })
                
                # Description
                if step.get("description"):
                    body.append({
                        "type": "text",
                        "content": step["description"],
                        "style": {"marginLeft": "large"}
                    })
                
                # Input/Output
                if step.get("inputs") or step.get("outputs"):
                    io_items = []
                    if step.get("inputs"):
                        io_items.append({
                            "label": "Input",
                            "items": step["inputs"],
                            "icon": "arrow-right"
                        })
                    if step.get("outputs"):
                        io_items.append({
                            "label": "Output",
                            "items": step["outputs"],
                            "icon": "arrow-left"
                        })
                    
                    body.append({
                        "type": "io_flow",
                        "items": io_items,
                        "style": {"marginLeft": "large", "compact": True}
                    })
                
                # Tools/Technologies
                if step.get("tools"):
                    body.append({
                        "type": "tool_tags",
                        "tools": step["tools"],
                        "style": {"marginLeft": "large", "tagStyle": "outline"}
                    })
                
                # Add separator if not last step
                if j < len(step_chunk) - 1:
                    body.append({
                        "type": "separator",
                        "style": {"margin": "medium"}
                    })
            
            slide_title = "Pipeline Steps"
            if len(steps) > steps_per_slide:
                slide_num = (i // steps_per_slide) + 1
                total_slides = (len(steps) - 1) // steps_per_slide + 1
                slide_title += f" ({slide_num}/{total_slides})"
            
            slides.append(self.create_slide(
                title=slide_title,
                body=body,
                speaker_notes=self._generate_pipeline_steps_notes(step_chunk),
                metadata={"section": "methodology", "subsection": "pipeline_steps"}
            ))
        
        return slides
    
    def _create_algorithm_slide(
        self,
        algorithm: Dict[str, Any],
        options: GeneratorInput
    ) -> SlideContent:
        """Create slide for a specific algorithm."""
        body = []
        
        # Algorithm description
        if algorithm.get("description"):
            body.append({
                "type": "text",
                "content": algorithm["description"],
                "style": {"marginBottom": "medium"}
            })
        
        # Novelty highlight
        if algorithm.get("novelty"):
            body.append({
                "type": "novelty_box",
                "content": algorithm["novelty"],
                "style": {
                    "backgroundColor": "warning_light",
                    "borderColor": "warning",
                    "icon": "star"
                }
            })
        
        # Pseudocode
        if algorithm.get("pseudocode"):
            body.append({
                "type": "pseudocode",
                "lines": algorithm["pseudocode"],
                "style": {
                    "lineNumbers": True,
                    "highlighting": "algorithmic",
                    "fontSize": "small"
                }
            })
        
        # Complexity analysis
        if algorithm.get("complexity"):
            complexity_items = []
            if algorithm["complexity"].get("time"):
                complexity_items.append(f"Time: {algorithm['complexity']['time']}")
            if algorithm["complexity"].get("space"):
                complexity_items.append(f"Space: {algorithm['complexity']['space']}")
            
            body.append({
                "type": "complexity_analysis",
                "items": complexity_items,
                "style": {
                    "layout": "inline",
                    "emphasis": True,
                    "marginTop": "medium"
                }
            })
        
        # Properties
        if algorithm.get("properties"):
            body.append({
                "type": "heading",
                "content": "Key Properties",
                "level": 3,
                "style": {"marginTop": "medium"}
            })
            body.append({
                "type": "bullet_list",
                "items": algorithm["properties"],
                "style": {"bulletStyle": "checkmark"}
            })
        
        return self.create_slide(
            title=f"Algorithm: {algorithm['name']}",
            body=body,
            layout="algorithm",
            speaker_notes=self._generate_algorithm_notes(algorithm),
            metadata={"section": "methodology", "subsection": "algorithm"}
        )
    
    def _create_implementation_slide(
        self,
        implementation: Dict[str, Any],
        options: GeneratorInput
    ) -> SlideContent:
        """Create implementation details slide."""
        body = []
        
        # Technology stack
        if implementation.get("technologies"):
            body.append({
                "type": "tech_stack",
                "technologies": implementation["technologies"],
                "style": {
                    "layout": "grid",
                    "showLogos": True
                }
            })
        
        # Architecture type
        if implementation.get("architecture"):
            body.append({
                "type": "architecture_info",
                "content": f"Architecture: {implementation['architecture']}",
                "style": {
                    "fontSize": "medium",
                    "emphasis": True,
                    "marginTop": "medium"
                }
            })
        
        # Code snippet example
        if implementation.get("code_snippets"):
            snippet = implementation["code_snippets"][0]  # Show first snippet
            body.append({
                "type": "heading",
                "content": snippet.get("description", "Implementation Example"),
                "level": 3,
                "style": {"marginTop": "large"}
            })
            body.append({
                "type": "code",
                "content": snippet["code"],
                "language": snippet.get("language", "python"),
                "style": {
                    "highlighting": True,
                    "lineNumbers": True,
                    "fontSize": "small"
                }
            })
        
        # Deployment info
        if implementation.get("deployment"):
            body.append({
                "type": "deployment_info",
                "content": f"Deployment: {implementation['deployment']}",
                "style": {
                    "marginTop": "medium",
                    "icon": "cloud"
                }
            })
        
        # Performance characteristics
        if implementation.get("performance"):
            body.append({
                "type": "heading",
                "content": "Performance Characteristics",
                "level": 3,
                "style": {"marginTop": "large"}
            })
            body.append({
                "type": "performance_metrics",
                "metrics": implementation["performance"],
                "style": {"layout": "table"}
            })
        
        return self.create_slide(
            title="Implementation Details",
            body=body,
            speaker_notes=self._generate_implementation_notes(implementation),
            metadata={"section": "methodology", "subsection": "implementation"}
        )
    
    def _create_evaluation_method_slide(
        self,
        evaluation: Dict[str, Any],
        options: GeneratorInput
    ) -> SlideContent:
        """Create evaluation methodology slide."""
        body = []
        
        # Evaluation metrics
        if evaluation.get("metrics"):
            body.append({
                "type": "heading",
                "content": "Evaluation Metrics",
                "level": 3
            })
            body.append({
                "type": "metric_list",
                "metrics": evaluation["metrics"],
                "style": {
                    "layout": "tags",
                    "showDescriptions": True
                }
            })
        
        # Datasets
        if evaluation.get("datasets"):
            body.append({
                "type": "heading",
                "content": "Datasets",
                "level": 3,
                "style": {"marginTop": "medium"}
            })
            
            dataset_items = []
            for dataset in evaluation["datasets"]:
                if isinstance(dataset, dict):
                    dataset_items.append(f"{dataset['name']} ({dataset.get('size', 'N/A')} samples)")
                else:
                    dataset_items.append(dataset)
            
            body.append({
                "type": "bullet_list",
                "items": dataset_items
            })
        
        # Baselines
        if evaluation.get("baselines"):
            body.append({
                "type": "heading",
                "content": "Baseline Methods",
                "level": 3,
                "style": {"marginTop": "medium"}
            })
            body.append({
                "type": "baseline_list",
                "baselines": evaluation["baselines"],
                "style": {"showReasons": True}
            })
        
        # Statistical tests
        if evaluation.get("statistical_tests"):
            body.append({
                "type": "heading",
                "content": "Statistical Validation",
                "level": 3,
                "style": {"marginTop": "medium"}
            })
            body.append({
                "type": "test_list",
                "tests": evaluation["statistical_tests"],
                "style": {"showPurpose": True}
            })
        
        # Evaluation protocol
        if evaluation.get("protocol"):
            body.append({
                "type": "protocol_box",
                "content": evaluation["protocol"],
                "style": {
                    "backgroundColor": "info_light",
                    "marginTop": "large"
                }
            })
        
        return self.create_slide(
            title="Evaluation Methodology",
            body=body,
            speaker_notes=self._generate_evaluation_notes(evaluation),
            metadata={"section": "methodology", "subsection": "evaluation"}
        )
    
    def _generate_overview_notes(self, overview: Dict[str, Any]) -> str:
        """Generate speaker notes for overview slide."""
        notes = []
        
        notes.append(f"Our methodology, {overview.get('approach_name', 'which I'll now present')}, addresses the limitations we identified.")
        
        if overview.get("key_innovation"):
            notes.append("The key innovation here is the novel way we approach the problem.")
        
        if overview.get("advantages"):
            notes.append(f"This approach offers {len(overview['advantages'])} main advantages over existing methods.")
        
        return " ".join(notes)
    
    def _generate_architecture_notes(self, content: Dict[str, Any]) -> str:
        """Generate speaker notes for architecture slide."""
        notes = []
        
        notes.append("This diagram shows the overall system architecture.")
        
        component_count = len(content.get("components", []))
        if component_count:
            notes.append(f"The system consists of {component_count} main components working together.")
        
        notes.append("Note how data flows through the system from input to output.")
        
        return " ".join(notes)
    
    def _generate_component_notes(self, components: List[Dict[str, Any]]) -> str:
        """Generate speaker notes for component slides."""
        notes = []
        
        notes.append("Let me explain each component in detail.")
        
        for i, comp in enumerate(components):
            if comp.get("complexity"):
                notes.append(f"The {comp['name']} has {comp['complexity']} complexity.")
        
        return " ".join(notes)
    
    def _generate_pipeline_overview_notes(self, pipeline: Dict[str, Any]) -> str:
        """Generate speaker notes for pipeline overview."""
        notes = []
        
        step_count = len(pipeline.get("steps", []))
        notes.append(f"Our processing pipeline consists of {step_count} main steps.")
        notes.append("Each step transforms the data and prepares it for the next stage.")
        
        return " ".join(notes)
    
    def _generate_pipeline_steps_notes(self, steps: List[Dict[str, Any]]) -> str:
        """Generate speaker notes for pipeline steps."""
        notes = []
        
        notes.append("Let me walk through each step of the pipeline.")
        
        for step in steps:
            if step.get("tools"):
                notes.append(f"For {step['name']}, we use {', '.join(step['tools'])}.")
        
        return " ".join(notes)
    
    def _generate_algorithm_notes(self, algorithm: Dict[str, Any]) -> str:
        """Generate speaker notes for algorithm slide."""
        notes = []
        
        notes.append(f"The {algorithm['name']} is central to our approach.")
        
        if algorithm.get("novelty"):
            notes.append("What makes this algorithm novel is how it handles the specific challenges of our problem.")
        
        if algorithm.get("complexity"):
            notes.append("The complexity analysis shows this is efficient for our use case.")
        
        return " ".join(notes)
    
    def _generate_implementation_notes(self, implementation: Dict[str, Any]) -> str:
        """Generate speaker notes for implementation slide."""
        notes = []
        
        notes.append("Our implementation uses modern technologies and best practices.")
        
        if implementation.get("architecture"):
            notes.append(f"We chose a {implementation['architecture']} architecture for scalability.")
        
        if implementation.get("code_snippets"):
            notes.append("This code snippet shows a key part of our implementation.")
        
        return " ".join(notes)
    
    def _generate_evaluation_notes(self, evaluation: Dict[str, Any]) -> str:
        """Generate speaker notes for evaluation methodology."""
        notes = []
        
        notes.append("To validate our approach, we use a comprehensive evaluation methodology.")
        
        if evaluation.get("metrics"):
            notes.append(f"We measure {len(evaluation['metrics'])} different metrics to assess performance.")
        
        if evaluation.get("statistical_tests"):
            notes.append("Statistical tests ensure the significance of our results.")
        
        return " ".join(notes)