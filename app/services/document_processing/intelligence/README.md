# Document Intelligence Layer

The Document Intelligence Layer provides advanced analysis capabilities for academic documents, offering comprehensive assessment and improvement recommendations through machine learning-based techniques.

## Overview

The intelligence layer consists of several key components:

- **Language Detection**: Automatic language identification with confidence scoring
- **Quality Assessment**: Multi-metric evaluation of document quality
- **Content Gap Analysis**: Identification of missing sections and content
- **Writing Issue Detection**: Academic style and grammar analysis
- **Citation Analysis**: Reference quality and completeness assessment
- **Coherence Analysis**: Document flow and logical structure evaluation
- **Presentation Readiness**: Assessment for slide conversion suitability

## Core Features

### 1. Language Detection with Confidence Scoring

Automatically detects the primary language of documents using pattern-based analysis:

```python
from app.services.document_processing.intelligence import IntelligenceEngine

engine = IntelligenceEngine()
result = await engine.analyze_document(processing_result)

# Language detection results
language_info = result.language_detection
print(f"Primary Language: {language_info.primary_language}")
print(f"Confidence: {language_info.confidence:.2%}")
print(f"Secondary Languages: {language_info.secondary_languages}")
```

**Supported Languages:**
- English (en)
- Spanish (es) 
- French (fr)
- German (de)
- Italian (it)
- Portuguese (pt)
- Chinese (zh)
- Japanese (ja)
- Korean (ko)
- Arabic (ar)
- Russian (ru)

### 2. Content Quality Assessment

Comprehensive quality evaluation using multiple academic metrics:

```python
quality = result.quality_metrics

print(f"Overall Quality: {quality.overall_score}/100 ({quality.quality_level})")
print(f"Readability: {quality.readability_score}/100")
print(f"Coherence: {quality.coherence_score}/100")
print(f"Academic Tone: {quality.academic_tone_score}/100")
print(f"Citation Quality: {quality.citation_quality_score}/100")
```

**Quality Metrics:**
- **Readability Score**: Based on sentence length and complexity
- **Coherence Score**: Transition quality and topic consistency
- **Completeness Score**: Presence of expected academic sections
- **Academic Tone Score**: Formal language and hedging patterns
- **Citation Quality Score**: Reference density and formatting
- **Structure Score**: Logical organization and hierarchy
- **Clarity Score**: Sentence clarity and vocabulary complexity
- **Conciseness Score**: Efficiency and redundancy analysis

**Quality Levels:**
- **Excellent** (90-100%): Publication-ready quality
- **Good** (70-89%): Minor improvements needed
- **Fair** (50-69%): Moderate revisions required
- **Poor** (30-49%): Significant improvements needed
- **Critical** (0-29%): Major restructuring required

### 3. Missing Section Identification

Identifies missing academic sections with importance ratings:

```python
missing_sections = result.missing_sections

for section in missing_sections:
    print(f"Missing: {section.section_type}")
    print(f"Importance: {section.importance}")
    print(f"Recommendation: {section.recommendation}")
    print(f"Expected Content: {section.expected_content}")
```

**Section Types Analyzed:**
- Title page
- Abstract/Executive Summary
- Introduction
- Literature Review
- Methodology/Methods
- Results/Findings
- Discussion/Analysis
- Conclusion
- References/Bibliography
- Acknowledgments
- Appendices

### 4. Content Gap Analysis

Identifies specific content gaps within existing sections:

```python
content_gaps = result.content_gaps

for gap in content_gaps:
    print(f"Section: {gap.section}")
    print(f"Gap: {gap.description}")
    print(f"Priority: {gap.priority}")
    print(f"Suggestion: {gap.suggestion}")
    print(f"Examples: {gap.examples}")
```

**Gap Types:**
- Missing problem statements
- Unclear research objectives
- Insufficient methodology details
- Lack of quantitative results
- Missing limitations discussion
- Absent future work suggestions

### 5. Writing Issue Detection

Identifies and categorizes writing problems:

```python
writing_issues = result.writing_issues

for issue in writing_issues:
    print(f"Type: {issue.issue_type}")
    print(f"Severity: {issue.severity}")
    print(f"Description: {issue.description}")
    print(f"Suggestion: {issue.suggestion}")
```

**Issue Types:**
- **Grammar**: Sentence fragments, run-on sentences
- **Style**: Passive voice overuse, inconsistent terminology
- **Clarity**: Complex vocabulary, unclear expressions
- **Coherence**: Poor transitions, logical gaps
- **Academic Tone**: Informal language, contractions
- **Citation Format**: Inconsistent references
- **Structure**: Poor organization, imbalanced sections
- **Completeness**: Missing required elements

### 6. Citation Quality Analysis

Comprehensive assessment of references and citations:

