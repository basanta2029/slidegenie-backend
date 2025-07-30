"""
Comprehensive LaTeX Beamer export system for academic presentations.

This module provides a complete Beamer document generation system with:
- Academic themes and customization
- BibTeX integration and citation management
- Mathematical equation rendering
- Figure placement optimization
- Handout version generation
- Professional table formatting
- Frame transitions and overlays
"""

import os
import re
import tempfile
import shutil
import subprocess
from pathlib import Path
from typing import Dict, List, Optional, Union, Tuple, Any
from dataclasses import dataclass, field
from enum import Enum
import logging
from datetime import datetime

logger = logging.getLogger(__name__)


class BeamerTheme(Enum):
    """Predefined academic Beamer themes with their characteristics."""
    BERLIN = "Berlin"
    MADRID = "Madrid" 
    WARSAW = "Warsaw"
    SINGAPORE = "Singapore"
    COPENHAGEN = "Copenhagen"
    ROCHESTER = "Rochester"
    DARMSTADT = "Darmstadt"
    FRANKFURT = "Frankfurt"
    HANNOVER = "Hannover"
    ILMENAU = "Ilmenau"
    JUANLESPINS = "JuanLesPins"
    LUEBECK = "Luebeck"
    MALMOE = "Malmoe"
    MARBURG = "Marburg"
    MONTPELLIER = "Montpellier"
    PITTSBURGH = "Pittsburgh"
    SZEGED = "Szeged"


class ColorTheme(Enum):
    """Beamer color themes."""
    DEFAULT = "default"
    ALBATROSS = "albatross"
    BEAVER = "beaver"
    BEETLE = "beetle"
    CRANE = "crane"
    DOLPHIN = "dolphin"
    DOVE = "dove"
    FLY = "fly"
    LILY = "lily"
    ORCHID = "orchid"
    ROSE = "rose"
    SEAGULL = "seagull"
    SEAHORSE = "seahorse"
    WHALE = "whale"
    WOLVERINE = "wolverine"


class HandoutLayout(Enum):
    """Handout layout options."""
    ONE_PER_PAGE = "1x1"
    TWO_PER_PAGE = "2x1" 
    FOUR_PER_PAGE = "2x2"
    SIX_PER_PAGE = "3x2"
    NINE_PER_PAGE = "3x3"


@dataclass
class BeamerFigure:
    """Configuration for figure placement in Beamer."""
    path: str
    caption: str = ""
    label: str = ""
    width: str = "0.8\\textwidth"
    height: Optional[str] = None
    position: str = "center"
    subfigures: List['BeamerFigure'] = field(default_factory=list)
    overlay: Optional[str] = None  # e.g., "<2->"


@dataclass
class BeamerTable:
    """Configuration for table formatting in Beamer."""
    data: List[List[str]]
    headers: List[str]
    caption: str = ""
    label: str = ""
    position: str = "center"
    column_spec: Optional[str] = None
    booktabs: bool = True
    overlay: Optional[str] = None


@dataclass
class BeamerSlide:
    """Individual Beamer slide configuration."""
    title: str
    content: str
    subtitle: Optional[str] = None
    frame_options: List[str] = field(default_factory=list)
    figures: List[BeamerFigure] = field(default_factory=list)
    tables: List[BeamerTable] = field(default_factory=list)
    equations: List[str] = field(default_factory=list)
    overlays: List[str] = field(default_factory=list)
    notes: Optional[str] = None
    transition: Optional[str] = None


@dataclass
class BibliographyConfig:
    """BibTeX and citation configuration."""
    bib_file: Optional[str] = None
    style: str = "authoryear"  # authoryear, numeric, alphabetic
    backend: str = "biber"  # biber, bibtex
    natbib: bool = False
    biblatex: bool = True
    sorting: str = "nyt"  # name, year, title
    max_names: int = 3
    min_names: int = 1


