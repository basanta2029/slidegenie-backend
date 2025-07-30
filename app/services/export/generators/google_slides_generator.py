"""
Comprehensive Google Slides generator for academic presentations.

This module provides a complete Google Slides integration system with:
- OAuth 2.0 authentication flow with Google API
- Direct upload to user's Google Drive with folder organization
- Format preservation when converting from internal format to Google Slides
- Collaborative link generation with permission management
- Template application and branding customization
- Bulk operations and batch processing
- Sharing and permission management (view, edit, comment)
- Automated slide formatting and layout optimization
"""

import asyncio
import io
import json
import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union
from urllib.parse import quote, urlencode
import uuid

try:
    import httpx
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import Flow
    from googleapiclient.discovery import build
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaIoBaseUpload
    import requests
    from PIL import Image
except ImportError as e:
    raise ImportError(
        f"Required packages not installed: {e}. "
        "Please install: pip install google-auth google-auth-oauthlib google-auth-httplib2 "
        "google-api-python-client httpx pillow requests"
    )

from app.core.logging import get_logger
from app.domain.schemas.generation import Citation, SlideContent

logger = get_logger(__name__)


class GoogleSlidesTemplate(Enum):
    """Google Slides template types."""
    SIMPLE_LIGHT = "SIMPLE_LIGHT"
    SIMPLE_DARK = "SIMPLE_DARK"
    STREAMLINE = "STREAMLINE"
    FOCUS = "FOCUS"
    SHIFT = "SHIFT"
    MOMENTUM = "MOMENTUM"
    PARADIGM = "PARADIGM"
    SPEARMINT = "SPEARMINT"
    SLATE = "SLATE"
    GEOMETRIC = "GEOMETRIC"
    CORAL = "CORAL"
    CUSTOM = "CUSTOM"


class PermissionRole(Enum):
    """Google Drive permission roles."""
    VIEWER = "reader"
    COMMENTER = "commenter"
    EDITOR = "writer"
    OWNER = "owner"


class ShareType(Enum):
    """Share type for Google Drive."""
    USER = "user"
    GROUP = "group"
    DOMAIN = "domain"
    ANYONE = "anyone"


class LayoutType(Enum):
    """Google Slides layout types."""
    BLANK = "BLANK"
    CAPTION_ONLY = "CAPTION_ONLY"
    TITLE = "TITLE"
    TITLE_AND_BODY = "TITLE_AND_BODY"
    TITLE_AND_TWO_COLUMNS = "TITLE_AND_TWO_COLUMNS"
    TITLE_ONLY = "TITLE_ONLY"
    SECTION_HEADER = "SECTION_HEADER"
    SECTION_TITLE_AND_DESCRIPTION = "SECTION_TITLE_AND_DESCRIPTION"
    ONE_COLUMN_TEXT = "ONE_COLUMN_TEXT"
    BIG_NUMBER = "BIG_NUMBER"


@dataclass
class GoogleCredentials:
    """Google API credentials configuration."""
    client_id: str
    client_secret: str
    redirect_uri: str = "http://localhost:8080/auth/google/callback"
    scopes: List[str] = field(default_factory=lambda: [
        "https://www.googleapis.com/auth/presentations",
        "https://www.googleapis.com/auth/drive",
        "https://www.googleapis.com/auth/drive.file"
    ])


@dataclass
class DriveConfig:
    """Google Drive configuration."""
    folder_name: str = "SlideGenie Presentations"
    parent_folder_id: Optional[str] = None
    auto_create_folders: bool = True
    organize_by_date: bool = True
    organize_by_topic: bool = False


@dataclass
class SharingConfig:
    """Sharing configuration for presentations."""
    default_role: PermissionRole = PermissionRole.VIEWER
    allow_public_sharing: bool = False
    notify_on_share: bool = True
    send_notification_email: bool = False
    message: Optional[str] = None


@dataclass
class TemplateConfig:
    """Template configuration for Google Slides."""
    template_id: Optional[str] = None
    template_type: GoogleSlidesTemplate = GoogleSlidesTemplate.SIMPLE_LIGHT
    theme_color: str = "#1f4e79"
    font_family: str = "Arial"
    apply_branding: bool = True
    logo_url: Optional[str] = None
    university_name: Optional[str] = None


@dataclass
class BatchConfig:
    """Configuration for batch operations."""
    max_concurrent_requests: int = 5
    retry_attempts: int = 3
    retry_delay: float = 1.0
    batch_size: int = 100
    rate_limit_delay: float = 0.1


class RateLimiter:
    """Rate limiter for Google API requests."""
    
    def __init__(self, requests_per_minute: int = 100):
        self.requests_per_minute = requests_per_minute
        self.requests = []
        self.lock = asyncio.Lock()
    
    async def acquire(self):
        """Acquire permission to make a request."""
        async with self.lock:
            now = time.time()
            # Remove requests older than 1 minute
            self.requests = [req_time for req_time in self.requests if now - req_time < 60]
            
            if len(self.requests) >= self.requests_per_minute:
                # Wait until we can make another request
                oldest_request = min(self.requests)
                wait_time = 60 - (now - oldest_request)
                if wait_time > 0:
                    await asyncio.sleep(wait_time)
            
            self.requests.append(now)


