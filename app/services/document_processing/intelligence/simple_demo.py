"""
Simple demonstration of the Intelligence Engine core functionality.

This simplified demo shows the key features without requiring all dependencies.
"""

import asyncio
import re
import statistics
from collections import Counter, defaultdict
from datetime import datetime
from uuid import uuid4

# Simplified implementations to demonstrate core functionality
class MockLogger:
    def info(self, msg, **kwargs): print(f"INFO: {msg}")
    def error(self, msg, **kwargs): print(f"ERROR: {msg}")

class SimpleBoundingBox:
    def __init__(self, x, y, width, height):
        self.x, self.y, self.width, self.height = x, y, width, height

class SimpleElement:
    def __init__(self, id, element_type, text, bounding_box):
        self.id = id
        self.element_type = element_type
        self.text = text
        self.bounding_box = bounding_box

class SimpleSection:
    def __init__(self, id, title, elements):
        self.id = id
        self.title = title
        self.elements = elements

class SimpleProcessingResult:
    def __init__(self, document_id, elements, sections):
        self.document_id = document_id
        self.elements = elements
        self.sections = sections

# Core intelligence functions (simplified)
class SimpleIntelligenceEngine:
    def __init__(self):
        self.language_patterns = {
            'english': {'common_words': {'the', 'and', 'of', 'to', 'a', 'in', 'is', 'it', 'you', 'that'}},
            'spanish': {'common_words': {'el', 'de', 'que', 'y', 'a', 'en', 'un', 'es', 'se', 'no'}},
            'french': {'common_words': {'le', 'de', 'et', 'à', 'un', 'il', 'être', 'et', 'en', 'avoir'}}
        }
        
        self.academic_patterns = {
            'formal_connectors': [r'\b(?:however|therefore|furthermore|moreover|nevertheless)\b'],
            'weak_language': [r'\b(?:very|really|quite|I think|I believe)\b'],
            'contractions': [r"\b\w+'\w+\b"]
        }
        
    def detect_language(self, text):
        """Detect primary language with confidence scoring."""
        if not text or len(text.strip()) < 50:
            return {'language': 'unknown', 'confidence': 0.0, 'evidence': ['Insufficient text']}
        
        clean_text = re.sub(r'[^\w\s]', ' ', text.lower())
        words = clean_text.split()
        total_words = len(words)
        
        language_scores = {}
        for lang, patterns in self.language_patterns.items():
            common_matches = sum(1 for word in words if word in patterns['common_words'])
            score = common_matches / total_words if total_words > 0 else 0
            language_scores[lang] = score
        
        primary_language = max(language_scores.items(), key=lambda x: x[1]) if language_scores else ('unknown', 0)
        
        return {
            'language': primary_language[0],
            'confidence': primary_language[1],
            'evidence': [f"Strong {primary_language[0]} indicators"] if primary_language[1] > 0.1 else ['Weak indicators']
        }
    
    def assess_academic_tone(self, text):
        """Assess academic writing tone."""
        if not text:
            return 0.0
        
        text_lower = text.lower()
        word_count = len(text.split())
        
        # Positive indicators
        formal_count = sum(len(re.findall(pattern, text_lower)) for pattern in self.academic_patterns['formal_connectors'])
        
        # Negative indicators  
        weak_count = sum(len(re.findall(pattern, text_lower)) for pattern in self.academic_patterns['weak_language'])
        contraction_count = len(re.findall(self.academic_patterns['contractions'][0], text))
        
        positive_score = (formal_count / word_count) * 100 if word_count > 0 else 0
        negative_score = ((weak_count + contraction_count) / word_count) * 50 if word_count > 0 else 0
        
        tone_score = max(0, min(100, positive_score - negative_score + 50))  # Base 50
        return tone_score
    
    def calculate_readability(self, text):
        """Calculate readability score."""
        if not text or len(text.strip()) < 100:
            return 0.0
        
        sentences = re.split(r'[.!?]+', text)
        sentences = [s.strip() for s in sentences if s.strip()]
        words = text.split()
        
        if not sentences or not words:
            return 0.0
        
        avg_sentence_length = len(words) / len(sentences)
        
        # Academic readability (adjusted for academic content)
        if 15 <= avg_sentence_length <= 25:  # Ideal range
            readability_score = 85
        elif 10 <= avg_sentence_length < 15 or 25 < avg_sentence_length <= 35:
            readability_score = 70
        else:
            readability_score = max(20, 85 - abs(avg_sentence_length - 20) * 2)
        
        return readability_score
    
    def identify_missing_sections(self, sections):
        """Identify missing academic sections."""
        section_keywords = {
            'abstract': ['abstract', 'summary'],
            'introduction': ['introduction', 'background'],
            'methodology': ['methodology', 'methods', 'approach'],
            'results': ['results', 'findings'],
            'discussion': ['discussion', 'analysis'],
            'conclusion': ['conclusion', 'conclusions'],
            'references': ['references', 'bibliography']
        }
        
        present_sections = set()
        for section in sections:
            title_lower = (section.title or '').lower()
            for section_type, keywords in section_keywords.items():
                if any(keyword in title_lower for keyword in keywords):
                    present_sections.add(section_type)
                    break
        
        required_sections = {'introduction', 'conclusion'}
        recommended_sections = {'abstract', 'methodology', 'results', 'discussion', 'references'}
        
        missing = []
        for section in required_sections:
            if section not in present_sections:
                missing.append({'section': section, 'importance': 'required'})
        
        for section in recommended_sections:
            if section not in present_sections:
                missing.append({'section': section, 'importance': 'recommended'})
        
        return missing
    
    def identify_writing_issues(self, text):
        """Identify common writing issues."""
        issues = []
        
        # Check for contractions
        contractions = re.findall(r"\b\w+'\w+\b", text)
        if contractions:
            issues.append({
                'type': 'academic_tone',
                'severity': 'medium',
                'description': f'Found {len(contractions)} contractions',
                'suggestion': 'Expand contractions for formal writing'
            })
        
        # Check for weak language
        weak_patterns = self.academic_patterns['weak_language']
        weak_count = sum(len(re.findall(pattern, text.lower())) for pattern in weak_patterns)
        if weak_count > 0:
            issues.append({
                'type': 'academic_tone', 
                'severity': 'low',
                'description': f'Found {weak_count} instances of weak language',
                'suggestion': 'Use more precise, academic terminology'
            })
        
        # Check sentence length
        sentences = re.split(r'[.!?]+', text)
        long_sentences = [s for s in sentences if len(s.split()) > 40]
        if long_sentences:
            issues.append({
                'type': 'clarity',
                'severity': 'medium', 
                'description': f'Found {len(long_sentences)} very long sentences',
                'suggestion': 'Break long sentences into shorter, clearer ones'
            })
        
        return issues
    
    def assess_presentation_readiness(self, processing_result):
        """Assess readiness for presentation conversion."""
        sections = processing_result.sections
        elements = processing_result.elements
        
        # Structure score
        section_count = len(sections)
        if 5 <= section_count <= 15:
            structure_score = 100
        else:
            structure_score = max(20, 100 - abs(section_count - 10) * 5)
        
        # Content density
        total_words = sum(len(elem.text.split()) for elem in elements)
        words_per_section = total_words / max(section_count, 1)
        
        if 100 <= words_per_section <= 300:
            density_score = 100
        else:
            density_score = max(20, 100 - abs(words_per_section - 200) / 10)
        
        # Visual elements (simplified)
        visual_score = 40  # Baseline score
        
        overall_readiness = (structure_score * 0.4 + density_score * 0.4 + visual_score * 0.2)
        
        return {
            'overall_readiness': overall_readiness,
            'structure_score': structure_score,
            'density_score': density_score,
            'visual_score': visual_score,
            'recommendations': []
        }