@dataclass
class BeamerConfig:
    """Comprehensive Beamer document configuration."""
    # Document metadata
    title: str
    author: str
    institute: Optional[str] = None
    date: Optional[str] = None
    
    # Theme configuration
    theme: BeamerTheme = BeamerTheme.BERLIN
    color_theme: ColorTheme = ColorTheme.DEFAULT
    font_theme: str = "default"
    outer_theme: Optional[str] = None
    inner_theme: Optional[str] = None
    
    # Document options
    aspect_ratio: str = "16:9"  # 4:3, 16:9, 14:9, 16:10, 3:2, 5:4
    font_size: str = "11pt"  # 8pt, 9pt, 10pt, 11pt, 12pt, 14pt, 17pt, 20pt
    navigation_symbols: bool = False
    
    # Bibliography
    bibliography: BibliographyConfig = field(default_factory=BibliographyConfig)
    
    # Package configuration
    packages: List[str] = field(default_factory=lambda: [
        "inputenc", "fontenc", "babel", "amsmath", "amsfonts", "amssymb",
        "graphicx", "booktabs", "array", "longtable", "multirow", "multicol",
        "xcolor", "tikz", "pgfplots", "hyperref", "url", "subcaption"
    ])
    
    # Custom commands and settings
    custom_commands: List[str] = field(default_factory=list)
    tikz_libraries: List[str] = field(default_factory=list)
    
    # Handout options
    generate_handout: bool = False
    handout_layout: HandoutLayout = HandoutLayout.FOUR_PER_PAGE
    handout_notes: bool = True


class BeamerTemplateManager:
    """Manages Beamer LaTeX templates and themes."""
    
    @staticmethod
    def get_preamble_template() -> str:
        """Get the base preamble template."""
        return r"""
\documentclass[{font_size},{aspect_ratio}{handout_option}]{{beamer}}

% Theme configuration
\usetheme{{{theme}}}
\usecolortheme{{{color_theme}}}
\usefonttheme{{{font_theme}}}
{outer_theme}
{inner_theme}

% Navigation symbols
{navigation_symbols}

% Package imports
{packages}

% Bibliography configuration
{bibliography_config}

% TikZ libraries
{tikz_libraries}

% Custom commands
{custom_commands}

% Title page information
\title{{{title}}}
\author{{{author}}}
{institute}
{date}

% Document settings
\setbeamertemplate{{frametitle continuation}}{{(\insertcontinuationcount)}}
\setbeamertemplate{{section in toc}}[sections numbered]
\setbeamertemplate{{subsection in toc}}[subsections numbered]

% Handout configuration
{handout_config}

\begin{{document}}

% Title frame
\begin{{frame}}
    \titlepage
\end{{frame}}

% Table of contents
{toc_frame}

{content}

% Bibliography
{bibliography_frame}

\end{{document}}
"""

    @staticmethod
    def get_frame_template() -> str:
        """Get the frame template."""
        return r"""
\begin{{frame}}{frame_options}{{{title}}}{subtitle}
{content}
{notes}
\end{{frame}}
"""

    @staticmethod
    def get_figure_template() -> str:
        """Get the figure template."""
        return r"""
\begin{{figure}}[{position}]
    \centering
    {subfigures_or_single}
    {caption}
    {label}
\end{{figure}}
"""

    @staticmethod
    def get_table_template() -> str:
        """Get the table template."""
        return r"""
\begin{{table}}[{position}]
    \centering
    {caption_top}
    \begin{{{table_env}}}{{{column_spec}}}
    {table_content}
    \end{{{table_env}}}
    {caption_bottom}
    {label}
\end{{table}}
"""


