"""
LaTeX parser utilities for tokenization and command/environment recognition.

Provides comprehensive parsing functionality for LaTeX documents including:
- Tokenization of LaTeX source
- Command parsing and argument extraction
- Environment detection and content extraction
- Cross-reference resolution
- Bibliography parsing
"""

import re
from typing import List, Dict, Tuple, Optional, Any, Union, NamedTuple
from dataclasses import dataclass
from enum import Enum
import structlog

logger = structlog.get_logger(__name__)


class TokenType(Enum):
    """Types of LaTeX tokens."""
    COMMAND = "command"
    ENVIRONMENT_BEGIN = "env_begin"
    ENVIRONMENT_END = "env_end"
    TEXT = "text"
    MATH_INLINE = "math_inline"
    MATH_DISPLAY = "math_display"
    COMMENT = "comment"
    WHITESPACE = "whitespace"
    BRACE_OPEN = "brace_open"
    BRACE_CLOSE = "brace_close"
    BRACKET_OPEN = "bracket_open"
    BRACKET_CLOSE = "bracket_close"
    SPECIAL_CHAR = "special_char"
    NEWLINE = "newline"
    PARAMETER = "parameter"


@dataclass
class LaTeXToken:
    """A LaTeX token with position information."""
    type: TokenType
    content: str
    line: int
    column: int
    position: int
    raw_content: str = ""
    
    def __repr__(self):
        return f"LaTeXToken({self.type.value}, {repr(self.content)}, {self.line}:{self.column})"


@dataclass
class LaTeXCommand:
    """A parsed LaTeX command with arguments."""
    name: str
    arguments: List[str]
    optional_args: List[str]
    position: int
    line: int
    column: int
    raw_content: str
    star_form: bool = False


@dataclass
class LaTeXEnvironment:
    """A parsed LaTeX environment."""
    name: str
    begin_args: List[str]
    begin_optional_args: List[str]
    content: str
    begin_position: int
    end_position: int
    begin_line: int
    begin_column: int
    end_line: int
    end_column: int
    raw_content: str
    nested_environments: List['LaTeXEnvironment'] = None
    
    def __post_init__(self):
        if self.nested_environments is None:
            self.nested_environments = []


