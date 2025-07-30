"""
Comprehensive example usage of the SlideGenie Export Coordinator system.

This example demonstrates:
- Setting up export configurations
- Submitting export jobs
- Tracking progress and handling results
- Managing templates and preferences
- Error handling and fallback strategies
"""

import asyncio
import json
from datetime import datetime
from pathlib import Path
from typing import List

from app.domain.schemas.generation import Citation, SlideContent
from app.services.export.export_coordinator import (
    ExportCoordinator,
    ExportConfig,
    ExportFormat,
    ExportPriority,
    ExportQuality,
    create_export_coordinator
)
from app.services.export.config_manager import (
    ConfigManager,
    ExportPreferences,
    BrandingConfig,
    TypographyConfig,
    create_config_manager
)


def create_sample_slides() -> List[SlideContent]:
    """Create sample slide content for demonstration."""
    return [
        SlideContent(
            title="Machine Learning in Healthcare",
            body=[
                {
                    "type": "text",
                    "content": "Overview of AI applications in medical diagnosis and treatment"
                },
                {
                    "type": "bullet_list",
                    "items": [
                        "Diagnostic imaging analysis",
                        "Drug discovery acceleration",
                        "Personalized treatment plans",
                        "Predictive analytics for patient outcomes"
                    ]
                }
            ],
            layout="title_and_content",
            notes="This slide introduces the main topic and provides an overview"
        ),
        SlideContent(
            title="Deep Learning for Medical Imaging",
            body=[
                {
                    "type": "text",
                    "content": "Convolutional Neural Networks have revolutionized medical image analysis"
                },
                {
                    "type": "image",
                    "src": "/path/to/cnn_architecture.png",
                    "alt": "CNN Architecture for Medical Imaging",
                    "caption": "Figure 1: CNN architecture for radiological image classification"
                },
                {
                    "type": "bullet_list",
                    "items": [
                        "X-ray analysis: 95% accuracy in pneumonia detection",
                        "MRI segmentation: Automated tumor boundary detection",
                        "CT scans: Early stage cancer identification"
                    ]
                }
            ],
            layout="title_and_content",
            notes="Highlight the CNN architecture and key achievements"
        ),
        SlideContent(
            title="Research Results",
            body=[
                {
                    "type": "text",
                    "content": "Performance comparison across different algorithms"
                },
                {
                    "type": "table",
                    "headers": ["Algorithm", "Accuracy", "Precision", "Recall"],
                    "rows": [
                        ["CNN", "95.2%", "94.8%", "95.6%"],
                        ["SVM", "87.3%", "86.9%", "87.8%"],
                        ["Random Forest", "82.1%", "81.7%", "82.5%"],
                        ["Logistic Regression", "78.9%", "78.2%", "79.3%"]
                    ]
                },
                {
                    "type": "chart",
                    "chart_type": "bar",
                    "data": {
                        "labels": ["CNN", "SVM", "Random Forest", "Logistic Regression"],
                        "datasets": [{
                            "label": "Accuracy",
                            "data": [95.2, 87.3, 82.1, 78.9]
                        }]
                    }
                }
            ],
            layout="title_and_content",
            notes="Emphasize CNN's superior performance"
        ),
        SlideContent(
            title="Mathematical Foundation",
            body=[
                {
                    "type": "text",
                    "content": "The convolution operation is fundamental to CNNs:"
                },
                {
                    "type": "equation",
                    "latex": "(f * g)(t) = \\int_{-\\infty}^{\\infty} f(\\tau) g(t - \\tau) d\\tau"
                },
                {
                    "type": "text",
                    "content": "For discrete 2D convolution in image processing:"
                },
                {
                    "type": "equation",
                    "latex": "(I * K)(i,j) = \\sum_{m=0}^{M-1} \\sum_{n=0}^{N-1} I(i+m, j+n) K(m,n)"
                }
            ],
            layout="title_and_content",
            notes="Explain the mathematical basis clearly"
        ),
        SlideContent(
            title="Future Directions",
            body=[
                {
                    "type": "text",
                    "content": "Emerging trends in medical AI"
                },
                {
                    "type": "bullet_list",
                    "items": [
                        "Federated learning for privacy-preserving model training",
                        "Explainable AI for clinical decision support",
                        "Multi-modal fusion combining imaging and genomic data",
                        "Real-time analysis for surgical guidance"
                    ]
                },
                {
                    "type": "text",
                    "content": "Timeline: Expected deployment within 2-5 years"
                }
            ],
            layout="title_and_content",
            notes="Discuss upcoming innovations and timeline"
        ),
        SlideContent(
            title="Conclusion",
            body=[
                {
                    "type": "text",
                    "content": "Key takeaways from our research"
                },
                {
                    "type": "bullet_list",
                    "items": [
                        "CNNs achieve state-of-the-art performance in medical imaging",
                        "Significant potential for improving patient outcomes",
                        "Integration challenges remain but are addressable",
                        "Regulatory approval pathways are becoming clearer"
                    ]
                },
                {
                    "type": "text",
                    "content": "Thank you for your attention!"
                }
            ],
            layout="title_and_content",
            notes="Summarize main points and thank audience"
        )
    ]


