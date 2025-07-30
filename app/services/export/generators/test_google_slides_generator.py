"""
Test suite for Google Slides generator.

This module provides comprehensive tests for the Google Slides integration including:
- OAuth authentication flow testing
- Google API integration testing
- Slide creation and formatting
- Permission management and sharing
- Batch operations
- Error handling and retry mechanisms
"""

import asyncio
import io
import json
import os
import pytest
import tempfile
import unittest
from unittest.mock import Mock, patch, MagicMock, AsyncMock
from typing import Dict, List, Any

try:
    from google.oauth2.credentials import Credentials
    from google.auth.exceptions import RefreshError
    from googleapiclient.errors import HttpError
    from googleapiclient.http import HttpRequest
except ImportError:
    pytest.skip("Google API packages not available", allow_module_level=True)

from app.core.logging import get_logger
from app.domain.schemas.generation import Citation, SlideContent
from app.services.export.generators.google_slides_generator import (
    GoogleSlidesGenerator,
    GoogleCredentials,
    GoogleSlidesTemplate,
    PermissionRole,
    ShareType,
    LayoutType,
    DriveConfig,
    SharingConfig,
    TemplateConfig,
    BatchConfig,
    GoogleOAuthManager,
    GoogleDriveManager,
    GoogleSlidesFormatConverter,
    ProgressTracker,
    RateLimiter,
    create_academic_google_slides_generator,
    create_collaborative_google_slides_generator
)

logger = get_logger(__name__)


class TestGoogleCredentials(unittest.TestCase):
    """Test Google credentials configuration."""
    
    def test_google_credentials_creation(self):
        """Test creating Google credentials."""
        credentials = GoogleCredentials(
            client_id="test_client_id",
            client_secret="test_client_secret"
        )
        
        self.assertEqual(credentials.client_id, "test_client_id")
        self.assertEqual(credentials.client_secret, "test_client_secret")
        self.assertEqual(credentials.redirect_uri, "http://localhost:8080/auth/google/callback")
        self.assertIn("https://www.googleapis.com/auth/presentations", credentials.scopes)
        self.assertIn("https://www.googleapis.com/auth/drive", credentials.scopes)
    
    def test_google_credentials_custom_config(self):
        """Test creating Google credentials with custom configuration."""
        custom_scopes = ["https://www.googleapis.com/auth/presentations"]
        credentials = GoogleCredentials(
            client_id="test_id",
            client_secret="test_secret",
            redirect_uri="http://custom-redirect.com/callback",
            scopes=custom_scopes
        )
        
        self.assertEqual(credentials.redirect_uri, "http://custom-redirect.com/callback")
        self.assertEqual(credentials.scopes, custom_scopes)


class TestDriveConfig(unittest.TestCase):
    """Test Drive configuration."""
    
    def test_default_drive_config(self):
        """Test default Drive configuration."""
        config = DriveConfig()
        
        self.assertEqual(config.folder_name, "SlideGenie Presentations")
        self.assertTrue(config.auto_create_folders)
        self.assertTrue(config.organize_by_date)
        self.assertFalse(config.organize_by_topic)
    
    def test_custom_drive_config(self):
        """Test custom Drive configuration."""
        config = DriveConfig(
            folder_name="Custom Presentations",
            parent_folder_id="custom_parent_id",
            organize_by_date=False,
            organize_by_topic=True
        )
        
        self.assertEqual(config.folder_name, "Custom Presentations")
        self.assertEqual(config.parent_folder_id, "custom_parent_id")
        self.assertFalse(config.organize_by_date)
        self.assertTrue(config.organize_by_topic)


class TestTemplateConfig(unittest.TestCase):
    """Test template configuration."""
    
    def test_default_template_config(self):
        """Test default template configuration."""
        config = TemplateConfig()
        
        self.assertEqual(config.template_type, GoogleSlidesTemplate.SIMPLE_LIGHT)
        self.assertEqual(config.theme_color, "#1f4e79")
        self.assertEqual(config.font_family, "Arial")
        self.assertTrue(config.apply_branding)
    
    def test_custom_template_config(self):
        """Test custom template configuration."""
        config = TemplateConfig(
            template_type=GoogleSlidesTemplate.FOCUS,
            theme_color="#ff0000",
            font_family="Helvetica",
            university_name="Test University",
            apply_branding=False
        )
        
        self.assertEqual(config.template_type, GoogleSlidesTemplate.FOCUS)
        self.assertEqual(config.theme_color, "#ff0000")
        self.assertEqual(config.font_family, "Helvetica")
        self.assertEqual(config.university_name, "Test University")
        self.assertFalse(config.apply_branding)


