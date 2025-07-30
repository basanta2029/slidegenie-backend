"""
Equation rendering utilities for LaTeX mathematical expressions.

Provides functionality to render LaTeX equations to various formats:
- PNG/SVG images using matplotlib
- MathML conversion
- Plain text representation
- Equation analysis and structure extraction
"""

import re
import base64
from io import BytesIO
from typing import List, Dict, Optional, Any, Tuple, Union
from dataclasses import dataclass
import structlog

# Optional imports for equation rendering
try:
    import matplotlib.pyplot as plt
    import matplotlib.patches as patches
    from matplotlib.patches import Rectangle
    import numpy as np
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False
    plt = None
    patches = None
    Rectangle = None
    np = None

try:
    from sympy import latex, sympify, symbols, parse_latex
    from sympy.parsing.latex import parse_latex as sympy_parse_latex
    SYMPY_AVAILABLE = True
except ImportError:
    SYMPY_AVAILABLE = False
    latex = None
    sympify = None
    symbols = None
    parse_latex = None

logger = structlog.get_logger(__name__)


@dataclass
class EquationInfo:
    """Information about a parsed equation."""
    latex_code: str
    equation_type: str  # inline, display, align, etc.
    variables: List[str]
    functions: List[str]
    operators: List[str]
    complexity_score: float
    has_fractions: bool
    has_integrals: bool
    has_summations: bool
    has_matrices: bool
    has_subscripts: bool
    has_superscripts: bool
    line_count: int = 1


@dataclass
class RenderedEquation:
    """A rendered equation with multiple formats."""
    latex_code: str
    png_data: Optional[bytes] = None
    svg_data: Optional[str] = None
    mathml: Optional[str] = None
    plain_text: Optional[str] = None
    width: Optional[int] = None
    height: Optional[int] = None
    baseline: Optional[int] = None
    info: Optional[EquationInfo] = None