def create_sample_citations() -> List[Citation]:
    """Create sample citations for the presentation."""
    return [
        Citation(
            id="lecun2015",
            authors=["LeCun, Y.", "Bengio, Y.", "Hinton, G."],
            title="Deep learning",
            journal="Nature",
            year=2015,
            volume="521",
            pages="436-444",
            doi="10.1038/nature14539"
        ),
        Citation(
            id="esteva2017",
            authors=["Esteva, A.", "Kuprel, B.", "Novoa, R.A."],
            title="Dermatologist-level classification of skin cancer with deep neural networks",
            journal="Nature",
            year=2017,
            volume="542",
            pages="115-118",
            doi="10.1038/nature21056"
        ),
        Citation(
            id="rajpurkar2017",
            authors=["Rajpurkar, P.", "Irvin, J.", "Zhu, K."],
            title="CheXNet: Radiologist-Level Pneumonia Detection on Chest X-Rays with Deep Learning",
            journal="arXiv preprint",
            year=2017,
            arxiv_id="1711.05225"
        )
    ]


async def example_basic_export():
    """Example 1: Basic export to multiple formats."""
    print("=== Example 1: Basic Export ===")
    
    # Create export coordinator
    coordinator = create_export_coordinator(max_concurrent_exports=3)
    
    # Prepare content
    slides = create_sample_slides()
    citations = create_sample_citations()
    
    metadata = {
        "title": "Machine Learning in Healthcare",
        "author": "Dr. Jane Smith",
        "institution": "Medical AI Research Lab",
        "conference": "AI in Medicine Conference 2024"
    }
    
    # Export to PowerPoint
    pptx_config = ExportConfig(
        format=ExportFormat.PPTX,
        template_name="ieee",
        quality=ExportQuality.HIGH,
        priority=ExportPriority.NORMAL,
        branding={
            "university_name": "Stanford University",
            "custom_footer": "AI in Medicine Conference 2024",
            "show_slide_numbers": True
        }
    )
    
    try:
        job_id = await coordinator.submit_export_job(
            slides=slides,
            config=pptx_config,
            citations=citations,
            metadata=metadata,
            user_id="user123"
        )
        
        print(f"PPTX export job submitted: {job_id}")
        
        # Monitor progress
        while True:
            progress = await coordinator.get_job_progress(job_id)
            if not progress:
                break
                
            print(f"Progress: {progress.progress_percent:.1f}% - {progress.current_step}")
            
            if progress.status.value in ["completed", "failed"]:
                break
                
            await asyncio.sleep(1)
        
        # Get result
        result = await coordinator.get_job_result(job_id)
        if result:
            print(f"Export completed: {result.file_path}")
            print(f"File size: {result.file_size} bytes")
            print(f"Validation score: {result.validation_results.get('score', 0)}")
        
    except Exception as e:
        print(f"Export failed: {e}")


