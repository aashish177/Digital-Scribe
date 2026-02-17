"""
Output management system for organizing pipeline outputs.

Creates structured directories and manages file organization.
"""

import json
from pathlib import Path
from typing import Dict, Any, List, Optional
from datetime import datetime
import re


class OutputManager:
    """Manage and organize pipeline outputs."""
    
    def __init__(self, base_dir: Path = Path("outputs")):
        """
        Initialize output manager.
        
        Args:
            base_dir: Base directory for all outputs
        """
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
    
    def create_session_directory(
        self,
        request_id: str,
        content_request: str
    ) -> Path:
        """
        Create organized directory structure for a generation session.
        
        Args:
            request_id: Unique request ID
            content_request: Content request text
            
        Returns:
            Path to session directory
        """
        # Create session name from timestamp and request
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        slug = self._create_slug(content_request)
        session_name = f"{timestamp}_{request_id[:8]}_{slug}"
        
        # Create directory structure
        session_dir = self.base_dir / session_name
        session_dir.mkdir(parents=True, exist_ok=True)
        
        # Create subdirectories
        (session_dir / 'content').mkdir(exist_ok=True)
        (session_dir / 'reports').mkdir(exist_ok=True)
        
        return session_dir
    
    def save_all_outputs(
        self,
        result: Dict[str, Any],
        session_dir: Path,
        formats: List[str],
        quality_report: Optional[Dict] = None,
        audit_log: Optional[Any] = None
    ) -> Dict[str, Path]:
        """
        Save all outputs in organized structure.
        
        Args:
            result: Pipeline result
            session_dir: Session directory
            formats: List of export formats
            quality_report: Quality analysis report (optional)
            audit_log: Audit logger instance (optional)
            
        Returns:
            Dictionary mapping output type to file path
        """
        from utils.exporters import ContentExporter
        
        output_files = {}
        exporter = ContentExporter()
        
        # Export content in requested formats
        content_dir = session_dir / 'content'
        
        if 'markdown' in formats or 'all' in formats:
            output_files['content_md'] = exporter.export_markdown(
                result,
                content_dir / 'article.md'
            )
        
        if 'html' in formats or 'all' in formats:
            output_files['content_html'] = exporter.export_html(
                result,
                content_dir / 'article.html'
            )
        
        if 'json' in formats or 'all' in formats:
            output_files['content_json'] = exporter.export_json(
                result,
                content_dir / 'article.json'
            )
        
        # Save reports
        reports_dir = session_dir / 'reports'
        
        # SEO metadata
        if result.get('seo_metadata'):
            metadata_file = reports_dir / 'seo_metadata.json'
            metadata_file.write_text(
                json.dumps(result['seo_metadata'], indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
            output_files['seo_metadata'] = metadata_file
        
        # Brief
        if result.get('brief'):
            brief_file = reports_dir / 'brief.json'
            brief_file.write_text(
                json.dumps(result['brief'], indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
            output_files['brief'] = brief_file
        
        # Quality report
        if quality_report:
            quality_file = reports_dir / 'quality_report.json'
            quality_file.write_text(
                json.dumps(quality_report, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
            output_files['quality_report'] = quality_file
        
        # Audit log
        if audit_log:
            output_files['audit_log'] = audit_log.save_audit_log(
                reports_dir / 'audit_log.json',
                result
            )
            output_files['execution_summary'] = audit_log.save_execution_summary(
                reports_dir / 'execution_summary.json',
                result
            )
        
        # Create session README
        self.create_session_readme(result, session_dir, output_files, quality_report)
        
        return output_files
    
    def create_session_readme(
        self,
        result: Dict[str, Any],
        session_dir: Path,
        output_files: Dict[str, Path],
        quality_report: Optional[Dict] = None
    ):
        """
        Create README summarizing this generation session.
        
        Args:
            result: Pipeline result
            session_dir: Session directory
            output_files: Dictionary of output files
            quality_report: Quality report (optional)
        """
        readme_content = self._generate_readme_content(
            result,
            output_files,
            quality_report
        )
        
        readme_file = session_dir / 'README.md'
        readme_file.write_text(readme_content, encoding='utf-8')
    
    def _create_slug(self, text: str, max_length: int = 30) -> str:
        """Create URL-friendly slug from text."""
        # Convert to lowercase and replace spaces with hyphens
        slug = text.lower().strip()
        slug = re.sub(r'[^\w\s-]', '', slug)
        slug = re.sub(r'[-\s]+', '-', slug)
        
        # Truncate to max length
        if len(slug) > max_length:
            slug = slug[:max_length].rsplit('-', 1)[0]
        
        return slug
    
    def _generate_readme_content(
        self,
        result: Dict[str, Any],
        output_files: Dict[str, Path],
        quality_report: Optional[Dict]
    ) -> str:
        """Generate README content."""
        lines = [
            "# Content Generation Session",
            "",
            "## Request",
            f"**Request ID:** `{result.get('request_id', 'N/A')}`  ",
            f"**Generated:** {result.get('started_at', 'N/A')}  ",
            "",
            f"**Content Request:**  ",
            f"> {result.get('content_request', 'N/A')}",
            ""
        ]
        
        # Execution summary
        execution_times = result.get('execution_times', {})
        if execution_times:
            total_time = sum(execution_times.values())
            lines.extend([
                "## Execution Summary",
                f"**Total Time:** {total_time:.1f}s  ",
                f"**Word Count:** {len(result.get('final_content', '').split())} words  ",
                "",
                "**Agent Execution Times:**",
                ""
            ])
            for agent, duration in execution_times.items():
                lines.append(f"- **{agent.capitalize()}:** {duration:.1f}s")
            lines.append("")
        
        # Quality metrics
        if quality_report:
            overall_score = quality_report.get('overall_score', 0)
            lines.extend([
                "## Quality Metrics",
                f"**Overall Score:** {overall_score}/100  ",
                ""
            ])
            
            if 'readability' in quality_report:
                r = quality_report['readability']
                lines.extend([
                    "**Readability:**",
                    f"- Flesch Reading Ease: {r.get('flesch_reading_ease', 0):.1f}",
                    f"- Grade Level: {r.get('flesch_kincaid_grade', 0):.1f}",
                    f"- Score: {r.get('score', 0)}/100",
                    ""
                ])
            
            if 'seo' in quality_report:
                s = quality_report['seo']
                lines.extend([
                    "**SEO:**",
                    f"- Meta Title Length: {s.get('meta_title_length', 0)} chars",
                    f"- Headings: {s.get('heading_count', 0)}",
                    f"- Score: {s.get('score', 0)}/100",
                    ""
                ])
        
        # Output files
        lines.extend([
            "## Output Files",
            ""
        ])
        
        for file_type, file_path in output_files.items():
            rel_path = file_path.relative_to(file_path.parent.parent)
            lines.append(f"- **{file_type}:** `{rel_path}`")
        
        lines.append("")
        
        # Recommendations
        if quality_report and quality_report.get('recommendations'):
            lines.extend([
                "## Recommendations",
                ""
            ])
            for rec in quality_report['recommendations']:
                lines.append(f"- {rec}")
            lines.append("")
        
        return '\n'.join(lines)
