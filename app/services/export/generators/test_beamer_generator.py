"""
Test file for the Beamer generator with comprehensive examples.
"""

import os
import tempfile
from pathlib import Path
import pytest

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


class TestBeamerGenerator:
    """Test suite for BeamerGenerator."""
    
    def test_basic_configuration(self):
        """Test basic Beamer configuration."""
        config = BeamerConfig(
            title="Test Presentation",
            author="Test Author",
            institute="Test University"
        )
        
        generator = BeamerGenerator(config)
        assert generator.config.title == "Test Presentation"
        assert generator.config.author == "Test Author"
        assert generator.config.institute == "Test University"
        assert generator.config.theme == BeamerTheme.BERLIN
    
    def test_slide_creation(self):
        """Test slide creation and content generation."""
        config = BeamerConfig(
            title="Test Presentation",
            author="Test Author"
        )
        generator = BeamerGenerator(config)
        
        slide = BeamerSlide(
            title="Introduction",
            content="This is a test slide with **bold** and *italic* text."
        )
        
        generator.add_slide(slide)
        assert len(generator.slides) == 1
        
        slide_content = generator.generate_slide_content(slide)
        assert "Introduction" in slide_content
        assert "\\textbf{bold}" in slide_content
        assert "\\textit{italic}" in slide_content
    
    def test_figure_generation(self):
        """Test figure generation with subfigures."""
        config = BeamerConfig(title="Test", author="Test")
        generator = BeamerGenerator(config)
        
        # Single figure
        figure = BeamerFigure(
            path="test_image.png",
            caption="Test figure",
            label="fig:test",
            width="0.6\\textwidth"
        )
        
        figure_latex = generator._generate_figure(figure)
        assert "includegraphics" in figure_latex
        assert "test_image.png" in figure_latex
        assert "Test figure" in figure_latex
        assert "fig:test" in figure_latex
        
        # Subfigures
        subfig1 = BeamerFigure(path="sub1.png", caption="Sub 1", width="0.45\\textwidth")
        subfig2 = BeamerFigure(path="sub2.png", caption="Sub 2", width="0.45\\textwidth")
        
        main_figure = BeamerFigure(
            path="",  # Not used for subfigures
            caption="Main figure",
            subfigures=[subfig1, subfig2]
        )
        
        subfig_latex = generator._generate_figure(main_figure)
        assert "subfigure" in subfig_latex
        assert "sub1.png" in subfig_latex
        assert "sub2.png" in subfig_latex
    
    def test_table_generation(self):
        """Test table generation with booktabs."""
        config = BeamerConfig(title="Test", author="Test")
        generator = BeamerGenerator(config)
        
        table = BeamerTable(
            headers=["Method", "Accuracy", "F1-Score"],
            data=[
                ["Random Forest", "0.85", "0.82"],
                ["SVM", "0.88", "0.86"],
                ["Neural Network", "0.92", "0.90"]
            ],
            caption="Model Comparison",
            label="tab:results"
        )
        
        table_latex = generator._generate_table(table)
        assert "tabular" in table_latex
        assert "toprule" in table_latex
        assert "midrule" in table_latex
        assert "bottomrule" in table_latex
        assert "Random Forest" in table_latex
        assert "Model Comparison" in table_latex
    
    def test_equation_generation(self):
        """Test equation generation and math environments."""
        config = BeamerConfig(title="Test", author="Test")
        generator = BeamerGenerator(config)
        
        # Simple equation
        eq1 = "E = mc^2"
        eq_latex1 = generator._generate_equation(eq1)
        assert "equation" in eq_latex1
        
        # Multi-line equation
        eq2 = "x = \\frac{-b \\pm \\sqrt{b^2 - 4ac}}{2a} \\\\ y = ax^2 + bx + c"
        eq_latex2 = generator._generate_equation(eq2)
        assert "align" in eq_latex2
        
        # Already wrapped equation
        eq3 = "\\begin{equation}\\label{eq:test}f(x) = x^2\\end{equation}"
        eq_latex3 = generator._generate_equation(eq3)
        assert eq_latex3 == eq3
    
    def test_citation_processing(self):
        """Test citation processing and bibliography integration."""
        bib_config = BibliographyConfig(
            bib_file="references.bib",
            style="authoryear",
            biblatex=True
        )
        
        config = BeamerConfig(
            title="Test",
            author="Test",
            bibliography=bib_config
        )
        generator = BeamerGenerator(config)
        
        content = "This is based on previous work [@smith2020] and [Jones2021]."
        processed = generator._process_citations(content)
        
        assert "\\cite{smith2020}" in processed
        assert "\\cite{Jones2021}" in processed
        assert "smith2020" in generator.citations
        assert "Jones2021" in generator.citations
    
    def test_list_processing(self):
        """Test markdown list conversion to LaTeX."""
        config = BeamerConfig(title="Test", author="Test")
        generator = BeamerGenerator(config)
        
        content = """
Key points:
- First point
- Second point
  
Numbered list:
1. Step one
2. Step two
3. Step three
"""
        
        processed = generator._process_lists(content)
        assert "\\begin{itemize}" in processed
        assert "\\begin{enumerate}" in processed
        assert "\\item First point" in processed
        assert "\\item Step one" in processed
    
    def test_theme_configuration(self):
        """Test different theme configurations."""
        themes_to_test = [
            (BeamerTheme.WARSAW, ColorTheme.CRANE),
            (BeamerTheme.MADRID, ColorTheme.DOLPHIN),
            (BeamerTheme.SINGAPORE, ColorTheme.ORCHID)
        ]
        
        for theme, color in themes_to_test:
            config = BeamerConfig(
                title="Test",
                author="Test",
                theme=theme,
                color_theme=color
            )
            generator = BeamerGenerator(config)
            preamble = generator.generate_preamble()
            
            assert f"\\usetheme{{{theme.value}}}" in preamble
            assert f"\\usecolortheme{{{color.value}}}" in preamble
    
    def test_handout_configuration(self):
        """Test handout generation configuration."""
        config = BeamerConfig(
            title="Test",
            author="Test",
            generate_handout=True,
            handout_layout=HandoutLayout.FOUR_PER_PAGE
        )
        generator = BeamerGenerator(config)
        
        handout_config = generator._generate_handout_config()
        assert "pgfpages" in handout_config
        assert "4 on 1" in handout_config
    
    def test_package_management(self):
        """Test package import generation."""
        config = BeamerConfig(
            title="Test",
            author="Test",
            packages=["amsmath", "graphicx", "booktabs", "tikz"]
        )
        generator = BeamerGenerator(config)
        
        packages = generator._generate_package_imports()
        assert "\\usepackage{amsmath}" in packages
        assert "\\usepackage{graphicx}" in packages
        assert "\\usepackage{booktabs}" in packages
        assert "\\usepackage{tikz}" in packages
    
    def test_latex_escaping(self):
        """Test LaTeX character escaping."""
        config = BeamerConfig(title="Test", author="Test")
        generator = BeamerGenerator(config)
        
        text = "Special chars: & $ % # _ { } ~ ^ \\"
        escaped = generator._escape_latex(text)
        
        assert "\\&" in escaped
        assert "\\$" in escaped
        assert "\\%" in escaped
        assert "\\#" in escaped
        assert "\\_" in escaped
        assert "\\{" in escaped
        assert "\\}" in escaped
    
    def test_full_document_generation(self):
        """Test complete document generation."""
        config = BeamerConfig(
            title="Machine Learning Overview",
            author="Dr. Alice Johnson",
            institute="AI Research Lab",
            theme=BeamerTheme.BERLIN,
            color_theme=ColorTheme.DEFAULT
        )
        
        generator = BeamerGenerator(config)
        
        # Add multiple slides
        slides = [
            BeamerSlide(
                title="Introduction",
                content="""
                Machine Learning is a subset of AI that focuses on:
                - Pattern recognition
                - Automated decision making  
                - Predictive modeling
                
                **Key applications:**
                - Computer vision
                - Natural language processing
                - Recommendation systems
                """
            ),
            BeamerSlide(
                title="Methodology",
                content="Our approach consists of three main phases:",
                figures=[BeamerFigure(
                    path="methodology_diagram.png",
                    caption="Research methodology overview",
                    width="0.8\\textwidth"
                )]
            ),
            BeamerSlide(
                title="Results",
                content="Performance comparison of different algorithms:",
                tables=[BeamerTable(
                    headers=["Algorithm", "Accuracy", "Training Time"],
                    data=[
                        ["Random Forest", "85.2%", "2.3s"],
                        ["SVM", "88.7%", "5.1s"],
                        ["Deep Neural Network", "92.4%", "45.2s"]
                    ],
                    caption="Algorithm performance comparison"
                )]
            )
        ]
        
        generator.add_slides(slides)
        
        # Generate complete document
        latex_content = generator.generate_latex()
        
        # Verify document structure
        assert "\\documentclass" in latex_content
        assert "\\begin{document}" in latex_content
        assert "\\end{document}" in latex_content
        assert "\\titlepage" in latex_content
        assert "Machine Learning Overview" in latex_content
        assert "Dr. Alice Johnson" in latex_content
        assert "\\begin{frame}" in latex_content
        assert "Introduction" in latex_content
    
    def test_academic_presentation_factory(self):
        """Test academic presentation factory function."""
        generator = create_academic_presentation(
            title="Research Presentation",
            author="Prof. Smith",
            institute="University College"
        )
        
        assert generator.config.title == "Research Presentation"
        assert generator.config.author == "Prof. Smith"
        assert generator.config.institute == "University College"
        assert generator.config.theme == BeamerTheme.BERLIN
        assert generator.config.generate_handout == True
        assert generator.config.bibliography.biblatex == True
    
    def test_math_presentation_factory(self):
        """Test mathematics presentation factory function."""
        generator = create_math_presentation(
            title="Advanced Calculus",
            author="Dr. Mathematics"
        )
        
        assert generator.config.title == "Advanced Calculus"
        assert generator.config.theme == BeamerTheme.WARSAW
        assert generator.config.color_theme == ColorTheme.CRANE
        
        # Check math packages
        assert "mathtools" in generator.config.packages
        assert "physics" in generator.config.packages
        assert "bm" in generator.config.packages
        
        # Check custom commands
        custom_cmds = generator.config.custom_commands
        assert any("\\mathbb{R}" in cmd for cmd in custom_cmds)
        assert any("\\mathbb{C}" in cmd for cmd in custom_cmds)
    
    def test_configuration_validation(self):
        """Test configuration validation."""
        # Valid configuration
        config = BeamerConfig(title="Test", author="Test Author")
        generator = BeamerGenerator(config)
        issues = generator.validate_config()
        assert len(issues) == 0
        
        # Invalid configuration
        invalid_config = BeamerConfig(
            title="",  # Empty title
            author="Test",
            aspect_ratio="invalid:ratio",  # Invalid aspect ratio
            font_size="15pt"  # Invalid font size
        )
        invalid_generator = BeamerGenerator(invalid_config)
        issues = invalid_generator.validate_config()
        
        assert len(issues) > 0
        assert any("Title is required" in issue for issue in issues)
        assert any("Invalid aspect ratio" in issue for issue in issues)
        assert any("Invalid font size" in issue for issue in issues)
    
    def test_overlay_generation(self):
        """Test overlay and transition generation."""
        config = BeamerConfig(title="Test", author="Test")
        generator = BeamerGenerator(config)
        
        # Figure with overlay
        figure = BeamerFigure(
            path="test.png",
            caption="Test",
            overlay="<2->"
        )
        
        figure_latex = generator._generate_figure(figure)
        assert "\\only<2->" in figure_latex
        
        # Table with overlay
        table = BeamerTable(
            headers=["A", "B"],
            data=[["1", "2"]],
            overlay="<3->"
        )
        
        table_latex = generator._generate_table(table)
        assert "\\only<3->" in table_latex