async def example_parallel_exports():
    """Example 2: Parallel exports to multiple formats."""
    print("\n=== Example 2: Parallel Exports ===")
    
    coordinator = create_export_coordinator(max_concurrent_exports=5)
    slides = create_sample_slides()
    citations = create_sample_citations()
    
    # Define multiple export configurations
    export_configs = [
        ExportConfig(
            format=ExportFormat.PPTX,
            template_name="ieee",
            quality=ExportQuality.STANDARD
        ),
        ExportConfig(
            format=ExportFormat.BEAMER,
            template_name="berlin",
            quality=ExportQuality.HIGH
        ),
        ExportConfig(
            format=ExportFormat.PDF,
            template_name="standard",
            quality=ExportQuality.STANDARD
        ),
        ExportConfig(
            format=ExportFormat.GOOGLE_SLIDES,
            template_name="academic",
            quality=ExportQuality.STANDARD
        )
    ]
    
    # Submit all jobs
    job_ids = []
    for config in export_configs:
        try:
            job_id = await coordinator.submit_export_job(
                slides=slides,
                config=config,
                citations=citations,
                user_id="user123"
            )
            job_ids.append((job_id, config.format.name))
            print(f"Submitted {config.format.name} export: {job_id}")
        except Exception as e:
            print(f"Failed to submit {config.format.name} export: {e}")
    
    # Monitor all jobs
    completed_jobs = set()
    while len(completed_jobs) < len(job_ids):
        for job_id, format_name in job_ids:
            if job_id in completed_jobs:
                continue
                
            progress = await coordinator.get_job_progress(job_id)
            if progress and progress.status.value in ["completed", "failed"]:
                completed_jobs.add(job_id)
                print(f"{format_name} export completed: {progress.status.value}")
                
                if progress.status.value == "completed":
                    result = await coordinator.get_job_result(job_id)
                    if result:
                        print(f"  File: {result.file_path or result.file_url}")
                        if result.validation_results:
                            score = result.validation_results.get('score', 0)
                            print(f"  Quality score: {score:.1f}/100")
        
        await asyncio.sleep(2)
    
    print("All exports completed!")


async def example_configuration_management():
    """Example 3: Configuration and template management."""
    print("\n=== Example 3: Configuration Management ===")
    
    # Create configuration manager
    config_manager = create_config_manager()
    user_id = "user123"
    
    # Get default user preferences
    preferences = config_manager.get_user_preferences(user_id)
    print(f"Default template for PPTX: {preferences.default_templates['pptx']}")
    
    # Customize branding
    preferences.branding = BrandingConfig(
        university_name="Stanford Medical School",
        logo_position="top_left",
        show_slide_numbers=True,
        custom_footer="Confidential Research",
        color_scheme={
            "primary": "#8C1515",  # Stanford Red
            "secondary": "#B83A4B",
            "accent": "#009639",
            "background": "#FFFFFF",
            "text": "#000000"
        }
    )
    
    # Customize typography
    preferences.typography = TypographyConfig(
        title_font="Helvetica",
        body_font="Arial",
        title_size=48,
        body_size=24,
        line_height=1.3
    )
    
    # Save preferences
    success = config_manager.save_user_preferences(user_id, preferences)
    print(f"Preferences saved: {success}")
    
    # Create a custom template
    custom_template = {
        "theme": "custom_stanford",
        "colors": preferences.branding.color_scheme,
        "fonts": {
            "title": preferences.typography.title_font,
            "body": preferences.typography.body_font
        },
        "layout": {
            "title_alignment": "center",
            "content_alignment": "left"
        }
    }
    
    template_saved = config_manager.save_custom_template(
        user_id=user_id,
        template_name="stanford_medical",
        template_config=custom_template,
        format=ExportFormat.PPTX
    )
    print(f"Custom template saved: {template_saved}")
    
    # Get format-specific configuration
    pptx_config = config_manager.get_format_config(
        user_id=user_id,
        format=ExportFormat.PPTX,
        template_name="stanford_medical"
    )
    print(f"PPTX config for custom template: {json.dumps(pptx_config, indent=2, default=str)[:200]}...")


