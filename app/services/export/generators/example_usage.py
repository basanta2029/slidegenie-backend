"""
Example usage of the PPTX generator for academic presentations.

This file demonstrates how to use the comprehensive PPTX generator
with various academic templates and features.
"""

import io
from pathlib import Path
from typing import List

from app.domain.schemas.generation import Citation, SlideContent
from app.services.export.generators.pptx_generator import (
    AcademicTemplate,
    BrandingConfig,
    ColorScheme,
    PPTXGenerator,
    TemplateConfig,
    Typography,
    create_academic_template_config,
    create_ieee_presentation,
    create_nature_presentation,
)


def create_sample_slides() -> List[SlideContent]:
    """Create sample slide content for demonstration."""
    slides = [
        # Title slide
        SlideContent(
            title="Advanced Machine Learning in Quantum Computing",
            subtitle="A Comprehensive Study of Quantum Neural Networks",
            body=[
                {
                    "type": "text",
                    "content": "Dr. Jane Smith, Ph.D.\nQuantum Computing Research Lab\nMIT Computer Science Department"
                },
                {
                    "type": "text", 
                    "content": "Conference on Quantum Technologies 2024"
                }
            ],
            layout="title_slide",
            metadata={"slide_type": "title"}
        ),
        
        # Overview slide
        SlideContent(
            title="Research Overview",
            body=[
                {
                    "type": "bullet_list",
                    "items": [
                        "Novel quantum neural network architectures",
                        "Hybrid classical-quantum optimization algorithms", 
                        "Performance analysis on NISQ devices",
                        "Applications in drug discovery and finance",
                        "Scalability challenges and solutions"
                    ]
                }
            ],
            speaker_notes="This slide provides an overview of our research focus areas. We'll dive deep into each of these topics throughout the presentation."
        ),
        
        # Methodology slide with equations
        SlideContent(
            title="Quantum Neural Network Architecture",
            subtitle="Mathematical Formulation",
            body=[
                {
                    "type": "text",
                    "content": "Our quantum neural network uses parameterized quantum circuits with the following formulation:"
                },
                {
                    "type": "equation",
                    "latex": r"|\\psi(\\theta)\\rangle = U_n(\\theta_n) \\cdots U_1(\\theta_1) |0\\rangle^{\\otimes n}",
                    "content": "State preparation circuit"
                },
                {
                    "type": "text",
                    "content": "Where each U_i represents a parameterized quantum gate layer."
                },
                {
                    "type": "equation",
                    "latex": r"\\langle H \\rangle = \\langle \\psi(\\theta) | H | \\psi(\\theta) \\rangle",
                    "content": "Expected value calculation"
                }
            ],
            speaker_notes="The mathematical foundation is crucial for understanding how quantum neural networks differ from classical approaches."
        ),
        
        # Results slide with chart
        SlideContent(
            title="Performance Comparison",
            subtitle="Classical vs Quantum Neural Networks",
            body=[
                {
                    "type": "chart",
                    "chart_type": "column",
                    "title": "Accuracy Comparison Across Datasets",
                    "data": {
                        "categories": ["MNIST", "CIFAR-10", "Drug Discovery", "Portfolio Optimization"],
                        "series": [
                            {
                                "name": "Classical NN",
                                "values": [98.2, 85.7, 76.3, 82.1]
                            },
                            {
                                "name": "Quantum NN", 
                                "values": [98.8, 87.2, 84.5, 89.3]
                            }
                        ]
                    }
                }
            ],
            speaker_notes="Our quantum neural networks show consistent improvements across all tested domains, with particularly strong performance in optimization tasks."
        ),
        
        # Two-column slide with image
        SlideContent(
            title="Circuit Architecture",
            body=[
                {
                    "type": "text",
                    "content": "Key Features:\n\n• Variational ansatz design\n• Entangling gate patterns\n• Measurement strategies\n• Error mitigation"
                },
                {
                    "type": "image",
                    "path": "/path/to/quantum_circuit.png",
                    "caption": "Example quantum neural network circuit with 4 qubits",
                    "alt_text": "Quantum circuit diagram showing gates and connections"
                }
            ],
            layout="two_content",
            speaker_notes="The circuit architecture is designed to balance expressivity with trainability on current NISQ devices."
        ),
        
        # Table slide
        SlideContent(
            title="Experimental Results Summary",
            body=[
                {
                    "type": "table",
                    "data": {
                        "headers": ["Dataset", "Classical Accuracy", "Quantum Accuracy", "Improvement"],
                        "rows": [
                            ["MNIST", "98.2%", "98.8%", "+0.6%"],
                            ["CIFAR-10", "85.7%", "87.2%", "+1.5%"],
                            ["Drug Discovery", "76.3%", "84.5%", "+8.2%"],
                            ["Portfolio Opt.", "82.1%", "89.3%", "+7.2%"]
                        ]
                    }
                }
            ],
            speaker_notes="The quantum advantage is most pronounced in optimization problems and structured data tasks."
        ),
        
        # Conclusions slide
        SlideContent(
            title="Conclusions and Future Work",
            body=[
                {
                    "type": "bullet_list",
                    "items": [
                        "Quantum neural networks show promise for specific problem domains",
                        "Hybrid approaches outperform pure quantum or classical methods",
                        "Error mitigation remains a critical challenge",
                        "Scalability to larger problem sizes is the next frontier"
                    ]
                },
                {
                    "type": "text",
                    "content": "Future directions: Fault-tolerant implementations, novel architectures, and real-world applications."
                }
            ],
            speaker_notes="Our work opens several exciting research directions in quantum machine learning."
        ),
        
        # Section header for Q&A
        SlideContent(
            title="Questions & Discussion",
            body=[],
            layout="section_header",
            metadata={"slide_type": "section"}
        )
    ]
    
    return slides


