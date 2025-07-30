"""
File Processing and Storage service interfaces for Agent 4.
"""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional, BinaryIO
from uuid import UUID


class IDocumentProcessingService(ABC):
    """Interface for document processing."""
    
    @abstractmethod
    async def parse_pdf(
        self,
        file_content: bytes,
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Parse PDF document and extract content."""
        pass
    
    @abstractmethod
    async def extract_images(
        self,
        file_content: bytes,
        min_size: Optional[tuple[int, int]] = None,
    ) -> List[Dict[str, Any]]:
        """Extract images from document."""
        pass
    
    @abstractmethod
    async def recognize_structure(
        self,
        document_content: str,
    ) -> Dict[str, Any]:
        """Recognize academic paper structure."""
        pass
    
    @abstractmethod
    async def extract_metadata(
        self,
        file_content: bytes,
    ) -> Dict[str, Any]:
        """Extract document metadata."""
        pass
    
    @abstractmethod
    async def convert_to_text(
        self,
        file_content: bytes,
        file_type: str,
    ) -> str:
        """Convert various file types to text."""
        pass


class IStorageService(ABC):
    """Interface for file storage operations."""
    
    @abstractmethod
    async def upload_file(
        self,
        file_content: bytes,
        file_name: str,
        content_type: str,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Upload file to storage."""
        pass
    
    @abstractmethod
    async def download_file(
        self,
        file_key: str,
    ) -> bytes:
        """Download file from storage."""
        pass
    
    @abstractmethod
    async def delete_file(
        self,
        file_key: str,
    ) -> bool:
        """Delete file from storage."""
        pass
    
    @abstractmethod
    async def generate_presigned_url(
        self,
        file_key: str,
        expires_in: int = 3600,
    ) -> str:
        """Generate presigned URL for direct access."""
        pass
    
    @abstractmethod
    async def list_files(
        self,
        prefix: str,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """List files with prefix."""
        pass


class IExportService(ABC):
    """Interface for presentation export."""
    
    @abstractmethod
    async def export_to_pptx(
        self,
        presentation_id: UUID,
        options: Optional[Dict[str, Any]] = None,
    ) -> bytes:
        """Export presentation to PowerPoint."""
        pass
    
    @abstractmethod
    async def export_to_pdf(
        self,
        presentation_id: UUID,
        options: Optional[Dict[str, Any]] = None,
    ) -> bytes:
        """Export presentation to PDF."""
        pass
    
    @abstractmethod
    async def export_to_latex(
        self,
        presentation_id: UUID,
        template: str = "beamer",
        options: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Export presentation to LaTeX/Beamer."""
        pass
    
    @abstractmethod
    async def export_to_html(
        self,
        presentation_id: UUID,
        framework: str = "reveal.js",
        options: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Export presentation to HTML."""
        pass
    
    @abstractmethod
    async def export_to_video(
        self,
        presentation_id: UUID,
        options: Optional[Dict[str, Any]] = None,
    ) -> str:
        """Export presentation to video (returns job ID)."""
        pass


class IThumbnailService(ABC):
    """Interface for thumbnail generation."""
    
    @abstractmethod
    async def generate_slide_thumbnail(
        self,
        slide_content: Dict[str, Any],
        size: tuple[int, int] = (320, 240),
    ) -> bytes:
        """Generate thumbnail for slide."""
        pass
    
    @abstractmethod
    async def generate_presentation_thumbnail(
        self,
        presentation_id: UUID,
        slide_number: int = 1,
    ) -> bytes:
        """Generate thumbnail for presentation."""
        pass
    
    @abstractmethod
    async def batch_generate_thumbnails(
        self,
        presentation_id: UUID,
    ) -> Dict[int, str]:
        """Generate thumbnails for all slides."""
        pass


class IImageOptimizationService(ABC):
    """Interface for image optimization."""
    
    @abstractmethod
    async def optimize_image(
        self,
        image_content: bytes,
        target_size: Optional[tuple[int, int]] = None,
        quality: int = 85,
    ) -> bytes:
        """Optimize image for presentations."""
        pass
    
    @abstractmethod
    async def convert_image_format(
        self,
        image_content: bytes,
        target_format: str,
    ) -> bytes:
        """Convert image to different format."""
        pass
    
    @abstractmethod
    async def create_image_variants(
        self,
        image_content: bytes,
        variants: List[Dict[str, Any]],
    ) -> Dict[str, bytes]:
        """Create multiple image variants."""
        pass
    
    @abstractmethod
    async def extract_dominant_colors(
        self,
        image_content: bytes,
        count: int = 5,
    ) -> List[str]:
        """Extract dominant colors from image."""
        pass