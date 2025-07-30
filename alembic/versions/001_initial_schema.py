"""Initial schema with academic features

Revision ID: 001
Revises: 
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import pgvector.sqlalchemy

# revision identifiers, used by Alembic.
revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create initial schema with all tables and extensions."""
    
    # Create extensions
    op.execute('CREATE EXTENSION IF NOT EXISTS "uuid-ossp"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "vector"')
    op.execute('CREATE EXTENSION IF NOT EXISTS "pg_trgm"')  # For text search
    
    # Create institutions table
    op.create_table('institution',
        sa.Column('id', sa.UUID(), nullable=False, default=sa.text('uuid_generate_v4()')),
        sa.Column('name', sa.String(length=500), nullable=False),
        sa.Column('short_name', sa.String(length=100), nullable=True),
        sa.Column('country', sa.String(length=100), nullable=True),
        sa.Column('website', sa.String(length=500), nullable=True),
        sa.Column('logo_url', sa.String(length=500), nullable=True),
        sa.Column('colors', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('subscription_type', sa.String(length=50), nullable=True),
        sa.Column('license_seats', sa.Integer(), nullable=True),
        sa.Column('license_expires', sa.DateTime(timezone=True), nullable=True),
        sa.Column('domain_whitelist', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('sso_enabled', sa.Boolean(), nullable=True, default=False),
        sa.Column('sso_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_institution_deleted_at', 'institution', ['deleted_at'], unique=False)
    
    # Create templates table (before users since users reference templates)
    op.create_table('template',
        sa.Column('id', sa.UUID(), nullable=False, default=sa.text('uuid_generate_v4()')),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('display_name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('category', sa.String(length=100), nullable=True),
        sa.Column('conference_series', sa.String(length=200), nullable=True),
        sa.Column('academic_field', sa.String(length=200), nullable=True),
        sa.Column('config', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column('thumbnail_url', sa.String(length=500), nullable=True),
        sa.Column('preview_slides', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_official', sa.Boolean(), nullable=True, default=False),
        sa.Column('is_premium', sa.Boolean(), nullable=True, default=False),
        sa.Column('is_active', sa.Boolean(), nullable=True, default=True),
        sa.Column('usage_count', sa.Integer(), nullable=True, default=0),
        sa.Column('rating', sa.Float(), nullable=True),
        sa.Column('source', sa.String(length=50), nullable=True, default='system'),
        sa.Column('source_url', sa.String(length=500), nullable=True),
        sa.Column('created_by_id', sa.UUID(), nullable=True),
        sa.Column('institution_id', sa.UUID(), nullable=True),
        sa.Column('version', sa.String(length=20), nullable=True, default='1.0.0'),
        sa.Column('compatible_with', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['institution_id'], ['institution.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index('idx_template_category_field', 'template', ['category', 'academic_field'], unique=False)
    op.create_index('idx_template_conference', 'template', ['conference_series'], unique=False)
    op.create_index('idx_template_deleted_at', 'template', ['deleted_at'], unique=False)
    
    # Create users table
    op.create_table('user',
        sa.Column('id', sa.UUID(), nullable=False, default=sa.text('uuid_generate_v4()')),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('password_hash', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=False),
        sa.Column('title', sa.String(length=50), nullable=True),
        sa.Column('institution', sa.String(length=255), nullable=True),
        sa.Column('department', sa.String(length=255), nullable=True),
        sa.Column('position', sa.String(length=100), nullable=True),
        sa.Column('orcid_id', sa.String(length=50), nullable=True),
        sa.Column('google_scholar_id', sa.String(length=100), nullable=True),
        sa.Column('research_interests', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('bio', sa.Text(), nullable=True),
        sa.Column('role', sa.String(length=50), nullable=False, default='user'),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('is_verified', sa.Boolean(), nullable=False, default=False),
        sa.Column('verification_token', sa.String(length=255), nullable=True),
        sa.Column('reset_token', sa.String(length=255), nullable=True),
        sa.Column('reset_token_expires', sa.DateTime(timezone=True), nullable=True),
        sa.Column('subscription_tier', sa.String(length=50), nullable=True, default='free'),
        sa.Column('subscription_expires', sa.DateTime(timezone=True), nullable=True),
        sa.Column('monthly_presentations_used', sa.Integer(), nullable=True, default=0),
        sa.Column('storage_used_bytes', sa.BigInteger(), nullable=True, default=0),
        sa.Column('preferences', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default={}),
        sa.Column('default_template_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['default_template_id'], ['template.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('email'),
        sa.UniqueConstraint('orcid_id')
    )
    op.create_index(op.f('ix_user_email'), 'user', ['email'], unique=False)
    op.create_index('idx_user_institution_dept', 'user', ['institution', 'department'], unique=False)
    op.create_index('idx_user_subscription', 'user', ['subscription_tier', 'subscription_expires'], unique=False)
    op.create_index('idx_user_deleted_at', 'user', ['deleted_at'], unique=False)
    
    # Update template table to add foreign key to user
    op.create_foreign_key(None, 'template', 'user', ['created_by_id'], ['id'])
    
    # Create tags table
    op.create_table('tag',
        sa.Column('id', sa.UUID(), nullable=False, default=sa.text('uuid_generate_v4()')),
        sa.Column('name', sa.String(length=100), nullable=False),
        sa.Column('category', sa.String(length=50), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name')
    )
    op.create_index('idx_tag_deleted_at', 'tag', ['deleted_at'], unique=False)
    
    # Create presentations table
    op.create_table('presentation',
        sa.Column('id', sa.UUID(), nullable=False, default=sa.text('uuid_generate_v4()')),
        sa.Column('owner_id', sa.UUID(), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=False),
        sa.Column('subtitle', sa.String(length=500), nullable=True),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('abstract', sa.Text(), nullable=True),
        sa.Column('presentation_type', sa.String(length=50), nullable=True),
        sa.Column('academic_level', sa.String(length=50), nullable=True),
        sa.Column('field_of_study', sa.String(length=200), nullable=True),
        sa.Column('keywords', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('doi', sa.String(length=200), nullable=True),
        sa.Column('conference_name', sa.String(length=500), nullable=True),
        sa.Column('conference_acronym', sa.String(length=50), nullable=True),
        sa.Column('conference_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('conference_location', sa.String(length=500), nullable=True),
        sa.Column('session_type', sa.String(length=100), nullable=True),
        sa.Column('duration_minutes', sa.Integer(), nullable=True),
        sa.Column('slide_count', sa.Integer(), nullable=True, default=0),
        sa.Column('aspect_ratio', sa.String(length=20), nullable=True, default='16:9'),
        sa.Column('language', sa.String(length=10), nullable=True, default='en'),
        sa.Column('template_id', sa.UUID(), nullable=True),
        sa.Column('theme_config', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default={}),
        sa.Column('status', sa.String(length=50), nullable=True, default='draft'),
        sa.Column('is_public', sa.Boolean(), nullable=True, default=False),
        sa.Column('is_template', sa.Boolean(), nullable=True, default=False),
        sa.Column('view_count', sa.Integer(), nullable=True, default=0),
        sa.Column('download_count', sa.Integer(), nullable=True, default=0),
        sa.Column('allow_comments', sa.Boolean(), nullable=True, default=True),
        sa.Column('allow_download', sa.Boolean(), nullable=True, default=False),
        sa.Column('share_token', sa.String(length=255), nullable=True),
        sa.Column('search_vector', postgresql.TSVECTOR(), nullable=True),
        sa.Column('last_accessed', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_modified_by_id', sa.UUID(), nullable=True),
        sa.Column('version', sa.Integer(), nullable=True, default=1),
        sa.Column('metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default={}),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['last_modified_by_id'], ['user.id'], ),
        sa.ForeignKeyConstraint(['owner_id'], ['user.id'], ),
        sa.ForeignKeyConstraint(['template_id'], ['template.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('share_token')
    )
    op.create_index('idx_presentation_conference', 'presentation', ['conference_name', 'conference_date'], unique=False)
    op.create_index('idx_presentation_owner_status', 'presentation', ['owner_id', 'status'], unique=False)
    op.create_index('idx_presentation_search', 'presentation', ['search_vector'], unique=False, postgresql_using='gin')
    op.create_index('idx_presentation_type_field', 'presentation', ['presentation_type', 'field_of_study'], unique=False)
    op.create_index('idx_presentation_deleted_at', 'presentation', ['deleted_at'], unique=False)
    
    # Create association tables
    op.create_table('presentation_authors',
        sa.Column('presentation_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('author_order', sa.Integer(), nullable=False, default=0),
        sa.Column('is_corresponding', sa.Boolean(), nullable=True, default=False),
        sa.Column('contribution', sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(['presentation_id'], ['presentation.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('presentation_id', 'user_id')
    )
    
    op.create_table('presentation_tags',
        sa.Column('presentation_id', sa.UUID(), nullable=False),
        sa.Column('tag_id', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['presentation_id'], ['presentation.id'], ),
        sa.ForeignKeyConstraint(['tag_id'], ['tag.id'], ),
        sa.PrimaryKeyConstraint('presentation_id', 'tag_id')
    )
    
    # Create dependent tables
    op.create_table('apikey',
        sa.Column('id', sa.UUID(), nullable=False, default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('key_prefix', sa.String(length=10), nullable=False),
        sa.Column('key_hash', sa.String(length=255), nullable=False),
        sa.Column('scopes', postgresql.ARRAY(sa.String()), nullable=True),
        sa.Column('rate_limit', sa.Integer(), nullable=True, default=1000),
        sa.Column('last_used_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_used_ip', sa.String(length=45), nullable=True),
        sa.Column('usage_count', sa.Integer(), nullable=True, default=0),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, default=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('key_hash')
    )
    op.create_index('idx_api_key_prefix', 'apikey', ['key_prefix'], unique=False)
    op.create_index('idx_apikey_deleted_at', 'apikey', ['deleted_at'], unique=False)
    
    op.create_table('export',
        sa.Column('id', sa.UUID(), nullable=False, default=sa.text('uuid_generate_v4()')),
        sa.Column('presentation_id', sa.UUID(), nullable=False),
        sa.Column('format', sa.String(length=50), nullable=False),
        sa.Column('options', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default={}),
        sa.Column('status', sa.String(length=50), nullable=False, default='pending'),
        sa.Column('file_url', sa.String(length=500), nullable=True),
        sa.Column('file_size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('requested_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('download_count', sa.Integer(), nullable=True, default=0),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['presentation_id'], ['presentation.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_export_deleted_at', 'export', ['deleted_at'], unique=False)
    
    op.create_table('generationjob',
        sa.Column('id', sa.UUID(), nullable=False, default=sa.text('uuid_generate_v4()')),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('presentation_id', sa.UUID(), nullable=True),
        sa.Column('job_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False, default='pending'),
        sa.Column('priority', sa.Integer(), nullable=True, default=5),
        sa.Column('input_type', sa.String(length=50), nullable=False),
        sa.Column('input_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column('processing_steps', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default=[]),
        sa.Column('result_data', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default={}),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('error_details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('tokens_used', sa.Integer(), nullable=True),
        sa.Column('ai_model_used', sa.String(length=100), nullable=True),
        sa.Column('generation_cost', sa.Float(), nullable=True),
        sa.Column('queued_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('duration_seconds', sa.Float(), nullable=True),
        sa.Column('user_rating', sa.Integer(), nullable=True),
        sa.Column('user_feedback', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['presentation_id'], ['presentation.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['user.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_job_queued', 'generationjob', ['status', 'priority', 'queued_at'], unique=False)
    op.create_index('idx_job_user_status', 'generationjob', ['user_id', 'status'], unique=False)
    op.create_index('idx_generationjob_deleted_at', 'generationjob', ['deleted_at'], unique=False)
    
    op.create_table('presentationembedding',
        sa.Column('id', sa.UUID(), nullable=False, default=sa.text('uuid_generate_v4()')),
        sa.Column('presentation_id', sa.UUID(), nullable=False),
        sa.Column('embedding_type', sa.String(length=50), nullable=True),
        sa.Column('embedding_model', sa.String(length=100), nullable=True),
        sa.Column('embedding', pgvector.sqlalchemy.VECTOR(1536), nullable=True),
        sa.Column('generated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.ForeignKeyConstraint(['presentation_id'], ['presentation.id'], ),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_embedding_vector', 'presentationembedding', ['embedding'], unique=False, postgresql_using='ivfflat', postgresql_with={'lists': '100'})
    
    op.create_table('presentationversion',
        sa.Column('id', sa.UUID(), nullable=False, default=sa.text('uuid_generate_v4()')),
        sa.Column('presentation_id', sa.UUID(), nullable=False),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=500), nullable=True),
        sa.Column('content_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('change_summary', sa.Text(), nullable=True),
        sa.Column('changed_by_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['changed_by_id'], ['user.id'], ),
        sa.ForeignKeyConstraint(['presentation_id'], ['presentation.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('presentation_id', 'version_number', name='uq_presentation_version')
    )
    op.create_index('idx_presentationversion_deleted_at', 'presentationversion', ['deleted_at'], unique=False)
    
    op.create_table('reference',
        sa.Column('id', sa.UUID(), nullable=False, default=sa.text('uuid_generate_v4()')),
        sa.Column('presentation_id', sa.UUID(), nullable=False),
        sa.Column('citation_key', sa.String(length=255), nullable=False),
        sa.Column('bibtex_type', sa.String(length=50), nullable=True),
        sa.Column('bibtex_data', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('formatted_citations', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default={}),
        sa.Column('url', sa.String(length=500), nullable=True),
        sa.Column('doi', sa.String(length=200), nullable=True),
        sa.Column('pmid', sa.String(length=50), nullable=True),
        sa.Column('arxiv_id', sa.String(length=50), nullable=True),
        sa.Column('usage_count', sa.Integer(), nullable=True, default=0),
        sa.Column('slide_numbers', postgresql.ARRAY(sa.Integer()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['presentation_id'], ['presentation.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('presentation_id', 'citation_key', name='uq_presentation_citation_key')
    )
    op.create_index('idx_reference_doi', 'reference', ['doi'], unique=False)
    op.create_index('idx_reference_deleted_at', 'reference', ['deleted_at'], unique=False)
    
    op.create_table('slide',
        sa.Column('id', sa.UUID(), nullable=False, default=sa.text('uuid_generate_v4()')),
        sa.Column('presentation_id', sa.UUID(), nullable=False),
        sa.Column('slide_number', sa.Integer(), nullable=False),
        sa.Column('content', postgresql.JSONB(astext_type=sa.Text()), nullable=False, default={}),
        sa.Column('layout_type', sa.String(length=50), nullable=True, default='content'),
        sa.Column('title', sa.String(length=500), nullable=True),
        sa.Column('section', sa.String(length=200), nullable=True),
        sa.Column('contains_equations', sa.Boolean(), nullable=True, default=False),
        sa.Column('contains_code', sa.Boolean(), nullable=True, default=False),
        sa.Column('contains_citations', sa.Boolean(), nullable=True, default=False),
        sa.Column('contains_figures', sa.Boolean(), nullable=True, default=False),
        sa.Column('figure_count', sa.Integer(), nullable=True, default=0),
        sa.Column('word_count', sa.Integer(), nullable=True, default=0),
        sa.Column('transitions', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default={}),
        sa.Column('animations', postgresql.JSONB(astext_type=sa.Text()), nullable=True, default={}),
        sa.Column('duration_seconds', sa.Integer(), nullable=True),
        sa.Column('speaker_notes', sa.Text(), nullable=True),
        sa.Column('is_hidden', sa.Boolean(), nullable=True, default=False),
        sa.Column('is_backup', sa.Boolean(), nullable=True, default=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['presentation_id'], ['presentation.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('presentation_id', 'slide_number', name='uq_presentation_slide_number')
    )
    op.create_index('idx_slide_content', 'slide', ['content'], unique=False, postgresql_using='gin')
    op.create_index('idx_slide_presentation_number', 'slide', ['presentation_id', 'slide_number'], unique=False)
    op.create_index('idx_slide_deleted_at', 'slide', ['deleted_at'], unique=False)
    
    # Create trigger for updating search vectors
    op.execute("""
        CREATE OR REPLACE FUNCTION update_presentation_search_vector()
        RETURNS trigger AS $$
        BEGIN
            NEW.search_vector := 
                setweight(to_tsvector('english', coalesce(NEW.title, '')), 'A') ||
                setweight(to_tsvector('english', coalesce(NEW.subtitle, '')), 'B') ||
                setweight(to_tsvector('english', coalesce(NEW.description, '')), 'C') ||
                setweight(to_tsvector('english', coalesce(NEW.abstract, '')), 'C');
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """)
    
    op.execute("""
        CREATE TRIGGER update_presentation_search_vector_trigger
        BEFORE INSERT OR UPDATE OF title, subtitle, description, abstract
        ON presentation
        FOR EACH ROW
        EXECUTE FUNCTION update_presentation_search_vector();
    """)


def downgrade() -> None:
    """Drop all tables and extensions."""
    # Drop trigger and function
    op.execute('DROP TRIGGER IF EXISTS update_presentation_search_vector_trigger ON presentation')
    op.execute('DROP FUNCTION IF EXISTS update_presentation_search_vector()')
    
    # Drop tables in reverse order
    op.drop_table('slide')
    op.drop_table('reference')
    op.drop_table('presentationversion')
    op.drop_table('presentationembedding')
    op.drop_table('generationjob')
    op.drop_table('export')
    op.drop_table('apikey')
    op.drop_table('presentation_tags')
    op.drop_table('presentation_authors')
    op.drop_table('presentation')
    op.drop_table('tag')
    op.drop_table('user')
    op.drop_table('template')
    op.drop_table('institution')
    
    # Drop extensions
    op.execute('DROP EXTENSION IF EXISTS "pg_trgm"')
    op.execute('DROP EXTENSION IF EXISTS "vector"')
    op.execute('DROP EXTENSION IF EXISTS "uuid-ossp"')