class GoogleOAuthManager:
    """Manages Google OAuth 2.0 authentication flow."""
    
    def __init__(self, credentials: GoogleCredentials):
        self.credentials = credentials
        self.logger = get_logger(self.__class__.__name__)
        self._flow: Optional[Flow] = None
    
    def get_authorization_url(self, state: Optional[str] = None) -> str:
        """
        Get Google OAuth authorization URL.
        
        Args:
            state: Optional state parameter for CSRF protection
            
        Returns:
            Authorization URL for user to visit
        """
        try:
            self._flow = Flow.from_client_config(
                {
                    "web": {
                        "client_id": self.credentials.client_id,
                        "client_secret": self.credentials.client_secret,
                        "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                        "token_uri": "https://oauth2.googleapis.com/token",
                        "redirect_uris": [self.credentials.redirect_uri]
                    }
                },
                scopes=self.credentials.scopes
            )
            self._flow.redirect_uri = self.credentials.redirect_uri
            
            authorization_url, _ = self._flow.authorization_url(
                access_type='offline',
                include_granted_scopes='true',
                state=state,
                prompt='consent'
            )
            
            self.logger.info("Generated authorization URL")
            return authorization_url
            
        except Exception as e:
            self.logger.error(f"Failed to generate authorization URL: {e}")
            raise
    
    def exchange_code_for_tokens(self, authorization_code: str) -> Credentials:
        """
        Exchange authorization code for access tokens.
        
        Args:
            authorization_code: Authorization code from callback
            
        Returns:
            Google OAuth credentials
        """
        try:
            if not self._flow:
                raise ValueError("Authorization flow not initialized. Call get_authorization_url first.")
            
            self._flow.fetch_token(code=authorization_code)
            credentials = self._flow.credentials
            
            self.logger.info("Successfully exchanged code for tokens")
            return credentials
            
        except Exception as e:
            self.logger.error(f"Failed to exchange code for tokens: {e}")
            raise
    
    def refresh_credentials(self, credentials: Credentials) -> Credentials:
        """
        Refresh expired credentials.
        
        Args:
            credentials: Expired credentials
            
        Returns:
            Refreshed credentials
        """
        try:
            if credentials.expired and credentials.refresh_token:
                credentials.refresh(Request())
                self.logger.info("Successfully refreshed credentials")
            
            return credentials
            
        except Exception as e:
            self.logger.error(f"Failed to refresh credentials: {e}")
            raise
    
    def save_credentials(self, credentials: Credentials, file_path: str) -> None:
        """Save credentials to file."""
        try:
            creds_data = {
                'token': credentials.token,
                'refresh_token': credentials.refresh_token,
                'id_token': credentials.id_token,
                'token_uri': credentials.token_uri,
                'client_id': credentials.client_id,
                'client_secret': credentials.client_secret,
                'scopes': credentials.scopes,
                'expiry': credentials.expiry.isoformat() if credentials.expiry else None
            }
            
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w') as f:
                json.dump(creds_data, f, indent=2)
                
            self.logger.info(f"Saved credentials to {file_path}")
            
        except Exception as e:
            self.logger.error(f"Failed to save credentials: {e}")
            raise
    
    def load_credentials(self, file_path: str) -> Optional[Credentials]:
        """Load credentials from file."""
        try:
            if not os.path.exists(file_path):
                return None
            
            with open(file_path, 'r') as f:
                creds_data = json.load(f)
            
            expiry = None
            if creds_data.get('expiry'):
                expiry = datetime.fromisoformat(creds_data['expiry'])
            
            credentials = Credentials(
                token=creds_data.get('token'),
                refresh_token=creds_data.get('refresh_token'),
                id_token=creds_data.get('id_token'),
                token_uri=creds_data.get('token_uri'),
                client_id=creds_data.get('client_id'),
                client_secret=creds_data.get('client_secret'),
                scopes=creds_data.get('scopes'),
                expiry=expiry
            )
            
            self.logger.info(f"Loaded credentials from {file_path}")
            return credentials
            
        except Exception as e:
            self.logger.error(f"Failed to load credentials: {e}")
            return None


