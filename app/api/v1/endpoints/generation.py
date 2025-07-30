"""
Presentation generation API endpoints.
"""
import json
from typing import Any, Dict, Optional
from uuid import UUID

import structlog
from fastapi import APIRouter, Depends, HTTPException, WebSocket, WebSocketDisconnect, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user
from app.core.database import get_db
from app.domain.schemas.user import UserRead
from app.services.ai.generation_pipeline import GenerationPipeline

logger = structlog.get_logger(__name__)
router = APIRouter()


class GenerationRequest(BaseModel):
    """Presentation generation request."""
    content: str = Field(..., min_length=50, max_length=50000)
    title: str = Field(..., min_length=1, max_length=200)
    options: Optional[Dict[str, Any]] = Field(default_factory=dict)
    

class GenerationResponse(BaseModel):
    """Generation response."""
    job_id: str
    status: str
    message: str
    

@router.post("/generate", response_model=GenerationResponse)
async def generate_presentation(
    request: GenerationRequest,
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GenerationResponse:
    """Generate presentation from content (async)."""
    try:
        pipeline = GenerationPipeline(db)
        
        # Start async generation
        job_id = str(UUID())
        
        # TODO: Queue generation job
        # For now, return job ID for WebSocket connection
        
        logger.info(
            "generation_started",
            user_id=str(current_user.id),
            job_id=job_id,
            content_length=len(request.content),
        )
        
        return GenerationResponse(
            job_id=job_id,
            status="processing",
            message="Generation started. Connect via WebSocket for updates.",
        )
        
    except Exception as e:
        logger.error("generation_error", error=str(e), user_id=str(current_user.id))
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to start generation",
        )
        

