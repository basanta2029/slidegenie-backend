"""
Prompt management system with versioning and A/B testing.
"""
import hashlib
import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple
from uuid import UUID, uuid4

import structlog
from sqlalchemy.ext.asyncio import AsyncSession

from app.infrastructure.cache import get_redis_client
from app.services.ai.base import ContentType, PromptTemplate

logger = structlog.get_logger(__name__)


class PromptManager:
    """Manages prompt templates with versioning and A/B testing."""
    
    def __init__(self, db_session: Optional[AsyncSession] = None):
        self.db = db_session
        self._cache_ttl = 3600  # 1 hour cache
        
    async def get_prompt(
        self,
        content_type: ContentType,
        version: Optional[int] = None,
        ab_test: bool = True
    ) -> PromptTemplate:
        """Get prompt template for content type."""
        # Try cache first
        cached = await self._get_cached_prompt(content_type, version)
        if cached:
            return cached
            
        # Get from database or defaults
        if self.db:
            prompt = await self._get_db_prompt(content_type, version, ab_test)
        else:
            prompt = self._get_default_prompt(content_type)
            
        # Cache the prompt
        await self._cache_prompt(prompt)
        
        return prompt
        
    async def create_prompt(
        self,
        name: str,
        content_type: ContentType,
        template: str,
        variables: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> PromptTemplate:
        """Create new prompt template."""
        prompt_id = str(uuid4())
        
        prompt = PromptTemplate(
            id=prompt_id,
            name=name,
            content_type=content_type,
            template=template,
            variables=variables,
            version=1,
            is_active=True,
            metadata=metadata or {}
        )
        
        # Save to database if available
        if self.db:
            await self._save_prompt_to_db(prompt)
            
        # Cache the prompt
        await self._cache_prompt(prompt)
        
        logger.info(
            "prompt_created",
            prompt_id=prompt_id,
            content_type=content_type,
            name=name
        )
        
        return prompt
        
    async def update_prompt(
        self,
        prompt_id: str,
        template: Optional[str] = None,
        variables: Optional[List[str]] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> PromptTemplate:
        """Update existing prompt (creates new version)."""
        # Get current prompt
        current = await self._get_prompt_by_id(prompt_id)
        if not current:
            raise ValueError(f"Prompt {prompt_id} not found")
            
        # Create new version
        new_version = current.version + 1
        
        updated = PromptTemplate(
            id=prompt_id,
            name=current.name,
            content_type=current.content_type,
            template=template or current.template,
            variables=variables or current.variables,
            version=new_version,
            is_active=True,
            metadata={**current.metadata, **(metadata or {})}
        )
        
        # Save to database
        if self.db:
            await self._save_prompt_to_db(updated)
            
        # Invalidate cache
        await self._invalidate_cache(current.content_type)
        
        logger.info(
            "prompt_updated",
            prompt_id=prompt_id,
            new_version=new_version
        )
        
        return updated
        
    async def record_performance(
        self,
        prompt_id: str,
        success: bool,
        latency_ms: int,
        tokens_used: int,
        feedback_score: Optional[float] = None
    ) -> None:
        """Record prompt performance for optimization."""
        redis = await get_redis_client()
        
        # Record in Redis for real-time metrics
        key = f"prompt:performance:{prompt_id}"
        
        data = {
            "success": int(success),
            "latency_ms": latency_ms,
            "tokens_used": tokens_used,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        
        if feedback_score is not None:
            data["feedback_score"] = feedback_score
            
        # Add to sorted set for time-series data
        await redis.zadd(
            key,
            {json.dumps(data): datetime.now(timezone.utc).timestamp()}
        )
        
        # Update aggregate metrics
        await self._update_aggregate_metrics(prompt_id, data)
        
    async def get_best_performing_prompt(
        self,
        content_type: ContentType,
        metric: str = "success_rate"
    ) -> PromptTemplate:
        """Get best performing prompt for content type."""
        redis = await get_redis_client()
        
        # Get all prompts for content type
        pattern = f"prompt:metrics:{content_type}:*"
        keys = await redis.keys(pattern)
        
        best_prompt_id = None
        best_score = -1
        
        for key in keys:
            metrics = await redis.hgetall(key)
            prompt_id = key.split(":")[-1]
            
            # Calculate score based on metric
            if metric == "success_rate":
                total = int(metrics.get("total_requests", 0))
                success = int(metrics.get("success_count", 0))
                score = success / total if total > 0 else 0
            elif metric == "avg_latency":
                total_latency = int(metrics.get("total_latency", 0))
                count = int(metrics.get("total_requests", 0))
                score = -1 * (total_latency / count) if count > 0 else -999999
            elif metric == "feedback_score":
                score = float(metrics.get("avg_feedback_score", 0))
            else:
                score = 0
                
            if score > best_score:
                best_score = score
                best_prompt_id = prompt_id
                
        if best_prompt_id:
            return await self._get_prompt_by_id(best_prompt_id)
        else:
            return self._get_default_prompt(content_type)
            
    def _get_default_prompt(self, content_type: ContentType) -> PromptTemplate:
        """Get default prompt for content type."""
        prompts = {
            ContentType.ABSTRACT_TO_OUTLINE: PromptTemplate(
                id="default_abstract_to_outline",
                name="Abstract to Outline Generator",
                content_type=ContentType.ABSTRACT_TO_OUTLINE,
                template="""You are an expert academic presentation designer. Convert the following research abstract into a clear, logical presentation outline.

Abstract:
{abstract}

Presentation Context:
- Target audience: {audience}
- Time limit: {duration} minutes
- Number of slides: {slide_count}

Create a presentation outline that:
1. Has a clear narrative flow
2. Highlights key findings and contributions
3. Includes appropriate sections (Introduction, Methods, Results, Discussion, Conclusion)
4. Suggests visual elements for complex concepts
5. Allocates time appropriately across sections

Format the outline with:
- Section titles
- Key points for each section
- Suggested slide count per section
- Visual suggestions where applicable""",
                variables=["abstract", "audience", "duration", "slide_count"],
                version=1
            ),
            
            ContentType.CONTENT_TO_SLIDES: PromptTemplate(
                id="default_content_to_slides",
                name="Content to Slides Splitter",
                content_type=ContentType.CONTENT_TO_SLIDES,
                template="""Convert the following research content into individual slide content. Create clear, concise slides that effectively communicate the research.

Content:
{content}

Section: {section}
Slide Type: {slide_type}

Create slide content that:
1. Has a clear, descriptive title
2. Contains 3-5 bullet points (max 10 words each)
3. Suggests relevant visuals or diagrams
4. Includes speaker notes for presentation
5. Maintains academic rigor while being accessible

Consider:
- Visual hierarchy and readability
- Data visualization for results
- Conceptual diagrams for methods
- Clear takeaway messages""",
                variables=["content", "section", "slide_type"],
                version=1
            ),
            
            ContentType.CITATION_FORMAT: PromptTemplate(
                id="default_citation_format",
                name="Citation Formatter",
                content_type=ContentType.CITATION_FORMAT,
                template="""Format the following references according to {citation_style} style.

References:
{references}

Requirements:
1. Ensure all citations follow {citation_style} format exactly
2. Maintain consistent formatting
3. Include all required fields (authors, year, title, journal/conference, etc.)
4. Sort alphabetically by first author's last name
5. Handle special characters and formatting properly

Output formatted citations only, one per line.""",
                variables=["references", "citation_style"],
                version=1
            ),
            
            ContentType.METHODOLOGY_VISUAL: PromptTemplate(
                id="default_methodology_visual",
                name="Methodology Visualizer",
                content_type=ContentType.METHODOLOGY_VISUAL,
                template="""Create a visual representation description for the following research methodology.

Methodology:
{methodology}

Research Type: {research_type}

Generate:
1. A flowchart/diagram description showing the methodology steps
2. Key components and their relationships
3. Data flow or process flow
4. Important decision points or branches
5. Visual style suggestions (colors, shapes, icons)

Make the visual:
- Clear and easy to follow
- Academically appropriate
- Self-explanatory with proper labels
- Suitable for a presentation slide""",
                variables=["methodology", "research_type"],
                version=1
            ),
            
            ContentType.RESULTS_SUMMARY: PromptTemplate(
                id="default_results_summary",
                name="Results Summarizer",
                content_type=ContentType.RESULTS_SUMMARY,
                template="""Summarize the following research results for presentation.

Results:
{results}

Study Type: {study_type}
Key Metrics: {key_metrics}

Create a results summary that:
1. Highlights the most significant findings
2. Presents statistical significance clearly
3. Suggests appropriate visualizations (charts, graphs, tables)
4. Provides context and interpretation
5. Links results to research questions/hypotheses

Format:
- Main findings (3-5 key points)
- Statistical details (p-values, effect sizes, confidence intervals)
- Visual suggestions with specific chart types
- Implications and takeaways""",
                variables=["results", "study_type", "key_metrics"],
                version=1
            ),
            
            ContentType.KEY_POINTS: PromptTemplate(
                id="default_key_points",
                name="Key Points Extractor",
                content_type=ContentType.KEY_POINTS,
                template="""Extract the key points from the following academic content.

Content:
{content}

Context: {context}

Extract:
1. Main arguments or findings (3-5 points)
2. Supporting evidence for each point
3. Practical implications
4. Limitations or caveats
5. Future directions

Format as clear, concise bullet points suitable for presentation slides.""",
                variables=["content", "context"],
                version=1
            ),
            
            ContentType.SPEAKER_NOTES: PromptTemplate(
                id="default_speaker_notes",
                name="Speaker Notes Generator",
                content_type=ContentType.SPEAKER_NOTES,
                template="""Generate speaker notes for the following presentation slide.

Slide Content:
{slide_content}

Slide Context:
- Section: {section}
- Duration: {duration} seconds
- Audience: {audience}

Create speaker notes that:
1. Expand on bullet points with examples
2. Include transition phrases
3. Add relevant anecdotes or explanations
4. Suggest engagement techniques (questions, interactions)
5. Include timing cues

Tone: Professional yet conversational, suitable for {audience}
Length: {duration} seconds of speaking time""",
                variables=["slide_content", "section", "duration", "audience"],
                version=1
            ),
        }
        
        return prompts.get(
            content_type,
            PromptTemplate(
                id="default_generic",
                name="Generic Template",
                content_type=content_type,
                template="Process the following content: {content}",
                variables=["content"],
                version=1
            )
        )
        
    async def _get_cached_prompt(
        self,
        content_type: ContentType,
        version: Optional[int] = None
    ) -> Optional[PromptTemplate]:
        """Get prompt from cache."""
        redis = await get_redis_client()
        
        cache_key = f"prompt:{content_type}:{version or 'latest'}"
        cached_data = await redis.get(cache_key)
        
        if cached_data:
            data = json.loads(cached_data)
            return PromptTemplate(**data)
            
        return None
        
    async def _cache_prompt(self, prompt: PromptTemplate) -> None:
        """Cache prompt template."""
        redis = await get_redis_client()
        
        cache_key = f"prompt:{prompt.content_type}:{prompt.version}"
        await redis.setex(
            cache_key,
            self._cache_ttl,
            json.dumps(prompt.model_dump())
        )
        
        # Also cache as latest if active
        if prompt.is_active:
            latest_key = f"prompt:{prompt.content_type}:latest"
            await redis.setex(
                latest_key,
                self._cache_ttl,
                json.dumps(prompt.model_dump())
            )
            
    async def _invalidate_cache(self, content_type: ContentType) -> None:
        """Invalidate cached prompts for content type."""
        redis = await get_redis_client()
        
        pattern = f"prompt:{content_type}:*"
        keys = await redis.keys(pattern)
        
        if keys:
            await redis.delete(*keys)
            
    async def _update_aggregate_metrics(
        self,
        prompt_id: str,
        data: Dict[str, Any]
    ) -> None:
        """Update aggregate performance metrics."""
        redis = await get_redis_client()
        
        # Get prompt details
        prompt = await self._get_prompt_by_id(prompt_id)
        if not prompt:
            return
            
        key = f"prompt:metrics:{prompt.content_type}:{prompt_id}"
        
        # Update counters
        await redis.hincrby(key, "total_requests", 1)
        if data.get("success"):
            await redis.hincrby(key, "success_count", 1)
            
        # Update latency
        await redis.hincrby(key, "total_latency", data.get("latency_ms", 0))
        
        # Update token usage
        await redis.hincrby(key, "total_tokens", data.get("tokens_used", 0))
        
        # Update feedback score (running average)
        if "feedback_score" in data:
            current_avg = float(await redis.hget(key, "avg_feedback_score") or 0)
            current_count = int(await redis.hget(key, "feedback_count") or 0)
            
            new_avg = ((current_avg * current_count) + data["feedback_score"]) / (current_count + 1)
            
            await redis.hset(key, "avg_feedback_score", new_avg)
            await redis.hincrby(key, "feedback_count", 1)
            
        # Set expiry
        await redis.expire(key, 86400 * 30)  # 30 days
        
    async def _get_prompt_by_id(self, prompt_id: str) -> Optional[PromptTemplate]:
        """Get prompt by ID."""
        # Try cache first
        redis = await get_redis_client()
        cached = await redis.get(f"prompt:id:{prompt_id}")
        
        if cached:
            return PromptTemplate(**json.loads(cached))
            
        # In production, this would query the database
        # For now, return None
        return None
        
    async def _get_db_prompt(
        self,
        content_type: ContentType,
        version: Optional[int] = None,
        ab_test: bool = True
    ) -> PromptTemplate:
        """Get prompt from database with A/B testing."""
        # In production, this would:
        # 1. Query database for active prompts
        # 2. Apply A/B testing logic
        # 3. Return selected prompt
        
        # For now, return default
        return self._get_default_prompt(content_type)
        
    async def _save_prompt_to_db(self, prompt: PromptTemplate) -> None:
        """Save prompt to database."""
        # In production, this would save to database
        # For now, just cache it
        await self._cache_prompt(prompt)