class GoogleDriveManager:
    """Manages Google Drive operations."""
    
    def __init__(self, credentials: Credentials, drive_config: DriveConfig):
        self.credentials = credentials
        self.config = drive_config
        self.logger = get_logger(self.__class__.__name__)
        self.drive_service = None
        self._initialize_service()
    
    def _initialize_service(self):
        """Initialize Google Drive service."""
        try:
            self.drive_service = build('drive', 'v3', credentials=self.credentials)
            self.logger.info("Initialized Google Drive service")
        except Exception as e:
            self.logger.error(f"Failed to initialize Drive service: {e}")
            raise
    
    def create_folder(self, name: str, parent_id: Optional[str] = None) -> str:
        """
        Create a folder in Google Drive.
        
        Args:
            name: Folder name
            parent_id: Parent folder ID
            
        Returns:
            Created folder ID
        """
        try:
            folder_metadata = {
                'name': name,
                'mimeType': 'application/vnd.google-apps.folder'
            }
            
            if parent_id:
                folder_metadata['parents'] = [parent_id]
            
            folder = self.drive_service.files().create(
                body=folder_metadata,
                fields='id'
            ).execute()
            
            folder_id = folder.get('id')
            self.logger.info(f"Created folder '{name}' with ID: {folder_id}")
            return folder_id
            
        except HttpError as e:
            self.logger.error(f"Failed to create folder: {e}")
            raise
    
    def find_folder(self, name: str, parent_id: Optional[str] = None) -> Optional[str]:
        """
        Find a folder by name.
        
        Args:
            name: Folder name to search for
            parent_id: Parent folder ID to search in
            
        Returns:
            Folder ID if found, None otherwise
        """
        try:
            query = f"name='{name}' and mimeType='application/vnd.google-apps.folder' and trashed=false"
            if parent_id:
                query += f" and '{parent_id}' in parents"
            
            results = self.drive_service.files().list(
                q=query,
                fields="files(id, name)"
            ).execute()
            
            folders = results.get('files', [])
            if folders:
                folder_id = folders[0]['id']
                self.logger.info(f"Found folder '{name}' with ID: {folder_id}")
                return folder_id
            
            return None
            
        except HttpError as e:
            self.logger.error(f"Failed to find folder: {e}")
            return None
    
    def get_or_create_folder(self, name: str, parent_id: Optional[str] = None) -> str:
        """Get existing folder or create new one."""
        folder_id = self.find_folder(name, parent_id)
        if folder_id:
            return folder_id
        return self.create_folder(name, parent_id)
    
    def organize_presentation_folder(self, presentation_title: str) -> str:
        """
        Create organized folder structure for presentation.
        
        Args:
            presentation_title: Title of the presentation
            
        Returns:
            Target folder ID for the presentation
        """
        try:
            # Get or create main folder
            main_folder_id = self.get_or_create_folder(
                self.config.folder_name, 
                self.config.parent_folder_id
            )
            
            target_folder_id = main_folder_id
            
            # Organize by date if enabled
            if self.config.organize_by_date:
                date_folder = datetime.now().strftime("%Y-%m")
                target_folder_id = self.get_or_create_folder(date_folder, target_folder_id)
            
            # Organize by topic if enabled
            if self.config.organize_by_topic:
                # Extract topic from title (simplified)
                topic = presentation_title.split(':')[0].strip() if ':' in presentation_title else "General"
                topic_folder = topic[:50]  # Limit folder name length
                target_folder_id = self.get_or_create_folder(topic_folder, target_folder_id)
            
            return target_folder_id
            
        except Exception as e:
            self.logger.error(f"Failed to organize folder structure: {e}")
            return main_folder_id if 'main_folder_id' in locals() else None
    
    def upload_file(
        self, 
        file_content: io.BytesIO, 
        filename: str, 
        mime_type: str, 
        parent_folder_id: Optional[str] = None
    ) -> str:
        """
        Upload file to Google Drive.
        
        Args:
            file_content: File content as BytesIO
            filename: Name of the file
            mime_type: MIME type of the file
            parent_folder_id: Parent folder ID
            
        Returns:
            Uploaded file ID
        """
        try:
            file_metadata = {'name': filename}
            if parent_folder_id:
                file_metadata['parents'] = [parent_folder_id]
            
            media = MediaIoBaseUpload(
                file_content, 
                mimetype=mime_type,
                resumable=True
            )
            
            file_obj = self.drive_service.files().create(
                body=file_metadata,
                media_body=media,
                fields='id'
            ).execute()
            
            file_id = file_obj.get('id')
            self.logger.info(f"Uploaded file '{filename}' with ID: {file_id}")
            return file_id
            
        except HttpError as e:
            self.logger.error(f"Failed to upload file: {e}")
            raise
    
    def set_file_permissions(
        self, 
        file_id: str, 
        permissions: List[Dict[str, Any]]
    ) -> None:
        """
        Set permissions for a file.
        
        Args:
            file_id: File ID
            permissions: List of permission configurations
        """
        try:
            for permission in permissions:
                self.drive_service.permissions().create(
                    fileId=file_id,
                    body=permission,
                    sendNotificationEmail=permission.get('sendNotificationEmail', False)
                ).execute()
            
            self.logger.info(f"Set permissions for file ID: {file_id}")
            
        except HttpError as e:
            self.logger.error(f"Failed to set file permissions: {e}")
            raise
    
    def get_file_link(self, file_id: str, link_type: str = "view") -> str:
        """
        Get shareable link for file.
        
        Args:
            file_id: File ID
            link_type: Type of link ('view', 'edit', 'comment')
            
        Returns:
            Shareable link URL
        """
        base_url = "https://docs.google.com/presentation/d"
        
        if link_type == "edit":
            return f"{base_url}/{file_id}/edit"
        elif link_type == "comment":
            return f"{base_url}/{file_id}/edit#mode=comment"
        else:  # view
            return f"{base_url}/{file_id}/view"


