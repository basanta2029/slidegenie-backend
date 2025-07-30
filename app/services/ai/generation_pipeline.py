"""
AI-powered presentation generation pipeline.
"""
import asyncio
import json
import time
from datetime import datetime, timezone
from typing import Any, AsyncIterator, Dict, List, Optional, Union
from uuid import UUID

import structlog
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.domain.schemas.presentation import (
    PresentationCreate,
    SlideCreate,
    SlideLayout,
    SlideType,
)
from app.infrastructure.cache.redis import get_redis_client
from app.services.ai.anthropic_provider import AnthropicProvider
from app.services.ai.base import (
    AIProvider,
    AIProviderBase,
    AIResponse,
    ContentType,
    GenerationRequest,
)
from app.services.ai.content_processor import ContentProcessor
from app.services.ai.cost_optimizer import CostOptimizer
from app.services.ai.openai_provider import OpenAIProvider
from app.services.ai.prompt_manager import PromptManager

logger = structlog.get_logger(__name__)
settings = get_settings()


class GenerationProgress(BaseModel):
    """Generation progress update."""
    job_id: str
    status: str  # 'processing', 'generating', 'completed', 'failed'
    current_step: str
    progress: float  # 0.0 to 1.0
    message: str
    metadata: Optional[Dict[str, Any]] = None
    

class OutlineSection(BaseModel):
    """Presentation outline section."""
    title: str
    slide_count: int
    duration_minutes: float
    key_points: List[str]
    visual_suggestions: List[str]
    notes: Optional[str] = None
    

class PresentationOutline(BaseModel):
    """Complete presentation outline."""
    title: str
    sections: List[OutlineSection]
    total_slides: int
    total_duration: float
    theme_suggestions: List[str]
    

class SlideContent(BaseModel):
    """Generated slide content."""
    title: str
    subtitle: Optional[str] = None
    content_items: List[str]
    speaker_notes: str
    visual_elements: List[Dict[str, Any]]
    layout_type: SlideLayout
    citations: List[str] = []
    

