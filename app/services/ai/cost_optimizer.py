"""
Cost optimization for AI service usage.
"""
import hashlib
import json
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional, Tuple

import structlog
from pydantic import BaseModel

from app.core.config import get_settings
from app.infrastructure.cache import get_redis_client
from app.services.ai.base import AIProvider, ContentType

logger = structlog.get_logger(__name__)
settings = get_settings()


class CostEstimate(BaseModel):
    """Cost estimate for AI operation."""
    provider: AIProvider
    model: str
    estimated_tokens: int
    estimated_cost: float
    cached: bool = False
    cache_hit_probability: float = 0.0
    

class UsageMetrics(BaseModel):
    """Usage metrics for cost tracking."""
    provider: AIProvider
    model: str
    total_tokens: int
    total_cost: float
    request_count: int
    cache_hits: int
    average_latency_ms: float
    period_start: datetime
    period_end: datetime
    

class BatchRequest(BaseModel):
    """Batch request for processing."""
    id: str
    content: str
    content_type: ContentType
    priority: int = 5  # 1-10, higher is more important
    estimated_tokens: int
    

class CostOptimizer:
    """Optimizes AI service costs through caching, batching, and smart routing."""
    
    def __init__(self):
        self.cache_ttl = 86400 * 7  # 7 days for cached responses
        self.batch_window_ms = 100  # Batch collection window
        self.max_batch_size = 10
        
        # Cost thresholds (monthly)
        self.budget_limits = {
            AIProvider.ANTHROPIC: settings.AI_BUDGET_ANTHROPIC or 1000.0,
            AIProvider.OPENAI: settings.AI_BUDGET_OPENAI or 500.0,
        }
        
    async def estimate_cost(
        self,
        content: str,
        content_type: ContentType,
        providers: List[AIProvider]
    ) -> List[CostEstimate]:
        """Estimate costs across different providers."""
        estimates = []
        
        # Estimate token count
        token_count = self._estimate_tokens(content)
        
        # Check cache probability
        cache_prob = await self._calculate_cache_probability(content, content_type)
        
        for provider in providers:
            # Get appropriate model for task
            model = self._select_model_for_budget(provider, content_type, token_count)
            
            # Calculate cost
            if provider == AIProvider.ANTHROPIC:
                cost = self._calculate_anthropic_cost(model, token_count)
            elif provider == AIProvider.OPENAI:
                cost = self._calculate_openai_cost(model, token_count)
            else:
                cost = 0.0
                
            estimates.append(CostEstimate(
                provider=provider,
                model=model,
                estimated_tokens=token_count,
                estimated_cost=cost * (1 - cache_prob),  # Adjust for cache hits
                cached=cache_prob > 0.5,
                cache_hit_probability=cache_prob
            ))
            
        # Sort by cost
        estimates.sort(key=lambda x: x.estimated_cost)
        
        return estimates
        
    async def get_cached_response(
        self,
        content: str,
        content_type: ContentType,
        **params
    ) -> Optional[Dict[str, Any]]:
        """Get cached response if available."""
        cache_key = self._generate_cache_key(content, content_type, **params)
        
        redis = await get_redis_client()
        cached = await redis.get(f"ai:cache:{cache_key}")
        
        if cached:
            logger.info(
                "cache_hit",
                content_type=content_type,
                cache_key=cache_key
            )
            
            # Update cache stats
            await self._update_cache_stats(content_type, hit=True)
            
            return json.loads(cached)
            
        # Update cache stats
        await self._update_cache_stats(content_type, hit=False)
        
        return None
        
    async def cache_response(
        self,
        content: str,
        content_type: ContentType,
        response: Dict[str, Any],
        **params
    ) -> None:
        """Cache AI response."""
        cache_key = self._generate_cache_key(content, content_type, **params)
        
        redis = await get_redis_client()
        
        # Store with TTL
        await redis.setex(
            f"ai:cache:{cache_key}",
            self.cache_ttl,
            json.dumps(response)
        )
        
        # Store cache metadata
        metadata = {
            "content_type": content_type,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "token_count": response.get("usage", {}).get("total_tokens", 0),
            "cost_saved": response.get("usage", {}).get("estimated_cost", 0)
        }
        
        await redis.hset(
            f"ai:cache:metadata:{cache_key}",
            mapping=metadata
        )
        
    async def batch_requests(
        self,
        requests: List[BatchRequest]
    ) -> List[List[BatchRequest]]:
        """Batch requests for efficient processing."""
        # Sort by priority and content type
        sorted_requests = sorted(
            requests,
            key=lambda x: (x.content_type, -x.priority, x.estimated_tokens)
        )
        
        batches = []
        current_batch = []
        current_tokens = 0
        current_type = None
        
        for request in sorted_requests:
            # Check if we should start a new batch
            if (current_type and current_type != request.content_type) or \
               len(current_batch) >= self.max_batch_size or \
               current_tokens + request.estimated_tokens > 4000:  # Token limit per batch
                
                if current_batch:
                    batches.append(current_batch)
                    
                current_batch = [request]
                current_tokens = request.estimated_tokens
                current_type = request.content_type
            else:
                current_batch.append(request)
                current_tokens += request.estimated_tokens
                current_type = request.content_type
                
        # Add last batch
        if current_batch:
            batches.append(current_batch)
            
        logger.info(
            "requests_batched",
            total_requests=len(requests),
            total_batches=len(batches),
            avg_batch_size=len(requests) / len(batches) if batches else 0
        )
        
        return batches
        
    async def track_usage(
        self,
        provider: AIProvider,
        model: str,
        tokens: int,
        cost: float,
        latency_ms: int,
        cached: bool = False
    ) -> None:
        """Track usage metrics for cost monitoring."""
        redis = await get_redis_client()
        
        # Get current period (daily)
        today = datetime.now(timezone.utc).date()
        key = f"ai:usage:{provider}:{model}:{today}"
        
        # Update metrics
        pipe = redis.pipeline()
        pipe.hincrby(key, "total_tokens", tokens)
        pipe.hincrbyfloat(key, "total_cost", cost)
        pipe.hincrby(key, "request_count", 1)
        if cached:
            pipe.hincrby(key, "cache_hits", 1)
            
        # Update latency (running average)
        pipe.hincrby(key, "total_latency", latency_ms)
        
        # Set expiry
        pipe.expire(key, 86400 * 30)  # 30 days
        
        await pipe.execute()
        
        # Check budget alerts
        await self._check_budget_alerts(provider, cost)
        
    async def get_usage_report(
        self,
        provider: Optional[AIProvider] = None,
        days: int = 30
    ) -> List[UsageMetrics]:
        """Get usage report for cost analysis."""
        redis = await get_redis_client()
        
        metrics = []
        end_date = datetime.now(timezone.utc).date()
        start_date = end_date - timedelta(days=days)
        
        # Get all providers if not specified
        providers = [provider] if provider else list(AIProvider)
        
        for prov in providers:
            # Scan for all models and dates
            pattern = f"ai:usage:{prov}:*"
            keys = await redis.keys(pattern)
            
            for key in keys:
                parts = key.split(":")
                if len(parts) >= 5:
                    model = parts[3]
                    date_str = parts[4]
                    
                    try:
                        date = datetime.strptime(date_str, "%Y-%m-%d").date()
                        if start_date <= date <= end_date:
                            # Get metrics
                            data = await redis.hgetall(key)
                            
                            if data:
                                total_tokens = int(data.get("total_tokens", 0))
                                total_cost = float(data.get("total_cost", 0))
                                request_count = int(data.get("request_count", 0))
                                cache_hits = int(data.get("cache_hits", 0))
                                total_latency = int(data.get("total_latency", 0))
                                
                                avg_latency = total_latency / request_count if request_count > 0 else 0
                                
                                metrics.append(UsageMetrics(
                                    provider=prov,
                                    model=model,
                                    total_tokens=total_tokens,
                                    total_cost=total_cost,
                                    request_count=request_count,
                                    cache_hits=cache_hits,
                                    average_latency_ms=avg_latency,
                                    period_start=datetime.combine(date, datetime.min.time()),
                                    period_end=datetime.combine(date, datetime.max.time())
                                ))
                    except ValueError:
                        continue
                        
        return metrics
        
    async def select_optimal_provider(
        self,
        content_type: ContentType,
        estimated_tokens: int,
        quality_required: float = 0.8  # 0.0 to 1.0
    ) -> Tuple[AIProvider, str]:
        """Select optimal provider based on cost, quality, and availability."""
        # Get current usage
        usage = await self.get_usage_report(days=30)
        
        # Calculate remaining budgets
        budgets = {}
        for provider in AIProvider:
            provider_usage = [m for m in usage if m.provider == provider]
            total_cost = sum(m.total_cost for m in provider_usage)
            remaining = self.budget_limits.get(provider, 0) - total_cost
            budgets[provider] = remaining
            
        # Score providers
        scores = []
        
        for provider in [AIProvider.ANTHROPIC, AIProvider.OPENAI]:
            if budgets.get(provider, 0) <= 0:
                continue  # Skip if over budget
                
            # Quality scores (subjective, can be adjusted)
            quality_scores = {
                AIProvider.ANTHROPIC: {
                    ContentType.ABSTRACT_TO_OUTLINE: 0.95,
                    ContentType.CONTENT_TO_SLIDES: 0.90,
                    ContentType.METHODOLOGY_VISUAL: 0.85,
                    ContentType.RESULTS_SUMMARY: 0.90,
                },
                AIProvider.OPENAI: {
                    ContentType.ABSTRACT_TO_OUTLINE: 0.85,
                    ContentType.CONTENT_TO_SLIDES: 0.88,
                    ContentType.METHODOLOGY_VISUAL: 0.80,
                    ContentType.RESULTS_SUMMARY: 0.85,
                }
            }
            
            quality = quality_scores.get(provider, {}).get(content_type, 0.8)
            
            if quality < quality_required:
                continue  # Skip if quality too low
                
            # Select model
            if provider == AIProvider.ANTHROPIC:
                model = self._select_model_for_budget(
                    provider, content_type, estimated_tokens
                )
                cost = self._calculate_anthropic_cost(model, estimated_tokens)
            else:
                model = self._select_model_for_budget(
                    provider, content_type, estimated_tokens
                )
                cost = self._calculate_openai_cost(model, estimated_tokens)
                
            # Calculate score (balance quality and cost)
            score = quality / (cost + 0.01)  # Avoid division by zero
            
            scores.append((score, provider, model))
            
        if not scores:
            # Fallback to cheapest available
            return AIProvider.OPENAI, "gpt-4o-mini"
            
        # Sort by score (highest first)
        scores.sort(key=lambda x: x[0], reverse=True)
        
        return scores[0][1], scores[0][2]
        
    def _estimate_tokens(self, content: str) -> int:
        """Estimate token count."""
        # Simple approximation: 1 token ≈ 4 characters
        # More accurate would use tiktoken or provider-specific tokenizer
        return len(content) // 4
        
    def _generate_cache_key(self, content: str, content_type: ContentType, **params) -> str:
        """Generate cache key for content."""
        # Create a stable hash
        key_parts = [
            content_type,
            content,
            json.dumps(params, sort_keys=True)
        ]
        
        key_string = "|".join(str(part) for part in key_parts)
        return hashlib.sha256(key_string.encode()).hexdigest()[:16]
        
    async def _calculate_cache_probability(
        self,
        content: str,
        content_type: ContentType
    ) -> float:
        """Calculate probability of cache hit."""
        redis = await get_redis_client()
        
        # Get cache stats for content type
        stats_key = f"ai:cache:stats:{content_type}"
        stats = await redis.hgetall(stats_key)
        
        if not stats:
            return 0.0
            
        hits = int(stats.get("hits", 0))
        misses = int(stats.get("misses", 0))
        total = hits + misses
        
        if total == 0:
            return 0.0
            
        # Base probability on hit rate
        hit_rate = hits / total
        
        # Adjust based on content similarity (simplified)
        # In production, could use embeddings for similarity
        return min(hit_rate * 0.8, 0.9)  # Cap at 90%
        
    async def _update_cache_stats(self, content_type: ContentType, hit: bool) -> None:
        """Update cache statistics."""
        redis = await get_redis_client()
        
        stats_key = f"ai:cache:stats:{content_type}"
        field = "hits" if hit else "misses"
        
        await redis.hincrby(stats_key, field, 1)
        await redis.expire(stats_key, 86400 * 30)  # 30 days
        
    def _select_model_for_budget(
        self,
        provider: AIProvider,
        content_type: ContentType,
        estimated_tokens: int
    ) -> str:
        """Select model based on budget constraints."""
        # Complex tasks requiring best models
        complex_tasks = {
            ContentType.ABSTRACT_TO_OUTLINE,
            ContentType.METHODOLOGY_VISUAL,
            ContentType.RESULTS_SUMMARY
        }
        
        if provider == AIProvider.ANTHROPIC:
            if content_type in complex_tasks:
                return "claude-3-5-sonnet-20241022"
            else:
                # Use Haiku for simple tasks to save costs
                return "claude-3-5-haiku-20241022"
                
        elif provider == AIProvider.OPENAI:
            if content_type in complex_tasks and estimated_tokens > 2000:
                return "gpt-4o"
            else:
                return "gpt-4o-mini"
                
        return "gpt-4o-mini"  # Default fallback
        
    def _calculate_anthropic_cost(self, model: str, tokens: int) -> float:
        """Calculate Anthropic API cost."""
        # Prices per 1M tokens
        prices = {
            "claude-3-5-sonnet-20241022": {"input": 3.0, "output": 15.0},
            "claude-3-5-haiku-20241022": {"input": 0.25, "output": 1.25},
            "claude-3-opus-20240229": {"input": 15.0, "output": 75.0},
        }
        
        model_prices = prices.get(model, prices["claude-3-5-haiku-20241022"])
        
        # Assume 30% output tokens
        input_tokens = int(tokens * 0.7)
        output_tokens = int(tokens * 0.3)
        
        input_cost = (input_tokens / 1_000_000) * model_prices["input"]
        output_cost = (output_tokens / 1_000_000) * model_prices["output"]
        
        return round(input_cost + output_cost, 4)
        
    def _calculate_openai_cost(self, model: str, tokens: int) -> float:
        """Calculate OpenAI API cost."""
        # Prices per 1M tokens
        prices = {
            "gpt-4o": {"input": 2.5, "output": 10.0},
            "gpt-4o-mini": {"input": 0.15, "output": 0.6},
            "gpt-4-turbo": {"input": 10.0, "output": 30.0},
        }
        
        model_prices = prices.get(model, prices["gpt-4o-mini"])
        
        # Assume 30% output tokens
        input_tokens = int(tokens * 0.7)
        output_tokens = int(tokens * 0.3)
        
        input_cost = (input_tokens / 1_000_000) * model_prices["input"]
        output_cost = (output_tokens / 1_000_000) * model_prices["output"]
        
        return round(input_cost + output_cost, 4)
        
    async def _check_budget_alerts(self, provider: AIProvider, cost: float) -> None:
        """Check and send budget alerts."""
        # Get current month usage
        usage = await self.get_usage_report(provider=provider, days=30)
        
        total_cost = sum(m.total_cost for m in usage) + cost
        budget = self.budget_limits.get(provider, 0)
        
        if budget > 0:
            usage_percent = (total_cost / budget) * 100
            
            # Alert thresholds
            if usage_percent >= 90:
                logger.warning(
                    "budget_alert_critical",
                    provider=provider,
                    usage_percent=usage_percent,
                    total_cost=total_cost,
                    budget=budget
                )
            elif usage_percent >= 75:
                logger.warning(
                    "budget_alert_high",
                    provider=provider,
                    usage_percent=usage_percent,
                    total_cost=total_cost,
                    budget=budget
                )