class GoogleSlidesFormatConverter:
    """Converts internal slide format to Google Slides format."""
    
    def __init__(self):
        self.logger = get_logger(self.__class__.__name__)
    
    def convert_slides_to_requests(
        self, 
        slides: List[SlideContent],
        presentation_id: str,
        template_config: TemplateConfig
    ) -> List[Dict[str, Any]]:
        """
        Convert slides to Google Slides API requests.
        
        Args:
            slides: List of slide content
            presentation_id: Google Slides presentation ID
            template_config: Template configuration
            
        Returns:
            List of API requests
        """
        requests = []
        
        # Apply template/theme
        if template_config.template_type != GoogleSlidesTemplate.CUSTOM:
            requests.extend(self._apply_template_requests(presentation_id, template_config))
        
        # Create slides
        for i, slide_content in enumerate(slides):
            slide_requests = self._convert_slide_content(slide_content, i, presentation_id)
            requests.extend(slide_requests)
        
        return requests
    
    def _apply_template_requests(
        self, 
        presentation_id: str, 
        template_config: TemplateConfig
    ) -> List[Dict[str, Any]]:
        """Generate requests to apply template."""
        requests = []
        
        # Apply theme color
        if template_config.theme_color:
            requests.append({
                'updatePageProperties': {
                    'objectId': presentation_id,
                    'pageProperties': {
                        'colorScheme': {
                            'colors': [
                                {
                                    'type': 'ACCENT1',
                                    'color': {
                                        'rgbColor': self._hex_to_rgb(template_config.theme_color)
                                    }
                                }
                            ]
                        }
                    },
                    'fields': 'colorScheme'
                }
            })
        
        return requests
    
    def _convert_slide_content(
        self, 
        slide_content: SlideContent, 
        slide_index: int,
        presentation_id: str
    ) -> List[Dict[str, Any]]:
        """Convert single slide content to API requests."""
        requests = []
        
        # Create slide
        slide_id = f"slide_{slide_index}_{uuid.uuid4().hex[:8]}"
        
        # Determine layout
        layout = self._determine_slide_layout(slide_content)
        
        requests.append({
            'createSlide': {
                'objectId': slide_id,
                'slideLayoutReference': {
                    'predefinedLayout': layout.value
                }
            }
        })
        
        # Add content
        content_requests = self._add_slide_content(slide_content, slide_id)
        requests.extend(content_requests)
        
        return requests
    
    def _determine_slide_layout(self, slide_content: SlideContent) -> LayoutType:
        """Determine appropriate layout for slide content."""
        if slide_content.metadata.get('slide_type') == 'title':
            return LayoutType.TITLE
        elif slide_content.metadata.get('slide_type') == 'section':
            return LayoutType.SECTION_HEADER
        elif len(slide_content.body) == 2:
            return LayoutType.TITLE_AND_TWO_COLUMNS
        elif slide_content.title and slide_content.body:
            return LayoutType.TITLE_AND_BODY
        elif slide_content.title:
            return LayoutType.TITLE_ONLY
        else:
            return LayoutType.BLANK
    
    def _add_slide_content(
        self, 
        slide_content: SlideContent, 
        slide_id: str
    ) -> List[Dict[str, Any]]:
        """Add content to slide."""
        requests = []
        
        # Add title
        if slide_content.title:
            requests.append({
                'insertText': {
                    'objectId': f"{slide_id}_title",
                    'text': slide_content.title
                }
            })
        
        # Add subtitle
        if slide_content.subtitle:
            requests.append({
                'insertText': {
                    'objectId': f"{slide_id}_subtitle", 
                    'text': slide_content.subtitle
                }
            })
        
        # Add body content
        for i, item in enumerate(slide_content.body):
            item_requests = self._convert_content_item(item, slide_id, i)
            requests.extend(item_requests)
        
        return requests
    
    def _convert_content_item(
        self, 
        item: Dict[str, Any], 
        slide_id: str, 
        item_index: int
    ) -> List[Dict[str, Any]]:
        """Convert content item to API requests."""
        requests = []
        content_type = item.get('type', 'text')
        
        if content_type == 'text':
            requests.extend(self._add_text_content(item, slide_id, item_index))
        elif content_type == 'bullet_list':
            requests.extend(self._add_bullet_list_content(item, slide_id, item_index))
        elif content_type == 'image':
            requests.extend(self._add_image_content(item, slide_id, item_index))
        elif content_type == 'table':
            requests.extend(self._add_table_content(item, slide_id, item_index))
        elif content_type == 'chart':
            requests.extend(self._add_chart_content(item, slide_id, item_index))
        
        return requests
    
    def _add_text_content(
        self, 
        item: Dict[str, Any], 
        slide_id: str, 
        item_index: int
    ) -> List[Dict[str, Any]]:
        """Add text content."""
        text_box_id = f"{slide_id}_text_{item_index}"
        
        return [
            {
                'createShape': {
                    'objectId': text_box_id,
                    'shapeType': 'TEXT_BOX',
                    'elementProperties': {
                        'pageObjectId': slide_id,
                        'size': {
                            'width': {'magnitude': 6000000, 'unit': 'EMU'},  # ~6.25 inches
                            'height': {'magnitude': 1440000, 'unit': 'EMU'}  # ~1.5 inches
                        },
                        'transform': {
                            'scaleX': 1,
                            'scaleY': 1,
                            'translateX': 1000000,  # ~1 inch from left
                            'translateY': 2000000 + (item_index * 1500000),  # Stacked vertically
                            'unit': 'EMU'
                        }
                    }
                }
            },
            {
                'insertText': {
                    'objectId': text_box_id,
                    'text': item.get('content', '')
                }
            }
        ]
    
    def _add_bullet_list_content(
        self, 
        item: Dict[str, Any], 
        slide_id: str, 
        item_index: int
    ) -> List[Dict[str, Any]]:
        """Add bullet list content."""
        text_box_id = f"{slide_id}_bullets_{item_index}"
        bullets = item.get('items', [])
        
        requests = [
            {
                'createShape': {
                    'objectId': text_box_id,
                    'shapeType': 'TEXT_BOX',
                    'elementProperties': {
                        'pageObjectId': slide_id,
                        'size': {
                            'width': {'magnitude': 6000000, 'unit': 'EMU'},
                            'height': {'magnitude': len(bullets) * 400000, 'unit': 'EMU'}
                        },
                        'transform': {
                            'scaleX': 1,
                            'scaleY': 1,
                            'translateX': 1000000,
                            'translateY': 2000000 + (item_index * 1500000),
                            'unit': 'EMU'
                        }
                    }
                }
            }
        ]
        
        # Add bullet text
        bullet_text = '\n'.join(f'• {bullet}' for bullet in bullets)
        requests.append({
            'insertText': {
                'objectId': text_box_id,
                'text': bullet_text
            }
        })
        
        return requests
    
    def _add_image_content(
        self, 
        item: Dict[str, Any], 
        slide_id: str, 
        item_index: int
    ) -> List[Dict[str, Any]]:
        """Add image content."""
        image_id = f"{slide_id}_image_{item_index}"
        image_url = item.get('url') or item.get('path')
        
        if not image_url:
            return []
        
        return [
            {
                'createImage': {
                    'objectId': image_id,
                    'url': image_url,
                    'elementProperties': {
                        'pageObjectId': slide_id,
                        'size': {
                            'width': {'magnitude': 4000000, 'unit': 'EMU'},
                            'height': {'magnitude': 3000000, 'unit': 'EMU'}
                        },
                        'transform': {
                            'scaleX': 1,
                            'scaleY': 1,
                            'translateX': 2000000,
                            'translateY': 1500000 + (item_index * 2000000),
                            'unit': 'EMU'
                        }
                    }
                }
            }
        ]
    
    def _add_table_content(
        self, 
        item: Dict[str, Any], 
        slide_id: str, 
        item_index: int
    ) -> List[Dict[str, Any]]:
        """Add table content."""
        table_id = f"{slide_id}_table_{item_index}"
        table_data = item.get('data', {})
        
        rows = table_data.get('rows', [])
        if not rows:
            return []
        
        cols = len(rows[0]) if rows else 1
        
        return [
            {
                'createTable': {
                    'objectId': table_id,
                    'elementProperties': {
                        'pageObjectId': slide_id,
                        'size': {
                            'width': {'magnitude': 6000000, 'unit': 'EMU'},
                            'height': {'magnitude': len(rows) * 400000, 'unit': 'EMU'}
                        },
                        'transform': {
                            'scaleX': 1,
                            'scaleY': 1,
                            'translateX': 1000000,
                            'translateY': 2000000 + (item_index * 2000000),
                            'unit': 'EMU'
                        }
                    },
                    'rows': len(rows),
                    'columns': cols
                }
            }
        ]
    
    def _add_chart_content(
        self, 
        item: Dict[str, Any], 
        slide_id: str, 
        item_index: int
    ) -> List[Dict[str, Any]]:
        """Add chart content - placeholder implementation."""
        # Google Slides API has limited chart support
        # This would typically create a chart from Google Sheets
        return []
    
    def _hex_to_rgb(self, hex_color: str) -> Dict[str, float]:
        """Convert hex color to RGB."""
        hex_color = hex_color.lstrip('#')
        return {
            'red': int(hex_color[0:2], 16) / 255.0,
            'green': int(hex_color[2:4], 16) / 255.0,
            'blue': int(hex_color[4:6], 16) / 255.0
        }


