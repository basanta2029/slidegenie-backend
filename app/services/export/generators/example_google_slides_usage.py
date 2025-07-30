"""
Example usage of Google Slides generator for academic presentations.

This module demonstrates how to use the comprehensive Google Slides integration
including OAuth authentication, presentation creation, sharing, and batch operations.
"""

import asyncio
import json
import os
from typing import List, Dict, Any

from app.core.logging import get_logger
from app.domain.schemas.generation import Citation, SlideContent
from app.services.export.generators.google_slides_generator import (
    GoogleSlidesGenerator,
    GoogleCredentials,
    GoogleSlidesTemplate,
    PermissionRole,
    DriveConfig,
    SharingConfig,
    TemplateConfig,
    create_academic_google_slides_generator,
    create_collaborative_google_slides_generator
)

logger = get_logger(__name__)


def create_sample_slides() -> List[SlideContent]:
    """Create sample slides for demonstration."""
    return [
        # Title slide
        SlideContent(
            title="Machine Learning in Academic Research",
            subtitle="A Comprehensive Overview",
            body=[
                {"type": "text", "content": "Dr. Jane Smith"},
                {"type": "text", "content": "University of Technology"},
                {"type": "text", "content": "Computer Science Department"}
            ],
            metadata={"slide_type": "title"}
        ),
        
        # Agenda slide
        SlideContent(
            title="Agenda",
            body=[
                {
                    "type": "bullet_list",
                    "items": [
                        "Introduction to Machine Learning",
                        "Current Research Trends",
                        "Methodology and Experiments",
                        "Results and Analysis",
                        "Future Directions",
                        "Q&A Session"
                    ]
                }
            ]
        ),
        
        # Section header
        SlideContent(
            title="Introduction",
            body=[],
            metadata={"slide_type": "section"}
        ),
        
        # Content with image
        SlideContent(
            title="What is Machine Learning?",
            body=[
                {
                    "type": "text",
                    "content": "Machine Learning is a subset of artificial intelligence that enables computers to learn and make decisions from data without being explicitly programmed for every task."
                },
                {
                    "type": "image",
                    "url": "https://example.com/ml-diagram.png",
                    "alt_text": "Machine Learning Diagram",
                    "caption": "Figure 1: Machine Learning Process Overview"
                }
            ]
        ),
        
        # Two-column layout
        SlideContent(
            title="Types of Machine Learning",
            body=[
                {
                    "type": "bullet_list",
                    "items": [
                        "Supervised Learning",
                        "Unsupervised Learning",
                        "Reinforcement Learning",
                        "Semi-supervised Learning"
                    ]
                },
                {
                    "type": "text",
                    "content": "Each type has specific applications:\n\n• Classification tasks\n• Clustering analysis\n• Decision making\n• Pattern recognition"
                }
            ]
        ),
        
        # Research methodology
        SlideContent(
            title="Research Methodology",
            body=[
                {
                    "type": "table",
                    "data": {
                        "headers": ["Method", "Dataset", "Accuracy", "Time (ms)"],
                        "rows": [
                            ["Random Forest", "MNIST", "97.2%", "45"],
                            ["SVM", "MNIST", "94.8%", "120"],
                            ["Neural Network", "MNIST", "98.1%", "89"],
                            ["Naive Bayes", "MNIST", "89.3%", "12"]
                        ]
                    }
                }
            ]
        ),
        
        # Results with chart
        SlideContent(
            title="Experimental Results",
            body=[
                {
                    "type": "chart",
                    "chart_type": "column",
                    "title": "Model Performance Comparison",
                    "data": {
                        "categories": ["Accuracy", "Precision", "Recall", "F1-Score"],
                        "series": [
                            {"name": "Random Forest", "values": [97.2, 96.8, 97.5, 97.1]},
                            {"name": "Neural Network", "values": [98.1, 97.9, 98.3, 98.1]},
                            {"name": "SVM", "values": [94.8, 94.2, 95.1, 94.6]}
                        ]
                    }
                }
            ]
        ),
        
        # Conclusions
        SlideContent(
            title="Conclusions",
            body=[
                {
                    "type": "bullet_list",
                    "items": [
                        "Neural networks achieved the highest accuracy (98.1%)",
                        "Random Forest provided the best balance of speed and accuracy",
                        "SVM showed consistent performance across different metrics",
                        "Future work will focus on ensemble methods"
                    ]
                }
            ]
        )
    ]