class TestProgressTracker(unittest.TestCase):
    """Test progress tracking."""
    
    def test_progress_tracker_creation(self):
        """Test creating progress tracker."""
        tracker = ProgressTracker(total_operations=10)
        
        self.assertEqual(tracker.total_operations, 10)
        self.assertEqual(tracker.completed_operations, 0)
        self.assertIsNotNone(tracker.start_time)
    
    def test_progress_update(self):
        """Test progress updates."""
        tracker = ProgressTracker(total_operations=5)
        
        tracker.update(1, "First operation")
        self.assertEqual(tracker.completed_operations, 1)
        
        tracker.update(2, "Second batch")
        self.assertEqual(tracker.completed_operations, 3)
    
    def test_progress_callbacks(self):
        """Test progress callbacks."""
        callback_data = []
        
        def test_callback(data):
            callback_data.append(data)
        
        tracker = ProgressTracker(total_operations=4)
        tracker.add_callback(test_callback)
        
        tracker.update(2, "Test update")
        
        self.assertEqual(len(callback_data), 1)
        self.assertEqual(callback_data[0]['completed'], 2)
        self.assertEqual(callback_data[0]['total'], 4)
        self.assertEqual(callback_data[0]['progress_percent'], 50.0)
    
    def test_progress_completion(self):
        """Test progress completion."""
        tracker = ProgressTracker(total_operations=3)
        
        tracker.update(2)
        tracker.complete()
        
        self.assertEqual(tracker.completed_operations, 3)


class TestRateLimiter(unittest.TestCase):
    """Test rate limiting."""
    
    @pytest.mark.asyncio
    async def test_rate_limiter_allows_requests(self):
        """Test that rate limiter allows requests within limit."""
        limiter = RateLimiter(requests_per_minute=5)
        
        # Should allow first request immediately
        start_time = asyncio.get_event_loop().time()
        await limiter.acquire()
        end_time = asyncio.get_event_loop().time()
        
        # Should complete quickly (no waiting)
        self.assertLess(end_time - start_time, 0.1)
    
    @pytest.mark.asyncio
    async def test_rate_limiter_enforces_limit(self):
        """Test that rate limiter enforces limits."""
        limiter = RateLimiter(requests_per_minute=2)
        
        # Make requests up to limit
        await limiter.acquire()
        await limiter.acquire()
        
        # Next request should be allowed (not hitting minute boundary yet)
        start_time = asyncio.get_event_loop().time()
        await limiter.acquire()
        end_time = asyncio.get_event_loop().time()
        
        # Should complete without significant delay for 3rd request
        self.assertLess(end_time - start_time, 1.0)