class LaTeXTokenizer:
    """Tokenizes LaTeX source code into structured tokens."""
    
    # LaTeX command pattern
    COMMAND_PATTERN = re.compile(r'\\([a-zA-Z]+\*?|[^a-zA-Z\s])')
    
    # Math delimiters
    MATH_INLINE_DELIMS = [('$', '$'), (r'\(', r'\)')]
    MATH_DISPLAY_DELIMS = [('$$', '$$'), (r'\[', r'\]')]
    
    # Special characters that need escaping
    SPECIAL_CHARS = {'{', '}', '[', ']', '%', '\\', '#', '$', '^', '_', '&', '~'}
    
    def __init__(self):
        self.tokens: List[LaTeXToken] = []
        self.position = 0
        self.line = 1
        self.column = 1
        self.source = ""
        
    def tokenize(self, source: str) -> List[LaTeXToken]:
        """Tokenize LaTeX source code."""
        self.source = source
        self.position = 0
        self.line = 1
        self.column = 1
        self.tokens = []
        
        while self.position < len(self.source):
            self._tokenize_next()
            
        return self.tokens
    
    def _tokenize_next(self):
        """Tokenize the next token."""
        if self.position >= len(self.source):
            return
            
        char = self.source[self.position]
        
        # Handle comments
        if char == '%':
            self._tokenize_comment()
        # Handle commands
        elif char == '\\':
            # Check if it's a command or escaped character
            if self.position + 1 < len(self.source):
                next_char = self.source[self.position + 1]
                if next_char.isalpha():
                    self._tokenize_command()
                elif next_char in self.SPECIAL_CHARS:
                    self._tokenize_escaped_char()
                else:
                    self._tokenize_command()
            else:
                self._add_token(TokenType.SPECIAL_CHAR, char)
                self._advance()
        # Handle math delimiters
        elif char == '$':
            self._tokenize_math()
        # Handle braces
        elif char == '{':
            self._add_token(TokenType.BRACE_OPEN, char)
            self._advance()
        elif char == '}':
            self._add_token(TokenType.BRACE_CLOSE, char)
            self._advance()
        # Handle brackets
        elif char == '[':
            self._add_token(TokenType.BRACKET_OPEN, char)
            self._advance()
        elif char == ']':
            self._add_token(TokenType.BRACKET_CLOSE, char)
            self._advance()
        # Handle newlines
        elif char == '\n':
            self._add_token(TokenType.NEWLINE, char)
            self._advance_line()
        # Handle whitespace
        elif char.isspace():
            self._tokenize_whitespace()
        # Handle regular text
        else:
            self._tokenize_text()
    
    def _tokenize_comment(self):
        """Tokenize a comment line."""
        start_pos = self.position
        start_line = self.line
        start_col = self.column
        
        # Find end of line
        while self.position < len(self.source) and self.source[self.position] != '\n':
            self.position += 1
            self.column += 1
            
        comment_text = self.source[start_pos:self.position]
        self._add_token_at_position(TokenType.COMMENT, comment_text, start_line, start_col, start_pos)
    
    def _tokenize_command(self):
        """Tokenize a LaTeX command."""
        start_pos = self.position
        start_line = self.line
        start_col = self.column
        
        # Skip the backslash
        self.position += 1
        self.column += 1
        
        if self.position >= len(self.source):
            self._add_token_at_position(TokenType.COMMAND, '\\', start_line, start_col, start_pos)
            return
        
        # Get command name
        command_start = self.position
        char = self.source[self.position]
        
        if char.isalpha():
            # Multi-character command
            while (self.position < len(self.source) and 
                   (self.source[self.position].isalpha() or 
                    (self.position == command_start and self.source[self.position] == '*'))):
                self.position += 1
                self.column += 1
        else:
            # Single character command
            self.position += 1
            self.column += 1
        
        command_text = self.source[start_pos:self.position]
        self._add_token_at_position(TokenType.COMMAND, command_text, start_line, start_col, start_pos)
    
    def _tokenize_escaped_char(self):
        """Tokenize an escaped special character."""
        start_pos = self.position
        start_line = self.line
        start_col = self.column
        
        # Include backslash and next character
        self.position += 2
        self.column += 2
        
        escaped_text = self.source[start_pos:self.position]
        self._add_token_at_position(TokenType.SPECIAL_CHAR, escaped_text, start_line, start_col, start_pos)
    
    def _tokenize_math(self):
        """Tokenize math delimiters."""
        if self.position + 1 < len(self.source) and self.source[self.position + 1] == '$':
            # Display math $$
            self._add_token(TokenType.MATH_DISPLAY, '$$')
            self.position += 2
            self.column += 2
        else:
            # Inline math $
            self._add_token(TokenType.MATH_INLINE, '$')
            self._advance()
    
    def _tokenize_whitespace(self):
        """Tokenize continuous whitespace."""
        start_pos = self.position
        start_line = self.line
        start_col = self.column
        
        while (self.position < len(self.source) and 
               self.source[self.position].isspace() and 
               self.source[self.position] != '\n'):
            self.position += 1
            self.column += 1
        
        whitespace_text = self.source[start_pos:self.position]
        self._add_token_at_position(TokenType.WHITESPACE, whitespace_text, start_line, start_col, start_pos)
    
    def _tokenize_text(self):
        """Tokenize regular text."""
        start_pos = self.position
        start_line = self.line
        start_col = self.column
        
        # Continue until we hit a special character
        while (self.position < len(self.source)):
            char = self.source[self.position]
            if (char in self.SPECIAL_CHARS or char.isspace() or 
                char in ['%'] or char == '\\'):
                break
            self.position += 1
            self.column += 1
        
        text_content = self.source[start_pos:self.position]
        if text_content:
            self._add_token_at_position(TokenType.TEXT, text_content, start_line, start_col, start_pos)
    
    def _add_token(self, token_type: TokenType, content: str):
        """Add a token at current position."""
        token = LaTeXToken(
            type=token_type,
            content=content,
            line=self.line,
            column=self.column,
            position=self.position,
            raw_content=content
        )
        self.tokens.append(token)
    
    def _add_token_at_position(self, token_type: TokenType, content: str, line: int, column: int, position: int):
        """Add a token at specified position."""
        token = LaTeXToken(
            type=token_type,
            content=content,
            line=line,
            column=column,
            position=position,
            raw_content=content
        )
        self.tokens.append(token)
    
    def _advance(self):
        """Advance position by one character."""
        self.position += 1
        self.column += 1
    
    def _advance_line(self):
        """Advance to next line."""
        self.position += 1
        self.line += 1
        self.column = 1


