"""
Anthropic Claude provider implementation.
"""
import time
from typing import Any, Dict, Optional, Union

import anthropic
import structlog
from anthropic import AsyncAnthropic
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


class AnthropicProvider(AIProviderBase):
    """Anthropic Claude provider."""
    
    def __init__(self, api_key: Optional[str] = None):
        super().__init__(api_key or settings.ANTHROPIC_API_KEY)
        self.provider = AIProvider.ANTHROPIC
        self.client = AsyncAnthropic(api_key=self.api_key)
        
        # Set capabilities
        self.capabilities = [
            ModelCapability.TEXT_GENERATION,
            ModelCapability.STRUCTURED_OUTPUT,
            ModelCapability.VISION,
            ModelCapability.STREAMING,
        ]
        
        # Available models
        self.default_model = "claude-3-5-sonnet-20241022"
        self.models = {
            "claude-3-5-sonnet-20241022": {"context": 200000, "output": 8192},
            "claude-3-5-haiku-20241022": {"context": 200000, "output": 8192},
            "claude-3-opus-20240229": {"context": 200000, "output": 4096},
            "claude-3-sonnet-20240229": {"context": 200000, "output": 4096},
            "claude-3-haiku-20240307": {"context": 200000, "output": 4096},
        }
        
        # Pricing per 1M tokens (as of 2024)
        self.pricing = {
            "claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0},
            "claude-3-5-haiku-20241022": {"input": 0.25, "output": 1.25},
            "claude-3-opus-20240229": {"input": 15.0, "output": 75.0},
            "claude-3-sonnet-20240229": {"input": 3.0, "output": 15.0},
            "claude-3-haiku-20240307": {"input": 0.25, "output": 1.25},
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
        """Generate text completion using Claude."""
        model = model or self.default_model
        max_tokens = max_tokens or 4096
        
        try:
            start_time = time.time()
            
            # Prepare messages
            messages = [{"role": "user", "content": prompt}]
            
            # Make request
            response = await self.client.messages.create(
                model=model,
                messages=messages,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                system=system,
                **kwargs
            )
            
            # Calculate latency
            latency_ms = int((time.time() - start_time) * 1000)
            
            # Extract content
            content = response.content[0].text if response.content else ""
            
            # Create usage info
            usage = TokenUsage(
                prompt_tokens=response.usage.input_tokens,
                completion_tokens=response.usage.output_tokens,
                total_tokens=response.usage.input_tokens + response.usage.output_tokens,
                estimated_cost=self.estimate_cost(
                    response.usage.input_tokens,
                    response.usage.output_tokens,
                    model
                )
            )
            
            logger.info(
                "anthropic_generation_complete",
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
                metadata={"message_id": response.id}
            )
            
        except anthropic.RateLimitError as e:
            logger.error("anthropic_rate_limit", error=str(e))
            raise RateLimitError(f"Anthropic rate limit exceeded: {e}")
        except Exception as e:
            logger.error("anthropic_generation_error", error=str(e))
            raise
            
    async def generate_structured(
        self,
        prompt: str,
        response_model: type[BaseModel],
        model: Optional[str] = None,
        **kwargs
    ) -> AIResponse:
        """Generate structured output using Claude."""
        model = model or self.default_model
        
        # Add instructions for structured output
        structured_prompt = f"""{prompt}

Please respond with a JSON object that matches this schema:
{response_model.model_json_schema()}

Respond ONLY with valid JSON, no additional text."""
        
        # Generate response
        response = await self.generate(
            prompt=structured_prompt,
            model=model,
            temperature=0.3,  # Lower temperature for structured output
            **kwargs
        )
        
        # Parse JSON response
        import json
        try:
            parsed_content = json.loads(response.content)
            validated_content = response_model(**parsed_content)
            
            # Update response with structured content
            response.content = validated_content.model_dump()
            return response
            
        except (json.JSONDecodeError, ValueError) as e:
            logger.error(
                "anthropic_structured_output_parse_error",
                error=str(e),
                response=response.content
            )
            # Retry with more explicit instructions
            retry_prompt = f"""{prompt}

IMPORTANT: You must respond with ONLY a valid JSON object, no markdown, no explanation.
The JSON must match this exact structure:
{response_model.model_json_schema()}

Example format:
{response_model.model_config.get('json_schema_extra', {}).get('example', {})}"""
            
            retry_response = await self.generate(
                prompt=retry_prompt,
                model=model,
                temperature=0.1,
                **kwargs
            )
            
            try:
                # Try to extract JSON from response
                content = retry_response.content
                if "```json" in content:
                    content = content.split("```json")[1].split("```")[0].strip()
                elif "```" in content:
                    content = content.split("```")[1].split("```")[0].strip()
                    
                parsed_content = json.loads(content)
                validated_content = response_model(**parsed_content)
                retry_response.content = validated_content.model_dump()
                return retry_response
            except Exception as e2:
                logger.error("anthropic_structured_output_retry_failed", error=str(e2))
                raise ValueError(f"Failed to generate structured output: {e2}")
                
    async def count_tokens(self, text: str, model: Optional[str] = None) -> int:
        """Count tokens using Anthropic's tokenizer."""
        # Anthropic uses a different tokenization method
        # For estimation, we'll use ~4 characters per token
        return len(text) // 4
        
    def select_model_for_task(
        self,
        content_type: ContentType,
        estimated_tokens: int,
        require_structured: bool = False
    ) -> str:
        """Select appropriate Claude model based on task."""
        # For complex academic tasks, use Sonnet
        complex_tasks = {
            ContentType.ABSTRACT_TO_OUTLINE,
            ContentType.METHODOLOGY_VISUAL,
            ContentType.RESULTS_SUMMARY,
        }
        
        # For simple tasks or high volume, use Haiku
        simple_tasks = {
            ContentType.CITATION_FORMAT,
            ContentType.KEY_POINTS,
            ContentType.SPEAKER_NOTES,
        }
        
        if content_type in complex_tasks or require_structured:
            # Use Sonnet for complex tasks
            return "claude-3-5-sonnet-20241022"
        elif content_type in simple_tasks and estimated_tokens < 1000:
            # Use Haiku for simple, short tasks
            return "claude-3-5-haiku-20241022"
        else:
            # Default to Sonnet for reliability
            return "claude-3-5-sonnet-20241022"
            
    async def stream_generate(
        self,
        prompt: str,
        model: Optional[str] = None,
        **kwargs
    ):
        """Stream generation for real-time output."""
        model = model or self.default_model
        
        messages = [{"role": "user", "content": prompt}]
        
        async with self.client.messages.stream(
            model=model,
            messages=messages,
            max_tokens=kwargs.get("max_tokens", 4096),
            temperature=kwargs.get("temperature", 0.7),
        ) as stream:
            async for event in stream:
                if event.type == "content_block_delta":
                    yield event.delta.text
                elif event.type == "message_stop":
                    # Final usage info
                    yield {
                        "type": "usage",
                        "usage": {
                            "input_tokens": stream.input_tokens,
                            "output_tokens": stream.output_tokens,
                            "total_tokens": stream.total_tokens,
                        }
                    }