def create_sample_citations() -> List[Citation]:
    """Create sample citations for the presentation."""
    return [
        Citation(
            key="nielsen2010quantum",
            authors=["Michael A. Nielsen", "Isaac L. Chuang"],
            title="Quantum Computation and Quantum Information",
            year=2010,
            venue="Cambridge University Press",
            bibtex_type="book"
        ),
        Citation(
            key="biamonte2017quantum",
            authors=["Jacob Biamonte", "Peter Wittek", "Nicola Pancotti"],
            title="Quantum machine learning",
            year=2017,
            venue="Nature",
            doi="10.1038/nature23474",
            bibtex_type="article"
        ),
        Citation(
            key="farhi2018quantum",
            authors=["Edward Farhi", "Hartmut Neven"],
            title="Classification with Quantum Neural Networks on Near Term Processors",
            year=2018,
            venue="arXiv preprint arXiv:1802.06002",
            bibtex_type="article"
        )
    ]


def example_ieee_presentation():
    """Create an IEEE-style presentation example."""
    print("Creating IEEE-style presentation...")
    
    slides = create_sample_slides()
    citations = create_sample_citations()
    
    # Create presentation buffer
    presentation_buffer = create_ieee_presentation(
        slides=slides,
        citations=citations,
        university_name="Massachusetts Institute of Technology",
        logo_path="/path/to/mit_logo.png"  # Optional logo path
    )
    
    # Save to file
    output_path = Path("ieee_presentation_example.pptx")
    with open(output_path, "wb") as f:
        f.write(presentation_buffer.getvalue())
    
    print(f"IEEE presentation saved to: {output_path}")
    return presentation_buffer


def example_nature_presentation():
    """Create a Nature-style presentation example."""
    print("Creating Nature-style presentation...")
    
    slides = create_sample_slides()
    citations = create_sample_citations()
    
    # Create presentation buffer
    presentation_buffer = create_nature_presentation(
        slides=slides,
        citations=citations,
        university_name="Stanford University"
    )
    
    # Save to file
    output_path = Path("nature_presentation_example.pptx")
    with open(output_path, "wb") as f:
        f.write(presentation_buffer.getvalue())
    
    print(f"Nature presentation saved to: {output_path}")
    return presentation_buffer