```python
citation_analysis = result.citation_analysis

print(f"Total Citations: {citation_analysis.total_citations}")
print(f"Unique Sources: {citation_analysis.unique_sources}")
print(f"Citation Density: {citation_analysis.citation_density:.1f} per page")
print(f"Format Consistency: {citation_analysis.format_consistency:.1%}")
print(f"Recency Score: {citation_analysis.recency_score:.1%}")
print(f"Authority Score: {citation_analysis.authority_score:.1%}")
```

**Citation Metrics:**
- Total citation count
- Unique source diversity
- Citation density per page
- Format consistency
- Source recency assessment
- Authority/credibility scoring
- Completeness of bibliographic information

### 7. Coherence and Flow Analysis

Evaluates document coherence and logical progression:

```python
coherence = result.coherence_analysis

print(f"Overall Coherence: {coherence.overall_coherence:.1%}")
print(f"Paragraph Flow: {coherence.paragraph_flow:.1%}")
print(f"Topic Continuity: {coherence.topic_continuity:.1%}")
print(f"Weak Transitions: {len(coherence.weak_transitions)}")
```

**Coherence Metrics:**
- Section-to-section transitions
- Paragraph flow quality
- Logical progression assessment
- Topic continuity analysis
- Transition word usage
- Thematic consistency

### 8. Presentation Readiness Assessment

Evaluates suitability for conversion to presentation format:

```python
presentation = result.presentation_readiness

print(f"Overall Readiness: {presentation.overall_readiness:.1f}/100")
print(f"Visual Elements: {presentation.visual_elements_score:.1f}/100")
print(f"Slide Adaptability: {presentation.slide_adaptability_score:.1f}/100")
print(f"Content Density: {presentation.content_density_score:.1f}/100")
```

**Readiness Metrics:**
- Visual element integration
- Slide structure adaptability
- Content density appropriateness
- Key points identifiability
- Narrative flow suitability
- Structure clarity for presentations

## Usage Examples

### Basic Document Analysis

```python
from app.services.document_processing.intelligence import IntelligenceEngine

# Initialize the engine
engine = IntelligenceEngine()

# Analyze a processed document
result = await engine.analyze_document(processing_result)

# Access different analysis components
print(f"Document Type: {result.document_type}")
print(f"Overall Quality: {result.quality_metrics.overall_score:.1f}/100")
print(f"Missing Sections: {len(result.missing_sections)}")
print(f"Writing Issues: {len(result.writing_issues)}")
```

### Quality-Focused Analysis

```python
# Focus on quality metrics
quality = result.quality_metrics

if quality.quality_level == QualityLevel.EXCELLENT:
    print("Document is publication-ready!")
elif quality.quality_level == QualityLevel.GOOD:
    print("Minor improvements recommended")
elif quality.quality_level == QualityLevel.FAIR:
    print("Moderate revisions needed")
else:
    print("Significant improvements required")

# Identify lowest-scoring metrics
metrics = {
    'Readability': quality.readability_score,
    'Coherence': quality.coherence_score,
    'Academic Tone': quality.academic_tone_score,
    'Citations': quality.citation_quality_score
}

lowest_metric = min(metrics.items(), key=lambda x: x[1])
print(f"Focus improvement on: {lowest_metric[0]} ({lowest_metric[1]:.1f}/100)")
```

### Improvement Recommendations

```python
# Get actionable recommendations
print("Priority Improvements:")
for improvement in result.priority_improvements:
    print(f"• {improvement}")

print("\nQuick Fixes:")
for fix in result.quick_fixes:
    print(f"• {fix}")

print("\nLong-term Suggestions:")
for suggestion in result.long_term_suggestions:
    print(f"• {suggestion}")
```

### Presentation Conversion Assessment

```python
presentation = result.presentation_readiness

if presentation.overall_readiness >= 80:
    print("✅ Ready for presentation conversion")
elif presentation.overall_readiness >= 60:
    print("⚠️ Minor adjustments needed for presentation")
else:
    print("❌ Significant restructuring needed for presentation")

# Get specific slide suggestions
for suggestion in presentation.slide_suggestions:
    print(f"Slide Suggestion: {suggestion['description']} (Priority: {suggestion['priority']})")
```

## Configuration Options

### Quality Thresholds

The engine uses configurable thresholds for quality assessment:

```python
# Default thresholds (can be customized)
quality_thresholds = {
    'readability': {'excellent': 80, 'good': 60, 'fair': 40, 'poor': 20},
    'coherence': {'excellent': 85, 'good': 70, 'fair': 50, 'poor': 30},
    'academic_tone': {'excellent': 90, 'good': 75, 'fair': 55, 'poor': 35},
    'citation_quality': {'excellent': 85, 'good': 70, 'fair': 50, 'poor': 30},
    'completeness': {'excellent': 95, 'good': 80, 'fair': 60, 'poor': 40}
}
```

