"""
Database models for SlideGenie with academic features.
"""
import uuid
from datetime import datetime
from typing import List, Optional

from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    JSON,
    String,
    Table,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB, TSVECTOR, UUID, ARRAY
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import relationship, validates
from sqlalchemy_utils import TSVectorType

from app.infrastructure.database.base import Base


class TimestampMixin:
    """Mixin for created_at, updated_at, and soft delete support."""
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)
    deleted_at = Column(DateTime(timezone=True), nullable=True, index=True)
    
    @hybrid_property
    def is_deleted(self) -> bool:
        """Check if record is soft deleted."""
        return self.deleted_at is not None


# Association tables for many-to-many relationships
presentation_authors = Table(
    'presentation_authors',
    Base.metadata,
    Column('presentation_id', UUID(as_uuid=True), ForeignKey('presentation.id'), primary_key=True),
    Column('user_id', UUID(as_uuid=True), ForeignKey('user.id'), primary_key=True),
    Column('author_order', Integer, nullable=False, default=0),
    Column('is_corresponding', Boolean, default=False),
    Column('contribution', String(500))
)

presentation_tags = Table(
    'presentation_tags',
    Base.metadata,
    Column('presentation_id', UUID(as_uuid=True), ForeignKey('presentation.id'), primary_key=True),
    Column('tag_id', UUID(as_uuid=True), ForeignKey('tag.id'), primary_key=True)
)


class User(Base, TimestampMixin):
    """User model with academic profile."""
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=True)  # Optional for OAuth users
    
    # Academic profile
    full_name = Column(String(255), nullable=False)
    title = Column(String(50))  # Dr., Prof., etc.
    institution = Column(String(255), index=True)
    department = Column(String(255))
    position = Column(String(100))  # PhD Student, Post-doc, Professor, etc.
    orcid_id = Column(String(50), unique=True)
    google_scholar_id = Column(String(100))
    research_interests = Column(ARRAY(String))
    bio = Column(Text)
    
    # Account settings
    role = Column(String(50), default="user", nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    is_verified = Column(Boolean, default=False, nullable=False)
    verification_token = Column(String(255))
    reset_token = Column(String(255))
    reset_token_expires = Column(DateTime(timezone=True))
    
    # Subscription info
    subscription_tier = Column(String(50), default="free")  # free, academic, professional, institutional
    subscription_expires = Column(DateTime(timezone=True))
    monthly_presentations_used = Column(Integer, default=0)
    storage_used_bytes = Column(BigInteger, default=0)
    
    # Preferences
    preferences = Column(JSONB, default=dict)
    default_template_id = Column(UUID(as_uuid=True), ForeignKey('template.id'))
    
    # Relationships
    presentations = relationship("Presentation", back_populates="owner", foreign_keys="Presentation.owner_id")
    authored_presentations = relationship("Presentation", secondary=presentation_authors, back_populates="authors")
    templates = relationship("Template", back_populates="created_by")
    api_keys = relationship("APIKey", back_populates="user", cascade="all, delete-orphan")
    generation_jobs = relationship("GenerationJob", back_populates="user", cascade="all, delete-orphan")
    oauth_accounts = relationship("OAuthAccount", back_populates="user", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_user_institution_dept', 'institution', 'department'),
        Index('idx_user_subscription', 'subscription_tier', 'subscription_expires'),
    )


class OAuthAccount(Base, TimestampMixin):
    """OAuth account linked to user."""
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('user.id'), nullable=False)
    
    # OAuth provider info
    provider = Column(String(50), nullable=False)  # google, microsoft, github, etc.
    provider_account_id = Column(String(255), nullable=False)  # Provider's user ID
    email = Column(String(255), nullable=False)
    
    # Additional provider data
    institution = Column(String(255))  # Institution from OAuth provider
    picture_url = Column(String(500))
    access_token = Column(Text)  # Encrypted in production
    refresh_token = Column(Text)  # Encrypted in production
    token_expires_at = Column(Float)  # Unix timestamp
    
    # Metadata
    raw_data = Column(JSONB, default=dict)  # Store provider-specific data
    
    # Relationships
    user = relationship("User", back_populates="oauth_accounts")
    
    # Constraints
    __table_args__ = (
        UniqueConstraint('user_id', 'provider', name='_user_provider_uc'),
        UniqueConstraint('provider', 'provider_account_id', name='_provider_account_uc'),
        Index('idx_oauth_user_provider', 'user_id', 'provider'),
    )


