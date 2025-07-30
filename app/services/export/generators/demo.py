#!/usr/bin/env python3
"""
Demo script for the comprehensive PPTX generator.

This script demonstrates the key features of the academic presentation
generator with a simple example that can be run independently.
"""

import sys
from pathlib import Path

# Add the project root to Python path for imports
project_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from app.domain.schemas.generation import Citation, SlideContent
    from app.services.export.generators.pptx_generator import (
        AcademicTemplate,
        PPTXGenerator,
        create_academic_template_config,
        create_ieee_presentation,
    )
except ImportError as e:
    print(f"Import error: {e}")
    print("Make sure you're running from the project root and dependencies are installed.")
    print("Run: pip install python-pptx pillow requests")
    sys.exit(1)


def create_demo_slides():
    """Create demonstration slide content."""
    return [
        # Title slide
        SlideContent(
            title="PPTX Generator Demo",
            subtitle="Comprehensive Academic Presentation System",
            body=[
                {
                    "type": "text",
                    "content": "SlideGenie Development Team\nAcademic Presentation Generator\nDemo Presentation 2024"
                }
            ],
            layout="title_slide",
            metadata={"slide_type": "title"},
            speaker_notes="Welcome to the PPTX generator demo. This presentation showcases the key features of our comprehensive academic presentation system."
        ),
        
        # Features overview
        SlideContent(
            title="Key Features",
            body=[
                {
                    "type": "bullet_list",
                    "items": [
                        "Academic template system (IEEE, ACM, Nature, Universities)",
                        "Advanced content support (equations, charts, images)",
                        "Custom branding and color schemes",
                        "Responsive layout management",
                        "Citation integration with multiple styles",
                        "High-quality image processing",
                        "Speaker notes and metadata support"
                    ]
                }
            ],
            speaker_notes="These are the core features that make our PPTX generator suitable for academic and professional presentations."
        ),
        
        # Mathematical content
        SlideContent(
            title="Mathematical Content Support",
            subtitle="LaTeX Equation Rendering",
            body=[
                {
                    "type": "text",
                    "content": "The system supports mathematical equations through LaTeX:"
                },
                {
                    "type": "equation",
                    "latex": r"E = mc^2",
                    "content": "Einstein's mass-energy equivalence"
                },
                {
                    "type": "text",
                    "content": "Complex equations are also supported:"
                },
                {
                    "type": "equation",
                    "latex": r"\int_{-\infty}^{\infty} e^{-x^2} dx = \sqrt{\pi}",
                    "content": "Gaussian integral"
                }
            ],
            speaker_notes="Mathematical content is essential for academic presentations. Our system renders LaTeX equations as high-quality images."
        ),
        
        # Data visualization
        SlideContent(
            title="Data Visualization",
            body=[
                {
                    "type": "chart",
                    "chart_type": "column",
                    "title": "Performance Comparison",
                    "data": {
                        "categories": ["Speed", "Quality", "Features", "Usability"],
                        "series": [
                            {
                                "name": "Previous System",
                                "values": [65, 70, 60, 75]
                            },
                            {
                                "name": "New PPTX Generator",
                                "values": [90, 95, 98, 92]
                            }
                        ]
                    }
                }
            ],
            speaker_notes="The new PPTX generator shows significant improvements across all metrics compared to previous solutions."
        ),
        
        # Template showcase
        SlideContent(
            title="Academic Templates",
            body=[
                {
                    "type": "text",
                    "content": "Available Templates:"
                },
                {
                    "type": "bullet_list",
                    "items": [
                        "IEEE - Professional blue theme for engineering",
                        "ACM - Modern blue/orange for computer science",
                        "Nature - Green theme for scientific research", 
                        "University-specific - MIT, Stanford, Harvard, etc.",
                        "Custom - Full customization support"
                    ]
                },
                {
                    "type": "text",
                    "content": "Each template includes appropriate color schemes, typography, and layout optimizations."
                }
            ],
            speaker_notes="Templates are designed to meet the standards of major academic conferences and institutions."
        ),
        
        # Technical implementation
        SlideContent(
            title="Technical Implementation",
            body=[
                {
                    "type": "text",
                    "content": "Built with modern Python architecture:"
                },
                {
                    "type": "bullet_list",
                    "items": [
                        "python-pptx for native PPTX generation",
                        "PIL/Pillow for image processing and optimization",
                        "Modular design with pluggable components",
                        "Comprehensive error handling and validation",
                        "Memory-efficient streaming for large presentations",
                        "Extensive test suite with >90% coverage"
                    ]
                }
            ],
            speaker_notes="The technical implementation focuses on reliability, performance, and maintainability."
        ),
        
        # Conclusion
        SlideContent(
            title="Summary",
            body=[
                {
                    "type": "text",
                    "content": "The PPTX generator provides:"
                },
                {
                    "type": "bullet_list",
                    "items": [
                        "Professional academic presentation generation",
                        "Comprehensive content type support",
                        "Flexible template and branding system",
                        "Production-ready reliability and performance",
                        "Easy integration with SlideGenie platform"
                    ]
                },
                {
                    "type": "text",
                    "content": "Ready for deployment in academic and professional environments."
                }
            ],
            speaker_notes="This demo shows just a fraction of the system's capabilities. The full implementation supports many more features and customization options."
        )
    ]


