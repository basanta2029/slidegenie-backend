"""Extension system for slide generation service."""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional, Type, Protocol
import importlib
import inspect
from dataclasses import dataclass
from pathlib import Path
import logging


logger = logging.getLogger(__name__)


class SlideExtension(ABC):
    """Base class for slide generation extensions."""
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Extension name."""
        pass
    
    @property
    @abstractmethod
    def version(self) -> str:
        """Extension version."""
        pass
    
    @property
    def description(self) -> str:
        """Extension description."""
        return ""
    
    @property
    def dependencies(self) -> List[str]:
        """Required extension dependencies."""
        return []
    
    @abstractmethod
    def initialize(self, config: Dict[str, Any]) -> None:
        """Initialize the extension with configuration."""
        pass
    
    def cleanup(self) -> None:
        """Cleanup resources when extension is unloaded."""
        pass


class GeneratorExtension(SlideExtension):
    """Extension for custom slide generators."""
    
    @abstractmethod
    def supports_format(self, format: str) -> bool:
        """Check if extension supports the given format."""
        pass
    
    @abstractmethod
    def generate(self, content: Dict[str, Any], config: Dict[str, Any]) -> Any:
        """Generate slides with custom logic."""
        pass


class LayoutExtension(SlideExtension):
    """Extension for custom layouts."""
    
    @abstractmethod
    def get_layouts(self) -> List[Dict[str, Any]]:
        """Get available layouts from this extension."""
        pass
    
    @abstractmethod
    def apply_layout(self, slide: Dict[str, Any], layout_name: str) -> Dict[str, Any]:
        """Apply layout to a slide."""
        pass


class RuleExtension(SlideExtension):
    """Extension for custom validation rules."""
    
    @abstractmethod
    def get_rules(self) -> List[Dict[str, Any]]:
        """Get validation rules from this extension."""
        pass
    
    @abstractmethod
    def validate(self, content: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Validate content and return violations."""
        pass


class QualityExtension(SlideExtension):
    """Extension for custom quality checks."""
    
    @abstractmethod
    def check_quality(self, presentation: Dict[str, Any]) -> Dict[str, Any]:
        """Perform quality checks and return results."""
        pass
    
    @abstractmethod
    def improve_quality(self, presentation: Dict[str, Any]) -> Dict[str, Any]:
        """Attempt to improve presentation quality."""
        pass


class ProcessorExtension(SlideExtension):
    """Extension for custom content processors."""
    
    @abstractmethod
    def process_content(self, content: Dict[str, Any]) -> Dict[str, Any]:
        """Process content before slide generation."""
        pass
    
    @abstractmethod
    def post_process(self, presentation: Dict[str, Any]) -> Dict[str, Any]:
        """Post-process generated presentation."""
        pass


@dataclass
class ExtensionInfo:
    """Information about a loaded extension."""
    name: str
    version: str
    description: str
    extension_type: Type[SlideExtension]
    instance: Optional[SlideExtension] = None
    enabled: bool = False
    config: Dict[str, Any] = None