class LaTeXParser:
    """Parses tokenized LaTeX source into structured commands and environments."""
    
    # Document structure commands
    SECTIONING_COMMANDS = {
        'part': 0,
        'chapter': 1,
        'section': 2,
        'subsection': 3,
        'subsubsection': 4,
        'paragraph': 5,
        'subparagraph': 6
    }
    
    # Citation commands
    CITATION_COMMANDS = {
        'cite', 'citep', 'citet', 'citealp', 'citealt', 'citeauthor', 'citeyear',
        'footcite', 'parencite', 'textcite', 'autocite', 'fullcite', 'footfullcite'
    }
    
    # Reference commands
    REFERENCE_COMMANDS = {'ref', 'eqref', 'pageref', 'nameref', 'autoref', 'cref', 'Cref'}
    
    # Math environments
    MATH_ENVIRONMENTS = {
        'equation', 'equation*', 'align', 'align*', 'alignat', 'alignat*',
        'gather', 'gather*', 'multline', 'multline*', 'split', 'array',
        'matrix', 'pmatrix', 'bmatrix', 'Bmatrix', 'vmatrix', 'Vmatrix'
    }
    
    # Theorem-like environments
    THEOREM_ENVIRONMENTS = {
        'theorem', 'lemma', 'corollary', 'proposition', 'definition',
        'remark', 'example', 'proof', 'claim', 'conjecture'
    }
    
    def __init__(self, tokens: List[LaTeXToken]):
        self.tokens = tokens
        self.position = 0
        self.commands: List[LaTeXCommand] = []
        self.environments: List[LaTeXEnvironment] = []
        
    def parse(self) -> Tuple[List[LaTeXCommand], List[LaTeXEnvironment]]:
        """Parse tokens into commands and environments."""
        self.position = 0
        self.commands = []
        self.environments = []
        
        while self.position < len(self.tokens):
            token = self.tokens[self.position]
            
            if token.type == TokenType.COMMAND:
                command = self._parse_command()
                if command:
                    self.commands.append(command)
                    
                    # Check if this is a begin command
                    if command.name == 'begin' and command.arguments:
                        env = self._parse_environment(command.arguments[0], command)
                        if env:
                            self.environments.append(env)
            else:
                self.position += 1
        
        return self.commands, self.environments
    
    def _parse_command(self) -> Optional[LaTeXCommand]:
        """Parse a single command with its arguments."""
        if self.position >= len(self.tokens):
            return None
            
        command_token = self.tokens[self.position]
        if command_token.type != TokenType.COMMAND:
            return None
        
        # Extract command name (remove backslash and check for star form)
        command_name = command_token.content[1:]  # Remove backslash
        star_form = command_name.endswith('*')
        if star_form:
            command_name = command_name[:-1]
        
        # Move past command token
        self.position += 1
        
        # Parse arguments
        optional_args = []
        arguments = []
        
        # Skip whitespace
        self._skip_whitespace()
        
        # Parse optional arguments [...]
        while (self.position < len(self.tokens) and 
               self.tokens[self.position].type == TokenType.BRACKET_OPEN):
            arg = self._parse_optional_argument()
            if arg is not None:
                optional_args.append(arg)
            else:
                break
        
        # Parse mandatory arguments {...}
        while (self.position < len(self.tokens) and 
               self.tokens[self.position].type == TokenType.BRACE_OPEN):
            arg = self._parse_mandatory_argument()
            if arg is not None:
                arguments.append(arg)
            else:
                break
        
        return LaTeXCommand(
            name=command_name,
            arguments=arguments,
            optional_args=optional_args,
            position=command_token.position,
            line=command_token.line,
            column=command_token.column,
            raw_content=command_token.raw_content,
            star_form=star_form
        )
    
    def _parse_environment(self, env_name: str, begin_command: LaTeXCommand) -> Optional[LaTeXEnvironment]:
        """Parse an environment from begin to end."""
        begin_pos = self.position
        content_start = self.position
        
        # Find matching \end{env_name}
        nesting_level = 1
        content_tokens = []
        
        while self.position < len(self.tokens) and nesting_level > 0:
            token = self.tokens[self.position]
            
            if token.type == TokenType.COMMAND:
                command = self._peek_command()
                if command and command.name == 'begin':
                    # Check if this begins the same environment type
                    if command.arguments and command.arguments[0] == env_name:
                        nesting_level += 1
                elif command and command.name == 'end':
                    # Check if this ends our environment type
                    if command.arguments and command.arguments[0] == env_name:
                        nesting_level -= 1
                        if nesting_level == 0:
                            # Found the matching end
                            end_command = self._parse_command()
                            break
            
            content_tokens.append(token)
            self.position += 1
        
        if nesting_level > 0:
            # Unmatched environment
            logger.warning(f"Unmatched environment: {env_name}")
            return None
        
        # Extract content
        if content_tokens:
            content_start_pos = content_tokens[0].position
            content_end_pos = content_tokens[-1].position + len(content_tokens[-1].content)
            content = self._extract_source_range(content_start_pos, content_end_pos)
        else:
            content = ""
        
        return LaTeXEnvironment(
            name=env_name,
            begin_args=begin_command.arguments[1:],  # Skip environment name
            begin_optional_args=begin_command.optional_args,
            content=content,
            begin_position=begin_command.position,
            end_position=self.tokens[self.position - 1].position if self.position > 0 else 0,
            begin_line=begin_command.line,
            begin_column=begin_command.column,
            end_line=self.tokens[self.position - 1].line if self.position > 0 else 0,
            end_column=self.tokens[self.position - 1].column if self.position > 0 else 0,
            raw_content=self._extract_source_range(begin_command.position, 
                                                 self.tokens[self.position - 1].position if self.position > 0 else 0)
        )
    
    def _peek_command(self) -> Optional[LaTeXCommand]:
        """Peek at the next command without consuming tokens."""
        saved_pos = self.position
        command = self._parse_command()
        self.position = saved_pos
        return command
    
    def _parse_optional_argument(self) -> Optional[str]:
        """Parse an optional argument [...]."""
        if (self.position >= len(self.tokens) or 
            self.tokens[self.position].type != TokenType.BRACKET_OPEN):
            return None
        
        self.position += 1  # Skip [
        content_tokens = []
        
        # Find closing bracket
        bracket_level = 1
        while self.position < len(self.tokens) and bracket_level > 0:
            token = self.tokens[self.position]
            
            if token.type == TokenType.BRACKET_OPEN:
                bracket_level += 1
            elif token.type == TokenType.BRACKET_CLOSE:
                bracket_level -= 1
                if bracket_level == 0:
                    break
            
            content_tokens.append(token)
            self.position += 1
        
        if bracket_level > 0:
            # Unmatched bracket
            return None
        
        self.position += 1  # Skip ]
        
        # Extract content
        if content_tokens:
            start_pos = content_tokens[0].position
            end_pos = content_tokens[-1].position + len(content_tokens[-1].content)
            return self._extract_source_range(start_pos, end_pos)
        
        return ""
    
    def _parse_mandatory_argument(self) -> Optional[str]:
        """Parse a mandatory argument {...}."""
        if (self.position >= len(self.tokens) or 
            self.tokens[self.position].type != TokenType.BRACE_OPEN):
            return None
        
        self.position += 1  # Skip {
        content_tokens = []
        
        # Find closing brace
        brace_level = 1
        while self.position < len(self.tokens) and brace_level > 0:
            token = self.tokens[self.position]
            
            if token.type == TokenType.BRACE_OPEN:
                brace_level += 1
            elif token.type == TokenType.BRACE_CLOSE:
                brace_level -= 1
                if brace_level == 0:
                    break
            
            content_tokens.append(token)
            self.position += 1
        
        if brace_level > 0:
            # Unmatched brace
            return None
        
        self.position += 1  # Skip }
        
        # Extract content
        if content_tokens:
            start_pos = content_tokens[0].position
            end_pos = content_tokens[-1].position + len(content_tokens[-1].content)
            return self._extract_source_range(start_pos, end_pos)
        
        return ""
    
    def _skip_whitespace(self):
        """Skip whitespace and newline tokens."""
        while (self.position < len(self.tokens) and 
               self.tokens[self.position].type in [TokenType.WHITESPACE, TokenType.NEWLINE]):
            self.position += 1
    
    def _extract_source_range(self, start_pos: int, end_pos: int) -> str:
        """Extract source text between positions."""
        # This would need access to the original source
        # For now, reconstruct from tokens
        return ""