def create_sample_citations() -> List[Citation]:
    """Create sample citations for the presentation."""
    return [
        Citation(
            authors=["Smith, J.", "Johnson, A.", "Williams, B."],
            title="Deep Learning Approaches for Academic Research",
            venue="Journal of Machine Learning Research",
            year=2023,
            doi="10.1234/jmlr.2023.001",
            url="https://jmlr.org/papers/v24/23-001.html"
        ),
        Citation(
            authors=["Brown, C.", "Davis, E."],
            title="Comparative Analysis of Classification Algorithms",
            venue="International Conference on Machine Learning",
            year=2022,
            doi="10.1234/icml.2022.456"
        ),
        Citation(
            authors=["Wilson, F.", "Taylor, G.", "Anderson, H."],
            title="Neural Network Optimization Techniques",
            venue="Neural Information Processing Systems",
            year=2023,
            doi="10.1234/nips.2023.789"
        )
    ]


async def basic_usage_example():
    """Demonstrate basic usage of Google Slides generator."""
    print("=== Basic Usage Example ===")
    
    # Configuration
    google_credentials = GoogleCredentials(
        client_id=os.getenv("GOOGLE_CLIENT_ID", "your_client_id"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET", "your_client_secret")
    )
    
    # Create generator
    generator = GoogleSlidesGenerator(google_credentials)
    
    try:
        # Step 1: Authentication
        print("Step 1: Starting authentication...")
        auth_url = generator.authenticate_user("credentials.json")
        
        if auth_url != "authenticated":
            print(f"Please visit this URL to authenticate: {auth_url}")
            print("After authentication, you'll get a code. Enter it below:")
            auth_code = input("Authorization code: ")
            
            generator.complete_authentication(auth_code, "credentials.json")
            print("Authentication completed!")
        else:
            print("Already authenticated!")
        
        # Step 2: Create presentation
        print("\nStep 2: Creating presentation...")
        slides = create_sample_slides()
        citations = create_sample_citations()
        
        # Progress callback
        def progress_callback(data):
            print(f"Progress: {data['progress_percent']:.1f}% - {data['message']}")
        
        result = await generator.create_presentation(
            slides=slides,
            title="ML in Academic Research - Demo",
            citations=citations,
            metadata={
                "author": "Dr. Jane Smith",
                "institution": "University of Technology",
                "subject": "Machine Learning",
                "keywords": "machine learning, research, academia"
            },
            progress_callback=progress_callback
        )
        
        print(f"\nPresentation created successfully!")
        print(f"Presentation ID: {result['presentation_id']}")
        print(f"View Link: {result['links']['view']}")
        print(f"Edit Link: {result['links']['edit']}")
        
        # Step 3: Share with collaborators
        print("\nStep 3: Sharing with collaborators...")
        share_result = generator.share_presentation(
            result['presentation_id'],
            "collaborator@example.com",
            PermissionRole.EDITOR,
            "Please review this presentation and provide feedback."
        )
        print(f"Shared with {share_result['email']} as {share_result['role']}")
        
        return result
        
    except Exception as e:
        print(f"Error: {e}")
        return None


async def academic_template_example():
    """Demonstrate academic template usage."""
    print("\n=== Academic Template Example ===")
    
    # Create academic generator with university branding
    generator = create_academic_google_slides_generator(
        client_id=os.getenv("GOOGLE_CLIENT_ID", "your_client_id"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET", "your_client_secret"),
        university_name="University of Technology",
        template_type=GoogleSlidesTemplate.FOCUS,
        theme_color="#003366"  # University blue
    )
    
    try:
        # Authenticate (assuming credentials already exist)
        auth_result = generator.authenticate_user("academic_credentials.json")
        if auth_result != "authenticated":
            print("Please complete authentication first")
            return
        
        # Create academic presentation
        slides = create_sample_slides()
        citations = create_sample_citations()
        
        result = await generator.create_presentation(
            slides=slides,
            title="Research Presentation - Q3 2024",
            citations=citations,
            metadata={
                "author": "Research Team",
                "department": "Computer Science",
                "course": "CS 598 - Advanced Machine Learning",
                "semester": "Fall 2024"
            }
        )
        
        print(f"Academic presentation created: {result['presentation_id']}")
        
        # Make it accessible to university domain
        if generator.sharing_config.allow_public_sharing:
            public_result = generator.make_presentation_public(
                result['presentation_id'],
                PermissionRole.VIEWER
            )
            print(f"Made public: {public_result['links']['view']}")
        
        return result
        
    except Exception as e:
        print(f"Academic template error: {e}")
        return None


async def collaborative_workflow_example():
    """Demonstrate collaborative workflow."""
    print("\n=== Collaborative Workflow Example ===")
    
    # Create collaborative generator
    generator = create_collaborative_google_slides_generator(
        client_id=os.getenv("GOOGLE_CLIENT_ID", "your_client_id"),
        client_secret=os.getenv("GOOGLE_CLIENT_SECRET", "your_client_secret"),
        allow_public_sharing=True
    )
    
    try:
        # Authenticate
        auth_result = generator.authenticate_user("collab_credentials.json")
        if auth_result != "authenticated":
            print("Authentication required for collaborative workflow")
            return
        
        # Create presentation
        slides = create_sample_slides()
        result = await generator.create_presentation(
            slides=slides,
            title="Team Collaboration Demo",
            metadata={
                "project": "ML Research Project",
                "team": "Data Science Team",
                "phase": "Initial Research"
            }
        )
        
        print(f"Collaborative presentation created: {result['presentation_id']}")
        
        # Share with multiple team members
        team_members = [
            ("researcher1@university.edu", PermissionRole.EDITOR),
            ("researcher2@university.edu", PermissionRole.EDITOR),
            ("advisor@university.edu", PermissionRole.COMMENTER),
            ("student@university.edu", PermissionRole.VIEWER)
        ]
        
        for email, role in team_members:
            try:
                share_result = generator.share_presentation(
                    result['presentation_id'],
                    email,
                    role,
                    f"Shared presentation with {role.value} access"
                )
                print(f"Shared with {email} as {role.value}")
            except Exception as e:
                print(f"Failed to share with {email}: {e}")
        
        # Get presentation info
        info = generator.get_presentation_info(result['presentation_id'])
        print(f"Presentation info: {info['slide_count']} slides, {info['title']}")
        
        return result
        
    except Exception as e:
        print(f"Collaborative workflow error: {e}")
        return None


async def batch_processing_example():
    """Demonstrate batch processing capabilities."""
    print("\n=== Batch Processing Example ===")
    
    # Create generator for batch operations
    generator = GoogleSlidesGenerator(
        google_credentials=GoogleCredentials(
            client_id=os.getenv("GOOGLE_CLIENT_ID", "your_client_id"),
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET", "your_client_secret")
        )
    )
    
    try:
        # Authenticate
        auth_result = generator.authenticate_user("batch_credentials.json")
        if auth_result != "authenticated":
            print("Authentication required for batch processing")
            return
        
        # Create multiple presentations
        presentations_data = []
        
        # Different presentation topics
        topics = [
            "Introduction to Deep Learning",
            "Computer Vision Applications", 
            "Natural Language Processing",
            "Reinforcement Learning Basics"
        ]
        
        base_slides = create_sample_slides()[:5]  # Use first 5 slides
        
        for i, topic in enumerate(topics):
            # Customize slides for each topic
            topic_slides = []
            for slide in base_slides:
                if slide.metadata.get('slide_type') == 'title':
                    # Update title slide
                    new_slide = SlideContent(
                        title=topic,
                        subtitle=f"Lecture {i+1} - Academic Series",
                        body=slide.body,
                        metadata=slide.metadata
                    )
                else:
                    new_slide = slide
                topic_slides.append(new_slide)
            
            presentations_data.append({
                'title': f"{topic} - Lecture {i+1}",
                'slides': topic_slides,
                'metadata': {
                    'series': 'ML Academic Series',
                    'lecture_number': i+1,
                    'topic': topic
                }
            })
        
        # Progress tracking for batch
        def batch_progress(data):
            print(f"Batch Progress: {data['message']}")
        
        print(f"Creating {len(presentations_data)} presentations in batch...")
        results = await generator.batch_create_presentations(
            presentations_data,
            progress_callback=batch_progress
        )
        
        # Process results
        successful = [r for r in results if r.get('status') == 'completed']
        failed = [r for r in results if r.get('status') == 'failed']
        
        print(f"\nBatch processing completed:")
        print(f"  Successful: {len(successful)}")
        print(f"  Failed: {len(failed)}")
        
        for result in successful:
            print(f"  ✓ {result['title']}: {result['links']['view']}")
        
        for result in failed:
            print(f"  ✗ {result['title']}: {result.get('error', 'Unknown error')}")
        
        return results
        
    except Exception as e:
        print(f"Batch processing error: {e}")
        return None


async def export_examples():
    """Demonstrate export capabilities."""
    print("\n=== Export Examples ===")
    
    generator = GoogleSlidesGenerator(
        google_credentials=GoogleCredentials(
            client_id=os.getenv("GOOGLE_CLIENT_ID", "your_client_id"),
            client_secret=os.getenv("GOOGLE_CLIENT_SECRET", "your_client_secret")
        )
    )
    
    try:
        # Authenticate
        auth_result = generator.authenticate_user("export_credentials.json")
        if auth_result != "authenticated":
            print("Authentication required for export examples")
            return
        
        # Create a presentation first
        slides = create_sample_slides()
        result = await generator.create_presentation(
            slides=slides,
            title="Export Demo Presentation"
        )
        
        presentation_id = result['presentation_id']
        print(f"Created presentation for export: {presentation_id}")
        
        # Export as PDF
        print("Exporting as PDF...")
        pdf_buffer = generator.export_to_pdf(presentation_id)
        
        with open("exported_presentation.pdf", "wb") as f:
            f.write(pdf_buffer.getvalue())
        print("PDF exported successfully")
        
        # Export as PPTX
        print("Exporting as PPTX...")
        pptx_buffer = generator.export_to_pptx(presentation_id)
        
        with open("exported_presentation.pptx", "wb") as f:
            f.write(pptx_buffer.getvalue())
        print("PPTX exported successfully")
        
        return {
            'presentation_id': presentation_id,
            'pdf_size': len(pdf_buffer.getvalue()),
            'pptx_size': len(pptx_buffer.getvalue())
        }
        
    except Exception as e:
        print(f"Export error: {e}")
        return None


def configuration_examples():
    """Demonstrate different configuration options."""
    print("\n=== Configuration Examples ===")
    
    # 1. Academic Research Configuration
    print("1. Academic Research Configuration:")
    academic_config = {
        'google_credentials': GoogleCredentials(
            client_id="your_client_id",
            client_secret="your_client_secret",
            scopes=[
                "https://www.googleapis.com/auth/presentations",
                "https://www.googleapis.com/auth/drive.file"
            ]
        ),
        'drive_config': DriveConfig(
            folder_name="Research Presentations 2024",
            organize_by_date=True,
            organize_by_topic=True,
            auto_create_folders=True
        ),
        'template_config': TemplateConfig(
            template_type=GoogleSlidesTemplate.SIMPLE_LIGHT,
            theme_color="#003366",
            font_family="Times New Roman",
            university_name="Research University",
            apply_branding=True
        ),
        'sharing_config': SharingConfig(
            default_role=PermissionRole.VIEWER,
            allow_public_sharing=False,
            notify_on_share=True,
            send_notification_email=False
        )
    }
    print("  - Organized by date and topic")
    print("  - Academic branding applied")
    print("  - Restricted sharing")
    
    # 2. Collaborative Team Configuration
    print("\n2. Collaborative Team Configuration:")
    collab_config = {
        'google_credentials': GoogleCredentials(
            client_id="your_client_id",
            client_secret="your_client_secret"
        ),
        'drive_config': DriveConfig(
            folder_name="Team Presentations",
            organize_by_date=False,
            organize_by_topic=False
        ),
        'template_config': TemplateConfig(
            template_type=GoogleSlidesTemplate.MOMENTUM,
            theme_color="#ff6600",
            font_family="Arial"
        ),
        'sharing_config': SharingConfig(
            default_role=PermissionRole.EDITOR,
            allow_public_sharing=True,
            notify_on_share=True,
            send_notification_email=True
        )
    }
    print("  - Flat folder organization")
    print("  - Collaborative editing enabled")
    print("  - Public sharing allowed")
    
    # 3. High-Volume Production Configuration
    print("\n3. High-Volume Production Configuration:")
    production_config = {
        'google_credentials': GoogleCredentials(
            client_id="your_client_id",
            client_secret="your_client_secret"
        ),
        'batch_config': {
            'max_concurrent_requests': 10,
            'retry_attempts': 5,
            'retry_delay': 2.0,
            'batch_size': 25,
            'rate_limit_delay': 0.2
        },
        'template_config': TemplateConfig(
            template_type=GoogleSlidesTemplate.STREAMLINE,
            theme_color="#000000"
        )
    }
    print("  - High concurrency settings")
    print("  - Robust retry mechanisms")
    print("  - Optimized for batch processing")


async def main():
    """Run all examples."""
    print("Google Slides Generator Examples")
    print("=" * 50)
    
    # Check for required environment variables
    if not os.getenv("GOOGLE_CLIENT_ID") or not os.getenv("GOOGLE_CLIENT_SECRET"):
        print("Warning: GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET environment variables not set")
        print("Some examples may not work without proper credentials")
        print()
    
    # Configuration examples (no auth required)
    configuration_examples()
    
    # Interactive examples (require user input)
    run_interactive = input("\nRun interactive examples? (y/n): ").lower().strip() == 'y'
    
    if run_interactive:
        try:
            # Basic usage
            await basic_usage_example()
            
            # Academic template
            await academic_template_example()
            
            # Collaborative workflow
            await collaborative_workflow_example()
            
            # Batch processing
            await batch_processing_example()
            
            # Export examples
            await export_examples()
            
        except KeyboardInterrupt:
            print("\nExamples interrupted by user")
        except Exception as e:
            print(f"Error running examples: {e}")
    
    print("\nAll examples completed!")


if __name__ == "__main__":
    # Set up environment
    import sys
    sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
    
    # Run examples
    asyncio.run(main())