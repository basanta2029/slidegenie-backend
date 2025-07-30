"""
Example usage of the Document Intelligence Engine.

This module demonstrates how to use the intelligence engine for comprehensive
document analysis including language detection, quality assessment, and 
improvement recommendations.
"""

import asyncio
from uuid import uuid4
from datetime import datetime
from typing import List

from app.domain.schemas.document_processing import (
    ProcessingResult,
    DocumentSection,
    TextElement,
    HeadingElement,
    ReferenceElement,
    CitationElement,
    EquationElement,
    ElementType,
    BoundingBox,
)

from .analyzer import (
    IntelligenceEngine,
    DocumentIntelligenceResult,
    LanguageCode,
    QualityLevel,
    DocumentType
)


def create_sample_research_paper() -> ProcessingResult:
    """Create a sample research paper for demonstration."""
    document_id = uuid4()
    
    # Create comprehensive document elements
    elements = [
        # Title section
        HeadingElement(
            id=uuid4(),
            element_type=ElementType.HEADING,
            text="Machine Learning Applications in Climate Change Prediction: A Comprehensive Study",
            bounding_box=BoundingBox(x=0, y=0, width=100, height=25),
            level=1
        ),
        TextElement(
            id=uuid4(),
            element_type=ElementType.TEXT,
            text="John Smith¹, Maria Garcia², David Johnson¹\n"
                 "¹University of Technology, Department of Computer Science\n"
                 "²Climate Research Institute, Environmental Sciences Division",
            bounding_box=BoundingBox(x=0, y=30, width=100, height=30)
        ),
        
        # Abstract section
        HeadingElement(
            id=uuid4(),
            element_type=ElementType.HEADING,
            text="Abstract",
            bounding_box=BoundingBox(x=0, y=70, width=100, height=20),
            level=2
        ),
        TextElement(
            id=uuid4(),
            element_type=ElementType.TEXT,
            text="Climate change represents one of the most pressing challenges of our time. "
                 "This study investigates the application of advanced machine learning techniques "
                 "for climate prediction modeling. We developed a novel ensemble approach combining "
                 "deep neural networks with traditional statistical methods. Our methodology was "
                 "evaluated using 30 years of climate data from multiple weather stations. "
                 "Results demonstrate a 23% improvement in prediction accuracy compared to existing methods. "
                 "The findings suggest that machine learning can significantly enhance climate forecasting "
                 "capabilities, providing valuable insights for environmental policy making.",
            bounding_box=BoundingBox(x=0, y=95, width=100, height=80)
        ),
        
        # Introduction section
        HeadingElement(
            id=uuid4(),
            element_type=ElementType.HEADING,
            text="1. Introduction",
            bounding_box=BoundingBox(x=0, y=180, width=100, height=20),
            level=2
        ),
        TextElement(
            id=uuid4(),
            element_type=ElementType.TEXT,
            text="Climate change has emerged as one of the most significant global challenges of the 21st century. "
                 "The increasing frequency of extreme weather events and rising global temperatures necessitate "
                 "improved prediction models for effective mitigation strategies. Traditional climate modeling "
                 "approaches, while valuable, face limitations in handling the complex, non-linear relationships "
                 "inherent in climate systems.\n\n"
                 "Machine learning techniques offer promising solutions to these challenges. Recent advances in "
                 "deep learning and ensemble methods have demonstrated remarkable success in various prediction "
                 "tasks. However, their application to climate prediction remains relatively unexplored. "
                 "This research addresses this gap by investigating how modern ML techniques can enhance "
                 "climate prediction accuracy.\n\n"
                 "The primary objectives of this study are: (1) to develop a novel ensemble approach combining "
                 "multiple ML algorithms, (2) to evaluate the performance against traditional methods, and "
                 "(3) to assess the practical implications for climate science applications.",
            bounding_box=BoundingBox(x=0, y=205, width=100, height=120)
        ),
        
        # Literature Review section
        HeadingElement(
            id=uuid4(),
            element_type=ElementType.HEADING,
            text="2. Literature Review",
            bounding_box=BoundingBox(x=0, y=330, width=100, height=20),
            level=2
        ),
        TextElement(
            id=uuid4(),
            element_type=ElementType.TEXT,
            text="Previous research in climate prediction has primarily relied on physical models and statistical approaches. "
                 "Chen et al. (2019) demonstrated the effectiveness of LSTM networks for temperature prediction, "
                 "achieving a mean absolute error of 1.2°C. Similarly, Rodriguez and Kim (2020) applied random forests "
                 "to precipitation forecasting with promising results.\n\n"
                 "Recent studies have explored ensemble methods for climate modeling. The work by Thompson et al. (2021) "
                 "showed that combining multiple algorithms can improve prediction robustness. However, most existing "
                 "approaches focus on single-variable predictions and lack comprehensive evaluation frameworks.",
            bounding_box=BoundingBox(x=0, y=355, width=100, height=80)
        ),
        
        # Add citations
        CitationElement(
            id=uuid4(),
            element_type=ElementType.CITATION,
            text="(Chen et al., 2019)",
            bounding_box=BoundingBox(x=45, y=380, width=25, height=15)
        ),
        CitationElement(
            id=uuid4(),
            element_type=ElementType.CITATION,
            text="(Rodriguez and Kim, 2020)",
            bounding_box=BoundingBox(x=60, y=395, width=35, height=15)
        ),
        
        # Methodology section
        HeadingElement(
            id=uuid4(),
            element_type=ElementType.HEADING,
            text="3. Methodology",
            bounding_box=BoundingBox(x=0, y=440, width=100, height=20),
            level=2
        ),
        TextElement(
            id=uuid4(),
            element_type=ElementType.TEXT,
            text="This study employs a mixed-methods approach combining quantitative analysis with machine learning techniques. "
                 "Data was collected from 150 weather stations across North America, spanning the period from 1990 to 2020. "
                 "The dataset includes temperature, humidity, precipitation, and atmospheric pressure measurements recorded "
                 "at 6-hour intervals.\n\n"
                 "Our proposed ensemble model integrates three distinct algorithms: (1) Long Short-Term Memory (LSTM) networks "
                 "for temporal pattern recognition, (2) Random Forest for handling non-linear relationships, and "
                 "(3) Support Vector Regression for robust prediction under uncertainty. The ensemble combines predictions "
                 "using a weighted averaging scheme optimized through cross-validation.\n\n"
                 "Model performance was evaluated using standard metrics including Mean Absolute Error (MAE), Root Mean "
                 "Square Error (RMSE), and correlation coefficient. Statistical significance was assessed using paired t-tests "
                 "with a significance level of α = 0.05.",
            bounding_box=BoundingBox(x=0, y=465, width=100, height=140)
        ),
        
        # Results section
        HeadingElement(
            id=uuid4(),
            element_type=ElementType.HEADING,
            text="4. Results",
            bounding_box=BoundingBox(x=0, y=610, width=100, height=20),
            level=2
        ),
        TextElement(
            id=uuid4(),
            element_type=ElementType.TEXT,
            text="The ensemble model demonstrated superior performance across all evaluation metrics. "
                 "Temperature prediction achieved a MAE of 0.87°C, representing a 23% improvement over the baseline "
                 "statistical model (MAE = 1.13°C). RMSE values were 1.24°C and 1.67°C for the ensemble and baseline "
                 "models, respectively (p < 0.001).\n\n"
                 "Precipitation forecasting showed similar improvements, with the ensemble model achieving 78% accuracy "
                 "in binary precipitation events compared to 65% for traditional methods. The correlation between "
                 "predicted and observed values was r = 0.89 for temperature and r = 0.72 for precipitation.\n\n"
                 "Regional analysis revealed consistent performance improvements across different climate zones, "
                 "with the largest gains observed in coastal regions (improvement = 28%) and the smallest in "
                 "arid regions (improvement = 15%).",
            bounding_box=BoundingBox(x=0, y=635, width=100, height=120)
        ),
        
        # Discussion section
        HeadingElement(
            id=uuid4(),
            element_type=ElementType.HEADING,
            text="5. Discussion",
            bounding_box=BoundingBox(x=0, y=760, width=100, height=20),
            level=2
        ),
        TextElement(
            id=uuid4(),
            element_type=ElementType.TEXT,
            text="The results demonstrate the significant potential of machine learning approaches for climate prediction. "
                 "The 23% improvement in temperature prediction accuracy has important practical implications for "
                 "agricultural planning, energy management, and disaster preparedness.\n\n"
                 "The ensemble approach proved particularly effective in capturing both short-term variations and "
                 "long-term trends. The LSTM component excelled at identifying temporal patterns, while the Random Forest "
                 "algorithm effectively handled non-linear relationships between variables. The SVM component provided "
                 "robustness against outliers and extreme events.\n\n"
                 "However, several limitations should be acknowledged. The model's performance varied across different "
                 "climate regions, suggesting the need for region-specific adaptations. Additionally, the computational "
                 "requirements are significantly higher than traditional methods, which may limit operational deployment.\n\n"
                 "Future research should explore the integration of satellite data and investigate the model's performance "
                 "for extreme weather event prediction. The development of more efficient algorithms would also enhance "
                 "practical applicability.",
            bounding_box=BoundingBox(x=0, y=785, width=100, height=160)
        ),
        
        # Conclusion section
        HeadingElement(
            id=uuid4(),
            element_type=ElementType.HEADING,
            text="6. Conclusion",
            bounding_box=BoundingBox(x=0, y=950, width=100, height=20),
            level=2
        ),
        TextElement(
            id=uuid4(),
            element_type=ElementType.TEXT,
            text="This study successfully demonstrates the effectiveness of machine learning ensemble methods for "
                 "climate prediction. The proposed approach achieves significant improvements in prediction accuracy "
                 "while maintaining computational feasibility. The findings contribute to the growing body of evidence "
                 "supporting the integration of AI technologies in climate science.\n\n"
                 "The practical implications extend beyond academic research, offering valuable tools for policy makers, "
                 "agricultural planners, and environmental managers. As climate change continues to pose global challenges, "
                 "such technological advances become increasingly crucial for effective adaptation and mitigation strategies.\n\n"
                 "We recommend the continued development and refinement of ML-based climate models, with particular "
                 "attention to regional customization and computational optimization.",
            bounding_box=BoundingBox(x=0, y=975, width=100, height=100)
        ),
        
        # References section
        HeadingElement(
            id=uuid4(),
            element_type=ElementType.HEADING,
            text="References",
            bounding_box=BoundingBox(x=0, y=1080, width=100, height=20),
            level=2
        ),
        ReferenceElement(
            id=uuid4(),
            element_type=ElementType.REFERENCE,
            text="Chen, L., Wang, Y., & Liu, Z. (2019). Deep learning approaches for temperature prediction in climate modeling. "
                 "Journal of Climate Science, 45(3), 234-248.",
            bounding_box=BoundingBox(x=0, y=1105, width=100, height=25)
        ),
        ReferenceElement(
            id=uuid4(),
            element_type=ElementType.REFERENCE,
            text="Rodriguez, M., & Kim, S. (2020). Machine learning applications in precipitation forecasting: A comparative study. "
                 "Environmental Modeling & Software, 128, 104-117.",
            bounding_box=BoundingBox(x=0, y=1135, width=100, height=25)
        ),
        ReferenceElement(
            id=uuid4(),
            element_type=ElementType.REFERENCE,
            text="Thompson, A., Davis, R., & Wilson, K. (2021). Ensemble methods for robust climate prediction modeling. "
                 "Nature Climate Change, 11(8), 667-674.",
            bounding_box=BoundingBox(x=0, y=1165, width=100, height=25)
        )
    ]
    
    # Create logical sections
    sections = [
        DocumentSection(
            id=uuid4(),
            title="Machine Learning Applications in Climate Change Prediction: A Comprehensive Study",
            elements=elements[:2],
            section_type="title"
        ),
        DocumentSection(
            id=uuid4(),
            title="Abstract",
            elements=elements[2:4],
            section_type="abstract"
        ),
        DocumentSection(
            id=uuid4(),
            title="Introduction",
            elements=elements[4:6],
            section_type="introduction"
        ),
        DocumentSection(
            id=uuid4(),
            title="Literature Review",
            elements=elements[6:9],  # Including citations
            section_type="literature_review"
        ),
        DocumentSection(
            id=uuid4(),
            title="Methodology",
            elements=elements[9:11],
            section_type="methodology"
        ),
        DocumentSection(
            id=uuid4(),
            title="Results",
            elements=elements[11:13],
            section_type="results"
        ),
        DocumentSection(
            id=uuid4(),
            title="Discussion",
            elements=elements[13:15],
            section_type="discussion"
        ),
        DocumentSection(
            id=uuid4(),
            title="Conclusion",
            elements=elements[15:17],
            section_type="conclusion"
        ),
        DocumentSection(
            id=uuid4(),
            title="References",
            elements=elements[17:],
            section_type="references"
        )
    ]
    
    return ProcessingResult(
        document_id=document_id,
        filename="climate_ml_research_paper.pdf",
        processing_status="completed",
        elements=elements,
        sections=sections,
        metadata={
            "author": "John Smith, Maria Garcia, David Johnson",
            "title": "Machine Learning Applications in Climate Change Prediction",
            "institution": "University of Technology",
            "year": "2024"
        },
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


def create_incomplete_document() -> ProcessingResult:
    """Create an incomplete document for testing gap analysis."""
    document_id = uuid4()
    
    elements = [
        HeadingElement(
            id=uuid4(),
            element_type=ElementType.HEADING,
            text="Blockchain Technology in Supply Chain Management",
            bounding_box=BoundingBox(x=0, y=0, width=100, height=20),
            level=1
        ),
        TextElement(
            id=uuid4(),
            element_type=ElementType.TEXT,
            text="This paper explores blockchain applications. It's a very interesting topic. "
                 "I think blockchain could revolutionize supply chains. We should definitely look into this more.",
            bounding_box=BoundingBox(x=0, y=25, width=100, height=40)
        ),
        HeadingElement(
            id=uuid4(),
            element_type=ElementType.HEADING,
            text="Some Background",
            bounding_box=BoundingBox(x=0, y=70, width=100, height=20),
            level=2
        ),
        TextElement(
            id=uuid4(),
            element_type=ElementType.TEXT,
            text="Blockchain is pretty cool. It has many uses. Supply chains are complex. "
                 "There are lots of problems. Blockchain might help fix them.",
            bounding_box=BoundingBox(x=0, y=95, width=100, height=40)
        )
    ]
    
    sections = [
        DocumentSection(
            id=uuid4(),
            title="Blockchain Technology in Supply Chain Management",
            elements=elements[:2],
            section_type="title"
        ),
        DocumentSection(
            id=uuid4(),
            title="Some Background",
            elements=elements[2:],
            section_type="introduction"
        )
    ]
    
    return ProcessingResult(
        document_id=document_id,
        filename="incomplete_blockchain_paper.pdf",
        processing_status="completed",
        elements=elements,
        sections=sections,
        metadata={},
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow()
    )


def print_analysis_summary(result: DocumentIntelligenceResult) -> None:
    """Print a comprehensive summary of the intelligence analysis."""
    print("=" * 80)
    print(f"DOCUMENT INTELLIGENCE ANALYSIS REPORT")
    print("=" * 80)
    print(f"Document ID: {result.document_id}")
    print(f"Analysis Time: {result.analysis_timestamp}")
    print(f"Processing Time: {result.processing_time:.2f} seconds")
    print(f"Analysis Confidence: {result.analysis_confidence:.2f}")
    print()
    
    # Basic document info
    print("📄 DOCUMENT OVERVIEW")
    print("-" * 40)
    print(f"Word Count: {result.word_count:,}")
    print(f"Section Count: {result.section_count}")
    print(f"Document Type: {result.document_type.value.replace('_', ' ').title()}")
    print()
    
    # Language analysis
    print("🌍 LANGUAGE ANALYSIS")
    print("-" * 40)
    print(f"Primary Language: {result.language_detection.primary_language.value.upper()}")
    print(f"Confidence: {result.language_detection.confidence:.2%}")
    if result.language_detection.secondary_languages:
        print("Secondary Languages:")
        for lang, conf in result.language_detection.secondary_languages:
            print(f"  - {lang.value.upper()}: {conf:.2%}")
    if result.language_detection.mixed_language_score > 0.2:
        print(f"Mixed Language Score: {result.language_detection.mixed_language_score:.2%}")
    print()
    
    # Quality metrics
    print("⭐ QUALITY ASSESSMENT")
    print("-" * 40)
    print(f"Overall Quality: {result.quality_metrics.overall_score:.1f}/100 ({result.quality_metrics.quality_level.value.upper()})")
    print("Individual Metrics:")
    print(f"  📖 Readability: {result.quality_metrics.readability_score:.1f}/100")
    print(f"  🔗 Coherence: {result.quality_metrics.coherence_score:.1f}/100")
    print(f"  ✅ Completeness: {result.quality_metrics.completeness_score:.1f}/100")
    print(f"  🎓 Academic Tone: {result.quality_metrics.academic_tone_score:.1f}/100")
    print(f"  📚 Citation Quality: {result.quality_metrics.citation_quality_score:.1f}/100")
    print(f"  🏗️ Structure: {result.quality_metrics.structure_score:.1f}/100")
    print(f"  💡 Clarity: {result.quality_metrics.clarity_score:.1f}/100")
    print(f"  ✂️ Conciseness: {result.quality_metrics.conciseness_score:.1f}/100")
    print()
    
    # Missing sections
    if result.missing_sections:
        print("❌ MISSING SECTIONS")
        print("-" * 40)
        for section in result.missing_sections:
            importance_icon = "🔴" if section.importance == "required" else "🟡" if section.importance == "recommended" else "⚪"
            print(f"{importance_icon} {section.section_type.value.replace('_', ' ').title()} ({section.importance})")
            print(f"   {section.description}")
            print(f"   💡 {section.recommendation}")
            print()
    
    # Content gaps
    if result.content_gaps:
        print("🕳️ CONTENT GAPS")
        print("-" * 40)
        for gap in result.content_gaps[:5]:  # Show top 5
            priority_icon = "🔥" if gap.priority == "high" else "🟡" if gap.priority == "medium" else "🔵"
            print(f"{priority_icon} {gap.description} ({gap.priority} priority)")
            print(f"   💡 {gap.suggestion}")
            if gap.examples:
                print(f"   📝 Examples: {'; '.join(gap.examples[:2])}")
            print()
    
    # Writing issues
    if result.writing_issues:
        print("✏️ WRITING ISSUES")
        print("-" * 40)
        issue_counts = {}
        for issue in result.writing_issues:
            issue_type = issue.issue_type.value.replace('_', ' ').title()
            if issue_type not in issue_counts:
                issue_counts[issue_type] = []
            issue_counts[issue_type].append(issue)
        
        for issue_type, issues in issue_counts.items():
            severity_icon = "🔴" if any(i.severity == "critical" for i in issues) else \
                          "🟠" if any(i.severity == "high" for i in issues) else \
                          "🟡" if any(i.severity == "medium" for i in issues) else "🔵"
            print(f"{severity_icon} {issue_type}: {len(issues)} issue(s)")
            
            # Show most severe issue
            most_severe = max(issues, key=lambda x: {"critical": 4, "high": 3, "medium": 2, "low": 1}[x.severity])
            print(f"   {most_severe.description}")
            print(f"   💡 {most_severe.suggestion}")
            print()
    
    # Citation analysis
    print("📚 CITATION ANALYSIS")
    print("-" * 40)
    print(f"Total Citations: {result.citation_analysis.total_citations}")
    print(f"Unique Sources: {result.citation_analysis.unique_sources}")
    print(f"Citation Density: {result.citation_analysis.citation_density:.1f} per page")
    print(f"Format Consistency: {result.citation_analysis.format_consistency:.1%}")
    print(f"Recency Score: {result.citation_analysis.recency_score:.1%}")
    print(f"Authority Score: {result.citation_analysis.authority_score:.1%}")
    print(f"Completeness Score: {result.citation_analysis.completeness_score:.1%}")
    if result.citation_analysis.issues:
        print("Issues:")
        for issue in result.citation_analysis.issues:
            print(f"  ⚠️ {issue}")
    print()
    
    # Coherence analysis
    print("🔗 COHERENCE ANALYSIS")
    print("-" * 40)
    print(f"Overall Coherence: {result.coherence_analysis.overall_coherence:.1%}")
    print(f"Paragraph Flow: {result.coherence_analysis.paragraph_flow:.1%}")
    print(f"Logical Progression: {result.coherence_analysis.logical_progression:.1%}")
    print(f"Topic Continuity: {result.coherence_analysis.topic_continuity:.1%}")
    if result.coherence_analysis.weak_transitions:
        print("Weak Transitions:")
        for transition in result.coherence_analysis.weak_transitions[:3]:
            print(f"  ⚠️ {transition['transition']}: {transition['score']:.1%}")
    print()
    
    # Presentation readiness
    print("🎯 PRESENTATION READINESS")
    print("-" * 40)
    print(f"Overall Readiness: {result.presentation_readiness.overall_readiness:.1f}/100")
    print("Component Scores:")
    print(f"  🖼️ Visual Elements: {result.presentation_readiness.visual_elements_score:.1f}/100")
    print(f"  📊 Slide Adaptability: {result.presentation_readiness.slide_adaptability_score:.1f}/100")
    print(f"  📝 Content Density: {result.presentation_readiness.content_density_score:.1f}/100")
    print(f"  🏗️ Structure Clarity: {result.presentation_readiness.structure_clarity_score:.1f}/100")
    print(f"  💎 Key Points: {result.presentation_readiness.key_points_identifiable:.1f}/100")
    print(f"  📈 Narrative Flow: {result.presentation_readiness.narrative_flow_score:.1f}/100")
    print()
    
    # Recommendations
    print("🎯 PRIORITY IMPROVEMENTS")
    print("-" * 40)
    for i, improvement in enumerate(result.priority_improvements, 1):
        print(f"{i}. {improvement}")
    print()
    
    if result.quick_fixes:
        print("⚡ QUICK FIXES")
        print("-" * 40)
        for i, fix in enumerate(result.quick_fixes, 1):
            print(f"{i}. {fix}")
        print()
    
    if result.long_term_suggestions:
        print("🚀 LONG-TERM SUGGESTIONS")
        print("-" * 40)
        for i, suggestion in enumerate(result.long_term_suggestions, 1):
            print(f"{i}. {suggestion}")
        print()
    
    print("=" * 80)


async def demonstrate_intelligence_analysis():
    """Demonstrate the intelligence engine with different document types."""
    engine = IntelligenceEngine()
    
    print("🧠 DOCUMENT INTELLIGENCE ENGINE DEMONSTRATION")
    print("=" * 80)
    print()
    
    # Analyze a comprehensive research paper
    print("📄 Analyzing comprehensive research paper...")
    comprehensive_doc = create_sample_research_paper()
    comprehensive_result = await engine.analyze_document(comprehensive_doc)
    print_analysis_summary(comprehensive_result)
    
    print("\n" + "="*80 + "\n")
    
    # Analyze an incomplete document
    print("📄 Analyzing incomplete document...")
    incomplete_doc = create_incomplete_document()
    incomplete_result = await engine.analyze_document(incomplete_doc)
    print_analysis_summary(incomplete_result)
    
    # Comparison summary
    print("\n" + "="*80)
    print("📊 COMPARISON SUMMARY")
    print("="*80)
    print(f"Comprehensive Document:")
    print(f"  Quality Score: {comprehensive_result.quality_metrics.overall_score:.1f}/100")
    print(f"  Missing Sections: {len(comprehensive_result.missing_sections)}")
    print(f"  Writing Issues: {len(comprehensive_result.writing_issues)}")
    print(f"  Presentation Readiness: {comprehensive_result.presentation_readiness.overall_readiness:.1f}/100")
    print()
    print(f"Incomplete Document:")
    print(f"  Quality Score: {incomplete_result.quality_metrics.overall_score:.1f}/100")
    print(f"  Missing Sections: {len(incomplete_result.missing_sections)}")
    print(f"  Writing Issues: {len(incomplete_result.writing_issues)}")
    print(f"  Presentation Readiness: {incomplete_result.presentation_readiness.overall_readiness:.1f}/100")
    print()
    
    improvement = comprehensive_result.quality_metrics.overall_score - incomplete_result.quality_metrics.overall_score
    print(f"Quality Improvement: {improvement:.1f} points ({improvement/incomplete_result.quality_metrics.overall_score:.1%})")
    print("="*80)


async def demonstrate_specific_features():
    """Demonstrate specific intelligence engine features."""
    engine = IntelligenceEngine()
    
    print("\n🔬 FEATURE-SPECIFIC DEMONSTRATIONS")
    print("=" * 80)
    
    # Language detection
    print("\n🌍 Language Detection Demo:")
    test_texts = [
        ("This is a comprehensive analysis of machine learning algorithms.", "English"),
        ("Esta es una investigación sobre inteligencia artificial.", "Spanish"),
        ("Cette recherche examine les applications de l'apprentissage automatique.", "French"),
        ("Diese Studie untersucht maschinelle Lernverfahren.", "German"),
        ("Too short", "Insufficient"),
    ]
    
    for text, expected in test_texts:
        result = await engine._detect_language(text)
        print(f"Text: '{text[:50]}...'")
        print(f"Detected: {result.primary_language.value} (confidence: {result.confidence:.2%})")
        print(f"Expected: {expected}")
        print()
    
    # Quality scoring
    print("\n⭐ Quality Scoring Demo:")
    quality_texts = [
        ("This research demonstrates significant improvements in algorithmic performance. "
         "However, further investigation is required to validate these findings. "
         "The methodology follows established protocols for experimental design.", "High Quality"),
        ("I think this is pretty good stuff. It's very nice and works well. "
         "We should definitely use this approach because it's awesome.", "Low Quality")
    ]
    
    for text, expected in quality_texts:
        academic_score = engine._calculate_academic_tone_score(text)
        readability_score = engine._calculate_readability_score(text)
        print(f"Text: '{text[:50]}...'")
        print(f"Academic Tone: {academic_score:.1f}/100")
        print(f"Readability: {readability_score:.1f}/100")
        print(f"Expected: {expected}")
        print()
    
    print("=" * 80)


if __name__ == "__main__":
    # Run demonstrations
    asyncio.run(demonstrate_intelligence_analysis())
    asyncio.run(demonstrate_specific_features())