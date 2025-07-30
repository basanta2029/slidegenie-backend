"""
Example usage of the PDF generator for academic presentations.

This file demonstrates various ways to use the PDFGenerator class and its features:
- Basic PDF generation for different formats
- Academic template configurations
- Custom styling and layouts
- Advanced features like watermarks and bookmarks
- Integration patterns for web applications
"""

import os
from pathlib import Path
from typing import List

from pdf_generator import (
    PDFGenerator,
    PDFConfig,
    PDFSlide,
    PDFFormat,
    PDFQuality,
    HandoutLayout,
    PageSize,
    PageOrientation,
    create_presentation_pdf,
    create_handout_pdf,
    create_notes_pdf,
    create_print_pdf,
    get_ieee_config,
    get_acm_config,
    get_nature_config
)
from app.domain.schemas.generation import Citation


def create_sample_presentation() -> List[PDFSlide]:
    """Create a sample academic presentation about quantum computing."""
    
    slides = [
        PDFSlide(
            title="Quantum Computing: Principles and Applications",
            content="""
            Quantum computing represents a revolutionary approach to computation that leverages quantum mechanical phenomena to process information in fundamentally new ways.

            Today's Agenda:
            • Quantum mechanics fundamentals
            • Quantum bits and superposition
            • Quantum algorithms and applications
            • Current challenges and future prospects
            """,
            notes="""
            Welcome everyone to today's presentation on quantum computing. This is an introductory talk suitable for computer science students and researchers who want to understand the basics of quantum computation.
            
            Start with a brief survey of the audience's background in quantum mechanics and computer science to gauge the appropriate level of detail.
            """,
            slide_number=1,
            layout_type="title_slide"
        ),
        
        PDFSlide(
            title="Quantum Bits: The Building Blocks",
            content="""
            Unlike classical bits that exist in states 0 or 1, quantum bits (qubits) can exist in a superposition of both states simultaneously.

            Key Properties:
            • Superposition: |ψ⟩ = α|0⟩ + β|1⟩
            • Entanglement: Correlated quantum states
            • Measurement: Collapses superposition
            • Decoherence: Loss of quantum properties

            Mathematical Representation:
            A qubit state is represented as a vector in a 2D complex vector space, where |α|² + |β|² = 1.
            """,
            notes="""
            This slide introduces the fundamental concept of qubits. Make sure to explain:
            1. The difference between classical and quantum bits
            2. What superposition means physically
            3. Why measurement is destructive in quantum systems
            4. The mathematical notation (bra-ket notation)
            
            Consider using the analogy of a spinning coin before it lands.
            """,
            slide_number=2,
            images=[
                {
                    "path": "https://via.placeholder.com/400x300/4472C4/FFFFFF?text=Qubit+Superposition",
                    "alt_text": "Visualization of qubit superposition on Bloch sphere",
                    "caption": "Figure 1: Qubit representation on the Bloch sphere"
                }
            ],
            citations=[
                Citation(
                    title="Quantum Computation and Quantum Information",
                    authors="Michael A. Nielsen, Isaac L. Chuang", 
                    year="2010",
                    url="https://doi.org/10.1017/CBO9780511976667"
                )
            ]
        ),
        
        PDFSlide(
            title="Quantum Algorithms: Shor's Algorithm",
            content="""
            Shor's algorithm demonstrates quantum computing's potential to solve problems exponentially faster than classical computers.

            Algorithm Overview:
            1. Reduction to period finding
            2. Quantum period finding subroutine
            3. Classical post-processing
            4. Factor extraction

            Complexity Analysis:
            • Classical: O(exp(n^(1/3))) - exponential
            • Quantum: O(n³) - polynomial

            Implications:
            • Breaks RSA encryption
            • Motivates post-quantum cryptography
            • Demonstrates quantum advantage
            """,
            notes="""
            Shor's algorithm is one of the most famous quantum algorithms. Key points to emphasize:
            
            1. The exponential speedup over classical algorithms
            2. The threat to current cryptographic systems
            3. The algorithm's structure: quantum period finding + classical processing
            4. Why this algorithm motivated significant investment in quantum computing research
            
            You might want to briefly mention Grover's algorithm as another important example.
            """,
            slide_number=3,
            citations=[
                Citation(
                    title="Algorithms for quantum computation: discrete logarithms and factoring",
                    authors="Peter W. Shor",
                    year="1994", 
                    url="https://doi.org/10.1109/SFCS.1994.365700"
                )
            ]
        ),
        
        PDFSlide(
            title="Current Quantum Computing Platforms",
            content="""
            Several approaches to building quantum computers are being pursued:

            Superconducting Qubits:
            • IBM Quantum, Google Sycamore
            • Fast gates, short coherence times
            • Operates at millikelvin temperatures

            Trapped Ions:
            • IonQ, Honeywell
            • Long coherence times, slower gates
            • High-fidelity two-qubit operations

            Photonic Systems:
            • Xanadu, PsiQuantum
            • Room temperature operation
            • Natural for quantum networking

            Other Approaches:
            • Neutral atoms, silicon qubits, topological qubits
            """,
            notes="""
            This slide provides an overview of different quantum computing technologies. For each platform, discuss:
            
            1. The physical principle used to create qubits
            2. Advantages and disadvantages
            3. Current state of development
            4. Leading companies and research groups
            
            Mention that no single approach has clearly emerged as superior - each has trade-offs.
            """,
            slide_number=4,
            images=[
                {
                    "path": "https://via.placeholder.com/500x300/34A853/FFFFFF?text=Quantum+Platforms",
                    "alt_text": "Comparison of different quantum computing platforms",
                    "caption": "Figure 2: Overview of quantum computing platforms"
                }
            ]
        ),
        
        PDFSlide(
            title="Challenges and Future Directions",
            content="""
            Despite significant progress, major challenges remain:

            Technical Challenges:
            • Quantum error correction
            • Scalability to many qubits
            • Decoherence and noise
            • Limited connectivity between qubits

            Algorithmic Challenges:
            • Finding quantum advantage for practical problems
            • Quantum software development
            • Hybrid classical-quantum algorithms

            Future Milestones:
            • Fault-tolerant quantum computers (~1M physical qubits)
            • Quantum advantage in optimization
            • Quantum internet and networking
            • Integration with classical computing infrastructure
            """,
            notes="""
            This concluding slide should provide a balanced view of the field:
            
            1. Acknowledge the significant technical hurdles
            2. Highlight the active research areas
            3. Discuss realistic timelines for different applications
            4. Mention career opportunities in quantum computing
            
            End with questions and discussion. Be prepared to discuss:
            - When quantum computers might become practically useful
            - How to get started learning quantum computing
            - Ethical implications of quantum technology
            """,
            slide_number=5,
            citations=[
                Citation(
                    title="Quantum advantage with shallow circuits",
                    authors="Sergey Bravyi, David Gosset, Robert König",
                    year="2018",
                    url="https://doi.org/10.1126/science.aar3106"
                )
            ]
        )
    ]
    
    return slides


