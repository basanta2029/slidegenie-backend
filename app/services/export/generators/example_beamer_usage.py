"""
Example usage of the Beamer LaTeX generator for academic presentations.

This file demonstrates various features of the BeamerGenerator including:
- Different theme configurations
- Mathematical content
- Figures and tables
- Bibliography integration
- Handout generation
"""

import os
import tempfile
from pathlib import Path

from beamer_generator import (
    BeamerGenerator,
    BeamerConfig,
    BeamerSlide,
    BeamerFigure,
    BeamerTable,
    BeamerTheme,
    ColorTheme,
    HandoutLayout,
    BibliographyConfig,
    create_academic_presentation,
    create_math_presentation
)


def example_basic_presentation():
    """Create a basic academic presentation."""
    print("=== Basic Academic Presentation ===")
    
    # Create generator using factory function
    generator = create_academic_presentation(
        title="Introduction to Machine Learning",
        author="Dr. Sarah Johnson",
        institute="Computer Science Department\\\\University of Technology"
    )
    
    # Add slides
    slides = [
        BeamerSlide(
            title="What is Machine Learning?",
            content="""
            Machine Learning is a branch of artificial intelligence that focuses on:
            
            - **Supervised Learning**: Learning from labeled data
            - **Unsupervised Learning**: Finding patterns in unlabeled data  
            - **Reinforcement Learning**: Learning through interaction
            
            > *"Machine learning is the field that gives computers the ability to learn without being explicitly programmed."*
            > — Arthur Samuel (1959)
            """
        ),
        
        BeamerSlide(
            title="Types of Machine Learning",
            content="""
            We can categorize ML algorithms into several types:
            
            1. **Supervised Learning**
               - Classification (discrete output)
               - Regression (continuous output)
            
            2. **Unsupervised Learning**
               - Clustering
               - Dimensionality reduction
               - Association rules
            
            3. **Reinforcement Learning**
               - Policy-based methods
               - Value-based methods
            """,
            equations=[
                "\\text{Classification: } f: X \\rightarrow \\{1, 2, \\ldots, K\\}",
                "\\text{Regression: } f: X \\rightarrow \\mathbb{R}"
            ]
        ),
        
        BeamerSlide(
            title="Performance Evaluation",
            content="Common metrics for evaluating ML models:",
            tables=[BeamerTable(
                headers=["Metric", "Classification", "Regression"],
                data=[
                    ["Accuracy", "✓", "✗"],
                    ["Precision/Recall", "✓", "✗"],
                    ["F1-Score", "✓", "✗"],
                    ["MSE/RMSE", "✗", "✓"],
                    ["MAE", "✗", "✓"],
                    ["R²", "✗", "✓"]
                ],
                caption="Evaluation metrics by problem type",
                label="tab:metrics"
            )],
            equations=[
                "\\text{Accuracy} = \\frac{\\text{Correct Predictions}}{\\text{Total Predictions}}",
                "\\text{MSE} = \\frac{1}{n}\\sum_{i=1}^{n}(y_i - \\hat{y}_i)^2"
            ]
        )
    ]
    
    generator.add_slides(slides)
    
    # Generate LaTeX
    latex_content = generator.generate_latex()
    print(f"Generated {len(latex_content)} characters of LaTeX")
    
    return generator, latex_content


