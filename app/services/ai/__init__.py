"""
AI service module for SlideGenie presentation generation.
"""
from .base import (
    AIProvider,
    AIProviderBase,
    AIResponse,
    ContentType,
    GenerationRequest,
    ModelCapability,
    PromptTemplate,
    TokenUsage,
)
from .content_processor import ContentProcessor, ProcessedChunk
from .cost_optimizer import CostEstimate, CostOptimizer, UsageMetrics
from .generation_pipeline import GenerationPipeline, GenerationProgress
from .prompt_manager import PromptManager

__all__ = [
    # Base classes
    "AIProvider",
    "AIProviderBase",
    "AIResponse",
    "ContentType",
    "GenerationRequest",
    "ModelCapability",
    "PromptTemplate",
    "TokenUsage",
    # Core services
    "ContentProcessor",
    "ProcessedChunk",
    "CostOptimizer",
    "CostEstimate",
    "UsageMetrics",
    "GenerationPipeline",
    "GenerationProgress",
    "PromptManager",
]