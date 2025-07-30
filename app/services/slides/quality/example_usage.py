"""
Example usage of the SlideGenie Quality Assurance System.

This script demonstrates how to use the quality checking system
to assess presentation quality and generate reports.
"""
from datetime import datetime
from uuid import uuid4

from app.domain.schemas.presentation import PresentationResponse, SlideResponse
from app.domain.schemas.generation import Citation
from . import create_quality_assurance_system, QualityMetricsCalculator


def create_sample_presentation() -> PresentationResponse:
    """Create a sample presentation for testing."""
    return PresentationResponse(
        id=uuid4(),
        owner_id=uuid4(),
        title="Machine Learning in Healthcare: A Comprehensive Review",
        subtitle="Recent Advances and Future Directions",
        description="Overview of ML applications in healthcare",
        abstract="This presentation reviews recent advances in machine learning applications for healthcare...",
        presentation_type="conference",
        academic_level="research",
        field_of_study="Computer Science",
        keywords=["machine learning", "healthcare", "AI", "medical diagnosis"],
        duration_minutes=20,
        status="draft",
        slide_count=15,
        view_count=0,
        is_public=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


def create_sample_slides() -> list[SlideResponse]:
    """Create sample slides for testing."""
    slides = []
    
    # Title slide
    slides.append(SlideResponse(
        id=uuid4(),
        presentation_id=uuid4(),
        slide_number=1,
        title="Machine Learning in Healthcare: A Comprehensive Review",
        content={
            "subtitle": "Recent Advances and Future Directions",
            "body": [
                {"type": "text", "content": "Dr. Jane Smith, PhD\nUniversity Medical Center\nConference on AI in Medicine 2024"}
            ],
            "layout": "title"
        },
        layout_type="title",
        contains_equations=False,
        contains_code=False,
        contains_citations=False,
        figure_count=0,
        is_hidden=False,
        is_backup=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    ))
    
    # Introduction slide
    slides.append(SlideResponse(
        id=uuid4(),
        presentation_id=uuid4(),
        slide_number=2,
        title="Introduction",
        content={
            "body": [
                {
                    "type": "bullet_list",
                    "items": [
                        "Healthcare generates massive amounts of data daily",
                        "Machine learning offers powerful tools for analysis",
                        "Growing need for automated diagnostic systems",
                        "Potential to improve patient outcomes significantly"
                    ]
                },
                {
                    "type": "citation",
                    "keys": ["Smith2023", "Jones2024"]
                }
            ],
            "layout": "content"
        },
        layout_type="content",
        contains_equations=False,
        contains_code=False,
        contains_citations=True,
        figure_count=0,
        is_hidden=False,
        is_backup=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    ))
    
    # Methods slide with issues
    slides.append(SlideResponse(
        id=uuid4(),
        presentation_id=uuid4(),
        slide_number=3,
        title="Methodology",
        content={
            "body": [
                {
                    "type": "text",
                    "content": "We conducted a comprehensive systematic review of the literature published between 2020 and 2024, focusing specifically on machine learning applications in healthcare settings, with particular emphasis on diagnostic accuracy, treatment optimization, and patient outcome prediction, utilizing multiple databases including PubMed, IEEE Xplore, and ACM Digital Library, while applying strict inclusion and exclusion criteria to ensure the quality and relevance of the selected studies."
                }
            ],
            "layout": "content"
        },
        layout_type="content",
        contains_equations=False,
        contains_code=False,
        contains_citations=False,  # Missing citation - quality issue
        figure_count=0,
        is_hidden=False,
        is_backup=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    ))
    
    # Results slide
    slides.append(SlideResponse(
        id=uuid4(),
        presentation_id=uuid4(),
        slide_number=4,
        title="Key Findings",
        content={
            "body": [
                {
                    "type": "bullet_list",
                    "items": [
                        "Deep learning models achieve 95% accuracy in medical imaging",
                        "Natural language processing improves clinical documentation",
                        "Predictive models reduce hospital readmissions by 30%"
                    ]
                },
                {
                    "type": "figure",
                    "url": "results_chart.png",
                    "caption": "Performance comparison of ML models"
                }
            ],
            "layout": "content"
        },
        layout_type="content",
        contains_equations=False,
        contains_code=False,
        contains_citations=False,
        figure_count=1,
        is_hidden=False,
        is_backup=False,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    ))
    
    return slides


def create_sample_references() -> list[Citation]:
    """Create sample citations."""
    return [
        Citation(
            key="Smith2023",
            authors=["Smith, John", "Doe, Jane"],
            title="Machine Learning Applications in Clinical Diagnosis",
            year=2023,
            venue="Journal of Medical AI",
            doi="10.1234/jmai.2023.001",
            bibtex_type="article"
        ),
        Citation(
            key="Jones2024", 
            authors=["Jones, Alice", "Brown, Bob"],
            title="Deep Learning for Healthcare: A Survey",
            year=2024,
            venue="Proceedings of AAAI",
            bibtex_type="inproceedings"
        )
    ]


def run_quality_assessment_example():
    """Run a complete quality assessment example."""
    print("SlideGenie Quality Assurance System - Example Usage")
    print("=" * 60)
    
    # Create sample data
    presentation = create_sample_presentation()
    slides = create_sample_slides()
    references = create_sample_references()
    
    # Initialize quality assurance system
    qa_system = create_quality_assurance_system()
    metrics_calculator = QualityMetricsCalculator(qa_system)
    
    # Run quality assessment
    print("\n1. Running quality analysis...")
    report = metrics_calculator.calculate_metrics(
        presentation=presentation,
        slides=slides,
        references=references
    )
    
    # Display results
    print(f"\n2. Quality Assessment Results")
    print(f"   Overall Score: {report.metrics.overall_score:.2f}")
    print(f"   Quality Level: {report.metrics.quality_level.value}")
    print(f"   Critical Issues: {report.metrics.critical_issues_count}")
    print(f"   Major Issues: {report.metrics.major_issues_count}")
    
    # Show dimension scores
    print(f"\n3. Dimension Scores:")
    for dimension, score in report.metrics.dimension_scores.items():
        print(f"   {dimension.value}: {score:.2f}")
    
    # Show issues
    print(f"\n4. Quality Issues Found:")
    for i, issue in enumerate(report.metrics.issues[:5], 1):  # Show first 5 issues
        print(f"   {i}. [{issue.severity.upper()}] {issue.description}")
        if issue.slide_number:
            print(f"      Slide: {issue.slide_number}")
        print(f"      Suggestion: {issue.suggestion}")
    
    # Show strengths
    if report.metrics.strengths:
        print(f"\n5. Identified Strengths:")
        for strength in report.metrics.strengths:
            print(f"   • {strength}")
    
    # Show recommendations
    if report.recommendations:
        print(f"\n6. Recommendations:")
        for rec in report.recommendations:
            print(f"   • {rec}")
    
    # Generate insights
    print(f"\n7. Quality Insights:")
    insights = metrics_calculator.generate_quality_insights(presentation.id)
    if 'summary' in insights:
        print(f"   Summary: {insights['summary']}")
    
    if 'priority_actions' in insights:
        print(f"   Priority Actions:")
        for action in insights['priority_actions'][:3]:
            print(f"   • {action['action']} (Est. {action['estimated_time']} min)")
    
    print(f"\n8. Estimated Revision Time: {report.estimated_revision_time} minutes")
    
    print("\n" + "=" * 60)
    print("Quality assessment complete!")


if __name__ == "__main__":
    run_quality_assessment_example()