def create_sample_document():
    """Create a sample document for testing."""
    elements = [
        SimpleElement(uuid4(), 'heading', 'Machine Learning in Healthcare: A Comprehensive Study', SimpleBoundingBox(0, 0, 100, 20)),
        SimpleElement(uuid4(), 'text', 
            "This research examines the application of machine learning techniques in healthcare settings. "
            "The study demonstrates significant improvements in diagnostic accuracy. However, there are "
            "several challenges that need to be addressed. Therefore, we propose a novel approach.", 
            SimpleBoundingBox(0, 25, 100, 60)),
        SimpleElement(uuid4(), 'heading', 'Introduction', SimpleBoundingBox(0, 90, 100, 20)),
        SimpleElement(uuid4(), 'text',
            "Healthcare systems worldwide face unprecedented challenges. Machine learning offers promising "
            "solutions to these problems. This study aims to evaluate the effectiveness of ML algorithms "
            "in clinical diagnosis. The research addresses the gap between theoretical capabilities and "
            "practical applications.",
            SimpleBoundingBox(0, 115, 100, 60)),
        SimpleElement(uuid4(), 'heading', 'Methodology', SimpleBoundingBox(0, 180, 100, 20)),
        SimpleElement(uuid4(), 'text',
            "We conducted experiments using a dataset of 10,000 patient records. The data was preprocessed "
            "using standard techniques. Statistical analysis was performed using established protocols. "
            "The methodology follows rigorous experimental design principles.",
            SimpleBoundingBox(0, 205, 100, 60))
    ]
    
    sections = [
        SimpleSection(uuid4(), 'Machine Learning in Healthcare: A Comprehensive Study', elements[:2]),
        SimpleSection(uuid4(), 'Introduction', elements[2:4]),
        SimpleSection(uuid4(), 'Methodology', elements[4:])
    ]
    
    return SimpleProcessingResult(uuid4(), elements, sections)


