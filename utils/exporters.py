"""
Content exporters for multiple output formats.

Supports exporting content as Markdown (with frontmatter), HTML (styled), and JSON.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import markdown2
from bs4 import BeautifulSoup


class ContentExporter:
    """Export content in multiple formats."""
    
    def __init__(self):
        """Initialize content exporter."""
        self.html_template = self._get_html_template()
        self.css_styles = self._get_css_styles()
    
    def export_markdown(
        self,
        result: Dict[str, Any],
        output_path: Path
    ) -> Path:
        """
        Export content as Markdown with YAML frontmatter.
        
        Args:
            result: Pipeline result dictionary
            output_path: Path to save markdown file
            
        Returns:
            Path to created file
        """
        content = result.get('final_content', '')
        metadata = result.get('seo_metadata', {})
        brief = result.get('brief', {})
        
        # Create frontmatter
        frontmatter = self._create_frontmatter(metadata, brief, result)
        
        # Combine frontmatter and content
        markdown_content = f"{frontmatter}\n\n{content}"
        
        # Write to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(markdown_content, encoding='utf-8')
        
        return output_path
    
    def export_html(
        self,
        result: Dict[str, Any],
        output_path: Path
    ) -> Path:
        """
        Export content as styled HTML.
        
        Args:
            result: Pipeline result dictionary
            output_path: Path to save HTML file
            
        Returns:
            Path to created file
        """
        content = result.get('final_content', '')
        metadata = result.get('seo_metadata', {})
        
        # Convert markdown to HTML
        html_body = markdown2.markdown(
            content,
            extras=['fenced-code-blocks', 'tables', 'header-ids']
        )
        
        # Create complete HTML document
        html_doc = self.html_template.format(
            title=metadata.get('meta_title', 'Generated Content'),
            description=metadata.get('meta_description', ''),
            keywords=', '.join(metadata.get('keywords', [])) if isinstance(metadata.get('keywords'), list) else '',
            styles=self.css_styles,
            content=html_body,
            generated_date=datetime.now().strftime('%Y-%m-%d')
        )
        
        # Write to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(html_doc, encoding='utf-8')
        
        return output_path
    
    def export_json(
        self,
        result: Dict[str, Any],
        output_path: Path,
        include_full_data: bool = True
    ) -> Path:
        """
        Export content and metadata as JSON.
        
        Args:
            result: Pipeline result dictionary
            output_path: Path to save JSON file
            include_full_data: Whether to include all pipeline data
            
        Returns:
            Path to created file
        """
        if include_full_data:
            # Export complete pipeline data
            export_data = {
                'request_id': result.get('request_id'),
                'generated_at': result.get('started_at'),
                'content_request': result.get('content_request'),
                'final_content': result.get('final_content'),
                'seo_metadata': result.get('seo_metadata'),
                'brief': result.get('brief'),
                'execution_times': result.get('execution_times'),
                'token_usage': result.get('token_usage'),
                'word_count': len(result.get('final_content', '').split()),
                'errors': result.get('errors', [])
            }
        else:
            # Export minimal data
            export_data = {
                'content': result.get('final_content'),
                'metadata': result.get('seo_metadata')
            }
        
        # Write to file
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(
            json.dumps(export_data, indent=2, ensure_ascii=False),
            encoding='utf-8'
        )
        
        return output_path
    
    def export_all(
        self,
        result: Dict[str, Any],
        output_dir: Path,
        base_name: str = 'content'
    ) -> Dict[str, Path]:
        """
        Export content in all formats.
        
        Args:
            result: Pipeline result dictionary
            output_dir: Directory to save files
            base_name: Base filename (without extension)
            
        Returns:
            Dictionary mapping format to file path
        """
        output_dir.mkdir(parents=True, exist_ok=True)
        
        files = {}
        files['markdown'] = self.export_markdown(
            result,
            output_dir / f"{base_name}.md"
        )
        files['html'] = self.export_html(
            result,
            output_dir / f"{base_name}.html"
        )
        files['json'] = self.export_json(
            result,
            output_dir / f"{base_name}.json"
        )
        
        return files
    
    def _create_frontmatter(
        self,
        metadata: Dict,
        brief: Dict,
        result: Dict
    ) -> str:
        """Create YAML frontmatter for markdown."""
        frontmatter_data = {
            'title': metadata.get('meta_title', brief.get('title', 'Untitled')),
            'description': metadata.get('meta_description', ''),
            'slug': metadata.get('slug', ''),
            'keywords': metadata.get('keywords', []),
            'generated_at': result.get('started_at', datetime.now().isoformat()),
            'word_count': len(result.get('final_content', '').split()),
            'request_id': result.get('request_id', '')
        }
        
        # Build YAML frontmatter
        lines = ['---']
        for key, value in frontmatter_data.items():
            if isinstance(value, list):
                if value:
                    lines.append(f'{key}:')
                    for item in value:
                        lines.append(f'  - {item}')
            elif value:
                # Escape quotes in strings
                if isinstance(value, str) and ('"' in value or ':' in value):
                    value = f'"{value.replace(chr(34), chr(92) + chr(34))}"'
                lines.append(f'{key}: {value}')
        lines.append('---')
        
        return '\n'.join(lines)
    
    def _get_html_template(self) -> str:
        """Get HTML document template."""
        return """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{description}">
    <meta name="keywords" content="{keywords}">
    <meta name="generator" content="Multi-Agent Content Generation Pipeline">
    
    <!-- Open Graph / Facebook -->
    <meta property="og:type" content="article">
    <meta property="og:title" content="{title}">
    <meta property="og:description" content="{description}">
    
    <!-- Twitter -->
    <meta property="twitter:card" content="summary_large_image">
    <meta property="twitter:title" content="{title}">
    <meta property="twitter:description" content="{description}">
    
    <title>{title}</title>
    
    <style>
{styles}
    </style>