class EquationParser:
    """Parses LaTeX equations to extract structure and information."""
    
    # Common mathematical functions
    MATH_FUNCTIONS = {
        'sin', 'cos', 'tan', 'sec', 'csc', 'cot',
        'arcsin', 'arccos', 'arctan', 'sinh', 'cosh', 'tanh',
        'log', 'ln', 'lg', 'exp', 'sqrt', 'lim', 'max', 'min',
        'det', 'dim', 'ker', 'gcd', 'lcm', 'sup', 'inf'
    }
    
    # Mathematical operators
    OPERATORS = {
        '+', '-', '*', '/', '=', '<', '>', '≤', '≥', '≠', '≈', '∝',
        '∞', '∂', '∇', '∆', '∫', '∮', '∑', '∏', '⋃', '⋂', '∈', '∉',
        '⊂', '⊃', '⊆', '⊇', '∧', '∨', '¬', '⇒', '⇔', '∀', '∃'
    }
    
    def __init__(self):
        self.variable_pattern = re.compile(r'\\?[a-zA-Z](?:_\{[^}]*\})?(?:\^\{[^}]*\})?')
        self.function_pattern = re.compile(r'\\(' + '|'.join(self.MATH_FUNCTIONS) + r')\b')
        self.operator_pattern = re.compile(r'[+\-*/=<>≤≥≠≈∝∞∂∇∆∫∮∑∏⋃⋂∈∉⊂⊃⊆⊇∧∨¬⇒⇔∀∃]')
        
    def parse_equation(self, latex_code: str, equation_type: str = "display") -> EquationInfo:
        """Parse a LaTeX equation and extract structural information."""
        # Clean the latex code
        cleaned_code = self._clean_latex(latex_code)
        
        # Extract variables
        variables = self._extract_variables(cleaned_code)
        
        # Extract functions
        functions = self._extract_functions(cleaned_code)
        
        # Extract operators
        operators = self._extract_operators(cleaned_code)
        
        # Analyze structure
        has_fractions = '\\frac' in cleaned_code or '\\dfrac' in cleaned_code or '\\tfrac' in cleaned_code
        has_integrals = any(integral in cleaned_code for integral in ['\\int', '\\iint', '\\iiint', '\\oint'])
        has_summations = any(sum_op in cleaned_code for sum_op in ['\\sum', '\\prod'])
        has_matrices = any(matrix in cleaned_code for matrix in ['\\matrix', '\\pmatrix', '\\bmatrix', '\\Bmatrix', '\\vmatrix', '\\Vmatrix'])
        has_subscripts = '_' in cleaned_code
        has_superscripts = '^' in cleaned_code
        
        # Calculate complexity score
        complexity_score = self._calculate_complexity(
            len(variables), len(functions), len(operators),
            has_fractions, has_integrals, has_summations, has_matrices
        )
        
        # Count lines (for multi-line equations)
        line_count = max(1, cleaned_code.count('\\\\') + 1)
        
        return EquationInfo(
            latex_code=latex_code,
            equation_type=equation_type,
            variables=variables,
            functions=functions,
            operators=operators,
            complexity_score=complexity_score,
            has_fractions=has_fractions,
            has_integrals=has_integrals,
            has_summations=has_summations,
            has_matrices=has_matrices,
            has_subscripts=has_subscripts,
            has_superscripts=has_superscripts,
            line_count=line_count
        )
    
    def _clean_latex(self, latex_code: str) -> str:
        """Clean LaTeX code for analysis."""
        # Remove comments
        latex_code = re.sub(r'%.*', '', latex_code)
        
        # Remove extra whitespace
        latex_code = re.sub(r'\s+', ' ', latex_code).strip()
        
        return latex_code
    
    def _extract_variables(self, latex_code: str) -> List[str]:
        """Extract mathematical variables from LaTeX code."""
        variables = set()
        
        # Find single letters that could be variables
        # This is a simplified approach - more sophisticated parsing would be needed
        matches = re.findall(r'(?<!\\)[a-zA-Z](?:_\{[^}]*\})?(?:\^\{[^}]*\})?', latex_code)
        
        for match in matches:
            # Filter out known functions and commands
            base_var = re.match(r'([a-zA-Z]+)', match)
            if base_var and base_var.group(1) not in self.MATH_FUNCTIONS:
                variables.add(match)
        
        return sorted(list(variables))
    
    def _extract_functions(self, latex_code: str) -> List[str]:
        """Extract mathematical functions from LaTeX code."""
        functions = set()
        
        matches = self.function_pattern.findall(latex_code)
        functions.update(matches)
        
        return sorted(list(functions))
    
    def _extract_operators(self, latex_code: str) -> List[str]:
        """Extract mathematical operators from LaTeX code."""
        operators = set()
        
        # Direct operator symbols
        matches = self.operator_pattern.findall(latex_code)
        operators.update(matches)
        
        # LaTeX operator commands
        latex_operators = re.findall(r'\\(leq|geq|neq|approx|propto|infty|partial|nabla|Delta|int|oint|sum|prod|cup|cap|in|notin|subset|supset|subseteq|supseteq|wedge|vee|neg|Rightarrow|Leftrightarrow|forall|exists)', latex_code)
        operators.update(latex_operators)
        
        return sorted(list(operators))
    
    def _calculate_complexity(self, var_count: int, func_count: int, op_count: int, 
                            has_fractions: bool, has_integrals: bool, 
                            has_summations: bool, has_matrices: bool) -> float:
        """Calculate equation complexity score."""
        base_score = var_count * 0.5 + func_count * 1.0 + op_count * 0.3
        
        structure_bonus = 0
        if has_fractions:
            structure_bonus += 2.0
        if has_integrals:
            structure_bonus += 3.0
        if has_summations:
            structure_bonus += 2.5
        if has_matrices:
            structure_bonus += 3.5
        
        return base_score + structure_bonus