class Presentation(Base, TimestampMixin):
    """Presentation model with academic metadata."""
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id = Column(UUID(as_uuid=True), ForeignKey('user.id'), nullable=False)
    
    # Basic info
    title = Column(String(500), nullable=False)
    subtitle = Column(String(500))
    description = Column(Text)
    abstract = Column(Text)  # Academic abstract
    
    # Academic metadata
    presentation_type = Column(String(50))  # conference, lecture, defense, seminar, workshop
    academic_level = Column(String(50))  # undergraduate, graduate, research, professional
    field_of_study = Column(String(200))
    keywords = Column(ARRAY(String))
    doi = Column(String(200))
    
    # Conference/Event info
    conference_name = Column(String(500))
    conference_acronym = Column(String(50))
    conference_date = Column(DateTime(timezone=True))
    conference_location = Column(String(500))
    session_type = Column(String(100))  # oral, poster, keynote, invited
    
    # Presentation settings
    duration_minutes = Column(Integer)
    slide_count = Column(Integer, default=0)
    aspect_ratio = Column(String(20), default="16:9")
    language = Column(String(10), default="en")
    
    # Template and styling
    template_id = Column(UUID(as_uuid=True), ForeignKey('template.id'))
    theme_config = Column(JSONB, default=dict)  # Colors, fonts, etc.
    
    # Status and visibility
    status = Column(String(50), default="draft")  # draft, ready, presented, archived
    is_public = Column(Boolean, default=False)
    is_template = Column(Boolean, default=False)  # Can be used as template
    view_count = Column(Integer, default=0)
    download_count = Column(Integer, default=0)
    
    # Collaboration
    allow_comments = Column(Boolean, default=True)
    allow_download = Column(Boolean, default=False)
    share_token = Column(String(255), unique=True)
    
    # Search
    search_vector = Column(TSVectorType('title', 'subtitle', 'description', 'abstract'))
    
    # Statistics
    last_accessed = Column(DateTime(timezone=True))
    last_modified_by_id = Column(UUID(as_uuid=True), ForeignKey('user.id'))
    version = Column(Integer, default=1)
    
    # Additional metadata
    metadata = Column(JSONB, default=dict)
    
    # Relationships
    owner = relationship("User", back_populates="presentations", foreign_keys=[owner_id])
    authors = relationship("User", secondary=presentation_authors, back_populates="authored_presentations")
    template = relationship("Template", back_populates="presentations")
    slides = relationship("Slide", back_populates="presentation", cascade="all, delete-orphan", order_by="Slide.slide_number")
    references = relationship("Reference", back_populates="presentation", cascade="all, delete-orphan")
    generation_jobs = relationship("GenerationJob", back_populates="presentation")
    exports = relationship("Export", back_populates="presentation", cascade="all, delete-orphan")
    versions = relationship("PresentationVersion", back_populates="presentation", cascade="all, delete-orphan")
    embeddings = relationship("PresentationEmbedding", back_populates="presentation", cascade="all, delete-orphan")
    tags = relationship("Tag", secondary=presentation_tags, back_populates="presentations")
    
    # Indexes
    __table_args__ = (
        Index('idx_presentation_search', 'search_vector', postgresql_using='gin'),
        Index('idx_presentation_owner_status', 'owner_id', 'status'),
        Index('idx_presentation_conference', 'conference_name', 'conference_date'),
        Index('idx_presentation_type_field', 'presentation_type', 'field_of_study'),
    )