def test_integration_example():
    """Integration test with a complete presentation example."""
    with tempfile.TemporaryDirectory() as temp_dir:
        # Create a bibliography file
        bib_content = """
@article{smith2020,
    author = {Smith, John and Doe, Jane},
    title = {Machine Learning Advances},
    journal = {AI Journal},
    year = {2020},
    volume = {15},
    pages = {123-145}
}

@book{jones2021,
    author = {Jones, Bob},
    title = {Deep Learning Fundamentals},
    publisher = {Tech Press},
    year = {2021}
}
"""
        
        bib_file = os.path.join(temp_dir, "references.bib")
        with open(bib_file, 'w') as f:
            f.write(bib_content)
        
        # Configure presentation with bibliography
        config = BeamerConfig(
            title="Advanced AI Techniques",
            author="Dr. Research",
            institute="AI Institute",
            theme=BeamerTheme.WARSAW,
            color_theme=ColorTheme.DOLPHIN,
            generate_handout=True,
            handout_layout=HandoutLayout.FOUR_PER_PAGE,
            bibliography=BibliographyConfig(
                bib_file="references.bib",
                style="authoryear",
                biblatex=True
            )
        )
        
        generator = BeamerGenerator(config)
        
        # Create comprehensive slides
        slides = [
            BeamerSlide(
                title="Literature Review",
                content="""
                Recent advances in machine learning [@smith2020] have shown:
                - Improved accuracy on benchmark datasets
                - Better generalization capabilities
                - Reduced computational requirements
                
                The foundational work by [jones2021] provides:
                - Theoretical framework
                - Practical implementation guidelines
                - Performance evaluation metrics
                """,
                equations=["\\text{Accuracy} = \\frac{\\text{Correct Predictions}}{\\text{Total Predictions}}"]
            ),
            BeamerSlide(
                title="Experimental Setup",
                content="We evaluated our approach using standard benchmarks:",
                figures=[BeamerFigure(
                    path="experimental_setup.png",
                    caption="Experimental pipeline overview",
                    width="0.9\\textwidth"
                )],
                tables=[BeamerTable(
                    headers=["Dataset", "Samples", "Features", "Classes"],
                    data=[
                        ["MNIST", "70,000", "784", "10"],
                        ["CIFAR-10", "60,000", "3,072", "10"],
                        ["ImageNet", "1.2M", "Variable", "1,000"]
                    ],
                    caption="Dataset characteristics"
                )]
            ),
            BeamerSlide(
                title="Mathematical Formulation",
                content="The optimization objective is defined as:",
                equations=[
                    "\\min_{\\theta} \\mathcal{L}(\\theta) = \\frac{1}{n}\\sum_{i=1}^{n} \\ell(f(x_i; \\theta), y_i) + \\lambda \\Omega(\\theta)",
                    "\\text{where } \\ell \\text{ is the loss function and } \\Omega \\text{ is the regularization term}"
                ]
            )
        ]
        
        generator.add_slides(slides)
        
        # Generate LaTeX
        latex_content = generator.generate_latex()
        
        # Save LaTeX file
        latex_file = os.path.join(temp_dir, "presentation.tex")
        generator.save_latex(latex_file)
        
        # Verify file was created and contains expected content
        assert os.path.exists(latex_file)
        
        with open(latex_file, 'r') as f:
            content = f.read()
            assert "Advanced AI Techniques" in content
            assert "Dr. Research" in content
            assert "\\cite{smith2020}" in content
            assert "\\cite{jones2021}" in content
            assert "Experimental Setup" in content
            assert "Mathematical Formulation" in content
            assert "printbibliography" in content or "bibliography{references}" in content


