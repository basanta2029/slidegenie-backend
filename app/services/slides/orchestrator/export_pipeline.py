"""Export pipeline for preparing presentations for various formats."""

from typing import Dict, List, Any, Optional, Set, Tuple, BinaryIO
from dataclasses import dataclass, field
from datetime import datetime
import logging
import asyncio
from enum import Enum
import json
import base64
from io import BytesIO

logger = logging.getLogger(__name__)


class ExportFormat(Enum):
    """Supported export formats."""
    PPTX = "pptx"
    PDF = "pdf"
    HTML = "html"
    JSON = "json"
    MARKDOWN = "markdown"
    IMAGES = "images"


@dataclass
class ExportOptions:
    """Options for export pipeline."""
    format: ExportFormat
    include_notes: bool = True
    include_animations: bool = True
    compress_images: bool = True
    image_quality: int = 85  # 1-100
    embed_fonts: bool = True
    password_protect: Optional[str] = None
    watermark: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExportResult:
    """Result of export operation."""
    format: ExportFormat
    data: Optional[bytes] = None
    file_path: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=datetime.utcnow)


class ExportPipeline:
    """Pipeline for exporting presentations to various formats."""
    
    def __init__(self):
        """Initialize the export pipeline."""
        self.formatters: Dict[ExportFormat, Any] = {}
        self.processors: List[Any] = []
        self.validators: Dict[ExportFormat, List[Any]] = {}
        self._export_cache: Dict[str, ExportResult] = {}
        self._init_default_formatters()
        
    def _init_default_formatters(self):
        """Initialize default format handlers."""
        # These would be actual formatter implementations
        self.formatters[ExportFormat.JSON] = self._export_to_json
        self.formatters[ExportFormat.HTML] = self._export_to_html
        self.formatters[ExportFormat.MARKDOWN] = self._export_to_markdown
        
    async def prepare_export(
        self,
        presentation_data: Dict[str, Any],
        options: ExportOptions
    ) -> ExportResult:
        """Prepare presentation for export."""
        logger.info(f"Preparing export for format: {options.format.value}")
        
        try:
            # Validate export options
            validation_errors = await self._validate_export(presentation_data, options)
            if validation_errors:
                return ExportResult(
                    format=options.format,
                    errors=validation_errors
                )
                
            # Pre-process presentation data
            processed_data = await self._preprocess_data(presentation_data, options)
            
            # Apply format-specific processing
            formatter = self.formatters.get(options.format)
            if not formatter:
                return ExportResult(
                    format=options.format,
                    errors=[f"Formatter not available for {options.format.value}"]
                )
                
            # Execute export
            export_data = await formatter(processed_data, options)
            
            # Post-process export data
            final_data = await self._postprocess_export(export_data, options)
            
            # Create result
            result = ExportResult(
                format=options.format,
                data=final_data,
                metadata={
                    "slide_count": len(processed_data.get("slides", [])),
                    "export_options": {
                        "include_notes": options.include_notes,
                        "include_animations": options.include_animations,
                        "image_quality": options.image_quality
                    }
                }
            )
            
            # Cache result if applicable
            cache_key = self._generate_cache_key(presentation_data, options)
            self._export_cache[cache_key] = result
            
            return result
            
        except Exception as e:
            logger.error(f"Export failed: {e}")
            return ExportResult(
                format=options.format,
                errors=[str(e)]
            )
            
    async def export_multiple_formats(
        self,
        presentation_data: Dict[str, Any],
        formats: List[ExportOptions]
    ) -> Dict[ExportFormat, ExportResult]:
        """Export presentation to multiple formats concurrently."""
        tasks = []
        
        for options in formats:
            task = self.prepare_export(presentation_data, options)
            tasks.append((options.format, task))
            
        # Execute exports concurrently
        results = {}
        format_tasks = [(fmt, task) for fmt, task in tasks]
        
        completed_tasks = await asyncio.gather(
            *[task for _, task in format_tasks],
            return_exceptions=True
        )
        
        for (fmt, _), result in zip(format_tasks, completed_tasks):
            if isinstance(result, Exception):
                results[fmt] = ExportResult(
                    format=fmt,
                    errors=[str(result)]
                )
            else:
                results[fmt] = result
                
        return results
        
    async def _validate_export(
        self,
        presentation_data: Dict[str, Any],
        options: ExportOptions
    ) -> List[str]:
        """Validate export request."""
        errors = []
        
        # Check presentation data
        if not presentation_data.get("slides"):
            errors.append("No slides found in presentation")
            
        # Check format-specific requirements
        validators = self.validators.get(options.format, [])
        for validator in validators:
            validator_errors = await validator(presentation_data, options)
            errors.extend(validator_errors)
            
        # Validate options
        if options.image_quality < 1 or options.image_quality > 100:
            errors.append("Image quality must be between 1 and 100")
            
        return errors
        
    async def _preprocess_data(
        self,
        presentation_data: Dict[str, Any],
        options: ExportOptions
    ) -> Dict[str, Any]:
        """Pre-process presentation data for export."""
        processed = presentation_data.copy()
        
        # Process images
        if options.compress_images:
            processed = await self._compress_images(processed, options.image_quality)
            
        # Remove animations if not included
        if not options.include_animations:
            processed = self._remove_animations(processed)
            
        # Remove notes if not included
        if not options.include_notes:
            processed = self._remove_notes(processed)
            
        # Apply watermark if specified
        if options.watermark:
            processed = await self._apply_watermark(processed, options.watermark)
            
        # Add export metadata
        processed["export_metadata"] = {
            "exported_at": datetime.utcnow().isoformat(),
            "export_format": options.format.value,
            "options": {
                "include_notes": options.include_notes,
                "include_animations": options.include_animations,
                "compress_images": options.compress_images
            }
        }
        
        return processed
        
    async def _postprocess_export(
        self,
        export_data: Any,
        options: ExportOptions
    ) -> bytes:
        """Post-process exported data."""
        if isinstance(export_data, bytes):
            final_data = export_data
        elif isinstance(export_data, str):
            final_data = export_data.encode('utf-8')
        else:
            final_data = json.dumps(export_data).encode('utf-8')
            
        # Apply password protection if specified
        if options.password_protect:
            # This would implement actual password protection
            # For now, just add a marker
            logger.info("Password protection requested but not implemented")
            
        return final_data
        
    async def _compress_images(
        self,
        presentation_data: Dict[str, Any],
        quality: int
    ) -> Dict[str, Any]:
        """Compress images in presentation."""
        compressed = presentation_data.copy()
        
        for slide in compressed.get("slides", []):
            content = slide.get("content", {})
            
            # Process images in content
            if "images" in content:
                for image in content["images"]:
                    if "data" in image and image["data"].startswith("data:image"):
                        # Simulate image compression
                        image["data"] = self._compress_image_data(image["data"], quality)
                        image["compressed"] = True
                        
        return compressed
        
    def _compress_image_data(self, image_data: str, quality: int) -> str:
        """Compress a single image."""
        # This is a simplified implementation
        # In production, use proper image compression libraries
        try:
            # Extract base64 data
            header, data = image_data.split(",", 1)
            
            # Add compression marker to header
            compressed_header = header.replace("data:", "data:compressed;q=" + str(quality) + ";")
            
            # Return with marker (actual compression would happen here)
            return compressed_header + "," + data
            
        except Exception as e:
            logger.error(f"Failed to compress image: {e}")
            return image_data
            
    def _remove_animations(self, presentation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove animation data from presentation."""
        cleaned = presentation_data.copy()
        
        for slide in cleaned.get("slides", []):
            if "animations" in slide:
                del slide["animations"]
                
            # Remove animation properties from style
            if "style" in slide:
                style = slide["style"]
                animation_props = ["animation", "transition", "transform"]
                for prop in animation_props:
                    if prop in style:
                        del style[prop]
                        
        return cleaned
        
    def _remove_notes(self, presentation_data: Dict[str, Any]) -> Dict[str, Any]:
        """Remove speaker notes from presentation."""
        cleaned = presentation_data.copy()
        
        for slide in cleaned.get("slides", []):
            if "notes" in slide:
                del slide["notes"]
                
        return cleaned
        
    async def _apply_watermark(
        self,
        presentation_data: Dict[str, Any],
        watermark: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Apply watermark to presentation."""
        watermarked = presentation_data.copy()
        
        watermark_style = {
            "position": "absolute",
            "opacity": watermark.get("opacity", 0.1),
            "fontSize": watermark.get("size", "48px"),
            "color": watermark.get("color", "#cccccc"),
            "transform": "rotate(-45deg)",
            "zIndex": 0
        }
        
        for slide in watermarked.get("slides", []):
            # Add watermark to slide content
            if "content" not in slide:
                slide["content"] = {}
                
            slide["content"]["watermark"] = {
                "text": watermark.get("text", "CONFIDENTIAL"),
                "style": watermark_style
            }
            
        return watermarked
        
    async def _export_to_json(
        self,
        presentation_data: Dict[str, Any],
        options: ExportOptions
    ) -> Dict[str, Any]:
        """Export presentation to JSON format."""
        return {
            "version": "1.0",
            "format": "slidegenie-json",
            "presentation": presentation_data,
            "metadata": options.metadata
        }
        
    async def _export_to_html(
        self,
        presentation_data: Dict[str, Any],
        options: ExportOptions
    ) -> str:
        """Export presentation to HTML format."""
        html_parts = []
        
        # HTML header
        html_parts.append("""
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        .slide {{
            width: 100%;
            max-width: 1024px;
            margin: 0 auto 2rem;
            padding: 2rem;
            border: 1px solid #ddd;
            background: #fff;
            min-height: 576px;
            position: relative;
        }}
        .slide-title {{
            font-size: 2.5rem;
            margin-bottom: 1rem;
            color: #333;
        }}
        .slide-content {{
            font-size: 1.25rem;
            line-height: 1.6;
        }}
        .slide-notes {{
            margin-top: 2rem;
            padding-top: 1rem;
            border-top: 1px solid #eee;
            font-style: italic;
            color: #666;
        }}
    </style>
</head>
<body>
    <div class="presentation">
""".format(title=presentation_data.get("title", "Presentation")))
        
        # Generate slides
        for idx, slide in enumerate(presentation_data.get("slides", [])):
            slide_html = self._generate_slide_html(slide, idx, options)
            html_parts.append(slide_html)
            
        # HTML footer
        html_parts.append("""
    </div>
</body>
</html>
""")
        
        return "".join(html_parts)
        
    def _generate_slide_html(
        self,
        slide: Dict[str, Any],
        index: int,
        options: ExportOptions
    ) -> str:
        """Generate HTML for a single slide."""
        content = slide.get("content", {})
        
        html = f'<div class="slide slide-{index}">\n'
        
        # Add title
        if "title" in content:
            html += f'  <h1 class="slide-title">{content["title"]}</h1>\n'
            
        # Add content
        html += '  <div class="slide-content">\n'
        
        # Add body text
        if "body" in content:
            html += f'    <p>{content["body"]}</p>\n'
            
        # Add bullets
        if "bullets" in content:
            html += '    <ul>\n'
            for bullet in content["bullets"]:
                text = bullet if isinstance(bullet, str) else bullet.get("text", "")
                html += f'      <li>{text}</li>\n'
            html += '    </ul>\n'
            
        html += '  </div>\n'
        
        # Add notes if included
        if options.include_notes and "notes" in slide:
            html += f'  <div class="slide-notes">Speaker Notes: {slide["notes"]}</div>\n'
            
        html += '</div>\n\n'
        
        return html
        
    async def _export_to_markdown(
        self,
        presentation_data: Dict[str, Any],
        options: ExportOptions
    ) -> str:
        """Export presentation to Markdown format."""
        md_parts = []
        
        # Title
        title = presentation_data.get("title", "Presentation")
        md_parts.append(f"# {title}\n\n")
        
        # Metadata
        if presentation_data.get("metadata"):
            md_parts.append("## Metadata\n\n")
            for key, value in presentation_data["metadata"].items():
                md_parts.append(f"- **{key}**: {value}\n")
            md_parts.append("\n")
            
        # Slides
        for idx, slide in enumerate(presentation_data.get("slides", [])):
            slide_md = self._generate_slide_markdown(slide, idx, options)
            md_parts.append(slide_md)
            md_parts.append("\n---\n\n")
            
        return "".join(md_parts)
        
    def _generate_slide_markdown(
        self,
        slide: Dict[str, Any],
        index: int,
        options: ExportOptions
    ) -> str:
        """Generate Markdown for a single slide."""
        content = slide.get("content", {})
        md = f"## Slide {index + 1}"
        
        # Add slide type if not content
        if slide.get("type") != "content":
            md += f" ({slide.get('type')})"
            
        md += "\n\n"
        
        # Add title
        if "title" in content:
            md += f"### {content['title']}\n\n"
            
        # Add body
        if "body" in content:
            md += f"{content['body']}\n\n"
            
        # Add bullets
        if "bullets" in content:
            for bullet in content["bullets"]:
                text = bullet if isinstance(bullet, str) else bullet.get("text", "")
                md += f"- {text}\n"
            md += "\n"
            
        # Add notes
        if options.include_notes and "notes" in slide:
            md += f"**Speaker Notes:** {slide['notes']}\n\n"
            
        return md
        
    def _generate_cache_key(
        self,
        presentation_data: Dict[str, Any],
        options: ExportOptions
    ) -> str:
        """Generate cache key for export result."""
        # Simple hash based on presentation ID and options
        presentation_id = presentation_data.get("id", "unknown")
        options_str = f"{options.format.value}_{options.include_notes}_{options.include_animations}_{options.image_quality}"
        return f"{presentation_id}_{options_str}"
        
    def clear_cache(self):
        """Clear export cache."""
        self._export_cache.clear()
        logger.info("Export cache cleared")