async def example_error_handling_and_fallbacks():
    """Example 4: Error handling and fallback strategies."""
    print("\n=== Example 4: Error Handling and Fallbacks ===")
    
    coordinator = create_export_coordinator()
    slides = create_sample_slides()
    
    # Configuration with fallback formats
    config = ExportConfig(
        format=ExportFormat.GOOGLE_SLIDES,  # Primary format (might fail)
        template_name="academic",
        quality=ExportQuality.HIGH,
        fallback_formats=[ExportFormat.PPTX, ExportFormat.PDF]  # Fallbacks
    )
    
    try:
        job_id = await coordinator.submit_export_job(
            slides=slides,
            config=config,
            user_id="user123"
        )
        
        print(f"Export job submitted with fallbacks: {job_id}")
        
        # Monitor with error handling
        while True:
            progress = await coordinator.get_job_progress(job_id)
            if not progress:
                print("Job not found")
                break
            
            print(f"Status: {progress.status.value} - {progress.current_step}")
            
            if progress.error_message:
                print(f"Error: {progress.error_message}")
            
            if progress.warnings:
                for warning in progress.warnings:
                    print(f"Warning: {warning}")
            
            if progress.status.value in ["completed", "failed"]:
                break
            
            await asyncio.sleep(1)
        
        # Check final result
        result = await coordinator.get_job_result(job_id)
        if result:
            if result.status.value == "completed":
                print(f"Export successful with format: {result.format.name}")
                print(f"Output: {result.file_path or result.file_url}")
            else:
                print(f"Export failed: {result.status.value}")
    
    except Exception as e:
        print(f"Export submission failed: {e}")


async def example_quality_validation():
    """Example 5: Quality validation and metrics."""
    print("\n=== Example 5: Quality Validation ===")
    
    coordinator = create_export_coordinator()
    slides = create_sample_slides()
    
    # High-quality export with validation
    config = ExportConfig(
        format=ExportFormat.PPTX,
        template_name="ieee",
        quality=ExportQuality.PREMIUM,
        validation_rules=[
            "check_file_integrity",
            "validate_slide_count",
            "check_image_quality",
            "validate_text_readability"
        ]
    )
    
    job_id = await coordinator.submit_export_job(
        slides=slides,
        config=config,
        user_id="user123"
    )
    
    print(f"High-quality export job: {job_id}")
    
    # Wait for completion
    while True:
        progress = await coordinator.get_job_progress(job_id)
        if not progress:
            break
            
        if progress.status.value == "validating":
            print("Performing quality validation...")
        elif progress.status.value in ["completed", "failed"]:
            break
            
        await asyncio.sleep(1)
    
    # Examine validation results
    result = await coordinator.get_job_result(job_id)
    if result and result.validation_results:
        validation = result.validation_results
        print(f"Validation score: {validation.get('score', 0):.1f}/100")
        
        checks = validation.get('checks', {})
        for check_name, check_result in checks.items():
            status = "✓" if check_result else "✗"
            print(f"  {status} {check_name}")
        
        recommendations = validation.get('recommendations', [])
        if recommendations:
            print("Recommendations:")
            for rec in recommendations:
                print(f"  - {rec}")