def example_math_presentation():
    """Create a mathematics-focused presentation."""
    print("\n=== Mathematics Presentation ===")
    
    # Create math-optimized generator
    generator = create_math_presentation(
        title="Linear Algebra in Machine Learning",
        author="Prof. Michael Chen"
    )
    
    # Add mathematical content
    slides = [
        BeamerSlide(
            title="Vector Spaces",
            content="""
            A **vector space** $V$ over a field $\\mathbb{F}$ is a set equipped with:
            
            - Vector addition: $+: V \\times V \\rightarrow V$
            - Scalar multiplication: $\\cdot: \\mathbb{F} \\times V \\rightarrow V$
            
            Satisfying the axioms:
            - Associativity of addition
            - Commutativity of addition  
            - Identity element for addition
            - Inverse elements for addition
            - Distributivity of scalar multiplication
            """,
            equations=[
                "\\forall \\mathbf{u}, \\mathbf{v} \\in V: \\mathbf{u} + \\mathbf{v} = \\mathbf{v} + \\mathbf{u}",
                "\\exists \\mathbf{0} \\in V: \\mathbf{v} + \\mathbf{0} = \\mathbf{v}, \\forall \\mathbf{v} \\in V"
            ]
        ),
        
        BeamerSlide(
            title="Matrix Operations",
            content="Essential matrix operations for ML:",
            equations=[
                "\\text{Matrix multiplication: } (AB)_{ij} = \\sum_{k=1}^{n} A_{ik}B_{kj}",
                "\\text{Transpose: } (A^T)_{ij} = A_{ji}",
                "\\text{Trace: } \\Tr(A) = \\sum_{i=1}^{n} A_{ii}",
                "\\text{Determinant: } \\det(A) = \\sum_{\\sigma \\in S_n} \\text{sgn}(\\sigma) \\prod_{i=1}^{n} A_{i,\\sigma(i)}"
            ]
        ),
        
        BeamerSlide(
            title="Eigenvalues and Eigenvectors",
            content="""
            For a square matrix $A \\in \\mathbb{R}^{n \\times n}$:
            
            An **eigenvector** $\\mathbf{v} \\neq \\mathbf{0}$ and **eigenvalue** $\\lambda$ satisfy:
            """,
            equations=[
                "A\\mathbf{v} = \\lambda\\mathbf{v}",
                "\\det(A - \\lambda I) = 0 \\quad \\text{(characteristic equation)}",
                "\\text{Eigendecomposition: } A = Q\\Lambda Q^{-1}"
            ],
            tables=[BeamerTable(
                headers=["Property", "Symmetric Matrix", "General Matrix"],
                data=[
                    ["Real eigenvalues", "Always", "Not guaranteed"],
                    ["Orthogonal eigenvectors", "Yes", "Not guaranteed"],
                    ["Diagonalizable", "Always", "Not guaranteed"]
                ],
                caption="Eigenvalue properties"
            )]
        )
    ]
    
    generator.add_slides(slides)
    
    # Generate LaTeX
    latex_content = generator.generate_latex()
    print(f"Generated {len(latex_content)} characters of LaTeX")
    
    return generator, latex_content


