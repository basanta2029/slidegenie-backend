"""
Base AI provider interface and abstract classes.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional, Union

import structlog
from pydantic import BaseModel, Field

logger = structlog.get_logger(__name__)


class AIProvider(str, Enum):
    """Available AI providers."""
    ANTHROPIC = "anthropic"
    OPENAI = "openai"
    GOOGLE = "google"
    COHERE = "cohere"
    

class ModelCapability(str, Enum):
    """Model capabilities."""
    TEXT_GENERATION = "text_generation"
    STRUCTURED_OUTPUT = "structured_output"
    VISION = "vision"
    FUNCTION_CALLING = "function_calling"
    STREAMING = "streaming"
    

class ContentType(str, Enum):
    """Content types for generation."""
    ABSTRACT_TO_OUTLINE = "abstract_to_outline"
    CONTENT_TO_SLIDES = "content_to_slides"
    CITATION_FORMAT = "citation_format"
    METHODOLOGY_VISUAL = "methodology_visual"
    RESULTS_SUMMARY = "results_summary"
    KEY_POINTS = "key_points"
    SLIDE_CONTENT = "slide_content"
    SPEAKER_NOTES = "speaker_notes"


@dataclass
class TokenUsage:
    """Token usage tracking."""
    prompt_tokens: int
    completion_tokens: int
    total_tokens: int
    estimated_cost: float
    

@dataclass
class AIResponse:
    """Standard AI response format."""
    content: Union[str, Dict[str, Any]]
    provider: AIProvider
    model: str
    usage: TokenUsage
    latency_ms: int
    cached: bool = False
    metadata: Optional[Dict[str, Any]] = None
    

class GenerationRequest(BaseModel):
    """Standard generation request."""
    content: str
    content_type: ContentType
    context: Optional[Dict[str, Any]] = None
    max_tokens: Optional[int] = None
    temperature: float = 0.7
    top_p: float = 0.9
    structured_output: Optional[type[BaseModel]] = None
    stream: bool = False
    

class PromptTemplate(BaseModel):
    """Prompt template structure."""
    id: str
    name: str
    content_type: ContentType
    template: str
    variables: List[str]
    version: int = 1
    is_active: bool = True
    performance_score: Optional[float] = None
    usage_count: int = 0
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
    def format(self, **kwargs) -> str:
        """Format template with provided variables."""
        return self.template.format(**kwargs)
        

class AIProviderBase(ABC):
    """Base class for AI providers."""
    
    def __init__(self, api_key: str, **kwargs):
        self.api_key = api_key
        self.provider = AIProvider.ANTHROPIC  # Override in subclasses
        self.capabilities: List[ModelCapability] = []
        self.default_model: str = ""
        self.token_limits: Dict[str, int] = {}
        self.pricing: Dict[str, Dict[str, float]] = {}  # model -> {input/output -> price}
        
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        top_p: float = 0.9,
        **kwargs
    ) -> AIResponse:
        """Generate text completion."""
        pass
        
    @abstractmethod
    async def generate_structured(
        self,
        prompt: str,
        response_model: type[BaseModel],
        model: Optional[str] = None,
        **kwargs
    ) -> AIResponse:
        """Generate structured output."""
        pass
        
    @abstractmethod
    async def count_tokens(self, text: str, model: Optional[str] = None) -> int:
        """Count tokens in text."""
        pass
        
    def estimate_cost(
        self,
        prompt_tokens: int,
        completion_tokens: int,
        model: Optional[str] = None
    ) -> float:
        """Estimate cost for token usage."""
        model = model or self.default_model
        if model not in self.pricing:
            return 0.0
            
        input_price = self.pricing[model].get("input", 0)
        output_price = self.pricing[model].get("output", 0)
        
        # Prices are usually per 1K or 1M tokens
        input_cost = (prompt_tokens / 1000) * input_price
        output_cost = (completion_tokens / 1000) * output_price
        
        return round(input_cost + output_cost, 6)
        
    def select_model_for_task(
        self,
        content_type: ContentType,
        estimated_tokens: int,
        require_structured: bool = False
    ) -> str:
        """Select appropriate model based on task requirements."""
        # Override in subclasses for provider-specific logic
        return self.default_model
        
    def supports_capability(self, capability: ModelCapability) -> bool:
        """Check if provider supports capability."""
        return capability in self.capabilities
        
    async def health_check(self) -> bool:
        """Check if provider is accessible."""
        try:
            # Simple token count as health check
            await self.count_tokens("test")
            return True
        except Exception as e:
            logger.error(f"{self.provider}_health_check_failed", error=str(e))
            return False


class AIProviderError(Exception):
    """Base exception for AI provider errors."""
    pass
    

class TokenLimitError(AIProviderError):
    """Raised when token limit is exceeded."""
    pass
    

class RateLimitError(AIProviderError):
    """Raised when rate limit is hit."""
    pass
    

class ModelNotAvailableError(AIProviderError):
    """Raised when requested model is not available."""
    pass