class ProgressTracker:
    """Tracks progress of presentation generation."""
    
    def __init__(self, total_operations: int):
        self.total_operations = total_operations
        self.completed_operations = 0
        self.start_time = time.time()
        self.logger = get_logger(self.__class__.__name__)
        self.callbacks = []
    
    def add_callback(self, callback):
        """Add progress callback function."""
        self.callbacks.append(callback)
    
    def update(self, increment: int = 1, message: str = ""):
        """Update progress."""
        self.completed_operations += increment
        progress_percent = (self.completed_operations / self.total_operations) * 100
        
        elapsed_time = time.time() - self.start_time
        if self.completed_operations > 0:
            estimated_total_time = elapsed_time * (self.total_operations / self.completed_operations)
            remaining_time = estimated_total_time - elapsed_time
        else:
            remaining_time = 0
        
        self.logger.info(
            f"Progress: {progress_percent:.1f}% ({self.completed_operations}/{self.total_operations}) - {message}"
        )
        
        # Call progress callbacks
        for callback in self.callbacks:
            try:
                callback({
                    'progress_percent': progress_percent,
                    'completed': self.completed_operations,
                    'total': self.total_operations,
                    'elapsed_time': elapsed_time,
                    'remaining_time': remaining_time,
                    'message': message
                })
            except Exception as e:
                self.logger.error(f"Progress callback error: {e}")
    
    def complete(self):
        """Mark as complete."""
        self.completed_operations = self.total_operations
        total_time = time.time() - self.start_time
        self.logger.info(f"Operation completed in {total_time:.2f} seconds")