def example_conference_presentation():
    """Create a conference-style presentation with figures and references."""
    print("\n=== Conference Presentation with Bibliography ===")
    
    # Create bibliography file content
    bib_content = """
@article{lecun2015deep,
    title={Deep learning},
    author={LeCun, Yann and Bengio, Yoshua and Hinton, Geoffrey},
    journal={Nature},
    volume={521},
    number={7553},
    pages={436--444},
    year={2015},
    publisher={Nature Publishing Group}
}

@article{attention2017,
    title={Attention is all you need},
    author={Vaswani, Ashish and Shazeer, Noam and Parmar, Niki and others},
    journal={Advances in neural information processing systems},
    volume={30},
    year={2017}
}

@book{bishop2006pattern,
    title={Pattern recognition and machine learning},
    author={Bishop, Christopher M},
    year={2006},
    publisher={Springer}
}
"""
    
    # Configure with bibliography
    config = BeamerConfig(
        title="Deep Learning for Computer Vision:\\\\Recent Advances and Applications",
        author="Dr. Elena Rodriguez\\\\Joint work with Alex Kim and Maria Santos",
        institute="AI Research Lab\\\\Institute of Technology",
        date="Conference on AI 2024",
        theme=BeamerTheme.MADRID,
        color_theme=ColorTheme.DOLPHIN,
        aspect_ratio="16:9",
        generate_handout=True,
        handout_layout=HandoutLayout.FOUR_PER_PAGE,
        bibliography=BibliographyConfig(
            bib_file="references.bib",
            style="authoryear-comp",
            biblatex=True,
            backend="biber"
        ),
        custom_commands=[
            "\\newcommand{\\CNN}{\\text{CNN}}",
            "\\newcommand{\\RNN}{\\text{RNN}}",
            "\\newcommand{\\LSTM}{\\text{LSTM}}",
            "\\DeclareMathOperator{\\softmax}{softmax}"
        ]
    )
    
    generator = BeamerGenerator(config)
    
    # Add slides with citations and figures
    slides = [
        BeamerSlide(
            title="Introduction",
            content="""
            Deep learning has revolutionized computer vision [@lecun2015deep]:
            
            - **Image Classification**: Surpassed human performance on ImageNet
            - **Object Detection**: Real-time detection in autonomous vehicles
            - **Semantic Segmentation**: Pixel-level understanding
            - **Generative Models**: Creating realistic synthetic images
            
            The transformer architecture [@attention2017] has also found applications in vision tasks.
            """,
            frame_options=["fragile"]  # Needed for citations in some cases
        ),
        
        BeamerSlide(
            title="Network Architecture",
            content="Our proposed architecture combines multiple components:",
            figures=[BeamerFigure(
                path="network_architecture.png",
                caption="Overview of the proposed deep network architecture",
                label="fig:architecture",
                width="0.95\\textwidth"
            )],
            equations=[
                "\\text{Output} = \\softmax(W_3 \\cdot \\text{ReLU}(W_2 \\cdot \\text{ReLU}(W_1 \\cdot \\mathbf{x} + \\mathbf{b}_1) + \\mathbf{b}_2) + \\mathbf{b}_3)"
            ]
        ),
        
        BeamerSlide(
            title="Experimental Results",
            content="Performance comparison on standard benchmarks:",
            tables=[BeamerTable(
                headers=["Method", "CIFAR-10", "CIFAR-100", "ImageNet", "Parameters"],
                data=[
                    ["ResNet-50", "95.3", "78.1", "76.2", "25.6M"],
                    ["DenseNet-121", "95.1", "77.9", "74.4", "8.0M"],
                    ["EfficientNet-B0", "96.7", "81.2", "77.3", "5.3M"],
                    ["Our Method", "**97.2**", "**82.8**", "**78.9**", "7.1M"]
                ],
                caption="Accuracy (\\%) comparison on image classification benchmarks",
                label="tab:results"
            )],
            equations=[
                "\\text{Improvement} = \\frac{\\text{Our Accuracy} - \\text{Baseline Accuracy}}{\\text{Baseline Accuracy}} \\times 100\\%"
            ]
        ),
        
        BeamerSlide(
            title="Ablation Study",
            content="Analysis of individual component contributions:",
            figures=[
                BeamerFigure(
                    path="",  # Main figure for subfigures
                    caption="Ablation study results",
                    label="fig:ablation",
                    subfigures=[
                        BeamerFigure(
                            path="ablation_accuracy.png", 
                            caption="Accuracy vs. components",
                            width="0.48\\textwidth"
                        ),
                        BeamerFigure(
                            path="ablation_loss.png",
                            caption="Training loss curves", 
                            width="0.48\\textwidth"
                        )
                    ]
                )
            ]
        ),
        
        BeamerSlide(
            title="Conclusions and Future Work",
            content="""
            **Key Contributions:**
            - Novel architecture achieving SOTA results
            - Efficient design with fewer parameters
            - Comprehensive evaluation on multiple datasets
            
            **Future Directions:**
            - Extension to video understanding
            - Multi-modal learning applications
            - Deployment optimization for mobile devices
            
            **Acknowledgments:** This work was supported by NSF Grant AI-2024-001.
            """,
            frame_options=["allowframebreaks"]
        )
    ]
    
    generator.add_slides(slides)
    
    # Generate complete document
    latex_content = generator.generate_latex()
    print(f"Generated {len(latex_content)} characters of LaTeX")
    
    return generator, latex_content, bib_content


def example_handout_generation():
    """Demonstrate handout generation with different layouts."""
    print("\n=== Handout Generation Example ===")
    
    layouts = [
        HandoutLayout.TWO_PER_PAGE,
        HandoutLayout.FOUR_PER_PAGE,
        HandoutLayout.SIX_PER_PAGE
    ]
    
    for layout in layouts:
        print(f"Creating handout with {layout.value} layout...")
        
        config = BeamerConfig(
            title=f"Sample Presentation - {layout.value}",
            author="Test Author",
            generate_handout=True,
            handout_layout=layout,
            handout_notes=True
        )
        
        generator = BeamerGenerator(config)
        
        # Add sample slides
        for i in range(6):
            slide = BeamerSlide(
                title=f"Slide {i+1}",
                content=f"""
                Content for slide {i+1}:
                - Point A
                - Point B  
                - Point C
                """,
                notes=f"Speaker notes for slide {i+1}"
            )
            generator.add_slide(slide)
        
        latex_content = generator.generate_latex()
        print(f"  Generated handout with {layout.value}: {len(latex_content)} characters")