class GenerationPipeline:
    """Main pipeline for AI-powered presentation generation."""
    
    def __init__(self, db_session: Optional[AsyncSession] = None):
        self.db = db_session
        self.content_processor = ContentProcessor()
        self.prompt_manager = PromptManager(db_session)
        self.cost_optimizer = CostOptimizer()
        
        # Initialize providers
        self.providers: Dict[AIProvider, AIProviderBase] = {}
        if settings.ANTHROPIC_API_KEY:
            self.providers[AIProvider.ANTHROPIC] = AnthropicProvider()
        if settings.OPENAI_API_KEY:
            self.providers[AIProvider.OPENAI] = OpenAIProvider()
            
        # Fallback order
        self.provider_order = [AIProvider.ANTHROPIC, AIProvider.OPENAI]
        
    async def generate_presentation(
        self,
        content: str,
        user_id: UUID,
        title: str,
        options: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[Union[GenerationProgress, Dict[str, Any]]]:
        """Generate complete presentation from content."""
        job_id = str(UUID())
        options = options or {}
        
        try:
            # Start progress tracking
            await self._update_progress(
                job_id, "processing", "Analyzing content", 0.1,
                {"content_length": len(content)}
            )
            yield self._create_progress(job_id, "processing", "Analyzing content", 0.1)
            
            # Process content
            processed_chunks = self.content_processor.process_document(content)
            
            # Extract key information
            abstract = self.content_processor.extract_abstract(content)
            key_sections = self.content_processor.extract_key_sections(content)
            
            await self._update_progress(
                job_id, "processing", "Content analysis complete", 0.2,
                {"sections_found": len(key_sections), "chunks": len(processed_chunks)}
            )
            yield self._create_progress(job_id, "processing", "Content analysis complete", 0.2)
            
            # Generate outline
            await self._update_progress(job_id, "generating", "Creating presentation outline", 0.3)
            yield self._create_progress(job_id, "generating", "Creating presentation outline", 0.3)
            
            outline = await self._generate_outline(
                abstract or content[:1000],
                key_sections,
                options
            )
            
            await self._update_progress(
                job_id, "generating", "Outline created", 0.4,
                {"total_slides": outline.total_slides}
            )
            yield self._create_progress(job_id, "generating", "Outline created", 0.4)
            
            # Generate slides
            slides = []
            total_sections = len(outline.sections)
            
            for i, section in enumerate(outline.sections):
                progress = 0.4 + (0.5 * (i / total_sections))
                
                await self._update_progress(
                    job_id, "generating", f"Generating section: {section.title}", progress
                )
                yield self._create_progress(
                    job_id, "generating", f"Generating section: {section.title}", progress
                )
                
                # Get relevant content for section
                section_content = self._get_section_content(
                    section.title,
                    key_sections,
                    processed_chunks
                )
                
                # Generate slides for section
                section_slides = await self._generate_section_slides(
                    section,
                    section_content,
                    options
                )
                
                slides.extend(section_slides)
                
            # Add title slide
            title_slide = await self._generate_title_slide(title, outline, options)
            slides.insert(0, title_slide)
            
            # Add conclusion slide
            conclusion_slide = await self._generate_conclusion_slide(
                outline,
                key_sections.get("conclusion", ""),
                options
            )
            slides.append(conclusion_slide)
            
            await self._update_progress(
                job_id, "completed", "Presentation generated successfully", 1.0,
                {"total_slides": len(slides)}
            )
            yield self._create_progress(
                job_id, "completed", "Presentation generated successfully", 1.0)
            
            # Return final result
            yield {
                "type": "result",
                "presentation": {
                    "title": title,
                    "outline": outline.model_dump(),
                    "slides": [slide.model_dump() for slide in slides],
                    "metadata": {
                        "generation_time": datetime.now(timezone.utc).isoformat(),
                        "total_slides": len(slides),
                        "estimated_duration": outline.total_duration,
                        "job_id": job_id
                    }
                }
            }
            
        except Exception as e:
            logger.error("generation_pipeline_error", error=str(e), job_id=job_id)
            
            await self._update_progress(
                job_id, "failed", f"Generation failed: {str(e)}", 0.0
            )
            yield self._create_progress(
                job_id, "failed", f"Generation failed: {str(e)}", 0.0
            )
            
            raise
            
    async def _generate_outline(
        self,
        abstract: str,
        key_sections: Dict[str, str],
        options: Dict[str, Any]
    ) -> PresentationOutline:
        """Generate presentation outline."""
        # Get prompt template
        prompt_template = await self.prompt_manager.get_prompt(
            ContentType.ABSTRACT_TO_OUTLINE
        )
        
        # Format prompt
        prompt = prompt_template.format(
            abstract=abstract,
            audience=options.get("audience", "academic researchers"),
            duration=options.get("duration", 20),
            slide_count=options.get("slide_count", 15)
        )
        
        # Check cache
        cached_response = await self.cost_optimizer.get_cached_response(
            abstract,
            ContentType.ABSTRACT_TO_OUTLINE,
            **options
        )
        
        if cached_response:
            return PresentationOutline(**cached_response)
            
        # Generate with fallback
        response = await self._generate_with_fallback(
            prompt,
            ContentType.ABSTRACT_TO_OUTLINE,
            PresentationOutline
        )
        
        # Cache response
        await self.cost_optimizer.cache_response(
            abstract,
            ContentType.ABSTRACT_TO_OUTLINE,
            response.content,
            **options
        )
        
        # Track usage
        await self.cost_optimizer.track_usage(
            response.provider,
            response.model,
            response.usage.total_tokens,
            response.usage.estimated_cost,
            response.latency_ms,
            response.cached
        )
        
        return PresentationOutline(**response.content)
        
    async def _generate_section_slides(
        self,
        section: OutlineSection,
        content: str,
        options: Dict[str, Any]
    ) -> List[SlideContent]:
        """Generate slides for a section."""
        slides = []
        
        # Determine slide types based on section
        slide_types = self._determine_slide_types(section.title.lower())
        
        for i in range(section.slide_count):
            slide_type = slide_types[i % len(slide_types)] if slide_types else SlideType.CONTENT
            
            # Get relevant content chunk
            chunk_size = len(content) // section.slide_count
            chunk_start = i * chunk_size
            chunk_end = min((i + 1) * chunk_size, len(content))
            chunk = content[chunk_start:chunk_end]
            
            # Generate slide content
            slide = await self._generate_slide_content(
                section_title=section.title,
                content=chunk,
                slide_type=slide_type,
                key_points=section.key_points[i] if i < len(section.key_points) else None,
                visual_suggestion=section.visual_suggestions[i] if i < len(section.visual_suggestions) else None,
                options=options
            )
            
            slides.append(slide)
            
        return slides
        
    async def _generate_slide_content(
        self,
        section_title: str,
        content: str,
        slide_type: SlideType,
        key_points: Optional[str] = None,
        visual_suggestion: Optional[str] = None,
        options: Dict[str, Any] = None
    ) -> SlideContent:
        """Generate individual slide content."""
        # Get prompt template
        prompt_template = await self.prompt_manager.get_prompt(
            ContentType.CONTENT_TO_SLIDES
        )
        
        # Format prompt
        prompt = prompt_template.format(
            content=content,
            section=section_title,
            slide_type=slide_type
        )
        
        # Generate with fallback
        response = await self._generate_with_fallback(
            prompt,
            ContentType.CONTENT_TO_SLIDES,
            SlideContent
        )
        
        slide_content = SlideContent(**response.content)
        
        # Add visual suggestion if provided
        if visual_suggestion:
            slide_content.visual_elements.append({
                "type": "suggestion",
                "description": visual_suggestion
            })
            
        # Generate speaker notes
        speaker_notes = await self._generate_speaker_notes(
            slide_content,
            section_title,
            options
        )
        slide_content.speaker_notes = speaker_notes
        
        return slide_content
        
    async def _generate_speaker_notes(
        self,
        slide: SlideContent,
        section: str,
        options: Dict[str, Any]
    ) -> str:
        """Generate speaker notes for slide."""
        prompt_template = await self.prompt_manager.get_prompt(
            ContentType.SPEAKER_NOTES
        )
        
        prompt = prompt_template.format(
            slide_content=json.dumps(slide.model_dump()),
            section=section,
            duration=options.get("slide_duration", 60),
            audience=options.get("audience", "academic researchers")
        )
        
        response = await self._generate_with_fallback(
            prompt,
            ContentType.SPEAKER_NOTES
        )
        
        return response.content
        
    async def _generate_title_slide(
        self,
        title: str,
        outline: PresentationOutline,
        options: Dict[str, Any]
    ) -> SlideContent:
        """Generate title slide."""
        return SlideContent(
            title=title,
            subtitle=options.get("subtitle", "Research Presentation"),
            content_items=[
                options.get("authors", ""),
                options.get("institution", ""),
                options.get("date", datetime.now().strftime("%B %Y")),
            ],
            speaker_notes=f"Welcome everyone. Today I'll be presenting {title}. This presentation will cover {len(outline.sections)} main sections and take approximately {outline.total_duration} minutes.",
            visual_elements=[{
                "type": "logo",
                "position": "bottom-right"
            }],
            layout_type=SlideLayout.TITLE
        )
        
    async def _generate_conclusion_slide(
        self,
        outline: PresentationOutline,
        conclusion_content: str,
        options: Dict[str, Any]
    ) -> SlideContent:
        """Generate conclusion slide."""
        key_takeaways = []
        for section in outline.sections:
            if section.key_points:
                key_takeaways.append(section.key_points[0])
                
        return SlideContent(
            title="Conclusions",
            content_items=key_takeaways[:5],  # Top 5 takeaways
            speaker_notes="To conclude, " + (conclusion_content[:200] if conclusion_content else "let me summarize the key findings of this research."),
            visual_elements=[{
                "type": "summary",
                "style": "bullet-points"
            }],
            layout_type=SlideLayout.CONTENT
        )
        
    async def _generate_with_fallback(
        self,
        prompt: str,
        content_type: ContentType,
        response_model: Optional[type[BaseModel]] = None
    ) -> AIResponse:
        """Generate with provider fallback."""
        # Select optimal provider
        provider, model = await self.cost_optimizer.select_optimal_provider(
            content_type,
            len(prompt) // 4,  # Estimated tokens
            quality_required=0.8
        )
        
        # Try primary provider
        if provider in self.providers:
            try:
                provider_instance = self.providers[provider]
                
                if response_model:
                    return await provider_instance.generate_structured(
                        prompt,
                        response_model,
                        model=model
                    )
                else:
                    return await provider_instance.generate(
                        prompt,
                        model=model
                    )
            except Exception as e:
                logger.error(
                    "primary_provider_failed",
                    provider=provider,
                    error=str(e)
                )
                
        # Fallback to other providers
        for fallback_provider in self.provider_order:
            if fallback_provider != provider and fallback_provider in self.providers:
                try:
                    provider_instance = self.providers[fallback_provider]
                    
                    # Select appropriate model for fallback
                    fallback_model = provider_instance.select_model_for_task(
                        content_type,
                        len(prompt) // 4
                    )
                    
                    if response_model:
                        return await provider_instance.generate_structured(
                            prompt,
                            response_model,
                            model=fallback_model
                        )
                    else:
                        return await provider_instance.generate(
                            prompt,
                            model=fallback_model
                        )
                except Exception as e:
                    logger.error(
                        "fallback_provider_failed",
                        provider=fallback_provider,
                        error=str(e)
                    )
                    continue
                    
        raise Exception("All AI providers failed")
        
    def _get_section_content(
        self,
        section_title: str,
        key_sections: Dict[str, str],
        processed_chunks: List[Any]
    ) -> str:
        """Get relevant content for section."""
        # Try to match with key sections
        section_lower = section_title.lower()
        
        for key, content in key_sections.items():
            if key in section_lower or section_lower in key:
                return content
                
        # Fall back to chunks
        relevant_chunks = []
        for chunk in processed_chunks:
            if chunk.section and section_title.lower() in chunk.section.lower():
                relevant_chunks.append(chunk.text)
                
        return "\n\n".join(relevant_chunks) if relevant_chunks else ""
        
    def _determine_slide_types(self, section_title: str) -> List[SlideType]:
        """Determine appropriate slide types for section."""
        if "method" in section_title or "approach" in section_title:
            return [SlideType.CONTENT, SlideType.DIAGRAM, SlideType.CONTENT]
        elif "result" in section_title or "finding" in section_title:
            return [SlideType.CONTENT, SlideType.CHART, SlideType.TABLE]
        elif "introduction" in section_title or "background" in section_title:
            return [SlideType.CONTENT, SlideType.IMAGE, SlideType.CONTENT]
        else:
            return [SlideType.CONTENT]
            
    async def _update_progress(
        self,
        job_id: str,
        status: str,
        message: str,
        progress: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Update job progress in Redis."""
        redis = await get_redis_client()
        
        progress_data = {
            "job_id": job_id,
            "status": status,
            "message": message,
            "progress": progress,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "metadata": metadata or {}
        }
        
        # Store in Redis
        await redis.setex(
            f"generation:progress:{job_id}",
            3600,  # 1 hour TTL
            json.dumps(progress_data)
        )
        
        # Publish to channel for real-time updates
        await redis.publish(
            f"generation:updates:{job_id}",
            json.dumps(progress_data)
        )
        
    def _create_progress(
        self,
        job_id: str,
        status: str,
        message: str,
        progress: float,
        metadata: Optional[Dict[str, Any]] = None
    ) -> GenerationProgress:
        """Create progress update object."""
        return GenerationProgress(
            job_id=job_id,
            status=status,
            current_step=message,
            progress=progress,
            message=message,
            metadata=metadata
        )
        
    async def stream_generation(
        self,
        content: str,
        user_id: UUID,
        title: str,
        options: Optional[Dict[str, Any]] = None
    ) -> AsyncIterator[str]:
        """Stream generation updates via WebSocket."""
        async for update in self.generate_presentation(content, user_id, title, options):
            yield json.dumps(update.model_dump() if hasattr(update, 'model_dump') else update)