if __name__ == "__main__":
    # Run basic tests
    test_suite = TestBeamerGenerator()
    
    print("Testing basic configuration...")
    test_suite.test_basic_configuration()
    print("✓ Basic configuration test passed")
    
    print("Testing slide creation...")
    test_suite.test_slide_creation()
    print("✓ Slide creation test passed")
    
    print("Testing figure generation...")
    test_suite.test_figure_generation()
    print("✓ Figure generation test passed")
    
    print("Testing table generation...")  
    test_suite.test_table_generation()
    print("✓ Table generation test passed")
    
    print("Testing equation generation...")
    test_suite.test_equation_generation()
    print("✓ Equation generation test passed")
    
    print("Testing citation processing...")
    test_suite.test_citation_processing()
    print("✓ Citation processing test passed")
    
    print("Testing full document generation...")
    test_suite.test_full_document_generation()
    print("✓ Full document generation test passed")
    
    print("Testing integration example...")
    test_integration_example()
    print("✓ Integration test passed") 
    
    print("\nAll tests passed! ✓")
    
    # Generate a sample presentation
    print("\nGenerating sample presentation...")
    
    generator = create_academic_presentation(
        title="Sample Academic Presentation",
        author="Test Author",
        institute="Test University"
    )
    
    sample_slide = BeamerSlide(
        title="Sample Slide",
        content="""
        This is a **sample slide** demonstrating:
        - LaTeX Beamer generation
        - Professional formatting
        - Academic presentation features
        
        Mathematical equation: $E = mc^2$
        """,
        equations=["\\sum_{i=1}^{n} x_i = X_{total}"]
    )
    
    generator.add_slide(sample_slide)
    
    # Generate and display LaTeX (first 50 lines)
    latex_content = generator.generate_latex()
    lines = latex_content.split('\n')
    
    print("Generated LaTeX (first 50 lines):")
    print("-" * 60)
    for i, line in enumerate(lines[:50], 1):
        print(f"{i:2d}: {line}")
    
    if len(lines) > 50:
        print(f"... ({len(lines) - 50} more lines)")
    
    print("-" * 60)
    print("Sample presentation generated successfully!")