"""Seed academic templates

Revision ID: 002
Revises: 001
Create Date: 2024-01-01 00:00:01.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.sql import table, column
from sqlalchemy import String, Text, Boolean, Integer, Float, JSON
import uuid

# revision identifiers, used by Alembic.
revision: str = '002'
down_revision: Union[str, None] = '001'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Insert seed data for academic templates."""
    
    # Create template table reference
    template_table = table('template',
        column('id', sa.UUID),
        column('name', String),
        column('display_name', String),
        column('description', Text),
        column('category', String),
        column('conference_series', String),
        column('academic_field', String),
        column('config', JSON),
        column('is_official', Boolean),
        column('is_active', Boolean),
        column('source', String),
        column('version', String)
    )
    
    # Academic templates
    templates = [
        {
            'id': str(uuid.uuid4()),
            'name': 'ieee_conference',
            'display_name': 'IEEE Conference Standard',
            'description': 'Official IEEE conference presentation template with proper formatting and citation styles',
            'category': 'conference',
            'conference_series': 'IEEE',
            'academic_field': 'Computer Science',
            'is_official': True,
            'is_active': True,
            'source': 'system',
            'version': '1.0.0',
            'config': {
                'layouts': {
                    'title': {
                        'elements': ['title', 'subtitle', 'authors', 'affiliations', 'conference_logo', 'date']
                    },
                    'content': {
                        'elements': ['title', 'body', 'footer']
                    },
                    'two_column': {
                        'elements': ['title', 'left_column', 'right_column', 'footer']
                    }
                },
                'theme': {
                    'colors': {
                        'primary': '#00629B',
                        'secondary': '#78BE20',
                        'background': '#FFFFFF',
                        'text': '#000000'
                    },
                    'fonts': {
                        'title': 'Arial',
                        'body': 'Arial',
                        'code': 'Courier New'
                    },
                    'spacing': {
                        'slide_padding': '40px',
                        'line_height': '1.4'
                    }
                },
                'defaults': {
                    'slide_count': 15,
                    'sections': ['Introduction', 'Related Work', 'Methodology', 'Results', 'Conclusion'],
                    'bibliography_style': 'ieee',
                    'citation_format': 'numeric'
                },
                'requirements': {
                    'title_slide': True,
                    'outline_slide': True,
                    'references_slide': True,
                    'acknowledgments_slide': True,
                    'ieee_copyright': True
                }
            }
        },
        {
            'id': str(uuid.uuid4()),
            'name': 'acm_conference',
            'display_name': 'ACM Conference Template',
            'description': 'ACM SIGCHI and general conference presentation template',
            'category': 'conference',
            'conference_series': 'ACM',
            'academic_field': 'Computer Science',
            'is_official': True,
            'is_active': True,
            'source': 'system',
            'version': '1.0.0',
            'config': {
                'layouts': {
                    'title': {
                        'elements': ['title', 'authors', 'affiliations', 'acm_logo', 'conference_info']
                    },
                    'content': {
                        'elements': ['title', 'body', 'page_number']
                    }
                },
                'theme': {
                    'colors': {
                        'primary': '#0085C3',
                        'secondary': '#F0AB00',
                        'background': '#FFFFFF',
                        'text': '#333333'
                    },
                    'fonts': {
                        'title': 'Helvetica Neue',
                        'body': 'Helvetica',
                        'code': 'Monaco'
                    }
                },
                'defaults': {
                    'slide_count': 12,
                    'sections': ['Problem', 'Approach', 'Implementation', 'Evaluation', 'Discussion'],
                    'bibliography_style': 'acm',
                    'citation_format': 'author-year'
                }
            }
        },
        {
            'id': str(uuid.uuid4()),
            'name': 'thesis_defense',
            'display_name': 'PhD Thesis Defense',
            'description': 'Comprehensive template for doctoral thesis defense presentations',
            'category': 'defense',
            'academic_field': 'General',
            'is_official': False,
            'is_active': True,
            'source': 'system',
            'version': '1.0.0',
            'config': {
                'layouts': {
                    'title': {
                        'elements': ['university_logo', 'title', 'candidate_name', 'advisor', 'committee', 'date']
                    },
                    'chapter': {
                        'elements': ['chapter_number', 'chapter_title', 'chapter_outline']
                    },
                    'content': {
                        'elements': ['title', 'body', 'slide_number']
                    }
                },
                'theme': {
                    'colors': {
                        'primary': '#800020',
                        'secondary': '#FFD700',
                        'background': '#FFFFFF',
                        'text': '#000000'
                    },
                    'fonts': {
                        'title': 'Georgia',
                        'body': 'Times New Roman',
                        'code': 'Consolas'
                    }
                },
                'defaults': {
                    'slide_count': 45,
                    'sections': [
                        'Introduction',
                        'Literature Review',
                        'Research Questions',
                        'Methodology',
                        'Results',
                        'Discussion',
                        'Contributions',
                        'Future Work',
                        'Conclusion'
                    ],
                    'bibliography_style': 'apa',
                    'include_acknowledgments': True,
                    'include_publications': True
                }
            }
        },
        {
            'id': str(uuid.uuid4()),
            'name': 'academic_lecture',
            'display_name': 'Academic Lecture',
            'description': 'Clean template for university lectures and course presentations',
            'category': 'lecture',
            'academic_field': 'General',
            'is_official': False,
            'is_active': True,
            'source': 'system',
            'version': '1.0.0',
            'config': {
                'layouts': {
                    'title': {
                        'elements': ['course_code', 'lecture_title', 'instructor', 'date', 'university']
                    },
                    'learning_objectives': {
                        'elements': ['title', 'objectives_list']
                    },
                    'content': {
                        'elements': ['title', 'body', 'footer']
                    },
                    'example': {
                        'elements': ['title', 'example_box', 'explanation']
                    }
                },
                'theme': {
                    'colors': {
                        'primary': '#003366',
                        'secondary': '#66CCFF',
                        'background': '#FFFFFF',
                        'text': '#000000',
                        'highlight': '#FFCC00'
                    },
                    'fonts': {
                        'title': 'Roboto',
                        'body': 'Open Sans',
                        'code': 'Source Code Pro'
                    }
                },
                'defaults': {
                    'slide_count': 30,
                    'sections': ['Objectives', 'Review', 'New Content', 'Examples', 'Summary', 'Questions'],
                    'include_exercises': True,
                    'include_reading_list': True
                }
            }
        },
        {
            'id': str(uuid.uuid4()),
            'name': 'research_seminar',
            'display_name': 'Research Seminar',
            'description': 'Professional template for research seminars and departmental talks',
            'category': 'seminar',
            'academic_field': 'General',
            'is_official': False,
            'is_active': True,
            'source': 'system',
            'version': '1.0.0',
            'config': {
                'layouts': {
                    'title': {
                        'elements': ['title', 'presenter', 'affiliation', 'email', 'date']
                    },
                    'agenda': {
                        'elements': ['title', 'timeline']
                    },
                    'results': {
                        'elements': ['title', 'figure', 'caption', 'interpretation']
                    }
                },
                'theme': {
                    'colors': {
                        'primary': '#2C3E50',
                        'secondary': '#3498DB',
                        'background': '#ECF0F1',
                        'text': '#2C3E50'
                    },
                    'fonts': {
                        'title': 'Lato',
                        'body': 'Lato',
                        'code': 'Fira Code'
                    }
                },
                'defaults': {
                    'slide_count': 20,
                    'sections': ['Background', 'Motivation', 'Methods', 'Results', 'Implications', 'Q&A'],
                    'bibliography_style': 'chicago',
                    'include_contact_slide': True
                }
            }
        },
        {
            'id': str(uuid.uuid4()),
            'name': 'poster_presentation',
            'display_name': 'Academic Poster Session',
            'description': 'Template for presenting academic posters in conference sessions',
            'category': 'poster',
            'academic_field': 'General',
            'is_official': False,
            'is_active': True,
            'source': 'system',
            'version': '1.0.0',
            'config': {
                'layouts': {
                    'title': {
                        'elements': ['poster_title', 'authors', 'poster_number', 'qr_code']
                    },
                    'poster_overview': {
                        'elements': ['poster_thumbnail', 'key_points']
                    },
                    'detail': {
                        'elements': ['section_title', 'content', 'figure']
                    }
                },
                'theme': {
                    'colors': {
                        'primary': '#4CAF50',
                        'secondary': '#FFC107',
                        'background': '#FAFAFA',
                        'text': '#212121'
                    },
                    'fonts': {
                        'title': 'Montserrat',
                        'body': 'Roboto',
                        'code': 'Ubuntu Mono'
                    }
                },
                'defaults': {
                    'slide_count': 5,
                    'sections': ['Overview', 'Key Finding 1', 'Key Finding 2', 'Conclusions', 'References'],
                    'include_poster_image': True,
                    'include_handout_link': True
                }
            }
        },
        {
            'id': str(uuid.uuid4()),
            'name': 'minimal_academic',
            'display_name': 'Minimalist Academic',
            'description': 'Clean, distraction-free template for academic presentations',
            'category': 'general',
            'academic_field': 'General',
            'is_official': False,
            'is_active': True,
            'source': 'system',
            'version': '1.0.0',
            'config': {
                'layouts': {
                    'title': {
                        'elements': ['title', 'subtitle', 'author', 'date']
                    },
                    'content': {
                        'elements': ['title', 'body']
                    },
                    'quote': {
                        'elements': ['quote', 'attribution']
                    }
                },
                'theme': {
                    'colors': {
                        'primary': '#000000',
                        'secondary': '#666666',
                        'background': '#FFFFFF',
                        'text': '#000000',
                        'accent': '#0066CC'
                    },
                    'fonts': {
                        'title': 'Helvetica',
                        'body': 'Helvetica',
                        'code': 'Menlo'
                    },
                    'spacing': {
                        'slide_padding': '60px',
                        'line_height': '1.6'
                    }
                },
                'defaults': {
                    'slide_count': 10,
                    'minimal_design': True,
                    'no_slide_numbers': False,
                    'bibliography_style': 'mla'
                }
            }
        },
        {
            'id': str(uuid.uuid4()),
            'name': 'medical_research',
            'display_name': 'Medical Research Presentation',
            'description': 'Template for medical and clinical research presentations',
            'category': 'conference',
            'academic_field': 'Medicine',
            'is_official': False,
            'is_active': True,
            'source': 'system',
            'version': '1.0.0',
            'config': {
                'layouts': {
                    'title': {
                        'elements': ['title', 'authors', 'institutions', 'clinical_trial_number', 'disclosure']
                    },
                    'patient_data': {
                        'elements': ['title', 'demographics_table', 'privacy_notice']
                    },
                    'results': {
                        'elements': ['title', 'statistical_table', 'p_values', 'confidence_intervals']
                    }
                },
                'theme': {
                    'colors': {
                        'primary': '#006747',
                        'secondary': '#00A859',
                        'background': '#FFFFFF',
                        'text': '#333333',
                        'warning': '#FF6B6B'
                    },
                    'fonts': {
                        'title': 'Arial',
                        'body': 'Arial',
                        'code': 'Courier New'
                    }
                },
                'defaults': {
                    'slide_count': 18,
                    'sections': [
                        'Background',
                        'Objectives',
                        'Methods',
                        'Patient Demographics',
                        'Results',
                        'Adverse Events',
                        'Discussion',
                        'Limitations',
                        'Conclusions'
                    ],
                    'bibliography_style': 'vancouver',
                    'include_ethics_approval': True,
                    'include_conflict_of_interest': True,
                    'statistical_notation': True
                }
            }
        }
    ]
    
    # Insert templates
    op.bulk_insert(template_table, templates)
    
    # Create tags
    tag_table = table('tag',
        column('id', sa.UUID),
        column('name', String),
        column('category', String)
    )
    
    tags = [
        # Field tags
        {'id': str(uuid.uuid4()), 'name': 'computer-science', 'category': 'field'},
        {'id': str(uuid.uuid4()), 'name': 'biology', 'category': 'field'},
        {'id': str(uuid.uuid4()), 'name': 'physics', 'category': 'field'},
        {'id': str(uuid.uuid4()), 'name': 'mathematics', 'category': 'field'},
        {'id': str(uuid.uuid4()), 'name': 'medicine', 'category': 'field'},
        {'id': str(uuid.uuid4()), 'name': 'engineering', 'category': 'field'},
        {'id': str(uuid.uuid4()), 'name': 'social-sciences', 'category': 'field'},
        
        # Method tags
        {'id': str(uuid.uuid4()), 'name': 'machine-learning', 'category': 'method'},
        {'id': str(uuid.uuid4()), 'name': 'statistical-analysis', 'category': 'method'},
        {'id': str(uuid.uuid4()), 'name': 'experimental', 'category': 'method'},
        {'id': str(uuid.uuid4()), 'name': 'theoretical', 'category': 'method'},
        {'id': str(uuid.uuid4()), 'name': 'computational', 'category': 'method'},
        {'id': str(uuid.uuid4()), 'name': 'qualitative', 'category': 'method'},
        {'id': str(uuid.uuid4()), 'name': 'quantitative', 'category': 'method'},
        
        # Conference tags
        {'id': str(uuid.uuid4()), 'name': 'ieee', 'category': 'conference'},
        {'id': str(uuid.uuid4()), 'name': 'acm', 'category': 'conference'},
        {'id': str(uuid.uuid4()), 'name': 'neurips', 'category': 'conference'},
        {'id': str(uuid.uuid4()), 'name': 'icml', 'category': 'conference'},
        {'id': str(uuid.uuid4()), 'name': 'cvpr', 'category': 'conference'},
        {'id': str(uuid.uuid4()), 'name': 'aaai', 'category': 'conference'},
    ]
    
    op.bulk_insert(tag_table, tags)


def downgrade() -> None:
    """Remove seed data."""
    # Delete in reverse order due to foreign keys
    op.execute("DELETE FROM tag WHERE category IN ('field', 'method', 'conference')")
    op.execute("DELETE FROM template WHERE source = 'system'")