</head>
<body>
    <article class="content">
{content}
    </article>
    
    <footer class="footer">
        <p>Generated on {generated_date} by Multi-Agent Content Generation Pipeline</p>
    </footer>
</body>
</html>"""
    
    def _get_css_styles(self) -> str:
        """Get CSS styles for HTML export."""
        return """        /* Reset and base styles */
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, 'Helvetica Neue', sans-serif;
            line-height: 1.6;
            color: #333;
            background-color: #f9fafb;
            padding: 20px;
        }
        
        .content {
            max-width: 800px;
            margin: 0 auto;
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }
        
        /* Typography */
        h1, h2, h3, h4, h5, h6 {
            color: #1a202c;
            margin-top: 1.5em;
            margin-bottom: 0.5em;
            font-weight: 600;
            line-height: 1.3;
        }
        
        h1 {
            font-size: 2.5em;
            margin-top: 0;
            border-bottom: 2px solid #e2e8f0;
            padding-bottom: 0.3em;
        }
        
        h2 {
            font-size: 2em;
            border-bottom: 1px solid #e2e8f0;
            padding-bottom: 0.3em;
        }
        
        h3 {
            font-size: 1.5em;
        }
        
        h4 {
            font-size: 1.25em;
        }
        
        p {
            margin-bottom: 1em;
        }
        
        /* Links */
        a {
            color: #3182ce;
            text-decoration: none;
        }
        
        a:hover {
            text-decoration: underline;
        }
        
        /* Lists */
        ul, ol {
            margin-left: 1.5em;
            margin-bottom: 1em;
        }
        
        li {
            margin-bottom: 0.5em;
        }
        
        /* Code */
        code {
            background: #f7fafc;
            padding: 0.2em 0.4em;
            border-radius: 3px;
            font-family: 'Monaco', 'Courier New', monospace;
            font-size: 0.9em;
            color: #e53e3e;
        }
        
        pre {
            background: #2d3748;
            color: #f7fafc;
            padding: 1em;
            border-radius: 5px;
            overflow-x: auto;
            margin-bottom: 1em;
        }
        
        pre code {
            background: none;
            color: inherit;
            padding: 0;
        }
        
        /* Blockquotes */
        blockquote {
            border-left: 4px solid #3182ce;
            padding-left: 1em;
            margin: 1em 0;
            color: #4a5568;
            font-style: italic;
        }
        
        /* Tables */
        table {
            width: 100%;
            border-collapse: collapse;
            margin-bottom: 1em;
        }
        
        th, td {
            padding: 0.75em;
            text-align: left;
            border-bottom: 1px solid #e2e8f0;
        }
        
        th {
            background: #f7fafc;
            font-weight: 600;
        }
        
        /* Images */
        img {
            max-width: 100%;
            height: auto;
            border-radius: 5px;
        }
        
        /* Footer */
        .footer {
            max-width: 800px;
            margin: 20px auto 0;
            padding: 20px;
            text-align: center;
            color: #718096;
            font-size: 0.9em;
        }
        
        /* Print styles */
        @media print {
            body {
                background: white;
                padding: 0;
            }
            
            .content {
                box-shadow: none;
                padding: 0;
            }
            
            .footer {
                display: none;
            }
        }
        
        /* Mobile responsive */
        @media (max-width: 768px) {
            .content {
                padding: 20px;
            }
            
            h1 {
                font-size: 2em;
            }
            
            h2 {
                font-size: 1.5em;
            }
        }"""