def example_custom_presentation():
    """Create a custom-styled presentation example."""
    print("Creating custom-styled presentation...")
    
    # Create custom template configuration
    custom_config = TemplateConfig(
        template=AcademicTemplate.CUSTOM,
        color_scheme=ColorScheme(
            primary="#2E8B57",  # Sea green
            secondary="#4682B4",  # Steel blue
            accent="#FF6347",  # Tomato
            text_primary="#000000",
            text_secondary="#555555",
            background="#FFFFFF",
            background_alt="#F0F8FF"
        ),
        typography=Typography(
            title_font="Georgia",
            body_font="Arial",
            title_size=46,
            body_size=22
        ),
        branding=BrandingConfig(
            university_name="Custom University",
            department_name="Department of Computer Science",
            show_slide_numbers=True,
            show_date=True,
            custom_footer="Custom Academic Conference 2024",
            logo_position="top_left"
        )
    )
    
    slides = create_sample_slides()
    citations = create_sample_citations()
    
    # Create presentation
    generator = PPTXGenerator(custom_config)
    presentation_buffer = generator.export_to_buffer(
        slides=slides,
        citations=citations,
        metadata={
            "title": "Advanced Machine Learning in Quantum Computing",
            "author": "Dr. Jane Smith",
            "subject": "Quantum Machine Learning Research",
            "keywords": "quantum computing, machine learning, neural networks",
            "description": "Research presentation on quantum neural networks"
        }
    )
    
    # Save to file
    output_path = Path("custom_presentation_example.pptx")
    with open(output_path, "wb") as f:
        f.write(presentation_buffer.getvalue())
    
    print(f"Custom presentation saved to: {output_path}")
    return presentation_buffer


def example_university_branding():
    """Example of university-specific branding."""
    print("Creating university-branded presentation...")
    
    # MIT branding
    mit_config = create_academic_template_config(
        template=AcademicTemplate.MIT,
        university_name="Massachusetts Institute of Technology",
        logo_path="/path/to/mit_logo.png",
        custom_colors={
            "primary": "#8C1515",  # MIT red
            "secondary": "#A51C30",
            "accent": "#009639"
        }
    )
    
    slides = create_sample_slides()
    citations = create_sample_citations()
    
    generator = PPTXGenerator(mit_config)
    presentation_buffer = generator.export_to_buffer(
        slides=slides,
        citations=citations
    )
    
    # Save to file
    output_path = Path("mit_branded_presentation.pptx")
    with open(output_path, "wb") as f:
        f.write(presentation_buffer.getvalue())
    
    print(f"MIT-branded presentation saved to: {output_path}")
    return presentation_buffer


def example_equation_heavy_presentation():
    """Example with many mathematical equations."""
    print("Creating equation-heavy presentation...")
    
    # Create slides with heavy mathematical content
    math_slides = [
        SlideContent(
            title="Mathematical Foundations",
            body=[
                {
                    "type": "text",
                    "content": "Quantum state evolution follows the Schrödinger equation:"
                },
                {
                    "type": "equation",
                    "latex": r"i\\hbar \\frac{\\partial}{\\partial t} |\\psi\\rangle = H |\\psi\\rangle"
                },
                {
                    "type": "text",
                    "content": "For our parameterized circuits, we optimize the cost function:"
                },
                {
                    "type": "equation", 
                    "latex": r"C(\\theta) = \\sum_{i} w_i \\langle \\psi(\\theta) | H_i | \\psi(\\theta) \\rangle"
                }
            ]
        ),
        SlideContent(
            title="Optimization Landscape",
            body=[
                {
                    "type": "text",
                    "content": "The gradient can be computed using the parameter shift rule:"
                },
                {
                    "type": "equation",
                    "latex": r"\\frac{\\partial}{\\partial \\theta_k} \\langle H \\rangle = \\frac{1}{2}[\\langle H \\rangle_{\\theta_k = \\theta_k^+ } - \\langle H \\rangle_{\\theta_k = \\theta_k^-}]"
                },
                {
                    "type": "text",
                    "content": "Where $\\theta_k^{\\pm} = \\theta_k \\pm \\pi/2$ for standard parameterized gates."
                }
            ]
        )
    ]
    
    config = create_academic_template_config(AcademicTemplate.IEEE)
    generator = PPTXGenerator(config)
    presentation_buffer = generator.export_to_buffer(slides=math_slides)
    
    # Save to file
    output_path = Path("equation_heavy_presentation.pptx")
    with open(output_path, "wb") as f:
        f.write(presentation_buffer.getvalue())
    
    print(f"Equation-heavy presentation saved to: {output_path}")
    return presentation_buffer


def run_all_examples():
    """Run all example presentations."""
    print("Running all PPTX generator examples...\n")
    
    # Run examples
    example_ieee_presentation()
    print()
    
    example_nature_presentation()
    print()
    
    example_custom_presentation()
    print()
    
    example_university_branding()
    print()
    
    example_equation_heavy_presentation()
    print()
    
    print("All examples completed successfully!")
    print("Check the generated .pptx files in the current directory.")


if __name__ == "__main__":
    run_all_examples()