class BeamerGenerator:
    """
    Comprehensive LaTeX Beamer document generator for academic presentations.
    
    Features:
    - Complete Beamer document generation with proper preamble
    - Academic themes with customization options
    - BibTeX integration with citation management
    - Mathematical equation rendering
    - Figure placement optimization with subfigures
    - Handout version generation with different layouts
    - Professional table formatting with booktabs
    - Frame transitions and overlays
    """
    
    def __init__(self, config: BeamerConfig):
        """Initialize the Beamer generator with configuration."""
        self.config = config
        self.template_manager = BeamerTemplateManager()
        self.slides: List[BeamerSlide] = []
        self.citations: List[str] = []
        self.temp_dir: Optional[str] = None
        
    def add_slide(self, slide: BeamerSlide) -> None:
        """Add a slide to the presentation."""
        self.slides.append(slide)
        
    def add_slides(self, slides: List[BeamerSlide]) -> None:
        """Add multiple slides to the presentation."""
        self.slides.extend(slides)
        
    def add_citation(self, citation_key: str) -> None:
        """Add a citation key to track usage."""
        if citation_key not in self.citations:
            self.citations.append(citation_key)
    
    def generate_preamble(self) -> str:
        """Generate the complete LaTeX preamble."""
        # Handle handout option
        handout_option = ",handout" if self.config.generate_handout else ""
        
        # Theme configurations
        outer_theme = f"\\useoutertheme{{{self.config.outer_theme}}}" if self.config.outer_theme else ""
        inner_theme = f"\\useinnertheme{{{self.config.inner_theme}}}" if self.config.inner_theme else ""
        
        # Navigation symbols
        nav_symbols = "" if self.config.navigation_symbols else "\\setbeamertemplate{navigation symbols}{}"
        
        # Package configuration
        packages = self._generate_package_imports()
        
        # Bibliography configuration
        bib_config = self._generate_bibliography_config()
        
        # TikZ libraries
        tikz_libs = self._generate_tikz_libraries()
        
        # Custom commands
        custom_commands = "\n".join(self.config.custom_commands)
        
        # Institute and date
        institute = f"\\institute{{{self.config.institute}}}" if self.config.institute else ""
        date_text = self.config.date or "\\today"
        date = f"\\date{{{date_text}}}"
        
        # Handout configuration
        handout_config = self._generate_handout_config()
        
        # TOC frame
        toc_frame = self._generate_toc_frame()
        
        return self.template_manager.get_preamble_template().format(
            font_size=self.config.font_size,
            aspect_ratio=self.config.aspect_ratio,
            handout_option=handout_option,
            theme=self.config.theme.value,
            color_theme=self.config.color_theme.value,
            font_theme=self.config.font_theme,
            outer_theme=outer_theme,
            inner_theme=inner_theme,
            navigation_symbols=nav_symbols,
            packages=packages,
            bibliography_config=bib_config,
            tikz_libraries=tikz_libs,
            custom_commands=custom_commands,
            title=self._escape_latex(self.config.title),
            author=self._escape_latex(self.config.author),
            institute=institute,
            date=date,
            handout_config=handout_config,
            toc_frame=toc_frame,
            content="{content}",  # Placeholder for content
            bibliography_frame="{bibliography_frame}"  # Placeholder for bibliography
        )
    
    def _generate_package_imports(self) -> str:
        """Generate package import statements."""
        imports = []
        
        # Standard packages with options
        if "inputenc" in self.config.packages:
            imports.append("\\usepackage[utf8]{inputenc}")
        if "fontenc" in self.config.packages:
            imports.append("\\usepackage[T1]{fontenc}")
        if "babel" in self.config.packages:
            imports.append("\\usepackage[english]{babel}")
        
        # Math packages
        math_packages = ["amsmath", "amsfonts", "amssymb", "amsthm"]
        for pkg in math_packages:
            if pkg in self.config.packages:
                imports.append(f"\\usepackage{{{pkg}}}")
        
        # Graphics and tables
        if "graphicx" in self.config.packages:
            imports.append("\\usepackage{graphicx}")
        if "booktabs" in self.config.packages:
            imports.append("\\usepackage{booktabs}")
        if "array" in self.config.packages:
            imports.append("\\usepackage{array}")
        if "longtable" in self.config.packages:
            imports.append("\\usepackage{longtable}")
        if "multirow" in self.config.packages:
            imports.append("\\usepackage{multirow}")
        if "multicol" in self.config.packages:
            imports.append("\\usepackage{multicol}")
        
        # Colors and graphics
        if "xcolor" in self.config.packages:
            imports.append("\\usepackage{xcolor}")
        if "tikz" in self.config.packages:
            imports.append("\\usepackage{tikz}")
        if "pgfplots" in self.config.packages:
            imports.append("\\usepackage{pgfplots}")
            imports.append("\\pgfplotsset{compat=1.18}")
        
        # References and URLs
        if "hyperref" in self.config.packages:
            imports.append("\\usepackage[colorlinks=true,linkcolor=blue,citecolor=red,urlcolor=blue]{hyperref}")
        if "url" in self.config.packages:
            imports.append("\\usepackage{url}")
        if "subcaption" in self.config.packages:
            imports.append("\\usepackage{subcaption}")
        
        # Additional packages not covered above
        additional = [pkg for pkg in self.config.packages if pkg not in [
            "inputenc", "fontenc", "babel", "amsmath", "amsfonts", "amssymb", "amsthm",
            "graphicx", "booktabs", "array", "longtable", "multirow", "multicol",
            "xcolor", "tikz", "pgfplots", "hyperref", "url", "subcaption"
        ]]
        
        for pkg in additional:
            imports.append(f"\\usepackage{{{pkg}}}")
        
        return "\n".join(imports)
    
    def _generate_bibliography_config(self) -> str:
        """Generate bibliography configuration."""
        if not self.config.bibliography.bib_file:
            return ""
        
        config = []
        
        if self.config.bibliography.biblatex:
            # Use biblatex
            bib_options = []
            bib_options.append(f"backend={self.config.bibliography.backend}")
            bib_options.append(f"style={self.config.bibliography.style}")
            bib_options.append(f"sorting={self.config.bibliography.sorting}")
            bib_options.append(f"maxnames={self.config.bibliography.max_names}")
            bib_options.append(f"minnames={self.config.bibliography.min_names}")
            
            config.append(f"\\usepackage[{','.join(bib_options)}]{{biblatex}}")
            config.append(f"\\addbibresource{{{self.config.bibliography.bib_file}}}")
        elif self.config.bibliography.natbib:
            # Use natbib
            config.append("\\usepackage{natbib}")
            config.append(f"\\bibliographystyle{{{self.config.bibliography.style}}}")
        
        return "\n".join(config)
    
    def _generate_tikz_libraries(self) -> str:
        """Generate TikZ library imports."""
        if not self.config.tikz_libraries:
            return ""
        
        libraries = ",".join(self.config.tikz_libraries)
        return f"\\usetikzlibrary{{{libraries}}}"
    
    def _generate_handout_config(self) -> str:
        """Generate handout-specific configuration."""
        if not self.config.generate_handout:
            return ""
        
        config = []
        
        # Page layout for handouts
        if self.config.handout_layout == HandoutLayout.ONE_PER_PAGE:
            config.append("\\usepackage{pgfpages}")
            config.append("\\pgfpagesuselayout{resize to}[a4paper,border shrink=5mm,landscape=false]")
        elif self.config.handout_layout == HandoutLayout.TWO_PER_PAGE:
            config.append("\\usepackage{pgfpages}")
            config.append("\\pgfpagesuselayout{2 on 1}[a4paper,border shrink=2mm]")
        elif self.config.handout_layout == HandoutLayout.FOUR_PER_PAGE:
            config.append("\\usepackage{pgfpages}")
            config.append("\\pgfpagesuselayout{4 on 1}[a4paper,border shrink=2mm,landscape]")
        elif self.config.handout_layout == HandoutLayout.SIX_PER_PAGE:
            config.append("\\usepackage{pgfpages}")
            config.append("\\pgfpagesuselayout{6 on 1}[a4paper,border shrink=2mm]")
        elif self.config.handout_layout == HandoutLayout.NINE_PER_PAGE:
            config.append("\\usepackage{pgfpages}")
            config.append("\\pgfpagesuselayout{9 on 1}[a4paper,border shrink=1mm]")
        
        # Notes configuration
        if self.config.handout_notes:
            config.append("\\setbeameroption{show notes}")
        
        return "\n".join(config)
    
    def _generate_toc_frame(self) -> str:
        """Generate table of contents frame."""
        return """
\\begin{frame}{Outline}
    \\tableofcontents
\\end{frame}
"""
    
    def generate_slide_content(self, slide: BeamerSlide) -> str:
        """Generate content for a single slide."""
        # Frame options
        frame_options = ""
        if slide.frame_options:
            frame_options = f"[{','.join(slide.frame_options)}]"
        
        # Subtitle
        subtitle = ""
        if slide.subtitle:
            subtitle = f"{{{self._escape_latex(slide.subtitle)}}}"
        
        # Build content sections
        content_parts = []
        
        # Main content
        if slide.content:
            content_parts.append(self._process_content(slide.content))
        
        # Figures
        for figure in slide.figures:
            content_parts.append(self._generate_figure(figure))
        
        # Tables
        for table in slide.tables:
            content_parts.append(self._generate_table(table))
        
        # Equations
        for equation in slide.equations:
            content_parts.append(self._generate_equation(equation))
        
        # Overlays
        for overlay in slide.overlays:
            content_parts.append(overlay)
        
        content = "\n\n".join(content_parts)
        
        # Notes
        notes = ""
        if slide.notes:
            notes = f"\\note{{{self._escape_latex(slide.notes)}}}"
        
        return self.template_manager.get_frame_template().format(
            frame_options=frame_options,
            title=self._escape_latex(slide.title),
            subtitle=subtitle,
            content=content,
            notes=notes
        )
    
    def _generate_figure(self, figure: BeamerFigure) -> str:
        """Generate LaTeX code for a figure."""
        # Handle subfigures
        if figure.subfigures:
            subfig_content = []
            for i, subfig in enumerate(figure.subfigures):
                caption_text = f"\\caption{{{self._escape_latex(subfig.caption)}}}" if subfig.caption else ""
                label_text = f"\\label{{{subfig.label}}}" if subfig.label else ""
                subfig_latex = f"""
    \\begin{{subfigure}}[b]{{{subfig.width}}}
        \\centering
        \\includegraphics[width=\\textwidth]{{{subfig.path}}}
        {caption_text}
        {label_text}
    \\end{{subfigure}}"""
                subfig_content.append(subfig_latex)
            
            subfigures_content = "\n".join(subfig_content)
        else:
            # Single figure
            width_height = f"width={figure.width}"
            if figure.height:
                width_height += f",height={figure.height}"
            
            subfigures_content = f"\\includegraphics[{width_height}]{{{figure.path}}}"
        
        # Apply overlay if specified
        if figure.overlay:
            subfigures_content = f"\\only{figure.overlay}{{{subfigures_content}}}"
        
        # Caption and label
        caption = f"\\caption{{{self._escape_latex(figure.caption)}}}" if figure.caption else ""
        label = f"\\label{{{figure.label}}}" if figure.label else ""
        
        return self.template_manager.get_figure_template().format(
            position=figure.position,
            subfigures_or_single=subfigures_content,
            caption=caption,
            label=label
        )
    
    def _generate_table(self, table: BeamerTable) -> str:
        """Generate LaTeX code for a table."""
        # Determine column specification
        if table.column_spec:
            column_spec = table.column_spec
        else:
            # Auto-generate column spec
            num_cols = len(table.headers) if table.headers else len(table.data[0])
            column_spec = "l" * num_cols
        
        # Table environment
        table_env = "tabular"
        
        # Build table content
        content_lines = []
        
        if table.booktabs:
            content_lines.append("\\toprule")
        
        # Headers
        if table.headers:
            header_line = " & ".join([self._escape_latex(h) for h in table.headers])
            content_lines.append(f"{header_line} " + "\\\\")
            if table.booktabs:
                content_lines.append("\\midrule")
            else:
                content_lines.append("\\hline")
        
        # Data rows
        for row in table.data:
            row_line = " & ".join([self._escape_latex(str(cell)) for cell in row])
            content_lines.append(f"{row_line} " + "\\\\")
        
        if table.booktabs:
            content_lines.append("\\bottomrule")
        else:
            content_lines.append("\\hline")
        
        table_content = "\n        ".join(content_lines)
        
        # Apply overlay if specified
        if table.overlay:
            table_content = f"\\only{table.overlay}" + "{{\n        " + table_content + "\n    }}"
        
        # Caption positioning (top or bottom)
        caption_top = ""
        caption_bottom = ""
        if table.caption:
            caption_latex = f"\\caption{{{self._escape_latex(table.caption)}}}"
            # For tables, caption typically goes on top
            caption_top = caption_latex
        
        label = f"\\label{{{table.label}}}" if table.label else ""
        
        return self.template_manager.get_table_template().format(
            position=table.position,
            caption_top=caption_top,
            table_env=table_env,
            column_spec=column_spec,
            table_content=table_content,
            caption_bottom=caption_bottom,
            label=label
        )
    
    def _generate_equation(self, equation: str) -> str:
        """Generate LaTeX code for an equation."""
        # Check if equation is already wrapped in math environment
        math_envs = ["equation", "align", "gather", "multline", "split", "eqnarray"]
        
        for env in math_envs:
            if f"\\begin{{{env}}}" in equation:
                return equation
        
        # Check for inline math
        if equation.startswith("$") and equation.endswith("$"):
            return equation
        
        # Check for display math
        if equation.startswith("$$") and equation.endswith("$$"):
            return equation
        
        # Wrap in equation environment
        if "=" in equation and "\\\\" not in equation:
            return "\\begin{equation}\n" + equation + "\n\\end{equation}"
        elif "\\\\" in equation:
            return "\\begin{align}\n" + equation + "\n\\end{align}"
        else:
            return "\\[ " + equation + " \\]"
    
    def _process_content(self, content: str) -> str:
        """Process slide content, handling citations and special formatting."""
        # Handle citations
        content = self._process_citations(content)
        
        # Handle itemize/enumerate conversion
        content = self._process_lists(content)
        
        # Handle emphasis
        content = self._process_emphasis(content)
        
        return content
    
    def _process_citations(self, content: str) -> str:
        """Process citations in content."""
        # Find citation patterns like [Author2023] or [@author2023]
        citation_patterns = [
            r'\[@([^]]+)\]',  # [@author2023]
            r'\[([a-zA-Z][^]]*\d{4}[^]]*)\]'  # [Author2023] or [author2023]
        ]
        
        for pattern in citation_patterns:
            matches = re.findall(pattern, content)
            for match in matches:
                self.add_citation(match)
                if self.config.bibliography.biblatex:
                    content = content.replace(f'[{match}]', f'\\cite{{{match}}}')
                    content = content.replace(f'[@{match}]', f'\\cite{{{match}}}')
                else:
                    content = content.replace(f'[{match}]', f'\\citep{{{match}}}')
                    content = content.replace(f'[@{match}]', f'\\citep{{{match}}}')
        
        return content
    
    def _process_lists(self, content: str) -> str:
        """Convert markdown-style lists to LaTeX."""
        lines = content.split('\n')
        processed_lines = []
        in_itemize = False
        in_enumerate = False
        
        for line in lines:
            stripped = line.strip()
            
            # Check for bullet points
            if stripped.startswith('- ') or stripped.startswith('* '):
                if not in_itemize:
                    processed_lines.append('\\begin{itemize}')
                    in_itemize = True
                if in_enumerate:
                    processed_lines.append('\\end{enumerate}')
                    in_enumerate = False
                item_text = stripped[2:].strip()
                processed_lines.append(f'  \\item {item_text}')
            
            # Check for numbered lists
            elif re.match(r'^\d+\.\s', stripped):
                if not in_enumerate:
                    processed_lines.append('\\begin{enumerate}')
                    in_enumerate = True
                if in_itemize:
                    processed_lines.append('\\end{itemize}')
                    in_itemize = False
                item_text = re.sub(r'^\d+\.\s', '', stripped)
                processed_lines.append(f'  \\item {item_text}')
            
            else:
                # Close any open lists
                if in_itemize:
                    processed_lines.append('\\end{itemize}')
                    in_itemize = False
                if in_enumerate:
                    processed_lines.append('\\end{enumerate}')
                    in_enumerate = False
                processed_lines.append(line)
        
        # Close any remaining open lists
        if in_itemize:
            processed_lines.append('\\end{itemize}')
        if in_enumerate:
            processed_lines.append('\\end{enumerate}')
        
        return '\n'.join(processed_lines)
    
    def _process_emphasis(self, content: str) -> str:
        """Convert markdown emphasis to LaTeX."""
        # Bold text
        content = re.sub(r'\*\*(.*?)\*\*', r'\\textbf{\1}', content)
        content = re.sub(r'__(.*?)__', r'\\textbf{\1}', content)
        
        # Italic text
        content = re.sub(r'\*(.*?)\*', r'\\textit{\1}', content)
        content = re.sub(r'_(.*?)_', r'\\textit{\1}', content)
        
        # Code
        content = re.sub(r'`(.*?)`', r'\\texttt{\1}', content)
        
        return content
    
    def _generate_bibliography_frame(self) -> str:
        """Generate bibliography frame if citations are used."""
        if not self.citations or not self.config.bibliography.bib_file:
            return ""
        
        if self.config.bibliography.biblatex:
            return """
\\begin{frame}[allowframebreaks]{References}
    \\printbibliography
\\end{frame}
"""
        else:
            return f"""
\\begin{{frame}}[allowframebreaks]{{References}}
    \\bibliography{{{self.config.bibliography.bib_file.replace('.bib', '')}}}
\\end{{frame}}
"""
    
    def generate_latex(self) -> str:
        """Generate complete LaTeX document."""
        # Generate slide content
        slide_contents = []
        for slide in self.slides:
            slide_contents.append(self.generate_slide_content(slide))
        
        content = "\n\n".join(slide_contents)
        
        # Generate bibliography frame
        bibliography_frame = self._generate_bibliography_frame()
        
        # Generate preamble with actual content
        preamble_template = self.generate_preamble()
        
        # Replace placeholders in the preamble
        document = preamble_template.replace("{content}", content)
        document = document.replace("{bibliography_frame}", bibliography_frame)
        
        return document
    
    def save_latex(self, output_path: str) -> str:
        """Save LaTeX document to file."""
        latex_content = self.generate_latex()
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(latex_content)
        
        logger.info(f"LaTeX document saved to: {output_path}")
        return output_path
    
    def compile_pdf(self, latex_path: str, output_dir: Optional[str] = None, 
                   clean_aux: bool = True) -> Tuple[str, bool]:
        """
        Compile LaTeX to PDF using pdflatex or lualatex.
        
        Returns:
            Tuple of (pdf_path, success)
        """
        if output_dir is None:
            output_dir = os.path.dirname(latex_path)
        
        # Create temporary working directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Copy LaTeX file to temp directory
            temp_latex = os.path.join(temp_dir, os.path.basename(latex_path))
            shutil.copy2(latex_path, temp_latex)
            
            # Copy bibliography file if exists
            if self.config.bibliography.bib_file:
                bib_source = os.path.join(os.path.dirname(latex_path), 
                                        self.config.bibliography.bib_file)
                if os.path.exists(bib_source):
                    bib_dest = os.path.join(temp_dir, self.config.bibliography.bib_file)
                    shutil.copy2(bib_source, bib_dest)
            
            try:
                # Choose compiler
                compiler = "pdflatex"
                if any("fontspec" in cmd for cmd in self.config.custom_commands):
                    compiler = "lualatex"
                
                # First compilation
                result = subprocess.run([
                    compiler,
                    "-interaction=nonstopmode",
                    "-output-directory", temp_dir,
                    temp_latex
                ], capture_output=True, text=True, cwd=temp_dir)
                
                if result.returncode != 0:
                    logger.error(f"First LaTeX compilation failed: {result.stderr}")
                    return "", False
                
                # Run bibliography if needed
                if self.citations and self.config.bibliography.bib_file:
                    if self.config.bibliography.backend == "biber":
                        biber_result = subprocess.run([
                            "biber",
                            os.path.splitext(os.path.basename(temp_latex))[0]
                        ], capture_output=True, text=True, cwd=temp_dir)
                        
                        if biber_result.returncode != 0:
                            logger.warning(f"Biber failed: {biber_result.stderr}")
                    else:
                        bibtex_result = subprocess.run([
                            "bibtex",
                            os.path.splitext(os.path.basename(temp_latex))[0]
                        ], capture_output=True, text=True, cwd=temp_dir)
                        
                        if bibtex_result.returncode != 0:
                            logger.warning(f"BibTeX failed: {bibtex_result.stderr}")
                    
                    # Second compilation for bibliography
                    subprocess.run([
                        compiler,
                        "-interaction=nonstopmode",
                        "-output-directory", temp_dir,
                        temp_latex
                    ], capture_output=True, text=True, cwd=temp_dir)
                
                # Final compilation for cross-references
                final_result = subprocess.run([
                    compiler,
                    "-interaction=nonstopmode", 
                    "-output-directory", temp_dir,
                    temp_latex
                ], capture_output=True, text=True, cwd=temp_dir)
                
                if final_result.returncode != 0:
                    logger.error(f"Final LaTeX compilation failed: {final_result.stderr}")
                    return "", False
                
                # Copy PDF to output directory
                pdf_name = os.path.splitext(os.path.basename(latex_path))[0] + ".pdf"
                temp_pdf = os.path.join(temp_dir, pdf_name)
                output_pdf = os.path.join(output_dir, pdf_name)
                
                if os.path.exists(temp_pdf):
                    shutil.copy2(temp_pdf, output_pdf)
                    logger.info(f"PDF compiled successfully: {output_pdf}")
                    return output_pdf, True
                else:
                    logger.error("PDF file not found after compilation")
                    return "", False
                    
            except Exception as e:
                logger.error(f"Error during compilation: {str(e)}")
                return "", False
    
    def generate_handout(self, latex_path: str, output_dir: Optional[str] = None) -> Tuple[str, bool]:
        """Generate handout version of the presentation."""
        if not self.config.generate_handout:
            logger.warning("Handout generation not enabled in configuration")
            return "", False
        
        # Modify config for handout
        original_handout = self.config.generate_handout
        self.config.generate_handout = True
        
        try:
            # Generate handout LaTeX
            handout_latex = self.generate_latex()
            
            # Save handout LaTeX
            handout_path = latex_path.replace('.tex', '_handout.tex')
            with open(handout_path, 'w', encoding='utf-8') as f:
                f.write(handout_latex)
            
            # Compile handout PDF
            handout_pdf, success = self.compile_pdf(handout_path, output_dir)
            
            return handout_pdf, success
            
        finally:
            # Restore original config
            self.config.generate_handout = original_handout
    
    def _escape_latex(self, text: str) -> str:
        """Escape special LaTeX characters."""
        if not isinstance(text, str):
            text = str(text)
        
        # LaTeX special characters
        replacements = {
            '\\': '\\textbackslash{}',
            '{': '\\{',
            '}': '\\}',
            '_': '\\_',
            '^': '\\textasciicircum{}',
            '#': '\\#',
            '&': '\\&',
            '$': '\\$',
            '%': '\\%',
            '~': '\\textasciitilde{}'
        }
        
        for char, replacement in replacements.items():
            text = text.replace(char, replacement)
        
        return text
    
    def validate_config(self) -> List[str]:
        """Validate the Beamer configuration and return any issues."""
        issues = []
        
        # Check required fields
        if not self.config.title:
            issues.append("Title is required")
        if not self.config.author:
            issues.append("Author is required")
        
        # Check bibliography configuration
        if self.config.bibliography.bib_file:
            if not os.path.exists(self.config.bibliography.bib_file):
                issues.append(f"Bibliography file not found: {self.config.bibliography.bib_file}")
        
        # Check aspect ratio
        valid_ratios = ["4:3", "16:9", "14:9", "16:10", "3:2", "5:4"]
        if self.config.aspect_ratio not in valid_ratios:
            issues.append(f"Invalid aspect ratio: {self.config.aspect_ratio}")
        
        # Check font size
        valid_sizes = ["8pt", "9pt", "10pt", "11pt", "12pt", "14pt", "17pt", "20pt"]
        if self.config.font_size not in valid_sizes:
            issues.append(f"Invalid font size: {self.config.font_size}")
        
        return issues
    
    def get_package_requirements(self) -> Dict[str, str]:
        """Get LaTeX package requirements and their purposes."""
        requirements = {
            "beamer": "Core presentation class",
            "inputenc": "Input encoding (UTF-8)",
            "fontenc": "Font encoding (T1)",
            "babel": "Language support",
            "amsmath": "Advanced math environments",
            "amsfonts": "AMS math fonts",
            "amssymb": "AMS math symbols",
            "graphicx": "Graphics inclusion",
            "booktabs": "Professional table formatting",
            "array": "Enhanced array and tabular",
            "longtable": "Multi-page tables",
            "multirow": "Multi-row table cells",
            "multicol": "Multi-column layouts",
            "xcolor": "Color support",
            "tikz": "Graphics and diagrams",
            "pgfplots": "Data plotting",
            "hyperref": "Hyperlinks and PDF features",
            "url": "URL formatting",
            "subcaption": "Subfigure captions"
        }
        
        if self.config.bibliography.biblatex:
            requirements["biblatex"] = "Modern bibliography system"
            requirements["biber"] = "Bibliography processor"
        elif self.config.bibliography.natbib:
            requirements["natbib"] = "Natural bibliography system"
        
        if self.config.generate_handout:
            requirements["pgfpages"] = "Multiple pages per sheet"
        
        return requirements