def create_demo_citations():
    """Create demonstration citations."""
    return [
        Citation(
            key="python_pptx2023",
            authors=["Steve Canny"],
            title="python-pptx: Python library for creating and updating PowerPoint files",
            year=2023,
            venue="GitHub Repository",
            url="https://github.com/scanny/python-pptx",
            bibtex_type="misc"
        ),
        Citation(
            key="academic_presentations2024",
            authors=["Academic Writing Team"],
            title="Best Practices for Academic Presentations",
            year=2024,
            venue="Journal of Academic Communication",
            doi="10.1000/jac.2024.001",
            bibtex_type="article"
        )
    ]


def main():
    """Run the demo."""
    print("🎯 PPTX Generator Demo")
    print("=" * 50)
    
    try:
        # Create demo content
        print("📝 Creating demo slides...")
        slides = create_demo_slides()
        citations = create_demo_citations()
        print(f"   ✓ Created {len(slides)} slides")
        print(f"   ✓ Created {len(citations)} citations")
        
        # Generate IEEE presentation
        print("\n🔧 Generating IEEE-style presentation...")
        ieee_buffer = create_ieee_presentation(
            slides=slides,
            citations=citations,
            university_name="Demo University"
        )
        
        # Save to file
        output_file = Path("pptx_generator_demo.pptx")
        with open(output_file, "wb") as f:
            f.write(ieee_buffer.getvalue())
        
        print(f"   ✓ Generated presentation: {output_file}")
        print(f"   📊 File size: {output_file.stat().st_size:,} bytes")
        
        # Generate custom presentation with different template
        print("\n🎨 Generating custom-styled presentation...")
        custom_config = create_academic_template_config(
            template=AcademicTemplate.NATURE,
            university_name="Demo Research Institute",
            custom_colors={
                "primary": "#2E8B57",  # Sea green
                "secondary": "#4682B4",  # Steel blue
                "accent": "#FF6347"     # Tomato
            }
        )
        
        generator = PPTXGenerator(custom_config)
        custom_buffer = generator.export_to_buffer(
            slides=slides,
            citations=citations,
            metadata={
                "title": "PPTX Generator Demo",
                "author": "SlideGenie Team",
                "subject": "Academic Presentation Generation",
                "keywords": "powerpoint, academic, presentation, generator",
                "description": "Demo of comprehensive PPTX generation capabilities"
            }
        )
        
        custom_output = Path("pptx_generator_demo_custom.pptx")
        with open(custom_output, "wb") as f:
            f.write(custom_buffer.getvalue())
        
        print(f"   ✓ Generated custom presentation: {custom_output}")
        print(f"   📊 File size: {custom_output.stat().st_size:,} bytes")
        
        # Success summary
        print("\n🎉 Demo completed successfully!")
        print("\nGenerated files:")
        print(f"   • {output_file} - IEEE template")
        print(f"   • {custom_output} - Custom Nature-style template")
        print("\n💡 Open these files in PowerPoint to see the results!")
        
        # Feature summary
        print("\n📋 Demo showcased:")
        print("   ✓ Title slides with branding")
        print("   ✓ Bullet point content with proper formatting")
        print("   ✓ Mathematical equation rendering")
        print("   ✓ Chart generation with data visualization")
        print("   ✓ Multiple academic templates (IEEE, Nature)")
        print("   ✓ Citation management and references")
        print("   ✓ Speaker notes integration")
        print("   ✓ Custom color schemes and branding")
        print("   ✓ Metadata and document properties")
        
    except Exception as e:
        print(f"❌ Demo failed: {e}")
        print("\nTroubleshooting:")
        print("1. Ensure dependencies are installed: pip install python-pptx pillow requests")
        print("2. Run from the correct directory")
        print("3. Check that all imports are available")
        return 1
    
    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)