class EquationRenderer:
    """Renders LaTeX equations to various formats."""
    
    def __init__(self, dpi: int = 150, font_size: int = 12):
        self.dpi = dpi
        self.font_size = font_size
        self.parser = EquationParser()
        
        if not MATPLOTLIB_AVAILABLE:
            logger.warning("matplotlib not available, image rendering disabled")
    
    def render_equation(self, latex_code: str, equation_type: str = "display", 
                       formats: List[str] = None) -> RenderedEquation:
        """Render equation to multiple formats."""
        if formats is None:
            formats = ['png', 'plain_text']
        
        # Parse equation information
        info = self.parser.parse_equation(latex_code, equation_type)
        
        rendered = RenderedEquation(
            latex_code=latex_code,
            info=info
        )
        
        # Render to requested formats
        if 'png' in formats and MATPLOTLIB_AVAILABLE:
            try:
                png_data, width, height, baseline = self._render_to_png(latex_code, equation_type)
                rendered.png_data = png_data
                rendered.width = width
                rendered.height = height
                rendered.baseline = baseline
            except Exception as e:
                logger.error(f"Failed to render equation to PNG: {e}")
        
        if 'svg' in formats and MATPLOTLIB_AVAILABLE:
            try:
                rendered.svg_data = self._render_to_svg(latex_code, equation_type)
            except Exception as e:
                logger.error(f"Failed to render equation to SVG: {e}")
        
        if 'mathml' in formats:
            try:
                rendered.mathml = self._convert_to_mathml(latex_code)
            except Exception as e:
                logger.error(f"Failed to convert equation to MathML: {e}")
        
        if 'plain_text' in formats:
            rendered.plain_text = self._convert_to_plain_text(latex_code)
        
        return rendered
    
    def _render_to_png(self, latex_code: str, equation_type: str) -> Tuple[bytes, int, int, int]:
        """Render equation to PNG image."""
        if not MATPLOTLIB_AVAILABLE:
            raise ImportError("matplotlib is not available")
        
        # Set up matplotlib for LaTeX rendering
        plt.rcParams['text.usetex'] = True
        plt.rcParams['font.family'] = 'serif'
        plt.rcParams['font.size'] = self.font_size
        
        # Create figure
        fig, ax = plt.subplots(figsize=(10, 3))
        ax.axis('off')
        
        # Prepare LaTeX string
        if equation_type == 'inline':
            latex_string = f'${latex_code}$'
        else:
            latex_string = f'$\\displaystyle {latex_code}$'
        
        # Render equation
        text = ax.text(0.5, 0.5, latex_string, transform=ax.transAxes,
                      fontsize=self.font_size, ha='center', va='center')
        
        # Get tight bounding box
        fig.canvas.draw()
        bbox = text.get_window_extent(renderer=fig.canvas.get_renderer())
        
        # Convert to data coordinates
        bbox_data = bbox.transformed(ax.transData.inverted())
        
        # Set figure size based on content
        width_inches = bbox_data.width * 1.2
        height_inches = bbox_data.height * 1.2
        fig.set_size_inches(width_inches, height_inches)
        
        # Save to bytes
        buffer = BytesIO()
        fig.savefig(buffer, format='png', dpi=self.dpi, bbox_inches='tight', 
                   pad_inches=0.1, transparent=True)
        plt.close(fig)
        
        buffer.seek(0)
        png_data = buffer.getvalue()
        
        # Calculate dimensions
        width = int(width_inches * self.dpi)
        height = int(height_inches * self.dpi)
        baseline = int(height * 0.5)  # Approximation
        
        return png_data, width, height, baseline
    
    def _render_to_svg(self, latex_code: str, equation_type: str) -> str:
        """Render equation to SVG format."""
        if not MATPLOTLIB_AVAILABLE:
            raise ImportError("matplotlib is not available")
        
        # Similar to PNG rendering but save as SVG
        plt.rcParams['text.usetex'] = True
        plt.rcParams['font.family'] = 'serif'
        plt.rcParams['font.size'] = self.font_size
        
        fig, ax = plt.subplots(figsize=(10, 3))
        ax.axis('off')
        
        if equation_type == 'inline':
            latex_string = f'${latex_code}$'
        else:
            latex_string = f'$\\displaystyle {latex_code}$'
        
        ax.text(0.5, 0.5, latex_string, transform=ax.transAxes,
               fontsize=self.font_size, ha='center', va='center')
        
        buffer = BytesIO()
        fig.savefig(buffer, format='svg', bbox_inches='tight', 
                   pad_inches=0.1, transparent=True)
        plt.close(fig)
        
        buffer.seek(0)
        svg_data = buffer.getvalue().decode('utf-8')
        
        return svg_data
    
    def _convert_to_mathml(self, latex_code: str) -> str:
        """Convert LaTeX to MathML (basic conversion)."""
        # This would require a proper LaTeX to MathML converter
        # For now, provide a basic template
        return f'<math xmlns="http://www.w3.org/1998/Math/MathML"><mtext>{latex_code}</mtext></math>'
    
    def _convert_to_plain_text(self, latex_code: str) -> str:
        """Convert LaTeX to plain text representation."""
        # Basic conversion - remove LaTeX commands and braces
        text = latex_code
        
        # Replace common LaTeX commands with text equivalents
        text = re.sub(r'\\frac\{([^}]+)\}\{([^}]+)\}', r'(\1)/(\2)', text)
        text = re.sub(r'\\sqrt\{([^}]+)\}', r'sqrt(\1)', text)
        text = re.sub(r'\\sum', 'sum', text)
        text = re.sub(r'\\int', 'integral', text)
        text = re.sub(r'\\prod', 'product', text)
        text = re.sub(r'\\lim', 'limit', text)
        text = re.sub(r'\\infty', 'infinity', text)
        text = re.sub(r'\\partial', 'd', text)
        text = re.sub(r'\\alpha', 'alpha', text)
        text = re.sub(r'\\beta', 'beta', text)
        text = re.sub(r'\\gamma', 'gamma', text)
        text = re.sub(r'\\delta', 'delta', text)
        text = re.sub(r'\\epsilon', 'epsilon', text)
        text = re.sub(r'\\theta', 'theta', text)
        text = re.sub(r'\\lambda', 'lambda', text)
        text = re.sub(r'\\mu', 'mu', text)
        text = re.sub(r'\\pi', 'pi', text)
        text = re.sub(r'\\sigma', 'sigma', text)
        text = re.sub(r'\\tau', 'tau', text)
        text = re.sub(r'\\phi', 'phi', text)
        text = re.sub(r'\\omega', 'omega', text)
        
        # Remove remaining LaTeX commands
        text = re.sub(r'\\[a-zA-Z]+', '', text)
        
        # Clean up braces and extra spaces
        text = re.sub(r'[{}]', '', text)
        text = re.sub(r'\s+', ' ', text).strip()
        
        return text


