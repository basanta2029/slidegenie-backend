"""
OpenAI GPT provider implementation.
"""
import time
from typing import Any, Dict, Optional, Union

import structlog
from openai import AsyncOpenAI
from pydantic import BaseModel

from app.core.config import get_settings
from app.services.ai.base import (
    AIProvider,
    AIProviderBase,
    AIResponse,
    ContentType,
    ModelCapability,
    RateLimitError,
    TokenUsage,
)

logger = structlog.get_logger(__name__)
settings = get_settings()


class OpenAIProvider(AIProviderBase):
    """OpenAI GPT provider."""
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key or settings.OPENAI_API_KEY)
        self.provider = AIProvider.OPENAI
        self.client = AsyncOpenAI(api_key=self.api_key)
        
        # Set capabilities
        self.capabilities = [
            ModelCapability.TEXT_GENERATION,
            ModelCapability.STRUCTURED_OUTPUT,
            ModelCapability.VISION,
            ModelCapability.FUNCTION_CALLING,
            ModelCapability.STREAMING,
        ]
        
        # Available models
        self.default_model = "gpt-4o-mini"
        self.models = {
            "gpt-4o": {"context": 128000, "output": 16384},
            "gpt-4o-mini": {"context": 128000, "output": 16384},
            "gpt-4-turbo": {"context": 128000, "output": 4096},
            "gpt-4": {"context": 8192, "output": 4096},
            "gpt-3.5-turbo": {"context": 16385, "output": 4096},
        }
        
        # Pricing per 1M tokens
        self.pricing = {
            "gpt-4o": {"input": 2.5, "output": 10.0},
            "gpt-4o-mini": {"input": 0.15, "output": 0.6},
            "gpt-4-turbo": {"input": 10.0, "output": 30.0},
            "gpt-4": {"input": 30.0, "output": 60.0},
            "gpt-3.5-turbo": {"input": 0.5, "output": 1.5},
        }
        
    async def generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        max_tokens: Optional[int] = None,
        temperature: float = 0.7,
        top_p: float = 0.9,
        system: Optional[str] = None,
        **kwargs
    ) -> AIResponse:
        """Generate text completion using GPT."""
        model = model or self.default_model
        max_tokens = max_tokens or 4096
        
        try:
            start_time = time.time()
            
            # Prepare messages
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})
            
            # Make request
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                **kwargs
            )
            
            # Calculate latency
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Extract content
            content = response.choices[0].message.content
            
            # Create usage info
            usage = TokenUsage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                estimated_cost=self.estimate_cost(
                    response.usage.prompt_tokens,
                    response.usage.completion_tokens,
                    model
                )
            )
            
            logger.info(
                "openai_generation_complete",
                model=model,
                tokens=usage.total_tokens,
                latency_ms=latency_ms,
                cost=usage.estimated_cost
            )
            
            return AIResponse(
                content=content,
                provider=self.provider,
                model=model,
                usage=usage,
                latency_ms=latency_ms,
                cached=False,
                metadata={
                    "completion_id": response.id,
                    "finish_reason": response.choices[0].finish_reason
                }
            )
            
        except Exception as e:
            if "rate_limit" in str(e).lower():
                logger.error("openai_rate_limit", error=str(e))
                raise RateLimitError(f"OpenAI rate limit exceeded: {e}")
            logger.error("openai_generation_error", error=str(e))
            raise
            
    async def generate_structured(
        self,
        prompt: str,
        response_model: type[BaseModel],
        model: Optional[str] = None,
        **kwargs
    ) -> AIResponse:
        """Generate structured output using GPT with response format."""
        model = model or self.default_model
        
        try:
            start_time = time.time()
            
            # Use OpenAI's response format feature
            response = await self.client.beta.chat.completions.parse(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                response_format=response_model,
                temperature=0.3,  # Lower temperature for structured output
                **kwargs
            )
            
            # Calculate latency
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Extract parsed content
            parsed_content = response.choices[0].message.parsed
            
            # Create usage info
            usage = TokenUsage(
                prompt_tokens=response.usage.prompt_tokens,
                completion_tokens=response.usage.completion_tokens,
                total_tokens=response.usage.total_tokens,
                estimated_cost=self.estimate_cost(
                    response.usage.prompt_tokens,
                    response.usage.completion_tokens,
                    model
                )
            )
            
            return AIResponse(
                content=parsed_content.model_dump() if parsed_content else {},
                provider=self.provider,
                model=model,
                usage=usage,
                latency_ms=latency_ms,
                cached=False,
                metadata={"completion_id": response.id}
            )
            
        except Exception as e:
            logger.error("openai_structured_output_error", error=str(e))
            # Fallback to JSON mode
            return await self._generate_structured_json_mode(
                prompt, response_model, model, **kwargs
            )
            
    async def _generate_structured_json_mode(
        self,
        prompt: str,
        response_model: type[BaseModel],
        model: Optional[str] = None,
        **kwargs
    ) -> AIResponse:
        """Fallback structured generation using JSON mode."""
        model = model or self.default_model
        
        structured_prompt = f"""{prompt}

Respond with a JSON object matching this schema:
{response_model.model_json_schema()}

Provide ONLY valid JSON, no additional text."""
        
        response = await self.generate(
            prompt=structured_prompt,
            model=model,
            temperature=0.3,
            response_format={"type": "json_object"},
            **kwargs
        )
        
        # Parse and validate JSON
        import json
        try:
            parsed_content = json.loads(response.content)
            validated_content = response_model(**parsed_content)
            response.content = validated_content.model_dump()
            return response
        except Exception as e:
            logger.error("openai_json_parse_error", error=str(e))
            raise ValueError(f"Failed to parse structured output: {e}")
            
    async def count_tokens(self, text: str, model: Optional[str] = None) -> int:
        """Count tokens using tiktoken."""
        import tiktoken
        
        model = model or self.default_model
        
        # Get encoding for model
        try:
            if "gpt-4o" in model:
                encoding = tiktoken.get_encoding("o200k_base")
            elif "gpt-4" in model:
                encoding = tiktoken.get_encoding("cl100k_base")
            else:
                encoding = tiktoken.get_encoding("cl100k_base")
                
            tokens = encoding.encode(text)
            return len(tokens)
        except Exception as e:
            logger.error("openai_token_count_error", error=str(e))
            # Fallback to approximation
            return len(text) // 4
            
    def select_model_for_task(
        self,
        content_type: ContentType,
        estimated_tokens: int,
        require_structured: bool = False
    ) -> str:
        """Select appropriate GPT model based on task."""
        # For complex academic tasks requiring reasoning
        complex_tasks = {
            ContentType.ABSTRACT_TO_OUTLINE,
            ContentType.METHODOLOGY_VISUAL,
            ContentType.RESULTS_SUMMARY,
        }
        
        # For simple formatting tasks
        simple_tasks = {
            ContentType.CITATION_FORMAT,
            ContentType.KEY_POINTS,
            ContentType.SPEAKER_NOTES,
        }
        
        # Use GPT-4o for complex tasks or when high quality is needed
        if content_type in complex_tasks:
            return "gpt-4o" if estimated_tokens > 4000 else "gpt-4o-mini"
        elif content_type in simple_tasks:
            return "gpt-4o-mini"  # Cost-effective for simple tasks
        elif require_structured:
            return "gpt-4o-mini"  # Good structured output support
        else:
            # Default based on token count
            if estimated_tokens > 8000:
                return "gpt-4o"  # Better for long context
            else:
                return "gpt-4o-mini"  # Cost-effective default
                
    async def stream_generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        **kwargs
    ):
        """Stream generation for real-time output."""
        model = model or self.default_model
        
        messages = [{"role": "user", "content": prompt}]
        if "system" in kwargs:
            messages.insert(0, {"role": "system", "content": kwargs.pop("system")})
            
        stream = await self.client.chat.completions.create(
            model=model,
            messages=messages,
            stream=True,
            **kwargs
        )
        
        total_tokens = 0
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                total_tokens += 1  # Approximate
                yield chunk.choices[0].delta.content
            elif chunk.choices[0].finish_reason:
                # Stream complete
                yield {
                    "type": "complete",
                    "finish_reason": chunk.choices[0].finish_reason,
                    "approximate_tokens": total_tokens
                }