@router.post("/generate/stream")
async def generate_presentation_stream(
    request: GenerationRequest,
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Generate presentation with streaming response."""
    pipeline = GenerationPipeline(db)
    
    async def generate():
        try:
            async for update in pipeline.stream_generation(
                request.content,
                current_user.id,
                request.title,
                request.options,
            ):
                yield f"data: {update}\n\n"
        except Exception as e:
            logger.error("stream_generation_error", error=str(e))
            yield f"data: {json.dumps({'error': str(e)})}\n\n"
            
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
    

@router.websocket("/generate/ws/{job_id}")
async def websocket_generation(
    websocket: WebSocket,
    job_id: str,
    db: AsyncSession = Depends(get_db),
):
    """WebSocket endpoint for real-time generation updates."""
    await websocket.accept()
    
    # TODO: Verify user has access to this job
    
    try:
        # Subscribe to Redis channel for updates
        from app.infrastructure.cache import get_redis_client
        redis = await get_redis_client()
        
        pubsub = redis.pubsub()
        await pubsub.subscribe(f"generation:updates:{job_id}")
        
        # Send current progress
        current_progress = await redis.get(f"generation:progress:{job_id}")
        if current_progress:
            await websocket.send_text(current_progress)
            
        # Listen for updates
        async for message in pubsub.listen():
            if message["type"] == "message":
                await websocket.send_text(message["data"])
                
                # Check if generation is complete
                data = json.loads(message["data"])
                if data.get("status") in ["completed", "failed"]:
                    break
                    
    except WebSocketDisconnect:
        logger.info("websocket_disconnected", job_id=job_id)
    except Exception as e:
        logger.error("websocket_error", error=str(e), job_id=job_id)
        await websocket.send_text(json.dumps({"error": str(e)}))
    finally:
        await websocket.close()
        

class GenerationStatus(BaseModel):
    """Generation job status."""
    job_id: str
    status: str
    progress: float
    message: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    

@router.get("/status/{job_id}", response_model=GenerationStatus)
async def get_generation_status(
    job_id: str,
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> GenerationStatus:
    """Get generation job status."""
    # TODO: Verify user has access to this job
    
    from app.infrastructure.cache import get_redis_client
    redis = await get_redis_client()
    
    # Get progress data
    progress_data = await redis.get(f"generation:progress:{job_id}")
    if not progress_data:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Job not found",
        )
        
    progress = json.loads(progress_data)
    
    # Get result if completed
    result = None
    if progress.get("status") == "completed":
        result_data = await redis.get(f"generation:result:{job_id}")
        if result_data:
            result = json.loads(result_data)
            
    return GenerationStatus(
        job_id=job_id,
        status=progress.get("status", "unknown"),
        progress=progress.get("progress", 0.0),
        message=progress.get("message", ""),
        result=result,
        error=progress.get("error"),
    )
    

class ContentAnalysis(BaseModel):
    """Content analysis result."""
    word_count: int
    estimated_slides: int
    estimated_duration: float
    detected_sections: List[str]
    key_topics: List[str]
    citations_found: int
    

@router.post("/analyze", response_model=ContentAnalysis)
async def analyze_content(
    content: str = Field(..., min_length=50, max_length=50000),
    current_user: UserRead = Depends(get_current_user),
) -> ContentAnalysis:
    """Analyze content before generation."""
    from app.services.ai.content_processor import ContentProcessor
    
    processor = ContentProcessor()
    
    # Extract sections
    sections = processor.extract_key_sections(content)
    key_points = processor.extract_key_points(content, max_points=10)
    
    # Count words
    word_count = len(content.split())
    
    # Estimate slides (roughly 100-150 words per slide)
    estimated_slides = max(5, min(50, word_count // 120))
    
    # Estimate duration (1-2 minutes per slide)
    estimated_duration = estimated_slides * 1.5
    
    # Extract citations
    import re
    citations = re.findall(r'\[([\d,\s-]+)\]|\(([^)]+(?:19|20)\d{2}[^)]*?)\)', content)
    
    return ContentAnalysis(
        word_count=word_count,
        estimated_slides=estimated_slides,
        estimated_duration=estimated_duration,
        detected_sections=list(sections.keys()),
        key_topics=key_points[:5],
        citations_found=len(citations),
    )
    

class CostEstimateRequest(BaseModel):
    """Cost estimate request."""
    content: str = Field(..., min_length=50, max_length=50000)
    options: Optional[Dict[str, Any]] = Field(default_factory=dict)
    

class CostEstimateResponse(BaseModel):
    """Cost estimate response."""
    estimates: List[Dict[str, Any]]
    recommended_provider: str
    estimated_total_cost: float
    cache_savings_potential: float
    

@router.post("/estimate-cost", response_model=CostEstimateResponse)
async def estimate_generation_cost(
    request: CostEstimateRequest,
    current_user: UserRead = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> CostEstimateResponse:
    """Estimate cost for presentation generation."""
    from app.services.ai.cost_optimizer import CostOptimizer
    from app.services.ai.base import AIProvider, ContentType
    
    optimizer = CostOptimizer()
    
    # Get estimates for different providers
    estimates = await optimizer.estimate_cost(
        request.content,
        ContentType.ABSTRACT_TO_OUTLINE,
        [AIProvider.ANTHROPIC, AIProvider.OPENAI],
    )
    
    # Convert to dict format
    estimate_dicts = [
        {
            "provider": est.provider,
            "model": est.model,
            "estimated_tokens": est.estimated_tokens,
            "estimated_cost": est.estimated_cost,
            "cached": est.cached,
            "cache_hit_probability": est.cache_hit_probability,
        }
        for est in estimates
    ]
    
    # Get recommended provider
    recommended_provider, recommended_model = await optimizer.select_optimal_provider(
        ContentType.ABSTRACT_TO_OUTLINE,
        estimates[0].estimated_tokens if estimates else 1000,
        quality_required=0.8,
    )
    
    # Calculate total cost (assuming full generation)
    total_cost = sum(est.estimated_cost for est in estimates[:1]) * 3  # Rough multiplier
    
    # Calculate cache savings
    cache_savings = total_cost * 0.3  # Assume 30% cache hit rate
    
    return CostEstimateResponse(
        estimates=estimate_dicts,
        recommended_provider=f"{recommended_provider}:{recommended_model}",
        estimated_total_cost=round(total_cost, 4),
        cache_savings_potential=round(cache_savings, 4),
    )