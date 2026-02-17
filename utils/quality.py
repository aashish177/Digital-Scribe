"""
Quality analysis module for content evaluation.

Provides comprehensive quality metrics including readability, SEO, and alignment checks.
"""

import re
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, asdict
import textstat


@dataclass
class ReadabilityMetrics:
    """Readability analysis results."""
    flesch_reading_ease: float
    flesch_kincaid_grade: float
    avg_sentence_length: float
    avg_word_length: float
    complex_word_percentage: float
    score: float  # 0-100


@dataclass
class SEOMetrics:
    """SEO quality analysis results."""
    keyword_density: float
    meta_title_length: int
    meta_description_length: int
    heading_count: int
    has_h1: bool
    content_length: int
    score: float  # 0-100


@dataclass
class AlignmentMetrics:
    """Brief alignment analysis results."""
    word_count_match: float  # 0-1, how close to target
    target_word_count: Optional[int]
    actual_word_count: int
    has_introduction: bool
    has_conclusion: bool
    score: float  # 0-100


@dataclass
class QualityReport:
    """Complete quality analysis report."""
    overall_score: float  # 0-100
    readability: ReadabilityMetrics
    seo: SEOMetrics
    alignment: AlignmentMetrics
    recommendations: List[str]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


class QualityAnalyzer:
    """Analyze content quality across multiple dimensions."""
    
    def __init__(self):
        """Initialize quality analyzer."""
        self.weights = {
            'readability': 0.35,
            'seo': 0.35,
            'alignment': 0.30
        }
    
    def analyze(
        self,
        content: str,
        metadata: Optional[Dict] = None,
        brief: Optional[Dict] = None
    ) -> QualityReport:
        """
        Perform comprehensive quality analysis.
        
        Args:
            content: The generated content text
            metadata: SEO metadata dictionary
            brief: Content brief dictionary
            
        Returns:
            QualityReport with all metrics and recommendations
        """
        metadata = metadata or {}
        brief = brief or {}
        
        # Analyze each dimension
        readability = self.analyze_readability(content)
        seo = self.analyze_seo(content, metadata)
        alignment = self.analyze_alignment(content, brief)
        
        # Calculate overall score
        overall_score = (
            readability.score * self.weights['readability'] +
            seo.score * self.weights['seo'] +
            alignment.score * self.weights['alignment']
        )
        
        # Generate recommendations
        recommendations = self._generate_recommendations(
            readability, seo, alignment, brief
        )
        
        return QualityReport(
            overall_score=round(overall_score, 1),
            readability=readability,
            seo=seo,
            alignment=alignment,
            recommendations=recommendations
        )
    
    def analyze_readability(self, content: str) -> ReadabilityMetrics:
        """
        Analyze content readability.
        
        Args:
            content: Content text
            
        Returns:
            ReadabilityMetrics
        """
        # Calculate metrics using textstat
        flesch_ease = textstat.flesch_reading_ease(content)
        flesch_grade = textstat.flesch_kincaid_grade(content)
        
        # Calculate additional metrics
        sentences = self._split_sentences(content)
        words = content.split()
        
        avg_sentence_length = len(words) / max(len(sentences), 1)
        avg_word_length = sum(len(word) for word in words) / max(len(words), 1)
        
        # Complex words (3+ syllables)
        complex_words = sum(1 for word in words if textstat.syllable_count(word) >= 3)
        complex_word_pct = (complex_words / max(len(words), 1)) * 100
        
        # Calculate score (0-100)
        # Flesch Reading Ease: 60-70 is ideal (standard)
        # Grade level: 8-10 is ideal for general audience
        score = self._calculate_readability_score(
            flesch_ease, flesch_grade, avg_sentence_length, complex_word_pct
        )
        
        return ReadabilityMetrics(
            flesch_reading_ease=round(flesch_ease, 1),
            flesch_kincaid_grade=round(flesch_grade, 1),
            avg_sentence_length=round(avg_sentence_length, 1),
            avg_word_length=round(avg_word_length, 1),
            complex_word_percentage=round(complex_word_pct, 1),
            score=round(score, 1)
        )
    
    def analyze_seo(self, content: str, metadata: Dict) -> SEOMetrics:
        """
        Analyze SEO quality.
        
        Args:
            content: Content text
            metadata: SEO metadata
            
        Returns:
            SEOMetrics
        """
        # Meta tag lengths
        meta_title = metadata.get('meta_title', '')
        meta_desc = metadata.get('meta_description', '')
        
        title_len = len(meta_title)
        desc_len = len(meta_desc)
        
        # Count headings
        h1_count = len(re.findall(r'^#\s+.+$', content, re.MULTILINE))
        all_headings = len(re.findall(r'^#{1,6}\s+.+$', content, re.MULTILINE))
        
        # Content length
        word_count = len(content.split())
        
        # Keyword density (simple: count title words in content)
        keyword_density = 0.0
        if meta_title:
            title_words = set(meta_title.lower().split())
            content_lower = content.lower()
            keyword_occurrences = sum(content_lower.count(word) for word in title_words)
            keyword_density = (keyword_occurrences / max(word_count, 1)) * 100
        
        # Calculate score
        score = self._calculate_seo_score(
            title_len, desc_len, h1_count, all_headings, word_count
        )
        
        return SEOMetrics(
            keyword_density=round(keyword_density, 2),
            meta_title_length=title_len,
            meta_description_length=desc_len,
            heading_count=all_headings,
            has_h1=(h1_count > 0),
            content_length=word_count,
            score=round(score, 1)
        )
    
    def analyze_alignment(self, content: str, brief: Dict) -> AlignmentMetrics:
        """
        Analyze alignment with content brief.
        
        Args:
            content: Content text
            brief: Content brief
            
        Returns:
            AlignmentMetrics
        """
        actual_word_count = len(content.split())
        target_word_count = brief.get('word_count')
        
        # Calculate word count match (0-1)
        if target_word_count:
            ratio = actual_word_count / target_word_count
            # Perfect match = 1.0, deviations reduce score
            if 0.9 <= ratio <= 1.1:
                word_count_match = 1.0
            elif 0.8 <= ratio <= 1.2:
                word_count_match = 0.8
            else:
                word_count_match = max(0.5, 1.0 - abs(1.0 - ratio))
        else:
            word_count_match = 1.0  # No target, assume OK
        
        # Check for introduction and conclusion
        content_lower = content.lower()
        has_intro = any(word in content_lower[:500] for word in [
            'introduction', 'overview', 'begin', 'start'
        ])
        has_conclusion = any(word in content_lower[-500:] for word in [
            'conclusion', 'summary', 'final', 'end'
        ])
        
        # Calculate score
        score = (
            word_count_match * 60 +  # 60% weight on word count
            (20 if has_intro else 0) +  # 20% for intro
            (20 if has_conclusion else 0)  # 20% for conclusion
        )
        
        return AlignmentMetrics(
            word_count_match=round(word_count_match, 2),
            target_word_count=target_word_count,
            actual_word_count=actual_word_count,
            has_introduction=has_intro,
            has_conclusion=has_conclusion,
            score=round(score, 1)
        )
    
    def _calculate_readability_score(
        self,
        flesch_ease: float,
        grade_level: float,
        avg_sentence_len: float,
        complex_word_pct: float
    ) -> float:
        """Calculate readability score (0-100)."""
        score = 0.0
        
        # Flesch Reading Ease (60-70 is ideal)
        if 60 <= flesch_ease <= 70:
            score += 40
        elif 50 <= flesch_ease < 60 or 70 < flesch_ease <= 80:
            score += 30
        else:
            score += 20
        
        # Grade level (8-10 is ideal for general audience)
        if 8 <= grade_level <= 10:
            score += 30
        elif 6 <= grade_level < 8 or 10 < grade_level <= 12:
            score += 20
        else:
            score += 10
        
        # Sentence length (15-20 words is ideal)
        if 15 <= avg_sentence_len <= 20:
            score += 20
        elif 10 <= avg_sentence_len < 15 or 20 < avg_sentence_len <= 25:
            score += 15
        else:
            score += 10
        
        # Complex words (< 20% is good)
        if complex_word_pct < 20:
            score += 10
        elif complex_word_pct < 30:
            score += 5
        
        return score
    
    def _calculate_seo_score(
        self,
        title_len: int,
        desc_len: int,
        h1_count: int,
        heading_count: int,
        word_count: int
    ) -> float:
        """Calculate SEO score (0-100)."""
        score = 0.0
        
        # Meta title (50-60 chars is ideal)
        if 50 <= title_len <= 60:
            score += 25
        elif 40 <= title_len < 50 or 60 < title_len <= 70:
            score += 20
        elif title_len > 0:
            score += 10
        
        # Meta description (150-160 chars is ideal)
        if 150 <= desc_len <= 160:
            score += 25
        elif 120 <= desc_len < 150 or 160 < desc_len <= 200:
            score += 20
        elif desc_len > 0:
            score += 10
        
        # H1 heading (should have exactly 1)
        if h1_count == 1:
            score += 20
        elif h1_count > 0:
            score += 10
        
        # Multiple headings (good for structure)
        if heading_count >= 3:
            score += 15
        elif heading_count >= 1:
            score += 10
        
        # Content length (300+ words is good)
        if word_count >= 500:
            score += 15
        elif word_count >= 300:
            score += 10
        elif word_count >= 100:
            score += 5
        
        return score
    
    def _generate_recommendations(
        self,
        readability: ReadabilityMetrics,
        seo: SEOMetrics,
        alignment: AlignmentMetrics,
        brief: Dict
    ) -> List[str]:
        """Generate actionable recommendations."""
        recommendations = []
        
        # Readability recommendations
        if readability.flesch_reading_ease < 50:
            recommendations.append(
                "Content is difficult to read. Consider simplifying sentences and using simpler words."
            )
        elif readability.flesch_reading_ease > 80:
            recommendations.append(
                "Content may be too simple. Consider adding more sophisticated vocabulary."
            )
        
        if readability.avg_sentence_length > 25:
            recommendations.append(
                f"Average sentence length is {readability.avg_sentence_length:.1f} words. "
                "Consider breaking up long sentences for better readability."
            )
        
        if readability.complex_word_percentage > 30:
            recommendations.append(
                f"High percentage of complex words ({readability.complex_word_percentage:.1f}%). "
                "Consider using simpler alternatives where possible."
            )
        
        # SEO recommendations
        if seo.meta_title_length == 0:
            recommendations.append("Add a meta title for SEO.")
        elif seo.meta_title_length > 70:
            recommendations.append(
                f"Meta title is too long ({seo.meta_title_length} chars). Keep it under 60 characters."
            )
        
        if seo.meta_description_length == 0:
            recommendations.append("Add a meta description for SEO.")
        elif seo.meta_description_length > 200:
            recommendations.append(
                f"Meta description is too long ({seo.meta_description_length} chars). "
                "Keep it under 160 characters."
            )
        
        if not seo.has_h1:
            recommendations.append("Add an H1 heading to improve content structure.")
        
        if seo.heading_count < 3:
            recommendations.append(
                "Add more headings (H2, H3) to improve content structure and SEO."
            )
        
        # Alignment recommendations
        if alignment.target_word_count:
            deviation = abs(alignment.actual_word_count - alignment.target_word_count)
            if deviation > alignment.target_word_count * 0.2:
                recommendations.append(
                    f"Content length ({alignment.actual_word_count} words) deviates significantly "
                    f"from target ({alignment.target_word_count} words)."
                )
        
        if not alignment.has_introduction:
            recommendations.append("Consider adding a clear introduction section.")
        
        if not alignment.has_conclusion:
            recommendations.append("Consider adding a conclusion or summary section.")
        
        return recommendations
    
    def _split_sentences(self, text: str) -> List[str]:
        """Split text into sentences."""
        # Simple sentence splitting
        sentences = re.split(r'[.!?]+', text)
        return [s.strip() for s in sentences if s.strip()]