class Slide(Base, TimestampMixin):
    """Slide model with flexible content structure."""
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    presentation_id = Column(UUID(as_uuid=True), ForeignKey('presentation.id'), nullable=False)
    slide_number = Column(Integer, nullable=False)
    
    # Content structure using JSONB for flexibility
    content = Column(JSONB, nullable=False, default=dict)
    """
    Content structure example:
    {
        "title": "Slide Title",
        "subtitle": "Optional subtitle",
        "body": [
            {"type": "text", "content": "Paragraph text", "style": {...}},
            {"type": "bullet_list", "items": [...], "level": 1},
            {"type": "equation", "content": "LaTeX equation", "display": true},
            {"type": "code", "content": "...", "language": "python"},
            {"type": "image", "url": "...", "caption": "...", "attribution": "..."},
            {"type": "table", "headers": [...], "rows": [...], "caption": "..."},
            {"type": "chart", "data": {...}, "type": "bar", "config": {...}},
            {"type": "citation", "keys": ["ref1", "ref2"], "style": "inline"}
        ],
        "layout": "two_column",  # single, two_column, image_left, etc.
        "background": {...},
        "notes": "Speaker notes here"
    }
    """
    
    # Slide metadata
    layout_type = Column(String(50), default="content")  # title, content, section, image, comparison, etc.
    title = Column(String(500))  # Extracted for easier querying
    section = Column(String(200))  # Section/chapter this slide belongs to
    
    # Academic elements
    contains_equations = Column(Boolean, default=False)
    contains_code = Column(Boolean, default=False)
    contains_citations = Column(Boolean, default=False)
    contains_figures = Column(Boolean, default=False)
    figure_count = Column(Integer, default=0)
    word_count = Column(Integer, default=0)
    
    # Animation and transitions
    transitions = Column(JSONB, default=dict)
    animations = Column(JSONB, default=dict)
    duration_seconds = Column(Integer)  # Estimated speaking time
    
    # Speaker notes
    speaker_notes = Column(Text)
    
    # Visibility
    is_hidden = Column(Boolean, default=False)  # Skip in presentation mode
    is_backup = Column(Boolean, default=False)  # Backup slide
    
    # Relationships
    presentation = relationship("Presentation", back_populates="slides")
    
    # Unique constraint and indexes
    __table_args__ = (
        UniqueConstraint('presentation_id', 'slide_number', name='uq_presentation_slide_number'),
        Index('idx_slide_presentation_number', 'presentation_id', 'slide_number'),
        Index('idx_slide_content', 'content', postgresql_using='gin'),
    )
    
    @validates('content')
    def validate_content(self, key, content):
        """Validate and extract metadata from content."""
        if content:
            # Extract metadata for easier querying
            self.contains_equations = any(
                item.get('type') == 'equation' 
                for item in content.get('body', [])
            )
            self.contains_code = any(
                item.get('type') == 'code' 
                for item in content.get('body', [])
            )
            self.contains_citations = any(
                item.get('type') == 'citation' 
                for item in content.get('body', [])
            )
            self.figure_count = sum(
                1 for item in content.get('body', [])
                if item.get('type') in ['image', 'chart', 'diagram']
            )
        return content


class Reference(Base, TimestampMixin):
    """Reference/Citation model with BibTeX support."""
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    presentation_id = Column(UUID(as_uuid=True), ForeignKey('presentation.id'), nullable=False)
    
    # Citation key (e.g., "Smith2023")
    citation_key = Column(String(255), nullable=False)
    
    # BibTeX data
    bibtex_type = Column(String(50))  # article, inproceedings, book, etc.
    bibtex_data = Column(JSONB, nullable=False)
    """
    BibTeX data structure:
    {
        "author": ["Smith, John", "Doe, Jane"],
        "title": "Paper Title",
        "journal": "Journal Name",
        "year": 2023,
        "volume": 10,
        "pages": "123-456",
        "doi": "10.1234/...",
        ...
    }
    """
    
    # Formatted citations
    formatted_citations = Column(JSONB, default=dict)
    """
    {
        "apa": "Smith, J., & Doe, J. (2023). Paper Title...",
        "mla": "Smith, John, and Jane Doe. \"Paper Title...\"",
        "chicago": "...",
        "ieee": "[1] J. Smith and J. Doe, \"Paper Title...\""
    }
    """
    
    # Additional metadata
    url = Column(String(500))
    doi = Column(String(200))
    pmid = Column(String(50))  # PubMed ID
    arxiv_id = Column(String(50))
    
    # Usage tracking
    usage_count = Column(Integer, default=0)  # How many times cited in presentation
    slide_numbers = Column(ARRAY(Integer))  # Which slides reference this
    
    # Relationships
    presentation = relationship("Presentation", back_populates="references")
    
    # Indexes
    __table_args__ = (
        UniqueConstraint('presentation_id', 'citation_key', name='uq_presentation_citation_key'),
        Index('idx_reference_doi', 'doi'),
    )