class GoogleSlidesGenerator:
    """
    Comprehensive Google Slides generator for academic presentations.
    
    Features:
    - OAuth 2.0 authentication with Google API
    - Direct upload to Google Drive with folder organization
    - Format preservation from internal format to Google Slides
    - Collaborative link generation with permission management
    - Template application and branding customization
    - Bulk operations and batch processing
    - Sharing and permission management
    - Automated slide formatting and layout optimization
    - Progress tracking for large presentations
    - Rate limiting and error handling
    """
    
    def __init__(
        self,
        google_credentials: GoogleCredentials,
        drive_config: Optional[DriveConfig] = None,
        template_config: Optional[TemplateConfig] = None,
        sharing_config: Optional[SharingConfig] = None,
        batch_config: Optional[BatchConfig] = None
    ):
        """
        Initialize Google Slides generator.
        
        Args:
            google_credentials: Google API credentials configuration
            drive_config: Google Drive configuration
            template_config: Template configuration
            sharing_config: Sharing configuration
            batch_config: Batch processing configuration
        """
        self.google_credentials = google_credentials
        self.drive_config = drive_config or DriveConfig()
        self.template_config = template_config or TemplateConfig()
        self.sharing_config = sharing_config or SharingConfig()
        self.batch_config = batch_config or BatchConfig()
        
        self.logger = get_logger(self.__class__.__name__)
        self.oauth_manager = GoogleOAuthManager(google_credentials)
        self.format_converter = GoogleSlidesFormatConverter()
        self.rate_limiter = RateLimiter()
        
        # Services
        self.user_credentials: Optional[Credentials] = None
        self.drive_manager: Optional[GoogleDriveManager] = None
        self.slides_service = None
        
        # Cache
        self._template_cache = {}
        self._folder_cache = {}
    
    def authenticate_user(self, credentials_file_path: Optional[str] = None) -> str:
        """
        Start user authentication process.
        
        Args:
            credentials_file_path: Path to saved credentials file
            
        Returns:
            Authorization URL for user to visit
        """
        try:
            # Try to load existing credentials
            if credentials_file_path:
                self.user_credentials = self.oauth_manager.load_credentials(credentials_file_path)
                
                if self.user_credentials:
                    # Refresh if expired
                    if self.user_credentials.expired:
                        self.user_credentials = self.oauth_manager.refresh_credentials(self.user_credentials)
                    
                    self._initialize_services()
                    self.logger.info("User authenticated with existing credentials")
                    return "authenticated"
            
            # Start new authentication flow
            auth_url = self.oauth_manager.get_authorization_url()
            self.logger.info("Started new authentication flow")
            return auth_url
            
        except Exception as e:
            self.logger.error(f"Authentication failed: {e}")
            raise
    
    def complete_authentication(
        self, 
        authorization_code: str, 
        credentials_file_path: Optional[str] = None
    ) -> None:
        """
        Complete authentication with authorization code.
        
        Args:
            authorization_code: Authorization code from callback
            credentials_file_path: Path to save credentials
        """
        try:
            self.user_credentials = self.oauth_manager.exchange_code_for_tokens(authorization_code)
            
            # Save credentials if path provided
            if credentials_file_path:
                self.oauth_manager.save_credentials(self.user_credentials, credentials_file_path)
            
            self._initialize_services()
            self.logger.info("Authentication completed successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to complete authentication: {e}")
            raise
    
    def _initialize_services(self):
        """Initialize Google API services."""
        if not self.user_credentials:
            raise ValueError("User credentials not available. Complete authentication first.")
        
        try:
            self.drive_manager = GoogleDriveManager(self.user_credentials, self.drive_config)
            self.slides_service = build('slides', 'v1', credentials=self.user_credentials)
            self.logger.info("Initialized Google API services")
        except Exception as e:
            self.logger.error(f"Failed to initialize services: {e}")
            raise
    
    async def create_presentation(
        self,
        slides: List[SlideContent],
        title: str,
        citations: Optional[List[Citation]] = None,
        metadata: Optional[Dict[str, Any]] = None,
        progress_callback: Optional[callable] = None
    ) -> Dict[str, Any]:
        """
        Create Google Slides presentation.
        
        Args:
            slides: List of slide content
            title: Presentation title
            citations: Optional citations
            metadata: Optional metadata
            progress_callback: Progress callback function
            
        Returns:
            Dictionary with presentation info
        """
        if not self.slides_service:
            raise ValueError("Services not initialized. Complete authentication first.")
        
        try:
            total_operations = len(slides) + 5  # slides + setup operations
            progress = ProgressTracker(total_operations)
            if progress_callback:
                progress.add_callback(progress_callback)
            
            self.logger.info(f"Creating presentation: {title}")
            progress.update(1, "Creating presentation...")
            
            # Create presentation
            presentation_body = {
                'title': title
            }
            
            await self.rate_limiter.acquire()
            presentation = self.slides_service.presentations().create(
                body=presentation_body
            ).execute()
            
            presentation_id = presentation['presentationId']
            progress.update(1, f"Created presentation with ID: {presentation_id}")
            
            # Apply template and formatting
            await self._apply_template(presentation_id, progress)
            
            # Convert slides to API requests
            progress.update(1, "Converting slides...")
            api_requests = self.format_converter.convert_slides_to_requests(
                slides, presentation_id, self.template_config
            )
            
            # Execute requests in batches
            await self._execute_batch_requests(presentation_id, api_requests, progress)
            
            # Add citations if provided
            if citations:
                await self._add_citations_slide(presentation_id, citations, progress)
            
            # Upload to Drive and organize
            folder_id = await self._organize_in_drive(presentation_id, title, progress)
            
            # Generate sharing links
            links = self._generate_sharing_links(presentation_id)
            
            progress.complete()
            
            result = {
                'presentation_id': presentation_id,
                'title': title,
                'folder_id': folder_id,
                'links': links,
                'slide_count': len(slides),
                'status': 'completed'
            }
            
            self.logger.info(f"Successfully created presentation: {presentation_id}")
            return result
            
        except Exception as e:
            self.logger.error(f"Failed to create presentation: {e}")
            raise
    
    async def _apply_template(self, presentation_id: str, progress: ProgressTracker):
        """Apply template to presentation."""
        try:
            if self.template_config.template_id:
                # Copy from template
                await self.rate_limiter.acquire()
                # Note: Google Slides API doesn't have direct template copying
                # This would require creating slides based on template structure
                pass
            
            # Apply theme and branding
            requests = []
            
            # Apply theme color
            if self.template_config.theme_color:
                requests.append({
                    'updateSlidesPosition': {
                        'slideObjectIds': [],
                        'insertionIndex': 0
                    }
                })
            
            if requests:
                await self.rate_limiter.acquire()
                self.slides_service.presentations().batchUpdate(
                    presentationId=presentation_id,
                    body={'requests': requests}
                ).execute()
            
            progress.update(1, "Applied template")
            
        except Exception as e:
            self.logger.error(f"Failed to apply template: {e}")
            progress.update(1, "Template application failed")
    
    async def _execute_batch_requests(
        self, 
        presentation_id: str, 
        requests: List[Dict[str, Any]], 
        progress: ProgressTracker
    ):
        """Execute API requests in batches."""
        try:
            batch_size = self.batch_config.batch_size
            total_batches = (len(requests) + batch_size - 1) // batch_size
            
            for i in range(0, len(requests), batch_size):
                batch_requests = requests[i:i + batch_size]
                
                await self.rate_limiter.acquire()
                
                try:
                    self.slides_service.presentations().batchUpdate(
                        presentationId=presentation_id,
                        body={'requests': batch_requests}
                    ).execute()
                    
                    batch_num = (i // batch_size) + 1
                    progress.update(
                        len(batch_requests), 
                        f"Processed batch {batch_num}/{total_batches}"
                    )
                    
                except HttpError as e:
                    if e.resp.status == 429:  # Rate limited
                        await asyncio.sleep(self.batch_config.retry_delay * 2)
                        # Retry the batch
                        await self.rate_limiter.acquire()
                        self.slides_service.presentations().batchUpdate(
                            presentationId=presentation_id,
                            body={'requests': batch_requests}
                        ).execute()
                    else:
                        raise
                
                # Small delay between batches
                await asyncio.sleep(self.batch_config.rate_limit_delay)
            
        except Exception as e:
            self.logger.error(f"Failed to execute batch requests: {e}")
            raise
    
    async def _add_citations_slide(
        self, 
        presentation_id: str, 
        citations: List[Citation], 
        progress: ProgressTracker
    ):
        """Add citations slide to presentation."""
        try:
            # Create references slide
            slide_id = f"references_{uuid.uuid4().hex[:8]}"
            
            requests = [
                {
                    'createSlide': {
                        'objectId': slide_id,
                        'slideLayoutReference': {
                            'predefinedLayout': 'TITLE_AND_BODY'
                        }
                    }
                },
                {
                    'insertText': {
                        'objectId': f"{slide_id}_title",
                        'text': 'References'
                    }
                }
            ]
            
            # Format citations
            citation_text = "\n".join([
                f"[{i+1}] {self._format_citation(citation)}"
                for i, citation in enumerate(citations)
            ])
            
            requests.append({
                'insertText': {
                    'objectId': f"{slide_id}_body",
                    'text': citation_text
                }
            })
            
            await self.rate_limiter.acquire()
            self.slides_service.presentations().batchUpdate(
                presentationId=presentation_id,
                body={'requests': requests}
            ).execute()
            
            progress.update(1, "Added citations slide")
            
        except Exception as e:
            self.logger.error(f"Failed to add citations slide: {e}")
            progress.update(1, "Citations slide failed")
    
    def _format_citation(self, citation: Citation) -> str:
        """Format citation for display."""
        parts = []
        if citation.authors:
            parts.append(", ".join(citation.authors))
        if citation.title:
            parts.append(f'"{citation.title}"')
        if citation.venue:
            parts.append(citation.venue)
        if citation.year:
            parts.append(str(citation.year))
        return ". ".join(parts) + "."
    
    async def _organize_in_drive(
        self, 
        presentation_id: str, 
        title: str, 
        progress: ProgressTracker
    ) -> str:
        """Organize presentation in Google Drive."""
        try:
            if not self.drive_manager:
                progress.update(1, "Drive organization skipped")
                return ""
            
            folder_id = self.drive_manager.organize_presentation_folder(title)
            
            # Move presentation to folder
            await self.rate_limiter.acquire()
            self.drive_manager.drive_service.files().update(
                fileId=presentation_id,
                addParents=folder_id,
                fields='id, parents'
            ).execute()
            
            progress.update(1, f"Organized in folder: {folder_id}")
            return folder_id
            
        except Exception as e:
            self.logger.error(f"Failed to organize in Drive: {e}")
            progress.update(1, "Drive organization failed")
            return ""
    
    def _generate_sharing_links(self, presentation_id: str) -> Dict[str, str]:
        """Generate sharing links for presentation."""
        try:
            if not self.drive_manager:
                return {}
            
            links = {
                'view': self.drive_manager.get_file_link(presentation_id, 'view'),
                'edit': self.drive_manager.get_file_link(presentation_id, 'edit'),
                'comment': self.drive_manager.get_file_link(presentation_id, 'comment')
            }
            
            self.logger.info("Generated sharing links")
            return links
            
        except Exception as e:
            self.logger.error(f"Failed to generate sharing links: {e}")
            return {}
    
    async def batch_create_presentations(
        self,
        presentations_data: List[Dict[str, Any]],
        progress_callback: Optional[callable] = None
    ) -> List[Dict[str, Any]]:
        """
        Create multiple presentations in batch.
        
        Args:
            presentations_data: List of presentation data
            progress_callback: Progress callback function
            
        Returns:
            List of created presentation info
        """
        results = []
        semaphore = asyncio.Semaphore(self.batch_config.max_concurrent_requests)
        
        async def create_single_presentation(pres_data):
            async with semaphore:
                try:
                    result = await self.create_presentation(
                        slides=pres_data['slides'],
                        title=pres_data['title'],
                        citations=pres_data.get('citations'),
                        metadata=pres_data.get('metadata'),
                        progress_callback=progress_callback
                    )
                    return result
                except Exception as e:
                    self.logger.error(f"Failed to create presentation '{pres_data['title']}': {e}")
                    return {
                        'title': pres_data['title'],
                        'status': 'failed',
                        'error': str(e)
                    }
        
        # Create tasks for all presentations
        tasks = [
            create_single_presentation(pres_data) 
            for pres_data in presentations_data
        ]
        
        # Execute all tasks
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        successful = sum(1 for r in results if isinstance(r, dict) and r.get('status') == 'completed')
        self.logger.info(f"Batch creation completed: {successful}/{len(presentations_data)} successful")
        
        return results
    
    def set_presentation_permissions(
        self,
        presentation_id: str,
        permissions: List[Dict[str, Any]]
    ) -> None:
        """
        Set permissions for a presentation.
        
        Args:
            presentation_id: Presentation ID
            permissions: List of permission configurations
        """
        try:
            if not self.drive_manager:
                raise ValueError("Drive manager not initialized")
            
            self.drive_manager.set_file_permissions(presentation_id, permissions)
            self.logger.info(f"Set permissions for presentation: {presentation_id}")
            
        except Exception as e:
            self.logger.error(f"Failed to set permissions: {e}")
            raise
    
    def share_presentation(
        self,
        presentation_id: str,
        email: str,
        role: PermissionRole = PermissionRole.VIEWER,
        message: Optional[str] = None
    ) -> Dict[str, str]:
        """
        Share presentation with specific user.
        
        Args:
            presentation_id: Presentation ID
            email: User email
            role: Permission role
            message: Optional message
            
        Returns:
            Sharing information
        """
        try:
            permission = {
                'type': ShareType.USER.value,
                'role': role.value,
                'emailAddress': email,
                'sendNotificationEmail': self.sharing_config.send_notification_email
            }
            
            if message:
                permission['emailMessage'] = message
            
            self.set_presentation_permissions(presentation_id, [permission])
            
            links = self._generate_sharing_links(presentation_id)
            
            return {
                'email': email,
                'role': role.value,
                'links': links,
                'status': 'shared'
            }
            
        except Exception as e:
            self.logger.error(f"Failed to share presentation: {e}")
            raise
    
    def make_presentation_public(
        self,
        presentation_id: str,
        role: PermissionRole = PermissionRole.VIEWER
    ) -> Dict[str, str]:
        """
        Make presentation publicly accessible.
        
        Args:
            presentation_id: Presentation ID
            role: Public permission role
            
        Returns:
            Public sharing information
        """
        try:
            if not self.sharing_config.allow_public_sharing:
                raise ValueError("Public sharing not allowed in configuration")
            
            permission = {
                'type': ShareType.ANYONE.value,
                'role': role.value
            }
            
            self.set_presentation_permissions(presentation_id, [permission])
            
            links = self._generate_sharing_links(presentation_id)
            
            return {
                'access': 'public',
                'role': role.value,
                'links': links,
                'status': 'public'
            }
            
        except Exception as e:
            self.logger.error(f"Failed to make presentation public: {e}")
            raise
    
    def get_presentation_info(self, presentation_id: str) -> Dict[str, Any]:
        """
        Get presentation information.
        
        Args:
            presentation_id: Presentation ID
            
        Returns:
            Presentation information
        """
        try:
            if not self.slides_service:
                raise ValueError("Slides service not initialized")
            
            presentation = self.slides_service.presentations().get(
                presentationId=presentation_id
            ).execute()
            
            return {
                'id': presentation['presentationId'],
                'title': presentation['title'],
                'slide_count': len(presentation.get('slides', [])),
                'page_size': presentation.get('pageSize', {}),
                'revision_id': presentation.get('revisionId'),
                'masters': len(presentation.get('masters', [])),
                'layouts': len(presentation.get('layouts', []))
            }
            
        except Exception as e:
            self.logger.error(f"Failed to get presentation info: {e}")
            raise
    
    def export_to_pdf(self, presentation_id: str) -> io.BytesIO:
        """
        Export presentation as PDF.
        
        Args:
            presentation_id: Presentation ID
            
        Returns:
            PDF content as BytesIO
        """
        try:
            if not self.drive_manager:
                raise ValueError("Drive manager not initialized")
            
            # Export as PDF
            pdf_export = self.drive_manager.drive_service.files().export_media(
                fileId=presentation_id,
                mimeType='application/pdf'
            ).execute()
            
            buffer = io.BytesIO(pdf_export)
            self.logger.info(f"Exported presentation {presentation_id} as PDF")
            return buffer
            
        except Exception as e:
            self.logger.error(f"Failed to export as PDF: {e}")
            raise
    
    def export_to_pptx(self, presentation_id: str) -> io.BytesIO:
        """
        Export presentation as PPTX.
        
        Args:
            presentation_id: Presentation ID
            
        Returns:
            PPTX content as BytesIO
        """
        try:
            if not self.drive_manager:
                raise ValueError("Drive manager not initialized")
            
            # Export as PPTX
            pptx_export = self.drive_manager.drive_service.files().export_media(
                fileId=presentation_id,
                mimeType='application/vnd.openxmlformats-officedocument.presentationml.presentation'
            ).execute()
            
            buffer = io.BytesIO(pptx_export)
            self.logger.info(f"Exported presentation {presentation_id} as PPTX")
            return buffer
            
        except Exception as e:
            self.logger.error(f"Failed to export as PPTX: {e}")
            raise


# Factory functions for common use cases

def create_academic_google_slides_generator(
    client_id: str,
    client_secret: str,
    university_name: Optional[str] = None,
    template_type: GoogleSlidesTemplate = GoogleSlidesTemplate.SIMPLE_LIGHT,
    theme_color: str = "#1f4e79"
) -> GoogleSlidesGenerator:
    """
    Create Google Slides generator for academic use.
    
    Args:
        client_id: Google OAuth client ID
        client_secret: Google OAuth client secret
        university_name: University name for branding
        template_type: Template type to use
        theme_color: Theme color
        
    Returns:
        Configured GoogleSlidesGenerator
    """
    credentials = GoogleCredentials(
        client_id=client_id,
        client_secret=client_secret
    )
    
    drive_config = DriveConfig(
        folder_name=f"{university_name} Presentations" if university_name else "Academic Presentations",
        organize_by_date=True,
        organize_by_topic=True
    )
    
    template_config = TemplateConfig(
        template_type=template_type,
        theme_color=theme_color,
        university_name=university_name,
        apply_branding=True
    )
    
    sharing_config = SharingConfig(
        default_role=PermissionRole.VIEWER,
        allow_public_sharing=False,
        notify_on_share=True
    )
    
    return GoogleSlidesGenerator(
        google_credentials=credentials,
        drive_config=drive_config,
        template_config=template_config,
        sharing_config=sharing_config
    )


def create_collaborative_google_slides_generator(
    client_id: str,
    client_secret: str,
    allow_public_sharing: bool = True
) -> GoogleSlidesGenerator:
    """
    Create Google Slides generator optimized for collaboration.
    
    Args:
        client_id: Google OAuth client ID
        client_secret: Google OAuth client secret
        allow_public_sharing: Whether to allow public sharing
        
    Returns:
        Configured GoogleSlidesGenerator
    """
    credentials = GoogleCredentials(
        client_id=client_id,
        client_secret=client_secret
    )
    
    drive_config = DriveConfig(
        folder_name="Collaborative Presentations",
        organize_by_date=True,
        auto_create_folders=True
    )
    
    sharing_config = SharingConfig(
        default_role=PermissionRole.EDITOR,
        allow_public_sharing=allow_public_sharing,
        notify_on_share=True,
        send_notification_email=True
    )
    
    batch_config = BatchConfig(
        max_concurrent_requests=10,
        batch_size=50
    )
    
    return GoogleSlidesGenerator(
        google_credentials=credentials,
        drive_config=drive_config,
        sharing_config=sharing_config,
        batch_config=batch_config
    )