def create_poor_quality_document():
    """Create a document with quality issues for comparison."""
    elements = [
        SimpleElement(uuid4(), 'text',
            "I think AI is pretty cool and it's gonna change everything. It's very interesting "
            "and I really believe it'll make things better. We should definitely use it more "
            "because it's awesome and works really well.",
            SimpleBoundingBox(0, 0, 100, 40)),
        SimpleElement(uuid4(), 'text',
            "There are lots of applications and they're all super useful. AI can do many things "
            "and it's getting better all the time. I'm sure it'll revolutionize everything "
            "and make our lives much easier.",
            SimpleBoundingBox(0, 45, 100, 40))
    ]
    
    sections = [
        SimpleSection(uuid4(), 'AI Discussion', elements)
    ]
    
    return SimpleProcessingResult(uuid4(), elements, sections)


def demonstrate_intelligence_features():
    """Demonstrate the intelligence engine features."""
    engine = SimpleIntelligenceEngine()
    
    print("🧠 DOCUMENT INTELLIGENCE ENGINE DEMONSTRATION")
    print("=" * 80)
    
    # Test documents
    good_doc = create_sample_document()
    poor_doc = create_poor_quality_document()
    
    # Extract text content
    good_text = ' '.join(elem.text for elem in good_doc.elements)
    poor_text = ' '.join(elem.text for elem in poor_doc.elements)
    
    print("\n1. LANGUAGE DETECTION")
    print("-" * 40)
    
    lang_result_good = engine.detect_language(good_text)
    lang_result_poor = engine.detect_language(poor_text)
    
    print(f"Good Document: {lang_result_good['language']} (confidence: {lang_result_good['confidence']:.2%})")
    print(f"Poor Document: {lang_result_poor['language']} (confidence: {lang_result_poor['confidence']:.2%})")
    
    print("\n2. ACADEMIC TONE ASSESSMENT")
    print("-" * 40)
    
    tone_good = engine.assess_academic_tone(good_text)
    tone_poor = engine.assess_academic_tone(poor_text)
    
    print(f"Good Document Academic Tone: {tone_good:.1f}/100")
    print(f"Poor Document Academic Tone: {tone_poor:.1f}/100")
    print(f"Improvement: {tone_good - tone_poor:.1f} points")
    
    print("\n3. READABILITY ANALYSIS")
    print("-" * 40)
    
    read_good = engine.calculate_readability(good_text)
    read_poor = engine.calculate_readability(poor_text)
    
    print(f"Good Document Readability: {read_good:.1f}/100")
    print(f"Poor Document Readability: {read_poor:.1f}/100")
    
    print("\n4. MISSING SECTIONS ANALYSIS")
    print("-" * 40)
    
    missing_good = engine.identify_missing_sections(good_doc.sections)
    missing_poor = engine.identify_missing_sections(poor_doc.sections)
    
    print("Good Document Missing Sections:")
    for section in missing_good:
        print(f"  - {section['section'].title()} ({section['importance']})")
    
    print("Poor Document Missing Sections:")
    for section in missing_poor:
        print(f"  - {section['section'].title()} ({section['importance']})")
    
    print("\n5. WRITING ISSUES IDENTIFICATION")
    print("-" * 40)
    
    issues_good = engine.identify_writing_issues(good_text)
    issues_poor = engine.identify_writing_issues(poor_text)
    
    print(f"Good Document Issues: {len(issues_good)}")
    for issue in issues_good:
        print(f"  - {issue['type']}: {issue['description']} ({issue['severity']})")
    
    print(f"Poor Document Issues: {len(issues_poor)}")
    for issue in issues_poor:
        print(f"  - {issue['type']}: {issue['description']} ({issue['severity']})")
    
    print("\n6. PRESENTATION READINESS")
    print("-" * 40)
    
    present_good = engine.assess_presentation_readiness(good_doc)
    present_poor = engine.assess_presentation_readiness(poor_doc)
    
    print(f"Good Document Presentation Readiness: {present_good['overall_readiness']:.1f}/100")
    print(f"  Structure Score: {present_good['structure_score']:.1f}/100")
    print(f"  Density Score: {present_good['density_score']:.1f}/100")
    print(f"  Visual Score: {present_good['visual_score']:.1f}/100")
    
    print(f"Poor Document Presentation Readiness: {present_poor['overall_readiness']:.1f}/100")
    print(f"  Structure Score: {present_poor['structure_score']:.1f}/100")
    print(f"  Density Score: {present_poor['density_score']:.1f}/100")
    print(f"  Visual Score: {present_poor['visual_score']:.1f}/100")
    
    print("\n7. OVERALL ASSESSMENT SUMMARY")
    print("-" * 40)
    
    good_overall = (tone_good + read_good + present_good['overall_readiness']) / 3
    poor_overall = (tone_poor + read_poor + present_poor['overall_readiness']) / 3
    
    print(f"Good Document Overall Score: {good_overall:.1f}/100")
    print(f"Poor Document Overall Score: {poor_overall:.1f}/100")
    print(f"Quality Difference: {good_overall - poor_overall:.1f} points")
    
    if good_overall >= 80:
        good_level = "EXCELLENT"
    elif good_overall >= 70:
        good_level = "GOOD"
    elif good_overall >= 50:
        good_level = "FAIR"
    else:
        good_level = "POOR"
    
    if poor_overall >= 80:
        poor_level = "EXCELLENT"
    elif poor_overall >= 70:
        poor_level = "GOOD"
    elif poor_overall >= 50:
        poor_level = "FAIR"
    else:
        poor_level = "POOR"
    
    print(f"Good Document Quality Level: {good_level}")
    print(f"Poor Document Quality Level: {poor_level}")
    
    print("\n8. IMPROVEMENT RECOMMENDATIONS")
    print("-" * 40)
    
    print("For Poor Quality Document:")
    print("• Replace informal language with academic terminology")
    print("• Expand contractions (I'm → I am, it's → it is)")  
    print("• Add missing sections (abstract, methodology, results, conclusion)")
    print("• Improve sentence structure and variety")
    print("• Include supporting citations and references")
    print("• Enhance coherence with transitional phrases")
    
    print("\n" + "=" * 80)
    print("✅ INTELLIGENCE ENGINE DEMONSTRATION COMPLETE")
    print("=" * 80)


if __name__ == "__main__":
    demonstrate_intelligence_features()