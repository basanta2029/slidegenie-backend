"""
Domain schemas for SlideGenie application.
"""

from .auth import *
from .generation import *
from .presentation import *
from .user import *
from .document_processing import *

__all__ = [
    # Auth schemas
    "UserCreate",
    "UserUpdate", 
    "UserResponse",
    "Token",
    "TokenData",
    
    # Generation schemas
    "GenerationRequest",
    "GenerationResponse",
    
    # Presentation schemas
    "PresentationCreate",
    "PresentationUpdate",
    "PresentationResponse",
    
    # User schemas
    "UserBase",
    "UserInDB",
    
    # Document processing schemas
    "DocumentType",
    "ElementType", 
    "ProcessingStatus",
    "BoundingBox",
    "TextStyle",
    "DocumentElement",
    "TextElement",
    "HeadingElement", 
    "FigureElement",
    "TableElement",
    "CitationElement",
    "ReferenceElement",
    "DocumentSection",
    "DocumentMetadata",
    "LayoutInfo",
    "ProcessingResult",
    "ProcessingRequest",
    "ProcessingProgress",
]