class MathEnvironmentAnalyzer:
    """Analyzes mathematical environments and their structure."""
    
    ENVIRONMENT_TYPES = {
        'equation': {'numbered': True, 'alignment': False, 'multiline': False},
        'equation*': {'numbered': False, 'alignment': False, 'multiline': False},
        'align': {'numbered': True, 'alignment': True, 'multiline': True},
        'align*': {'numbered': False, 'alignment': True, 'multiline': True},
        'alignat': {'numbered': True, 'alignment': True, 'multiline': True},
        'alignat*': {'numbered': False, 'alignment': True, 'multiline': True},
        'gather': {'numbered': True, 'alignment': False, 'multiline': True},
        'gather*': {'numbered': False, 'alignment': False, 'multiline': True},
        'multline': {'numbered': True, 'alignment': False, 'multiline': True},
        'multline*': {'numbered': False, 'alignment': False, 'multiline': True},
        'split': {'numbered': False, 'alignment': True, 'multiline': True},
        'array': {'numbered': False, 'alignment': True, 'multiline': True},
    }
    
    def analyze_environment(self, env_name: str, content: str) -> Dict[str, Any]:
        """Analyze a mathematical environment."""
        env_info = self.ENVIRONMENT_TYPES.get(env_name, {
            'numbered': False, 'alignment': False, 'multiline': False
        })
        
        # Count equations/lines
        lines = content.split('\\\\')
        equation_count = len([line.strip() for line in lines if line.strip()])
        
        # Find alignment points
        alignment_points = content.count('&')
        
        # Find labels
        labels = re.findall(r'\\label\{([^}]+)\}', content)
        
        # Calculate complexity
        parser = EquationParser()
        equation_info = parser.parse_equation(content, env_name)
        
        return {
            'environment_name': env_name,
            'is_numbered': env_info.get('numbered', False),
            'has_alignment': env_info.get('alignment', False),
            'is_multiline': env_info.get('multiline', False),
            'equation_count': equation_count,
            'alignment_points': alignment_points,
            'labels': labels,
            'complexity_score': equation_info.complexity_score,
            'variables': equation_info.variables,
            'functions': equation_info.functions,
            'structure_features': {
                'has_fractions': equation_info.has_fractions,
                'has_integrals': equation_info.has_integrals,
                'has_summations': equation_info.has_summations,
                'has_matrices': equation_info.has_matrices,
                'has_subscripts': equation_info.has_subscripts,
                'has_superscripts': equation_info.has_superscripts
            }
        }