class ExtensionRegistry:
    """Registry for managing slide generation extensions."""
    
    def __init__(self):
        self._extensions: Dict[str, ExtensionInfo] = {}
        self._extension_types = {
            "generator": GeneratorExtension,
            "layout": LayoutExtension,
            "rule": RuleExtension,
            "quality": QualityExtension,
            "processor": ProcessorExtension
        }
    
    def register(self, extension_class: Type[SlideExtension]) -> None:
        """Register an extension class."""
        if not issubclass(extension_class, SlideExtension):
            raise ValueError(f"{extension_class} must be a subclass of SlideExtension")
        
        # Create temporary instance to get metadata
        temp_instance = extension_class()
        name = temp_instance.name
        
        # Determine extension type
        extension_type = None
        for type_name, type_class in self._extension_types.items():
            if issubclass(extension_class, type_class):
                extension_type = type_class
                break
        
        if not extension_type:
            extension_type = SlideExtension
        
        self._extensions[name] = ExtensionInfo(
            name=name,
            version=temp_instance.version,
            description=temp_instance.description,
            extension_type=extension_type,
            instance=None,
            enabled=False
        )
        
        logger.info(f"Registered extension: {name} v{temp_instance.version}")
    
    def load_from_module(self, module_path: str) -> None:
        """Load extensions from a Python module."""
        try:
            module = importlib.import_module(module_path)
            
            # Find all extension classes in the module
            for name, obj in inspect.getmembers(module):
                if (inspect.isclass(obj) and 
                    issubclass(obj, SlideExtension) and 
                    obj != SlideExtension and
                    not name.startswith("_")):
                    self.register(obj)
        
        except ImportError as e:
            logger.error(f"Failed to load module {module_path}: {e}")
            raise
    
    def load_from_directory(self, directory: str) -> None:
        """Load all extensions from a directory."""
        dir_path = Path(directory)
        if not dir_path.exists():
            logger.warning(f"Extension directory does not exist: {directory}")
            return
        
        for file_path in dir_path.glob("*.py"):
            if file_path.name.startswith("_"):
                continue
            
            module_name = file_path.stem
            try:
                spec = importlib.util.spec_from_file_location(module_name, file_path)
                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)
                
                # Find extension classes
                for name, obj in inspect.getmembers(module):
                    if (inspect.isclass(obj) and 
                        issubclass(obj, SlideExtension) and 
                        obj != SlideExtension):
                        self.register(obj)
            
            except Exception as e:
                logger.error(f"Failed to load extension from {file_path}: {e}")
    
    def enable(self, name: str, config: Optional[Dict[str, Any]] = None) -> None:
        """Enable an extension with optional configuration."""
        if name not in self._extensions:
            raise ValueError(f"Extension not found: {name}")
        
        info = self._extensions[name]
        
        # Check dependencies
        for dep in info.instance.dependencies if info.instance else []:
            if dep not in self._extensions or not self._extensions[dep].enabled:
                raise ValueError(f"Dependency not satisfied: {dep}")
        
        # Create instance if needed
        if not info.instance:
            extension_class = next(
                (obj for obj in globals().values() 
                 if inspect.isclass(obj) and 
                 issubclass(obj, SlideExtension) and
                 hasattr(obj(), "name") and 
                 obj().name == name),
                None
            )
            
            if extension_class:
                info.instance = extension_class()
            else:
                raise ValueError(f"Cannot instantiate extension: {name}")
        
        # Initialize with config
        info.instance.initialize(config or {})
        info.enabled = True
        info.config = config
        
        logger.info(f"Enabled extension: {name}")
    
    def disable(self, name: str) -> None:
        """Disable an extension."""
        if name not in self._extensions:
            raise ValueError(f"Extension not found: {name}")
        
        info = self._extensions[name]
        if info.enabled and info.instance:
            info.instance.cleanup()
            info.enabled = False
            logger.info(f"Disabled extension: {name}")
    
    def get_extension(self, name: str) -> Optional[SlideExtension]:
        """Get an enabled extension by name."""
        info = self._extensions.get(name)
        if info and info.enabled:
            return info.instance
        return None
    
    def get_extensions_by_type(self, extension_type: Type[SlideExtension]) -> List[SlideExtension]:
        """Get all enabled extensions of a specific type."""
        extensions = []
        for info in self._extensions.values():
            if info.enabled and isinstance(info.instance, extension_type):
                extensions.append(info.instance)
        return extensions
    
    def list_extensions(self, enabled_only: bool = False) -> List[ExtensionInfo]:
        """List all registered extensions."""
        if enabled_only:
            return [info for info in self._extensions.values() if info.enabled]
        return list(self._extensions.values())
    
    def get_extension_info(self, name: str) -> Optional[ExtensionInfo]:
        """Get information about an extension."""
        return self._extensions.get(name)
    
    def cleanup(self) -> None:
        """Cleanup all enabled extensions."""
        for info in self._extensions.values():
            if info.enabled and info.instance:
                try:
                    info.instance.cleanup()
                except Exception as e:
                    logger.error(f"Error cleaning up extension {info.name}: {e}")


# Example custom extension
class MarkdownExportExtension(GeneratorExtension):
    """Example extension for exporting to Markdown format."""
    
    @property
    def name(self) -> str:
        return "markdown_export"
    
    @property
    def version(self) -> str:
        return "1.0.0"
    
    @property
    def description(self) -> str:
        return "Export presentations to Markdown format with YAML frontmatter"
    
    def initialize(self, config: Dict[str, Any]) -> None:
        self.include_speaker_notes = config.get("include_speaker_notes", True)
        self.include_metadata = config.get("include_metadata", True)
    
    def supports_format(self, format: str) -> bool:
        return format.lower() in ["markdown", "md"]
    
    def generate(self, content: Dict[str, Any], config: Dict[str, Any]) -> str:
        """Generate Markdown from presentation content."""
        lines = []
        
        # Add metadata
        if self.include_metadata:
            lines.extend([
                "---",
                f"title: {content.get('title', 'Untitled')}",
                f"author: {content.get('author', 'Unknown')}",
                f"date: {content.get('date', '')}",
                "---",
                ""
            ])
        
        # Add slides
        for i, slide in enumerate(content.get("slides", [])):
            if i > 0:
                lines.append("---")
                lines.append("")
            
            # Slide title
            if slide.get("title"):
                lines.append(f"## {slide['title']}")
                lines.append("")
            
            # Slide content
            if slide.get("content"):
                lines.append(slide["content"])
                lines.append("")
            
            # Speaker notes
            if self.include_speaker_notes and slide.get("notes"):
                lines.append("<!--")
                lines.append(f"Speaker Notes: {slide['notes']}")
                lines.append("-->")
                lines.append("")
        
        return "\n".join(lines)