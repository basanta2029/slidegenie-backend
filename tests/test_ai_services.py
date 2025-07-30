"""
Tests for AI service components.
"""
import json
from datetime import datetime, timezone
from typing import Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pydantic import BaseModel

from app.services.ai.base import (
    AIProvider,
    AIResponse,
    ContentType,
    TokenUsage,
)
from app.services.ai.content_processor import ContentProcessor, ProcessedChunk
from app.services.ai.cost_optimizer import CostEstimate, CostOptimizer
from app.services.ai.generation_pipeline import (
    GenerationPipeline,
    PresentationOutline,
    SlideContent,
)
from app.services.ai.prompt_manager import PromptManager


class TestContentProcessor:
    """Test content processing functionality."""
    
    @pytest.fixture
    def processor(self):
        return ContentProcessor()
        
    @pytest.fixture
    def sample_paper(self):
        return """
# Abstract
This research presents a novel approach to quantum computing using topological qubits.
We demonstrate a 99.9% fidelity rate in quantum gate operations.

## Introduction
Quantum computing has emerged as a transformative technology...

## Methods
We employed a hybrid approach combining:
1. Topological protection
2. Error correction codes
3. Machine learning optimization

## Results
Our experiments show:
- 99.9% gate fidelity
- 10x improvement in coherence time
- Scalable to 100+ qubits

## Conclusion
This work represents a significant advancement in quantum computing.
"""
    
    def test_extract_abstract(self, processor, sample_paper):
        """Test abstract extraction."""
        abstract = processor.extract_abstract(sample_paper)
        
        assert abstract is not None
        assert "novel approach" in abstract
        assert "topological qubits" in abstract
        assert "99.9% fidelity" in abstract
        
    def test_extract_sections(self, processor, sample_paper):
        """Test section extraction."""
        sections = processor._extract_sections(sample_paper)
        
        assert len(sections) > 0
        section_titles = [s.title for s in sections]
        
        assert "Abstract" in section_titles
        assert "Introduction" in section_titles
        assert "Methods" in section_titles
        assert "Results" in section_titles
        assert "Conclusion" in section_titles
        
    def test_extract_key_sections(self, processor, sample_paper):
        """Test key section extraction."""
        key_sections = processor.extract_key_sections(sample_paper)
        
        assert "introduction" in key_sections
        assert "methods" in key_sections
        assert "results" in key_sections
        assert "conclusion" in key_sections
        
        assert "quantum computing" in key_sections["introduction"]
        assert "hybrid approach" in key_sections["methods"]
        
    def test_process_document(self, processor, sample_paper):
        """Test complete document processing."""
        chunks = processor.process_document(sample_paper, chunk_size=500)
        
        assert len(chunks) > 0
        assert all(isinstance(chunk, ProcessedChunk) for chunk in chunks)
        
        # Check chunk properties
        first_chunk = chunks[0]
        assert first_chunk.text
        assert first_chunk.token_count > 0
        assert first_chunk.section is not None
        
    def test_extract_key_points(self, processor, sample_paper):
        """Test key point extraction."""
        results_section = "Our experiments show: 99.9% gate fidelity, 10x improvement in coherence time"
        key_points = processor.extract_key_points(results_section, max_points=3)
        
        assert len(key_points) > 0
        assert any("99.9%" in point for point in key_points)
        