def basic_pdf_generation_example():
    """Demonstrate basic PDF generation in different formats."""
    print("=== Basic PDF Generation Example ===")
    
    slides = create_sample_presentation()
    output_dir = "quantum_computing_presentation"
    os.makedirs(output_dir, exist_ok=True)
    
    # 1. Standard presentation format
    print("Generating presentation PDF...")
    success = create_presentation_pdf(
        slides, 
        f"{output_dir}/quantum_presentation.pdf"
    )
    print(f"Presentation PDF: {'✓' if success else '✗'}")
    
    # 2. Handout format with 2x3 layout
    print("Generating handout PDF...")
    success = create_handout_pdf(
        slides,
        f"{output_dir}/quantum_handout.pdf",
        HandoutLayout.LAYOUT_2x3
    )
    print(f"Handout PDF: {'✓' if success else '✗'}")
    
    # 3. Notes format with speaker notes
    print("Generating notes PDF...")
    success = create_notes_pdf(
        slides,
        f"{output_dir}/quantum_notes.pdf"
    )
    print(f"Notes PDF: {'✓' if success else '✗'}")
    
    # 4. Print-optimized format
    print("Generating print-optimized PDF...")
    success = create_print_pdf(
        slides,
        f"{output_dir}/quantum_print.pdf"
    )
    print(f"Print PDF: {'✓' if success else '✗'}")


