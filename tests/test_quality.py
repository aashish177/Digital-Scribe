import pytest
from utils.quality import QualityAnalyzer, ReadabilityMetrics, SEOMetrics, AlignmentMetrics, QualityReport

@pytest.fixture
def analyzer():
    return QualityAnalyzer()

def test_analyze_readability(analyzer):
    # A simple, short text
    text_simple = "This is a very simple sentence. It is easy to read. A cat sat on the mat."
    metrics_simple = analyzer.analyze_readability(text_simple)
    
    assert isinstance(metrics_simple, ReadabilityMetrics)
    # Simple text should have high reading ease and low grade
    assert metrics_simple.flesch_reading_ease > 70
    assert metrics_simple.flesch_kincaid_grade < 6
    assert metrics_simple.complex_word_percentage == 0.0

    # A complex text
    text_complex = "The juxtaposition of inextricably linked physiological paradigms necessitates comprehensive multidisciplinary investigation to elucidate underlying mechanisms."
    metrics_complex = analyzer.analyze_readability(text_complex)
    
    # Complex text should have lower reading ease and higher grade
    assert metrics_complex.flesch_reading_ease < 50
    assert metrics_complex.flesch_kincaid_grade > 10
    assert metrics_complex.complex_word_percentage > 20

def test_analyze_seo(analyzer):
    content = "# Main Title\n\nSome introductory text.\n\n## Subheader\n\nMore text here with keyword. Another keyword here."
    metadata = {
        "meta_title": "Main Keyword Title",
        "meta_description": "This is a meta description for the seo test." * 3,
    }
    
    metrics = analyzer.analyze_seo(content, metadata)
    assert isinstance(metrics, SEOMetrics)
    assert metrics.heading_count == 2
    assert metrics.has_h1 is True
    assert metrics.content_length > 0
    assert metrics.meta_title_length == 18
    assert metrics.keyword_density > 0

def test_analyze_alignment(analyzer):
    content = "Introduction: We begin our discussion here. " + "Word " * 90 + "Conclusion: Finally, we summarize the topic."
    brief = {
        "word_count": 100
    }
    
    metrics = analyzer.analyze_alignment(content, brief)
    assert isinstance(metrics, AlignmentMetrics)
    assert metrics.target_word_count == 100
    assert metrics.actual_word_count > 90 # should be around 95-105 depending on exact split
    assert metrics.word_count_match >= 0.9 # Close to perfect match
    assert metrics.has_introduction is True
    assert metrics.has_conclusion is True

def test_analyze_overall(analyzer):
    content = "# Good Content\n\nIntroduction to the topic. " + "This is a good sentence. " * 30 + "In conclusion, it is good."
    metadata = {
        "meta_title": "Good Content Title that is Long Enough",
        "meta_description": "A comprehensive meta description that explains what the content is about and is of adequate length for SEO purposes."
    }
    brief = {
        "word_count": 150
    }
    
    report = analyzer.analyze(content, metadata, brief)
    assert isinstance(report, QualityReport)
    assert report.overall_score > 0
    assert report.readability is not None
    assert report.seo is not None
    assert report.alignment is not None
    
    # Dict conversion test
    report_dict = report.to_dict()
    assert isinstance(report_dict, dict)
    assert "overall_score" in report_dict
    assert "recommendations" in report_dict