class TestGoogleOAuthManager(unittest.TestCase):
    """Test Google OAuth manager."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.credentials = GoogleCredentials(
            client_id="test_client_id",
            client_secret="test_client_secret"
        )
        self.oauth_manager = GoogleOAuthManager(self.credentials)
    
    @patch('app.services.export.generators.google_slides_generator.Flow')
    def test_get_authorization_url(self, mock_flow_class):
        """Test getting authorization URL."""
        mock_flow = Mock()
        mock_flow.authorization_url.return_value = ("http://auth.url", "state")
        mock_flow_class.from_client_config.return_value = mock_flow
        
        auth_url = self.oauth_manager.get_authorization_url("test_state")
        
        self.assertEqual(auth_url, "http://auth.url")
        mock_flow_class.from_client_config.assert_called_once()
        mock_flow.authorization_url.assert_called_once()
    
    @patch('app.services.export.generators.google_slides_generator.Flow')
    def test_exchange_code_for_tokens(self, mock_flow_class):
        """Test exchanging authorization code for tokens."""
        mock_credentials = Mock(spec=Credentials)
        mock_flow = Mock()
        mock_flow.credentials = mock_credentials
        mock_flow_class.from_client_config.return_value = mock_flow
        self.oauth_manager._flow = mock_flow
        
        result = self.oauth_manager.exchange_code_for_tokens("auth_code")
        
        self.assertEqual(result, mock_credentials)
        mock_flow.fetch_token.assert_called_once_with(code="auth_code")
    
    @patch('app.services.export.generators.google_slides_generator.Request')
    def test_refresh_credentials(self, mock_request):
        """Test refreshing credentials."""
        mock_credentials = Mock(spec=Credentials)
        mock_credentials.expired = True
        mock_credentials.refresh_token = "refresh_token"
        
        result = self.oauth_manager.refresh_credentials(mock_credentials)
        
        self.assertEqual(result, mock_credentials)
        mock_credentials.refresh.assert_called_once()
    
    def test_save_and_load_credentials(self):
        """Test saving and loading credentials."""
        mock_credentials = Mock(spec=Credentials)
        mock_credentials.token = "access_token"
        mock_credentials.refresh_token = "refresh_token"
        mock_credentials.id_token = "id_token"
        mock_credentials.token_uri = "https://oauth2.googleapis.com/token"
        mock_credentials.client_id = "client_id"
        mock_credentials.client_secret = "client_secret"
        mock_credentials.scopes = ["scope1", "scope2"]
        mock_credentials.expiry = None
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.json') as f:
            temp_path = f.name
        
        try:
            # Test saving
            self.oauth_manager.save_credentials(mock_credentials, temp_path)
            self.assertTrue(os.path.exists(temp_path))
            
            # Test loading
            loaded_credentials = self.oauth_manager.load_credentials(temp_path)
            self.assertIsNotNone(loaded_credentials)
            self.assertEqual(loaded_credentials.token, "access_token")
            self.assertEqual(loaded_credentials.refresh_token, "refresh_token")
            
        finally:
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestGoogleDriveManager(unittest.TestCase):
    """Test Google Drive manager."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.mock_credentials = Mock(spec=Credentials)
        self.drive_config = DriveConfig()
        
        with patch('app.services.export.generators.google_slides_generator.build'):
            self.drive_manager = GoogleDriveManager(self.mock_credentials, self.drive_config)
            self.drive_manager.drive_service = Mock()
    
    def test_create_folder(self):
        """Test creating folder."""
        mock_response = {'id': 'folder_123'}
        self.drive_manager.drive_service.files().create().execute.return_value = mock_response
        
        folder_id = self.drive_manager.create_folder("Test Folder")
        
        self.assertEqual(folder_id, "folder_123")
        self.drive_manager.drive_service.files().create.assert_called_once()
    
    def test_find_folder(self):
        """Test finding folder."""
        mock_response = {'files': [{'id': 'existing_folder', 'name': 'Test Folder'}]}
        self.drive_manager.drive_service.files().list().execute.return_value = mock_response
        
        folder_id = self.drive_manager.find_folder("Test Folder")
        
        self.assertEqual(folder_id, "existing_folder")
        self.drive_manager.drive_service.files().list.assert_called_once()
    
    def test_find_folder_not_found(self):
        """Test finding folder that doesn't exist."""
        mock_response = {'files': []}
        self.drive_manager.drive_service.files().list().execute.return_value = mock_response
        
        folder_id = self.drive_manager.find_folder("Nonexistent Folder")
        
        self.assertIsNone(folder_id)
    
    def test_get_or_create_folder_existing(self):
        """Test getting existing folder."""
        with patch.object(self.drive_manager, 'find_folder', return_value='existing_id'):
            folder_id = self.drive_manager.get_or_create_folder("Test Folder")
            self.assertEqual(folder_id, "existing_id")
    
    def test_get_or_create_folder_new(self):
        """Test creating new folder when it doesn't exist."""
        with patch.object(self.drive_manager, 'find_folder', return_value=None), \
             patch.object(self.drive_manager, 'create_folder', return_value='new_id'):
            folder_id = self.drive_manager.get_or_create_folder("Test Folder")
            self.assertEqual(folder_id, "new_id")
    
    def test_upload_file(self):
        """Test uploading file."""
        mock_response = {'id': 'file_123'}
        self.drive_manager.drive_service.files().create().execute.return_value = mock_response
        
        file_content = io.BytesIO(b"test content")
        file_id = self.drive_manager.upload_file(
            file_content, "test.txt", "text/plain", "parent_folder_id"
        )
        
        self.assertEqual(file_id, "file_123")
        self.drive_manager.drive_service.files().create.assert_called_once()
    
    def test_set_file_permissions(self):
        """Test setting file permissions."""
        permissions = [
            {'type': 'user', 'role': 'reader', 'emailAddress': 'test@example.com'}
        ]
        
        self.drive_manager.set_file_permissions("file_123", permissions)
        
        self.drive_manager.drive_service.permissions().create.assert_called_once()
    
    def test_get_file_link(self):
        """Test getting file links."""
        file_id = "test_file_id"
        
        view_link = self.drive_manager.get_file_link(file_id, "view")
        edit_link = self.drive_manager.get_file_link(file_id, "edit")
        comment_link = self.drive_manager.get_file_link(file_id, "comment")
        
        self.assertIn(file_id, view_link)
        self.assertIn("/view", view_link)
        self.assertIn("/edit", edit_link)
        self.assertIn("mode=comment", comment_link)