def advanced_configuration_example():
    """Demonstrate advanced PDF configuration options."""
    print("\n=== Advanced Configuration Example ===")
    
    slides = create_sample_presentation()
    output_dir = "advanced_pdfs"
    os.makedirs(output_dir, exist_ok=True)
    
    # Custom configuration with watermark
    custom_config = PDFConfig(
        format=PDFFormat.PRESENTATION,
        quality=PDFQuality.HIGH_QUALITY,
        page_size=PageSize.A4,
        orientation=PageOrientation.LANDSCAPE,
        
        # Watermark settings
        watermark_text="CONFIDENTIAL RESEARCH",
        watermark_opacity=0.1,
        watermark_rotation=45,
        
        # Custom colors
        primary_color="#1B365D",
        accent_color="#4472C4", 
        text_color="#2C3E50",
        background_color="#FAFAFA",
        
        # Typography
        title_font="Helvetica-Bold",
        body_font="Helvetica",
        font_size_title=18,
        font_size_body=12,
        
        # Layout
        margin_top=60,
        margin_bottom=60,
        margin_left=80,
        margin_right=80,
        
        # Features
        include_toc=True,
        include_bookmarks=True,
        include_page_numbers=True,
        include_headers=True,
        include_footers=True,
        
        # Quality settings
        image_dpi=200,
        compress_images=True,
        high_contrast=False
    )
    
    generator = PDFGenerator(custom_config)
    
    metadata = {
        'Title': 'Quantum Computing: Principles and Applications',
        'Author': 'Dr. Quantum Researcher',
        'Subject': 'Introduction to Quantum Computing',
        'Keywords': 'quantum computing, qubits, algorithms, Shor',
        'Creator': 'SlideGenie Academic PDF Generator'
    }
    
    success = generator.generate_pdf(
        slides, 
        f"{output_dir}/quantum_advanced.pdf",
        metadata
    )
    print(f"Advanced configured PDF: {'✓' if success else '✗'}")


def academic_templates_example():
    """Demonstrate academic journal/conference templates."""
    print("\n=== Academic Templates Example ===")
    
    slides = create_sample_presentation()
    output_dir = "academic_templates"
    os.makedirs(output_dir, exist_ok=True)
    
    # IEEE Conference Style
    print("Generating IEEE style PDF...")
    ieee_generator = PDFGenerator(get_ieee_config())
    success = ieee_generator.generate_pdf(
        slides,
        f"{output_dir}/quantum_ieee.pdf"
    )
    print(f"IEEE template: {'✓' if success else '✗'}")
    
    # ACM Conference Style
    print("Generating ACM style PDF...")
    acm_generator = PDFGenerator(get_acm_config())
    success = acm_generator.generate_pdf(
        slides,
        f"{output_dir}/quantum_acm.pdf"
    )
    print(f"ACM template: {'✓' if success else '✗'}")
    
    # Nature Journal Style
    print("Generating Nature style PDF...")
    nature_generator = PDFGenerator(get_nature_config())
    success = nature_generator.generate_pdf(
        slides,
        f"{output_dir}/quantum_nature.pdf"
    )
    print(f"Nature template: {'✓' if success else '✗'}")


def handout_layouts_example():
    """Demonstrate different handout layouts."""
    print("\n=== Handout Layouts Example ===")
    
    slides = create_sample_presentation()
    output_dir = "handout_layouts"
    os.makedirs(output_dir, exist_ok=True)
    
    layouts = [
        (HandoutLayout.LAYOUT_1x2, "1x2 (two slides vertically)"),
        (HandoutLayout.LAYOUT_2x2, "2x2 (four slides in grid)"),
        (HandoutLayout.LAYOUT_2x3, "2x3 (six slides)"),
        (HandoutLayout.LAYOUT_3x3, "3x3 (nine slides)"),
        (HandoutLayout.LAYOUT_4x3, "4x3 (twelve slides)")
    ]
    
    for layout, description in layouts:
        print(f"Generating {description}...")
        config = PDFConfig(
            format=PDFFormat.HANDOUT,
            handout_layout=layout,
            page_size=PageSize.A4,
            orientation=PageOrientation.PORTRAIT
        )
        
        generator = PDFGenerator(config)
        success = generator.generate_pdf(
            slides,
            f"{output_dir}/handout_{layout.name.lower()}.pdf"
        )
        print(f"  {layout.name}: {'✓' if success else '✗'}")


def quality_comparison_example():
    """Demonstrate different quality settings."""
    print("\n=== Quality Comparison Example ===")
    
    slides = create_sample_presentation()
    output_dir = "quality_comparison"
    os.makedirs(output_dir, exist_ok=True)
    
    qualities = [
        (PDFQuality.DRAFT, "Fast generation, lower quality"),
        (PDFQuality.STANDARD, "Balanced quality and speed"),
        (PDFQuality.HIGH_QUALITY, "Maximum quality"),
        (PDFQuality.PRINT_READY, "Optimized for printing")
    ]
    
    for quality, description in qualities:
        print(f"Generating {quality.value} quality ({description})...")
        
        config = PDFConfig(
            format=PDFFormat.PRESENTATION,
            quality=quality,
            image_dpi=150 if quality == PDFQuality.DRAFT else 300,
            compress_images=quality in [PDFQuality.DRAFT, PDFQuality.STANDARD]
        )
        
        generator = PDFGenerator(config)
        success = generator.generate_pdf(
            slides,
            f"{output_dir}/quantum_{quality.value}.pdf"
        )
        print(f"  {quality.value}: {'✓' if success else '✗'}")