class CrossReferenceResolver:
    """Resolves cross-references in LaTeX documents."""
    
    def __init__(self):
        self.labels: Dict[str, Dict[str, Any]] = {}
        self.references: Dict[str, List[Dict[str, Any]]] = {}
        
    def extract_labels(self, commands: List[LaTeXCommand], environments: List[LaTeXEnvironment]):
        """Extract all labels from commands and environments."""
        for command in commands:
            if command.name == 'label' and command.arguments:
                label_name = command.arguments[0]
                self.labels[label_name] = {
                    'type': 'command',
                    'position': command.position,
                    'line': command.line,
                    'column': command.column
                }
        
        for env in environments:
            # Look for labels in environment content
            # This would require parsing the environment content
            pass
    
    def extract_references(self, commands: List[LaTeXCommand]):
        """Extract all references from commands."""
        for command in commands:
            if command.name in LaTeXParser.REFERENCE_COMMANDS and command.arguments:
                ref_label = command.arguments[0]
                if ref_label not in self.references:
                    self.references[ref_label] = []
                
                self.references[ref_label].append({
                    'command': command.name,
                    'position': command.position,
                    'line': command.line,
                    'column': command.column
                })
    
    def resolve_references(self) -> Dict[str, Dict[str, Any]]:
        """Resolve all references to their targets."""
        resolved = {}
        
        for ref_label, ref_list in self.references.items():
            if ref_label in self.labels:
                resolved[ref_label] = {
                    'target': self.labels[ref_label],
                    'references': ref_list
                }
            else:
                resolved[ref_label] = {
                    'target': None,
                    'references': ref_list,
                    'error': 'Undefined reference'
                }
        
        return resolved