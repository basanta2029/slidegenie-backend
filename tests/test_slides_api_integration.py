"""Integration tests for slides API endpoints."""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import Mock, AsyncMock, patch
import json
import io
from datetime import datetime

from app.main import app
from app.services.slides.service import SlideGenerationService
from app.services.slides.config import OutputFormat, LayoutStyle, QualityLevel
from app.domain.schemas.user import User


class TestSlidesAPIIntegration:
    """Integration tests for slides API endpoints."""
    
    @pytest.fixture
    def client(self):
        """Create test client."""
        return TestClient(app)
    
    @pytest.fixture
    def mock_user(self):
        """Create mock user for authentication."""
        return User(
            id=1,
            email="test@example.com",
            full_name="Test User",
            is_active=True
        )
    
    @pytest.fixture
    def mock_slide_service(self):
        """Create mock slide service."""
        service = Mock(spec=SlideGenerationService)
        
        # Mock generation methods
        service.generate_presentation = AsyncMock(return_value=(
            b"mock_presentation_data",
            {
                "job_id": "test_job_123",
                "format": "pptx",
                "slides_count": 5,
                "generation_time": 15.5,
                "quality_score": 0.85,
                "timestamp": datetime.utcnow().isoformat()
            }
        ))
        
        service.generate_from_preset = AsyncMock(return_value=(
            b"preset_presentation_data",
            {"job_id": "preset_job_456", "format": "pptx", "slides_count": 3}
        ))
        
        service.preview_presentation = AsyncMock(return_value=Mock(
            title="Preview Presentation",
            subtitle="Test Subtitle",
            slides=[
                Mock(title="Slide 1", content="Preview content 1", layout_type="title"),
                Mock(title="Slide 2", content="Preview content 2", layout_type="content")
            ]
        ))
        
        service.validate_content = AsyncMock(return_value=Mock(
            is_valid=True,
            errors=None,
            warnings=["Minor formatting issue"],
            suggestions=["Consider adding more detail"]
        ))
        
        service.get_job_status = Mock(return_value={
            "job_id": "test_job_123",
            "status": "completed",
            "progress": 100.0,
            "started_at": datetime.utcnow(),
            "completed_at": datetime.utcnow()
        })
        
        service.cancel_job = AsyncMock(return_value=True)
        
        service.get_supported_formats = Mock(return_value=[
            "pptx", "pdf", "google_slides", "reveal_js", "markdown"
        ])
        
        service.get_available_styles = Mock(return_value=[
            "minimal", "modern", "academic", "business", "creative"
        ])
        
        return service
    
    @patch('app.api.v1.endpoints.slides.slide_service')
    @patch('app.core.dependencies.get_current_user')
    @patch('app.services.auth.authorization.decorators.require_permission')
    def test_generate_presentation_endpoint(
        self, mock_permission, mock_get_user, mock_service, client, mock_user, mock_slide_service
    ):
        """Test presentation generation endpoint."""
        # Setup mocks
        mock_get_user.return_value = mock_user
        mock_permission.return_value = lambda f: f  # Bypass permission check
        mock_service.return_value = mock_slide_service
        
        # Test data
        request_data = {
            "content": "This is a test presentation about machine learning.",
            "output_format": "pptx",
            "title": "ML Presentation",
            "author": "Test Author",
            "options": {"max_slides": 10}
        }
        
        # Make request
        response = client.post("/api/v1/slides/generate", json=request_data)
        
        # Verify response
        assert response.status_code == 200
        data = response.json()
        
        assert "job_id" in data
        assert data["status"] == "processing"
        assert data["message"] == "Presentation generation started"
        assert "estimated_time" in data
    
    @patch('app.api.v1.endpoints.slides.slide_service')
    @patch('app.core.dependencies.get_current_user')
    @patch('app.services.auth.authorization.decorators.require_permission')
    def test_preview_presentation_endpoint(
        self, mock_permission, mock_get_user, mock_service, client, mock_user, mock_slide_service
    ):
        """Test presentation preview endpoint."""
        # Setup mocks
        mock_get_user.return_value = mock_user
        mock_permission.return_value = lambda f: f
        mock_service.return_value = mock_slide_service
        
        request_data = {
            "content": "This is test content for preview",
            "max_slides": 3
        }
        
        response = client.post("/api/v1/slides/preview", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["title"] == "Preview Presentation"
        assert data["subtitle"] == "Test Subtitle"
        assert data["slides_count"] == 2
        assert len(data["slides"]) == 2
        assert data["slides"][0]["title"] == "Slide 1"
    
    @patch('app.api.v1.endpoints.slides.slide_service')
    @patch('app.core.dependencies.get_current_user')
    @patch('app.services.auth.authorization.decorators.require_permission')
    def test_validate_content_endpoint(
        self, mock_permission, mock_get_user, mock_service, client, mock_user, mock_slide_service
    ):
        """Test content validation endpoint."""
        # Setup mocks
        mock_get_user.return_value = mock_user
        mock_permission.return_value = lambda f: f
        mock_service.return_value = mock_slide_service
        
        request_data = {
            "content": "This is content to validate"
        }
        
        response = client.post("/api/v1/slides/validate", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["is_valid"] is True
        assert data["errors"] == []
        assert "Minor formatting issue" in data["warnings"]
        assert "Consider adding more detail" in data["suggestions"]
    
    @patch('app.api.v1.endpoints.slides.slide_service')
    @patch('app.core.dependencies.get_current_user')
    @patch('app.services.auth.authorization.decorators.require_permission')
    def test_job_status_endpoint(
        self, mock_permission, mock_get_user, mock_service, client, mock_user, mock_slide_service
    ):
        """Test job status endpoint."""
        # Setup mocks
        mock_get_user.return_value = mock_user
        mock_permission.return_value = lambda f: f
        mock_service.return_value = mock_slide_service
        
        job_id = "test_job_123"
        response = client.get(f"/api/v1/slides/job/{job_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["job_id"] == job_id
        assert data["status"] == "completed"
        assert data["progress"] == 100.0
    
    @patch('app.api.v1.endpoints.slides.slide_service')
    @patch('app.core.dependencies.get_current_user')
    @patch('app.services.auth.authorization.decorators.require_permission')
    def test_cancel_job_endpoint(
        self, mock_permission, mock_get_user, mock_service, client, mock_user, mock_slide_service
    ):
        """Test job cancellation endpoint."""
        # Setup mocks
        mock_get_user.return_value = mock_user
        mock_permission.return_value = lambda f: f
        mock_service.return_value = mock_slide_service
        
        job_id = "test_job_123"
        response = client.delete(f"/api/v1/slides/job/{job_id}")
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["message"] == "Job cancelled successfully"
    
    def test_get_supported_formats_endpoint(self, client):
        """Test getting supported formats."""
        response = client.get("/api/v1/slides/formats")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) > 0
        
        # Check format structure
        format_info = data[0]
        assert "format" in format_info
        assert "name" in format_info
        assert "description" in format_info
        assert "file_extension" in format_info
        assert "supports_animations" in format_info
        assert "supports_speaker_notes" in format_info
    
    def test_get_available_styles_endpoint(self, client):
        """Test getting available styles."""
        response = client.get("/api/v1/slides/styles")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, list)
        assert len(data) > 0
        
        # Check style structure
        style_info = data[0]
        assert "style" in style_info
        assert "name" in style_info
        assert "description" in style_info
    
    def test_get_presets_endpoint(self, client):
        """Test getting configuration presets."""
        response = client.get("/api/v1/slides/presets")
        
        assert response.status_code == 200
        data = response.json()
        
        assert isinstance(data, dict)
        assert "quick_draft" in data
        assert "academic_presentation" in data
        assert "business_pitch" in data
        
        # Check preset structure
        preset = data["quick_draft"]
        assert "name" in preset
        assert "description" in preset
        assert "config" in preset
    
    @patch('app.api.v1.endpoints.slides.slide_service')
    @patch('app.core.dependencies.get_current_user')
    @patch('app.services.auth.authorization.decorators.require_permission')
    def test_advanced_generation_with_file_upload(
        self, mock_permission, mock_get_user, mock_service, client, mock_user, mock_slide_service
    ):
        """Test advanced generation with file upload."""
        # Setup mocks
        mock_get_user.return_value = mock_user
        mock_permission.return_value = lambda f: f
        mock_service.return_value = mock_slide_service
        
        # Create test file
        test_content = "This is test content from uploaded file"
        files = {
            "content": ("test.txt", io.BytesIO(test_content.encode()), "text/plain")
        }
        
        form_data = {
            "layout_style": "modern",
            "quality_level": "standard",
            "max_slides": 5,
            "enable_animations": True
        }
        
        response = client.post(
            "/api/v1/slides/generate-advanced",
            files=files,
            data=form_data
        )
        
        assert response.status_code == 200
        data = response.json()
        
        assert "job_id" in data
        assert data["status"] == "processing"
    
    @patch('app.api.v1.endpoints.slides.slide_service')
    def test_unsupported_file_type(self, mock_service, client):
        """Test upload with unsupported file type."""
        # Create unsupported file
        files = {
            "content": ("test.exe", io.BytesIO(b"binary content"), "application/exe")
        }
        
        response = client.post(
            "/api/v1/slides/generate-advanced",
            files=files,
            data={"max_slides": 5}
        )
        
        assert response.status_code == 400
        assert "Unsupported file type" in response.json()["detail"]
    
    @patch('app.api.v1.endpoints.slides.slide_service')
    @patch('app.core.dependencies.get_current_user')
    @patch('app.services.auth.authorization.decorators.require_permission')
    def test_validation_error_response(
        self, mock_permission, mock_get_user, mock_service, client, mock_user, mock_slide_service
    ):
        """Test API response to validation errors."""
        # Setup mocks
        mock_get_user.return_value = mock_user
        mock_permission.return_value = lambda f: f
        mock_service.return_value = mock_slide_service
        
        # Mock validation failure
        mock_slide_service.validate_content = AsyncMock(return_value=Mock(
            is_valid=False,
            errors=["Content is too short", "Missing required elements"],
            warnings=None,
            suggestions=["Add more content", "Include proper structure"]
        ))
        
        request_data = {"content": "Bad"}
        response = client.post("/api/v1/slides/validate", json=request_data)
        
        assert response.status_code == 200
        data = response.json()
        
        assert data["is_valid"] is False
        assert len(data["errors"]) == 2
        assert "Content is too short" in data["errors"]
        assert len(data["suggestions"]) == 2
    
    @patch('app.api.v1.endpoints.slides.slide_service')
    @patch('app.core.dependencies.get_current_user')
    @patch('app.services.auth.authorization.decorators.require_permission')
    def test_service_error_handling(
        self, mock_permission, mock_get_user, mock_service, client, mock_user, mock_slide_service
    ):
        """Test API error handling when service fails."""
        # Setup mocks
        mock_get_user.return_value = mock_user
        mock_permission.return_value = lambda f: f
        mock_service.return_value = mock_slide_service
        
        # Mock service failure
        mock_slide_service.preview_presentation = AsyncMock(
            side_effect=Exception("Service unavailable")
        )
        
        request_data = {"content": "Test content", "max_slides": 3}
        response = client.post("/api/v1/slides/preview", json=request_data)
        
        assert response.status_code == 500
        assert "Preview generation failed" in response.json()["detail"]
    
    def test_missing_authentication(self, client):
        """Test endpoints without authentication."""
        # These endpoints should require authentication
        protected_endpoints = [
            ("/api/v1/slides/generate", "POST", {"content": "test"}),
            ("/api/v1/slides/preview", "POST", {"content": "test"}),
            ("/api/v1/slides/validate", "POST", {"content": "test"}),
            ("/api/v1/slides/job/test123", "GET", None),
        ]
        
        for endpoint, method, data in protected_endpoints:
            if method == "POST":
                response = client.post(endpoint, json=data)
            else:
                response = client.get(endpoint)
            
            # Should require authentication
            assert response.status_code in [401, 403]
    
    @patch('app.api.v1.endpoints.slides.generation_limiter')
    @patch('app.core.dependencies.get_current_user')
    @patch('app.services.auth.authorization.decorators.require_permission')
    def test_rate_limiting(
        self, mock_permission, mock_get_user, mock_rate_limiter, client, mock_user
    ):
        """Test rate limiting for generation endpoints."""
        # Setup mocks
        mock_get_user.return_value = mock_user
        mock_permission.return_value = lambda f: f
        mock_rate_limiter.check_limit.return_value = False  # Rate limit exceeded
        
        request_data = {"content": "Test content"}
        response = client.post("/api/v1/slides/generate", json=request_data)
        
        assert response.status_code == 429
        assert "rate limit exceeded" in response.json()["detail"].lower()


class TestAPIDataValidation:
    """Test API request/response data validation."""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_generation_request_validation(self, client):
        """Test validation of generation request data."""
        # Missing required field
        response = client.post("/api/v1/slides/generate", json={})
        assert response.status_code == 422
        
        # Invalid output format
        response = client.post("/api/v1/slides/generate", json={
            "content": "test",
            "output_format": "invalid_format"
        })
        assert response.status_code == 422
        
        # Valid request
        response = client.post("/api/v1/slides/generate", json={
            "content": "Valid test content",
            "output_format": "pptx",
            "title": "Test Title"
        })
        # This will fail due to auth, but validation should pass
        assert response.status_code in [401, 403]  # Auth error, not validation
    
    def test_preview_request_validation(self, client):
        """Test validation of preview request data."""
        # Invalid max_slides
        response = client.post("/api/v1/slides/preview", json={
            "content": "test",
            "max_slides": 0  # Should be >= 1
        })
        assert response.status_code == 422
        
        response = client.post("/api/v1/slides/preview", json={
            "content": "test",
            "max_slides": 15  # Should be <= 10
        })
        assert response.status_code == 422
    
    def test_advanced_options_validation(self, client):
        """Test validation of advanced generation options."""
        test_file = ("test.txt", io.BytesIO(b"test content"), "text/plain")
        
        # Invalid max_slides
        response = client.post(
            "/api/v1/slides/generate-advanced",
            files={"content": test_file},
            data={"max_slides": 150}  # Should be <= 100
        )
        assert response.status_code == 422


class TestAPIResponseFormats:
    """Test API response formats and structures."""
    
    @pytest.fixture
    def client(self):
        return TestClient(app)
    
    def test_formats_response_structure(self, client):
        """Test structure of formats endpoint response."""
        response = client.get("/api/v1/slides/formats")
        data = response.json()
        
        for format_info in data:
            # Required fields
            assert "format" in format_info
            assert "name" in format_info
            assert "description" in format_info
            assert "file_extension" in format_info
            assert "supports_animations" in format_info
            assert "supports_speaker_notes" in format_info
            
            # Data types
            assert isinstance(format_info["format"], str)
            assert isinstance(format_info["name"], str)
            assert isinstance(format_info["description"], str)
            assert isinstance(format_info["file_extension"], str)
            assert isinstance(format_info["supports_animations"], bool)
            assert isinstance(format_info["supports_speaker_notes"], bool)
    
    def test_styles_response_structure(self, client):
        """Test structure of styles endpoint response."""
        response = client.get("/api/v1/slides/styles")
        data = response.json()
        
        for style_info in data:
            assert "style" in style_info
            assert "name" in style_info
            assert "description" in style_info
            # preview_url is optional
            
            assert isinstance(style_info["style"], str)
            assert isinstance(style_info["name"], str)
            assert isinstance(style_info["description"], str)
    
    def test_presets_response_structure(self, client):
        """Test structure of presets endpoint response."""
        response = client.get("/api/v1/slides/presets")
        data = response.json()
        
        assert isinstance(data, dict)
        
        for preset_name, preset_info in data.items():
            assert isinstance(preset_name, str)
            assert "name" in preset_info
            assert "description" in preset_info
            assert "config" in preset_info
            
            # Config should be a dictionary
            assert isinstance(preset_info["config"], dict)
            assert "generator" in preset_info["config"]
            assert "layout" in preset_info["config"]
            assert "quality" in preset_info["config"]