async def example_batch_export_with_callbacks():
    """Example 6: Batch export with progress callbacks."""
    print("\n=== Example 6: Batch Export with Callbacks ===")
    
    coordinator = create_export_coordinator()
    slides = create_sample_slides()
    
    # Progress tracking
    progress_updates = {}
    
    async def progress_callback(progress):
        job_id = progress.job_id
        progress_updates[job_id] = {
            "status": progress.status.value,
            "percent": progress.progress_percent,
            "step": progress.current_step
        }
        print(f"Job {job_id[:8]}: {progress.progress_percent:.1f}% - {progress.current_step}")
    
    async def completion_callback(job, result):
        print(f"Job {job.job_id[:8]} completed: {result.status.value}")
        if result.file_size:
            print(f"  File size: {result.file_size:,} bytes")
    
    # Submit multiple jobs
    configs = [
        ExportConfig(format=ExportFormat.PPTX, template_name="ieee"),
        ExportConfig(format=ExportFormat.BEAMER, template_name="berlin"),
        ExportConfig(format=ExportFormat.PDF, template_name="standard")
    ]
    
    job_ids = []
    for i, config in enumerate(configs):
        job_id = await coordinator.submit_export_job(
            slides=slides,
            config=config,
            user_id="user123"
        )
        
        # Add callbacks
        coordinator.add_progress_callback(job_id, progress_callback)
        coordinator.add_completion_callback(job_id, completion_callback)
        
        job_ids.append(job_id)
        print(f"Submitted job {i+1}: {job_id[:8]} ({config.format.name})")
    
    # Wait for all jobs to complete
    completed = 0
    while completed < len(job_ids):
        await asyncio.sleep(2)
        
        completed = 0
        for job_id in job_ids:
            progress = await coordinator.get_job_progress(job_id)
            if progress and progress.status.value in ["completed", "failed"]:
                completed += 1
    
    print(f"All {len(job_ids)} jobs completed!")


async def example_statistics_and_monitoring():
    """Example 7: Statistics and system monitoring."""
    print("\n=== Example 7: Statistics and Monitoring ===")
    
    coordinator = create_export_coordinator()
    
    # Get system statistics
    stats = coordinator.get_statistics()
    print("Export Service Statistics:")
    print(f"  Total exports: {stats['total_exports']}")
    print(f"  Successful: {stats['successful_exports']}")
    print(f"  Failed: {stats['failed_exports']}")
    print(f"  Active jobs: {stats['resources']['active_jobs']}")
    print(f"  Available slots: {stats['resources']['available_slots']}")
    
    print("\nExports by format:")
    for format_name, count in stats['exports_by_format'].items():
        print(f"  {format_name.name}: {count}")
    
    # Health check
    health = await coordinator.health_check()
    print(f"\nService health: {health['status']}")
    print(f"Generators available: {health['generators_available']}")
    
    for check_name, check_result in health['checks'].items():
        status = "✓" if check_result == "ok" else "✗"
        print(f"  {status} {check_name}: {check_result}")
    
    # Resource usage
    resource_stats = coordinator.resource_manager.get_resource_stats()
    print(f"\nResource usage:")
    print(f"  Active jobs: {resource_stats['active_jobs']}/{resource_stats['max_concurrent']}")
    
    for format_name, usage in resource_stats['format_usage'].items():
        print(f"  {format_name.name}: {usage} jobs")


async def main():
    """Run all examples."""
    print("SlideGenie Export Coordinator Examples")
    print("=" * 50)
    
    try:
        await example_basic_export()
        await asyncio.sleep(2)
        
        await example_parallel_exports()
        await asyncio.sleep(2)
        
        await example_configuration_management()
        await asyncio.sleep(2)
        
        await example_error_handling_and_fallbacks()
        await asyncio.sleep(2)
        
        await example_quality_validation()
        await asyncio.sleep(2)
        
        await example_batch_export_with_callbacks()
        await asyncio.sleep(2)
        
        await example_statistics_and_monitoring()
        
    except KeyboardInterrupt:
        print("\nExamples interrupted by user")
    except Exception as e:
        print(f"\nUnexpected error: {e}")
    
    print("\nAll examples completed!")


if __name__ == "__main__":
    # Run the examples
    asyncio.run(main())