class Template(Base, TimestampMixin):
    """Template model for academic presentation templates."""
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Basic info
    name = Column(String(255), nullable=False, unique=True)
    display_name = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(String(100))  # conference, lecture, defense, poster, etc.
    
    # Academic specifics
    conference_series = Column(String(200))  # IEEE, ACM, etc.
    academic_field = Column(String(200))  # Computer Science, Biology, etc.
    
    # Template configuration
    config = Column(JSONB, nullable=False, default=dict)
    """
    Config structure:
    {
        "layouts": {...},  # Available slide layouts
        "theme": {
            "colors": {...},
            "fonts": {...},
            "spacing": {...}
        },
        "defaults": {
            "slide_count": 15,
            "sections": ["Introduction", "Methods", "Results", "Conclusion"],
            "bibliography_style": "ieee"
        },
        "requirements": {
            "title_slide": true,
            "outline_slide": true,
            "references_slide": true,
            "acknowledgments_slide": false
        }
    }
    """
    
    # Assets
    thumbnail_url = Column(String(500))
    preview_slides = Column(JSONB)  # Array of preview slide data
    
    # Metadata
    is_official = Column(Boolean, default=False)  # Official conference template
    is_premium = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    usage_count = Column(Integer, default=0)
    rating = Column(Float)
    
    # Source info
    source = Column(String(50), default="system")  # system, user, institution, conference
    source_url = Column(String(500))  # Link to official template page
    created_by_id = Column(UUID(as_uuid=True), ForeignKey('user.id'))
    institution_id = Column(UUID(as_uuid=True), ForeignKey('institution.id'))
    
    # Version info
    version = Column(String(20), default="1.0.0")
    compatible_with = Column(ARRAY(String))  # PowerPoint versions, etc.
    
    # Relationships
    presentations = relationship("Presentation", back_populates="template")
    created_by = relationship("User", back_populates="templates")
    institution = relationship("Institution")
    
    # Indexes
    __table_args__ = (
        Index('idx_template_category_field', 'category', 'academic_field'),
        Index('idx_template_conference', 'conference_series'),
    )


class GenerationJob(Base, TimestampMixin):
    """Generation job tracking model."""
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('user.id'), nullable=False)
    presentation_id = Column(UUID(as_uuid=True), ForeignKey('presentation.id'))
    
    # Job info
    job_type = Column(String(50), nullable=False)  # full_generation, slide_generation, regeneration
    status = Column(String(50), default="pending", nullable=False)  # pending, processing, completed, failed, cancelled
    priority = Column(Integer, default=5)  # 1-10, higher is more priority
    
    # Input data
    input_type = Column(String(50), nullable=False)  # text, pdf, abstract, outline
    input_data = Column(JSONB, nullable=False, default=dict)
    """
    Input data structure varies by type:
    - text: {"content": "...", "instructions": "..."}
    - pdf: {"file_url": "...", "page_range": [1, 10], "extract_images": true}
    - abstract: {"abstract": "...", "keywords": [...], "conference": "..."}
    """
    
    # Processing info
    processing_steps = Column(JSONB, default=list)
    """
    [
        {"step": "parsing", "status": "completed", "duration_ms": 1200},
        {"step": "extraction", "status": "completed", "duration_ms": 3400},
        {"step": "generation", "status": "processing", "progress": 0.6}
    ]
    """
    
    # Results
    result_data = Column(JSONB, default=dict)
    error_message = Column(Text)
    error_details = Column(JSONB)
    
    # Metrics
    tokens_used = Column(Integer)
    ai_model_used = Column(String(100))
    generation_cost = Column(Float)  # In cents
    
    # Timing
    queued_at = Column(DateTime(timezone=True), server_default=func.now())
    started_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    duration_seconds = Column(Float)
    
    # User feedback
    user_rating = Column(Integer)  # 1-5 stars
    user_feedback = Column(Text)
    
    # Relationships
    user = relationship("User", back_populates="generation_jobs")
    presentation = relationship("Presentation", back_populates="generation_jobs")
    
    # Indexes
    __table_args__ = (
        Index('idx_job_user_status', 'user_id', 'status'),
        Index('idx_job_queued', 'status', 'priority', 'queued_at'),
    )