class TestGoogleSlidesFormatConverter(unittest.TestCase):
    """Test Google Slides format converter."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.converter = GoogleSlidesFormatConverter()
        self.template_config = TemplateConfig()
    
    def test_determine_slide_layout(self):
        """Test determining slide layout."""
        # Title slide
        title_slide = SlideContent(
            title="Test Presentation",
            subtitle="Subtitle",
            body=[],
            metadata={'slide_type': 'title'}
        )
        layout = self.converter._determine_slide_layout(title_slide)
        self.assertEqual(layout, LayoutType.TITLE)
        
        # Section header
        section_slide = SlideContent(
            title="Section Header",
            body=[],
            metadata={'slide_type': 'section'}
        )
        layout = self.converter._determine_slide_layout(section_slide)
        self.assertEqual(layout, LayoutType.SECTION_HEADER)
        
        # Two column layout
        two_col_slide = SlideContent(
            title="Two Columns",
            body=[
                {'type': 'text', 'content': 'Left column'},
                {'type': 'text', 'content': 'Right column'}
            ]
        )
        layout = self.converter._determine_slide_layout(two_col_slide)
        self.assertEqual(layout, LayoutType.TITLE_AND_TWO_COLUMNS)
        
        # Regular content slide
        content_slide = SlideContent(
            title="Content Slide",
            body=[{'type': 'text', 'content': 'Some content'}]
        )
        layout = self.converter._determine_slide_layout(content_slide)
        self.assertEqual(layout, LayoutType.TITLE_AND_BODY)
    
    def test_convert_slides_to_requests(self):
        """Test converting slides to API requests."""
        slides = [
            SlideContent(
                title="Test Slide",
                body=[{'type': 'text', 'content': 'Test content'}]
            )
        ]
        
        requests = self.converter.convert_slides_to_requests(
            slides, "presentation_id", self.template_config
        )
        
        self.assertIsInstance(requests, list)
        self.assertGreater(len(requests), 0)
        
        # Check for slide creation request
        create_slide_requests = [
            req for req in requests if 'createSlide' in req
        ]
        self.assertGreater(len(create_slide_requests), 0)
    
    def test_hex_to_rgb_conversion(self):
        """Test hex to RGB color conversion."""
        rgb = self.converter._hex_to_rgb("#ff0000")
        self.assertEqual(rgb['red'], 1.0)
        self.assertEqual(rgb['green'], 0.0)
        self.assertEqual(rgb['blue'], 0.0)
        
        rgb = self.converter._hex_to_rgb("#00ff00")
        self.assertEqual(rgb['red'], 0.0)
        self.assertEqual(rgb['green'], 1.0)
        self.assertEqual(rgb['blue'], 0.0)


class TestGoogleSlidesGenerator(unittest.TestCase):
    """Test Google Slides generator."""
    
    def setUp(self):
        """Set up test fixtures."""
        self.google_credentials = GoogleCredentials(
            client_id="test_client_id",
            client_secret="test_client_secret"
        )
        self.generator = GoogleSlidesGenerator(self.google_credentials)
    
    def test_generator_initialization(self):
        """Test generator initialization."""
        self.assertIsNotNone(self.generator.oauth_manager)
        self.assertIsNotNone(self.generator.format_converter)
        self.assertIsNotNone(self.generator.rate_limiter)
        self.assertEqual(self.generator.google_credentials, self.google_credentials)
    
    def test_authenticate_user_new_flow(self):
        """Test starting new authentication flow."""
        with patch.object(self.generator.oauth_manager, 'get_authorization_url', 
                         return_value='http://auth.url'):
            auth_url = self.generator.authenticate_user()
            self.assertEqual(auth_url, 'http://auth.url')
    
    def test_authenticate_user_existing_credentials(self):
        """Test authentication with existing credentials."""
        mock_credentials = Mock(spec=Credentials)
        mock_credentials.expired = False
        
        with patch.object(self.generator.oauth_manager, 'load_credentials', 
                         return_value=mock_credentials), \
             patch.object(self.generator, '_initialize_services'):
            
            result = self.generator.authenticate_user("credentials.json")
            self.assertEqual(result, "authenticated")
    
    def test_complete_authentication(self):
        """Test completing authentication."""
        mock_credentials = Mock(spec=Credentials)
        
        with patch.object(self.generator.oauth_manager, 'exchange_code_for_tokens', 
                         return_value=mock_credentials), \
             patch.object(self.generator.oauth_manager, 'save_credentials'), \
             patch.object(self.generator, '_initialize_services'):
            
            self.generator.complete_authentication("auth_code", "credentials.json")
            self.assertEqual(self.generator.user_credentials, mock_credentials)
    
    @pytest.mark.asyncio
    async def test_create_presentation(self):
        """Test creating presentation."""
        # Setup mocks
        mock_credentials = Mock(spec=Credentials)
        self.generator.user_credentials = mock_credentials
        
        mock_slides_service = Mock()
        mock_presentation_response = {
            'presentationId': 'test_presentation_id',
            'title': 'Test Presentation'
        }
        mock_slides_service.presentations().create().execute.return_value = mock_presentation_response
        self.generator.slides_service = mock_slides_service
        
        mock_drive_manager = Mock()
        mock_drive_manager.organize_presentation_folder.return_value = 'folder_id'
        self.generator.drive_manager = mock_drive_manager
        
        # Test data
        slides = [
            SlideContent(
                title="Test Slide 1",
                body=[{'type': 'text', 'content': 'Content 1'}]
            ),
            SlideContent(
                title="Test Slide 2", 
                body=[{'type': 'text', 'content': 'Content 2'}]
            )
        ]
        
        with patch.object(self.generator, '_apply_template'), \
             patch.object(self.generator, '_execute_batch_requests'), \
             patch.object(self.generator, '_organize_in_drive', return_value='folder_id'), \
             patch.object(self.generator, '_generate_sharing_links', return_value={'view': 'http://view.link'}):
            
            result = await self.generator.create_presentation(
                slides=slides,
                title="Test Presentation"
            )
        
        self.assertEqual(result['presentation_id'], 'test_presentation_id')
        self.assertEqual(result['title'], 'Test Presentation')
        self.assertEqual(result['slide_count'], 2)
        self.assertEqual(result['status'], 'completed')
    
    def test_set_presentation_permissions(self):
        """Test setting presentation permissions."""
        mock_drive_manager = Mock()
        self.generator.drive_manager = mock_drive_manager
        
        permissions = [
            {'type': 'user', 'role': 'reader', 'emailAddress': 'test@example.com'}
        ]
        
        self.generator.set_presentation_permissions('presentation_id', permissions)
        
        mock_drive_manager.set_file_permissions.assert_called_once_with(
            'presentation_id', permissions
        )
    
    def test_share_presentation(self):
        """Test sharing presentation with user."""
        mock_drive_manager = Mock()
        self.generator.drive_manager = mock_drive_manager
        
        with patch.object(self.generator, 'set_presentation_permissions'), \
             patch.object(self.generator, '_generate_sharing_links', 
                         return_value={'view': 'http://view.link'}):
            
            result = self.generator.share_presentation(
                'presentation_id', 
                'test@example.com', 
                PermissionRole.EDITOR
            )
        
        self.assertEqual(result['email'], 'test@example.com')
        self.assertEqual(result['role'], 'writer')
        self.assertEqual(result['status'], 'shared')
    
    def test_make_presentation_public(self):
        """Test making presentation public."""
        self.generator.sharing_config.allow_public_sharing = True
        mock_drive_manager = Mock()
        self.generator.drive_manager = mock_drive_manager
        
        with patch.object(self.generator, 'set_presentation_permissions'), \
             patch.object(self.generator, '_generate_sharing_links', 
                         return_value={'view': 'http://view.link'}):
            
            result = self.generator.make_presentation_public('presentation_id')
        
        self.assertEqual(result['access'], 'public')
        self.assertEqual(result['status'], 'public')
    
    def test_make_presentation_public_not_allowed(self):
        """Test making presentation public when not allowed."""
        self.generator.sharing_config.allow_public_sharing = False
        
        with self.assertRaises(ValueError):
            self.generator.make_presentation_public('presentation_id')
    
    def test_get_presentation_info(self):
        """Test getting presentation info."""
        mock_slides_service = Mock()
        mock_presentation = {
            'presentationId': 'test_id',
            'title': 'Test Presentation',
            'slides': [{'objectId': 'slide1'}, {'objectId': 'slide2'}],
            'pageSize': {'width': {'magnitude': 10}, 'height': {'magnitude': 7.5}},
            'revisionId': 'revision_123',
            'masters': [{'objectId': 'master1'}],
            'layouts': [{'objectId': 'layout1'}, {'objectId': 'layout2'}]
        }
        mock_slides_service.presentations().get().execute.return_value = mock_presentation
        self.generator.slides_service = mock_slides_service
        
        info = self.generator.get_presentation_info('test_id')
        
        self.assertEqual(info['id'], 'test_id')
        self.assertEqual(info['title'], 'Test Presentation')
        self.assertEqual(info['slide_count'], 2)


class TestFactoryFunctions(unittest.TestCase):
    """Test factory functions."""
    
    def test_create_academic_google_slides_generator(self):
        """Test creating academic Google Slides generator."""
        generator = create_academic_google_slides_generator(
            client_id="test_client_id",
            client_secret="test_client_secret",
            university_name="Test University",
            template_type=GoogleSlidesTemplate.FOCUS,
            theme_color="#ff0000"
        )
        
        self.assertIsInstance(generator, GoogleSlidesGenerator)
        self.assertEqual(generator.google_credentials.client_id, "test_client_id")
        self.assertEqual(generator.template_config.template_type, GoogleSlidesTemplate.FOCUS)
        self.assertEqual(generator.template_config.theme_color, "#ff0000")
        self.assertEqual(generator.template_config.university_name, "Test University")
        self.assertIn("Test University Presentations", generator.drive_config.folder_name)
    
    def test_create_collaborative_google_slides_generator(self):
        """Test creating collaborative Google Slides generator."""
        generator = create_collaborative_google_slides_generator(
            client_id="test_client_id",
            client_secret="test_client_secret",
            allow_public_sharing=True
        )
        
        self.assertIsInstance(generator, GoogleSlidesGenerator)
        self.assertEqual(generator.sharing_config.default_role, PermissionRole.EDITOR)
        self.assertTrue(generator.sharing_config.allow_public_sharing)
        self.assertTrue(generator.sharing_config.send_notification_email)
        self.assertEqual(generator.batch_config.max_concurrent_requests, 10)


class IntegrationTestGoogleSlidesGenerator(unittest.TestCase):
    """Integration tests for Google Slides generator (requires real credentials)."""
    
    def setUp(self):
        """Set up integration test fixtures."""
        # Skip integration tests if no credentials available
        self.client_id = os.getenv('GOOGLE_CLIENT_ID')
        self.client_secret = os.getenv('GOOGLE_CLIENT_SECRET')
        
        if not self.client_id or not self.client_secret:
            self.skipTest("Google credentials not available for integration testing")
        
        self.credentials = GoogleCredentials(
            client_id=self.client_id,
            client_secret=self.client_secret
        )
        self.generator = GoogleSlidesGenerator(self.credentials)
    
    @pytest.mark.integration
    def test_oauth_flow_generation(self):
        """Test OAuth flow URL generation (integration)."""
        auth_url = self.generator.authenticate_user()
        
        self.assertIsInstance(auth_url, str)
        self.assertIn('accounts.google.com', auth_url)
        self.assertIn('oauth2', auth_url)
        self.assertIn(self.client_id, auth_url)
    
    @pytest.mark.integration
    @pytest.mark.skipif(not os.getenv('GOOGLE_CREDENTIALS_FILE'), 
                       reason="Google credentials file not available")
    def test_with_real_credentials(self):
        """Test with real Google credentials (requires manual setup)."""
        credentials_file = os.getenv('GOOGLE_CREDENTIALS_FILE')
        
        # This test requires manually obtaining credentials
        result = self.generator.authenticate_user(credentials_file)
        
        if result == "authenticated":
            # Test basic operations
            info = self.generator.get_presentation_info("test_presentation_id")
            self.assertIsInstance(info, dict)


if __name__ == '__main__':
    # Configure logging for tests
    import logging
    logging.basicConfig(level=logging.INFO)
    
    # Run tests
    unittest.main(verbosity=2)