class TestPromptManager:
    """Test prompt management functionality."""
    
    @pytest.fixture
    def manager(self):
        return PromptManager()
        
    @pytest.mark.asyncio
    async def test_get_default_prompt(self, manager):
        """Test getting default prompts."""
        prompt = await manager.get_prompt(ContentType.ABSTRACT_TO_OUTLINE)
        
        assert prompt is not None
        assert prompt.content_type == ContentType.ABSTRACT_TO_OUTLINE
        assert prompt.template
        assert prompt.variables
        assert "abstract" in prompt.variables
        
    @pytest.mark.asyncio
    async def test_create_prompt(self, manager):
        """Test creating new prompt."""
        with patch('app.services.ai.prompt_manager.get_redis_client') as mock_redis:
            mock_redis.return_value = AsyncMock()
            
            prompt = await manager.create_prompt(
                name="Test Prompt",
                content_type=ContentType.KEY_POINTS,
                template="Extract {count} key points from {content}",
                variables=["count", "content"]
            )
            
            assert prompt.name == "Test Prompt"
            assert prompt.content_type == ContentType.KEY_POINTS
            assert prompt.version == 1
            assert prompt.is_active
            
    @pytest.mark.asyncio
    async def test_prompt_performance_tracking(self, manager):
        """Test performance tracking."""
        with patch('app.services.ai.prompt_manager.get_redis_client') as mock_redis:
            mock_redis.return_value = AsyncMock()
            
            await manager.record_performance(
                prompt_id="test_prompt",
                success=True,
                latency_ms=150,
                tokens_used=1000,
                feedback_score=0.9
            )
            
            # Verify Redis calls
            mock_redis.return_value.zadd.assert_called_once()
            

class TestCostOptimizer:
    """Test cost optimization functionality."""
    
    @pytest.fixture
    def optimizer(self):
        return CostOptimizer()
        
    @pytest.mark.asyncio
    async def test_estimate_cost(self, optimizer):
        """Test cost estimation."""
        content = "This is a test content for cost estimation" * 100
        
        estimates = await optimizer.estimate_cost(
            content,
            ContentType.ABSTRACT_TO_OUTLINE,
            [AIProvider.ANTHROPIC, AIProvider.OPENAI]
        )
        
        assert len(estimates) == 2
        assert all(isinstance(e, CostEstimate) for e in estimates)
        
        # Check cost ordering (should be sorted by cost)
        costs = [e.estimated_cost for e in estimates]
        assert costs == sorted(costs)
        
    @pytest.mark.asyncio
    async def test_cache_operations(self, optimizer):
        """Test cache operations."""
        with patch('app.services.ai.cost_optimizer.get_redis_client') as mock_redis:
            mock_client = AsyncMock()
            mock_redis.return_value = mock_client
            
            content = "Test content"
            response = {"result": "Generated output"}
            
            # Test cache miss
            mock_client.get.return_value = None
            cached = await optimizer.get_cached_response(
                content,
                ContentType.KEY_POINTS
            )
            assert cached is None
            
            # Cache the response
            await optimizer.cache_response(
                content,
                ContentType.KEY_POINTS,
                response
            )
            
            # Test cache hit
            mock_client.get.return_value = json.dumps(response)
            cached = await optimizer.get_cached_response(
                content,
                ContentType.KEY_POINTS
            )
            assert cached == response
            
    @pytest.mark.asyncio
    async def test_batch_requests(self, optimizer):
        """Test request batching."""
        from app.services.ai.cost_optimizer import BatchRequest
        
        requests = [
            BatchRequest(
                id="1",
                content="Content 1",
                content_type=ContentType.KEY_POINTS,
                priority=5,
                estimated_tokens=100
            ),
            BatchRequest(
                id="2",
                content="Content 2",
                content_type=ContentType.KEY_POINTS,
                priority=8,
                estimated_tokens=150
            ),
            BatchRequest(
                id="3",
                content="Content 3",
                content_type=ContentType.CITATION_FORMAT,
                priority=3,
                estimated_tokens=50
            ),
        ]
        
        batches = await optimizer.batch_requests(requests)
        
        assert len(batches) >= 1
        # Higher priority requests should be in earlier batches
        first_batch_priorities = [r.priority for r in batches[0]]
        assert max(first_batch_priorities) >= 5
        
    @pytest.mark.asyncio
    async def test_usage_tracking(self, optimizer):
        """Test usage tracking."""
        with patch('app.services.ai.cost_optimizer.get_redis_client') as mock_redis:
            mock_redis.return_value = AsyncMock()
            
            await optimizer.track_usage(
                provider=AIProvider.ANTHROPIC,
                model="claude-3-5-sonnet-20241022",
                tokens=1500,
                cost=0.045,
                latency_ms=250,
                cached=False
            )
            
            # Verify tracking calls
            mock_redis.return_value.pipeline.assert_called_once()
            