# Example usage and factory functions
def create_academic_presentation(title: str, author: str, institute: str = None) -> BeamerGenerator:
    """Create a standard academic presentation configuration."""
    config = BeamerConfig(
        title=title,
        author=author,
        institute=institute,
        theme=BeamerTheme.BERLIN,
        color_theme=ColorTheme.DEFAULT,
        aspect_ratio="16:9",
        font_size="11pt",
        generate_handout=True,
        handout_layout=HandoutLayout.FOUR_PER_PAGE
    )
    
    # Enable bibliography
    config.bibliography.biblatex = True
    config.bibliography.style = "authoryear"
    
    return BeamerGenerator(config)


def create_math_presentation(title: str, author: str) -> BeamerGenerator:
    """Create a presentation optimized for mathematical content."""
    config = BeamerConfig(
        title=title,
        author=author,
        theme=BeamerTheme.WARSAW,
        color_theme=ColorTheme.CRANE,
        packages=[
            "inputenc", "fontenc", "babel", "amsmath", "amsfonts", "amssymb", "amsthm",
            "mathtools", "physics", "bm", "graphicx", "tikz", "pgfplots"
        ],
        custom_commands=[
            "\\newcommand{\\R}{\\mathbb{R}}",
            "\\newcommand{\\C}{\\mathbb{C}}",
            "\\newcommand{\\N}{\\mathbb{N}}",
            "\\newcommand{\\Z}{\\mathbb{Z}}",
            "\\DeclareMathOperator{\\Tr}{Tr}",
        ],
        tikz_libraries=["calc", "patterns", "decorations.pathreplacing"]
    )
    
    return BeamerGenerator(config)


if __name__ == "__main__":
    # Example usage
    generator = create_academic_presentation(
        title="Advanced Machine Learning Techniques",
        author="Dr. Jane Smith",
        institute="University of Excellence"
    )
    
    # Add some example slides
    title_slide = BeamerSlide(
        title="Introduction",
        content="""
        This presentation covers:
        - Deep learning fundamentals
        - Neural network architectures  
        - Recent advances in the field
        
        **Key contributions:**
        - Novel attention mechanism
        - Improved training stability
        - State-of-the-art results on benchmark datasets
        """
    )
    
    generator.add_slide(title_slide)
    
    # Generate and save
    latex_content = generator.generate_latex()
    print("Generated LaTeX document successfully!")