### Language Models

Language detection can be enhanced with additional patterns:

```python
# Add custom language patterns
engine.language_patterns['custom_language'] = {
    'common_words': {'word1', 'word2', 'word3'},
    'patterns': [r'\bpattern1\b', r'\bpattern2\b'],
    'stopwords': {'stop1', 'stop2', 'stop3'}
}
```

## Integration with Other Services

### Document Processing Pipeline

```python
from app.services.document_processing import DocumentProcessor
from app.services.document_processing.intelligence import IntelligenceEngine

# Process document
processor = DocumentProcessor()
processing_result = await processor.process_document(document_path)

# Analyze with intelligence engine
intelligence_engine = IntelligenceEngine()
intelligence_result = await intelligence_engine.analyze_document(processing_result)

# Use results for recommendations
recommendations = intelligence_result.priority_improvements
```

### Slide Generation Enhancement

```python
from app.services.slides import SlideService

# Use intelligence analysis to improve slide generation
slide_service = SlideService()

# Apply presentation readiness insights
if intelligence_result.presentation_readiness.overall_readiness < 60:
    # Apply content restructuring
    slide_service.enable_content_restructuring()

# Use identified key points
key_points = intelligence_result.presentation_readiness.slide_suggestions
slide_service.incorporate_key_points(key_points)
```

## Performance Considerations

### Analysis Speed

- Basic analysis: ~1-2 seconds for typical documents
- Comprehensive analysis: ~3-5 seconds including ML components
- Large documents (>50 pages): ~10-15 seconds

### Memory Usage

- Typical memory footprint: 50-100MB
- Large documents: Up to 200MB
- Language models: ~20MB additional

### Optimization Tips

1. **Batch Processing**: Process multiple documents together
2. **Selective Analysis**: Skip unnecessary components for speed
3. **Caching**: Cache language detection results
4. **Incremental Updates**: Re-analyze only changed sections

## Testing

### Unit Tests

```bash
# Run intelligence engine tests
python -m pytest app/services/document_processing/intelligence/test_*.py -v
```

### Integration Tests

```bash
# Run full integration tests
python -m pytest tests/integration/test_intelligence_integration.py -v
```

### Performance Tests

```bash
# Run performance benchmarks
python app/services/document_processing/intelligence/benchmark.py
```

## Error Handling

The intelligence engine provides robust error handling:

```python
try:
    result = await engine.analyze_document(processing_result)
except IntelligenceAnalysisError as e:
    logger.error(f"Analysis failed: {e}")
    # Fallback to basic analysis
except InsufficientContentError as e:
    logger.warning(f"Insufficient content: {e}")
    # Return minimal analysis
```

## Extensibility

### Custom Analyzers

Add custom analysis components:

```python
class CustomAnalyzer:
    def analyze(self, processing_result):
        # Custom analysis logic
        return custom_results

# Register custom analyzer
engine.register_analyzer('custom', CustomAnalyzer())
```

### Machine Learning Models

Integrate ML models for enhanced analysis:

```python
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.cluster import KMeans

class MLEnhancedAnalyzer:
    def __init__(self):
        self.vectorizer = TfidfVectorizer()
        self.clustering = KMeans(n_clusters=5)
    
    def analyze_topics(self, text_content):
        # ML-based topic analysis
        features = self.vectorizer.fit_transform([text_content])
        topics = self.clustering.fit_predict(features)
        return topics
```

## API Reference

### IntelligenceEngine

Main class for document intelligence analysis.

#### Methods

- `analyze_document(processing_result, metadata=None)`: Comprehensive analysis
- `detect_language(text_content)`: Language detection only
- `assess_quality(processing_result, text_content)`: Quality metrics only
- `identify_missing_sections(processing_result)`: Section analysis only

### Data Models

#### DocumentIntelligenceResult

Complete analysis result containing all intelligence components.

#### QualityMetrics

Quality assessment scores and overall quality level.

#### LanguageDetectionResult

Language identification with confidence and evidence.

#### WritingIssue

Individual writing problem with severity and suggestions.

#### MissingSection

Missing academic section with importance and recommendations.

#### CitationAnalysis

Citation quality metrics and recommendations.

#### CoherenceAnalysis

Document flow and coherence assessment.

#### PresentationReadiness

Presentation conversion suitability metrics.

## Contributing

To contribute to the intelligence layer:

1. Follow the existing code patterns
2. Add comprehensive tests for new features
3. Update documentation with examples
4. Ensure performance benchmarks pass
5. Add type hints for all public methods

## License

This intelligence layer is part of the SlideGenie project and follows the same licensing terms.