def integration_example():
    """Demonstrate integration patterns for web applications."""
    print("\n=== Integration Example ===")
    
    def generate_pdf_for_api(slide_data: dict, format_type: str, options: dict) -> tuple:
        """
        Example function showing how to integrate PDF generation into a web API.
        
        Args:
            slide_data: Dictionary containing slide information
            format_type: Type of PDF to generate ('presentation', 'handout', 'notes', 'print')
            options: Additional configuration options
            
        Returns:
            (success: bool, file_path: str, error_message: str)
        """
        try:
            # Convert API data to PDFSlide objects
            slides = []
            for i, slide_info in enumerate(slide_data.get('slides', []), 1):
                slide = PDFSlide(
                    title=slide_info.get('title', ''),
                    content=slide_info.get('content', ''),
                    notes=slide_info.get('notes', ''),
                    slide_number=i,
                    images=slide_info.get('images', []),
                    citations=[
                        Citation(**citation) for citation in slide_info.get('citations', [])
                    ]
                )
                slides.append(slide)
            
            # Configure PDF generation
            config = PDFConfig()
            
            # Apply format type
            if format_type == 'handout':
                config.format = PDFFormat.HANDOUT
                config.handout_layout = HandoutLayout(tuple(options.get('layout', [2, 3])))
            elif format_type == 'notes':
                config.format = PDFFormat.NOTES
            elif format_type == 'print':
                config.format = PDFFormat.PRINT_OPTIMIZED
            else:
                config.format = PDFFormat.PRESENTATION
            
            # Apply additional options
            if 'page_size' in options:
                config.page_size = PageSize[options['page_size'].upper()]
            if 'orientation' in options:
                config.orientation = PageOrientation(options['orientation'])
            if 'quality' in options:
                config.quality = PDFQuality(options['quality'])
            if 'watermark' in options:
                config.watermark_text = options['watermark']
            
            # Generate PDF
            output_path = f"temp_pdf_{format_type}_{hash(str(slide_data))}.pdf"
            generator = PDFGenerator(config)
            
            metadata = {
                'Title': slide_data.get('title', 'Generated Presentation'),
                'Author': slide_data.get('author', 'SlideGenie User'),
                'Subject': slide_data.get('subject', 'Academic Presentation')
            }
            
            success = generator.generate_pdf(slides, output_path, metadata)
            
            if success:
                return True, output_path, ""
            else:
                return False, "", "PDF generation failed"
                
        except Exception as e:
            return False, "", str(e)
    
    # Example API call simulation
    sample_api_data = {
        'title': 'Sample Presentation',
        'author': 'API User',
        'subject': 'Test Presentation',
        'slides': [
            {
                'title': 'Introduction',
                'content': 'This is a test slide generated via API.',
                'notes': 'This demonstrates API integration.',
                'images': [],
                'citations': []
            },
            {
                'title': 'Conclusion', 
                'content': 'The PDF generation API works successfully.',
                'notes': 'Wrap up the demonstration.',
                'images': [],
                'citations': []
            }
        ]
    }
    
    # Test different format types
    formats_to_test = [
        ('presentation', {}),
        ('handout', {'layout': [2, 2]}),
        ('notes', {}),
        ('print', {'quality': 'high'})
    ]
    
    for format_type, options in formats_to_test:
        success, file_path, error = generate_pdf_for_api(sample_api_data, format_type, options)
        print(f"API integration test - {format_type}: {'✓' if success else '✗'}")
        if not success:
            print(f"  Error: {error}")
        else:
            print(f"  Generated: {file_path}")


def main():
    """Run all examples."""
    print("PDF Generator Examples")
    print("=" * 50)
    
    try:
        basic_pdf_generation_example()
        advanced_configuration_example()
        academic_templates_example()
        handout_layouts_example()
        quality_comparison_example()
        integration_example()
        
        print("\n" + "=" * 50)
        print("All examples completed successfully!")
        print("Check the generated directories for PDF outputs.")
        
    except Exception as e:
        print(f"\nError running examples: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()