class Institution(Base, TimestampMixin):
    """Institution model for academic organizations."""
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    
    # Basic info
    name = Column(String(500), nullable=False)
    short_name = Column(String(100))
    country = Column(String(100))
    website = Column(String(500))
    
    # Branding
    logo_url = Column(String(500))
    colors = Column(JSONB)  # {"primary": "#...", "secondary": "#..."}
    
    # Subscription
    subscription_type = Column(String(50))  # enterprise, department, lab
    license_seats = Column(Integer)
    license_expires = Column(DateTime(timezone=True))
    
    # Settings
    domain_whitelist = Column(ARRAY(String))  # Email domains
    sso_enabled = Column(Boolean, default=False)
    sso_config = Column(JSONB)
    
    # Templates
    templates = relationship("Template", back_populates="institution")


class Tag(Base, TimestampMixin):
    """Tag model for categorizing presentations."""
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(100), unique=True, nullable=False)
    category = Column(String(50))  # field, method, conference, etc.
    
    # Relationships
    presentations = relationship("Presentation", secondary=presentation_tags, back_populates="tags")


class Export(Base, TimestampMixin):
    """Export tracking model."""
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    presentation_id = Column(UUID(as_uuid=True), ForeignKey('presentation.id'), nullable=False)
    
    # Export details
    format = Column(String(50), nullable=False)  # pptx, pdf, latex, html, video
    options = Column(JSONB, default=dict)
    """
    Options examples:
    - pdf: {"include_notes": true, "slides_per_page": 1}
    - latex: {"template": "beamer", "include_bibliography": true}
    - video: {"fps": 30, "resolution": "1920x1080", "include_audio": true}
    """
    
    # Status
    status = Column(String(50), default="pending", nullable=False)
    file_url = Column(String(500))
    file_size_bytes = Column(BigInteger)
    error_message = Column(Text)
    
    # Timing
    requested_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    expires_at = Column(DateTime(timezone=True))
    download_count = Column(Integer, default=0)
    
    # Relationships
    presentation = relationship("Presentation", back_populates="exports")


class PresentationVersion(Base, TimestampMixin):
    """Version history for presentations."""
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    presentation_id = Column(UUID(as_uuid=True), ForeignKey('presentation.id'), nullable=False)
    version_number = Column(Integer, nullable=False)
    
    # Snapshot data
    title = Column(String(500))
    content_snapshot = Column(JSONB)  # Compressed slide data
    
    # Change info
    change_summary = Column(Text)
    changed_by_id = Column(UUID(as_uuid=True), ForeignKey('user.id'))
    
    # Relationships
    presentation = relationship("Presentation", back_populates="versions")
    
    # Indexes
    __table_args__ = (
        UniqueConstraint('presentation_id', 'version_number', name='uq_presentation_version'),
    )


class PresentationEmbedding(Base):
    """Vector embeddings for similarity search."""
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    presentation_id = Column(UUID(as_uuid=True), ForeignKey('presentation.id'), nullable=False)
    
    # Embedding data
    embedding_type = Column(String(50))  # title, abstract, content, combined
    embedding_model = Column(String(100))  # Model used to generate embedding
    embedding_vector = Column('embedding', pgvector.VECTOR(1536))  # OpenAI ada-002 dimension
    
    # Metadata
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    
    # Relationships
    presentation = relationship("Presentation", back_populates="embeddings")
    
    # Indexes
    __table_args__ = (
        Index('idx_embedding_vector', 'embedding_vector', postgresql_using='ivfflat'),
    )


class APIKey(Base, TimestampMixin):
    """API Key model for programmatic access."""
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('user.id'), nullable=False)
    
    # Key info
    name = Column(String(255), nullable=False)
    key_prefix = Column(String(10), nullable=False)  # First 8 chars for identification
    key_hash = Column(String(255), nullable=False, unique=True)
    
    # Permissions
    scopes = Column(ARRAY(String))  # ['read:presentations', 'write:presentations', ...]
    rate_limit = Column(Integer, default=1000)  # Requests per hour
    
    # Usage
    last_used_at = Column(DateTime(timezone=True))
    last_used_ip = Column(String(45))
    usage_count = Column(Integer, default=0)
    
    # Validity
    expires_at = Column(DateTime(timezone=True))
    is_active = Column(Boolean, default=True, nullable=False)
    
    # Relationships
    user = relationship("User", back_populates="api_keys")
    
    # Indexes
    __table_args__ = (
        Index('idx_api_key_prefix', 'key_prefix'),
    )


# Import pgvector extension
try:
    import pgvector.sqlalchemy as pgvector
except ImportError:
    # Fallback for development without pgvector
    class pgvector:
        VECTOR = lambda x: ARRAY(Float)