class TestGenerationPipeline:
    """Test generation pipeline functionality."""
    
    @pytest.fixture
    def pipeline(self):
        with patch('app.services.ai.generation_pipeline.AnthropicProvider'):
            with patch('app.services.ai.generation_pipeline.OpenAIProvider'):
                return GenerationPipeline()
                
    @pytest.fixture
    def mock_ai_response(self):
        return AIResponse(
            content={
                "title": "Test Presentation",
                "sections": [
                    {
                        "title": "Introduction",
                        "slide_count": 3,
                        "duration_minutes": 5,
                        "key_points": ["Point 1", "Point 2"],
                        "visual_suggestions": ["Diagram 1"]
                    }
                ],
                "total_slides": 10,
                "total_duration": 20,
                "theme_suggestions": ["Academic Blue"]
            },
            provider=AIProvider.ANTHROPIC,
            model="claude-3-5-sonnet-20241022",
            usage=TokenUsage(
                prompt_tokens=500,
                completion_tokens=200,
                total_tokens=700,
                estimated_cost=0.021
            ),
            latency_ms=150,
            cached=False
        )
        
    @pytest.mark.asyncio
    async def test_generate_outline(self, pipeline, mock_ai_response):
        """Test outline generation."""
        with patch.object(
            pipeline,
            '_generate_with_fallback',
            return_value=mock_ai_response
        ):
            outline = await pipeline._generate_outline(
                "Test abstract",
                {"introduction": "Intro content"},
                {"duration": 20}
            )
            
            assert outline.title == "Test Presentation"
            assert len(outline.sections) == 1
            assert outline.total_slides == 10
            
    @pytest.mark.asyncio
    async def test_generate_slide_content(self, pipeline):
        """Test slide content generation."""
        mock_response = AIResponse(
            content={
                "title": "Introduction to Quantum Computing",
                "content_items": [
                    "What is quantum computing?",
                    "Key principles: superposition and entanglement",
                    "Applications in cryptography and optimization"
                ],
                "speaker_notes": "Begin with a brief history...",
                "visual_elements": [{"type": "diagram", "description": "Qubit visualization"}],
                "layout_type": "content"
            },
            provider=AIProvider.ANTHROPIC,
            model="claude-3-5-sonnet-20241022",
            usage=TokenUsage(100, 50, 150, 0.0045),
            latency_ms=100
        )
        
        with patch.object(pipeline, '_generate_with_fallback', return_value=mock_response):
            slide = await pipeline._generate_slide_content(
                section_title="Introduction",
                content="Quantum computing basics...",
                slide_type="content"
            )
            
            assert slide.title == "Introduction to Quantum Computing"
            assert len(slide.content_items) == 3
            assert slide.speaker_notes
            assert len(slide.visual_elements) > 0
            
    @pytest.mark.asyncio
    async def test_progress_updates(self, pipeline):
        """Test progress update generation."""
        with patch('app.services.ai.generation_pipeline.get_redis_client') as mock_redis:
            mock_redis.return_value = AsyncMock()
            
            progress = pipeline._create_progress(
                job_id="test-job",
                status="processing",
                message="Analyzing content",
                progress=0.25
            )
            
            assert progress.job_id == "test-job"
            assert progress.status == "processing"
            assert progress.progress == 0.25
            
    @pytest.mark.asyncio
    async def test_provider_fallback(self, pipeline):
        """Test provider fallback mechanism."""
        # Mock primary provider failure
        with patch.object(
            pipeline.providers.get(AIProvider.ANTHROPIC, MagicMock()),
            'generate',
            side_effect=Exception("API Error")
        ):
            # Mock fallback provider success
            fallback_response = AIResponse(
                content="Fallback response",
                provider=AIProvider.OPENAI,
                model="gpt-4o-mini",
                usage=TokenUsage(100, 50, 150, 0.002),
                latency_ms=100
            )
            
            with patch.object(
                pipeline.providers.get(AIProvider.OPENAI, MagicMock()),
                'generate',
                return_value=fallback_response
            ):
                # Should use fallback
                response = await pipeline._generate_with_fallback(
                    "Test prompt",
                    ContentType.KEY_POINTS
                )
                
                assert response.provider == AIProvider.OPENAI
                assert response.content == "Fallback response"