def example_theme_showcase():
    """Showcase different Beamer themes."""
    print("\n=== Theme Showcase ===")
    
    themes = [
        (BeamerTheme.BERLIN, ColorTheme.DEFAULT),
        (BeamerTheme.WARSAW, ColorTheme.CRANE),
        (BeamerTheme.MADRID, ColorTheme.DOLPHIN),
        (BeamerTheme.SINGAPORE, ColorTheme.ORCHID),
    ]
    
    for theme, color in themes:
        print(f"Creating presentation with {theme.value} theme and {color.value} colors...")
        
        config = BeamerConfig(
            title=f"Theme Demo: {theme.value}",
            author="Theme Tester",
            theme=theme,
            color_theme=color
        )
        
        generator = BeamerGenerator(config)
        
        # Add sample slide
        slide = BeamerSlide(
            title="Theme Demonstration",
            content=f"""
            This slide demonstrates the **{theme.value}** theme with **{color.value}** colors.
            
            Features shown:
            - Title formatting
            - Text styling
            - List formatting
            - Color scheme
            """,
            equations=["\\sum_{i=1}^{n} x_i = \\text{Total}"]
        )
        
        generator.add_slide(slide)
        
        latex_content = generator.generate_latex()
        print(f"  Generated {theme.value} theme: {len(latex_content)} characters")


def save_examples_to_files():
    """Save example presentations to files for compilation."""
    print("\n=== Saving Examples to Files ===")
    
    # Create output directory
    output_dir = Path("beamer_examples")
    output_dir.mkdir(exist_ok=True)
    
    # Generate and save basic presentation
    print("Saving basic presentation...")
    generator, latex = example_basic_presentation()
    basic_path = output_dir / "basic_presentation.tex"
    generator.save_latex(str(basic_path))
    
    # Generate and save math presentation
    print("Saving math presentation...")
    generator, latex = example_math_presentation()
    math_path = output_dir / "math_presentation.tex"
    generator.save_latex(str(math_path))
    
    # Generate and save conference presentation with bibliography
    print("Saving conference presentation...")
    generator, latex, bib_content = example_conference_presentation()
    conf_path = output_dir / "conference_presentation.tex"
    bib_path = output_dir / "references.bib"
    
    generator.save_latex(str(conf_path))
    with open(bib_path, 'w') as f:
        f.write(bib_content)
    
    print(f"Examples saved to {output_dir}/")
    print("To compile:")
    print(f"  cd {output_dir}")
    print("  pdflatex basic_presentation.tex")
    print("  pdflatex math_presentation.tex")
    print("  pdflatex conference_presentation.tex")
    print("  biber conference_presentation")  
    print("  pdflatex conference_presentation.tex")
    print("  pdflatex conference_presentation.tex")


if __name__ == "__main__":
    print("LaTeX Beamer Generator Examples")
    print("=" * 50)
    
    # Run all examples
    example_basic_presentation()
    example_math_presentation() 
    example_conference_presentation()
    example_handout_generation()
    example_theme_showcase()
    
    # Save examples to files
    save_examples_to_files()
    
    print("\n" + "=" * 50)
    print("All examples completed successfully!")
    print("\nFeatures demonstrated:")
    print("✓ Basic academic presentations")
    print("✓ Mathematics-heavy content") 
    print("✓ Conference presentations with citations")
    print("✓ Multiple handout layouts")
    print("✓ Different theme combinations")
    print("✓ Figures, tables, and equations")
    print("✓ Bibliography integration")
    print("✓ Custom commands and packages")
    
    print("\nThe Beamer generator provides:")
    print("- Complete LaTeX document generation")
    print("- Professional academic themes")
    print("- BibTeX/biblatex integration")
    print("- Mathematical equation support")
    print("- Figure and table optimization")
    print("- Handout generation")
    print("- Comprehensive error handling")
    print("- Template system")
    print("- Package management")