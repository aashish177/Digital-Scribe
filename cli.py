#!/usr/bin/env python3
"""
Content Generation Pipeline - Command Line Interface

Usage:
    python cli.py --request "Write a guide on meditation"
    python cli.py --request "Tech trends 2025" --word-count 1500 --tone professional
    python cli.py --request "Green tea benefits" --debug
"""

import argparse
import sys
import os
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any

from rich.console import Console
from rich.panel import Panel

from config import Config
from logging_config import setup_logging
from graph.workflow import create_content_workflow, initialize_state
from utils.progress import PipelineProgress
from utils.output_formatter import OutputFormatter

# Version
__version__ = "0.2.0"

# Console for rich output
console = Console()


def parse_arguments() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        description="Multi-Agent Content Generation Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Basic usage
  python cli.py --request "Write a guide on meditation"
  
  # With custom options
  python cli.py --request "Tech trends 2025" --word-count 1500 --tone professional
  
  # Verbose mode
  python cli.py --request "Green tea benefits" --verbose
  
  # Debug mode with all formats
  python cli.py --request "Indoor gardening" --debug --format all
  
  # Custom output directory
  python cli.py --request "Productivity tips" --output-dir ./my-content
        """
    )
    
    # Required arguments
    parser.add_argument(
        "--request",
        type=str,
        required=True,
        help="Content request description (required)"
    )
    
    # Optional arguments
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./outputs",
        help="Output directory for generated content (default: ./outputs)"
    )
    
    parser.add_argument(
        "--word-count",
        type=int,
        help="Target word count for the content"
    )
    
    parser.add_argument(
        "--tone",
        type=str,
        choices=["professional", "casual", "friendly", "technical"],
        help="Content tone"
    )
    
    parser.add_argument(
        "--format",
        type=str,
        choices=["markdown", "json", "html", "all"],
        default="markdown",
        help="Output format (default: markdown)"
    )
    
    # Flags
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Show detailed output including research findings and edit notes"
    )
    
    parser.add_argument(
        "--debug", "-d",
        action="store_true",
        help="Enable debug mode with full logging"
    )
    
    parser.add_argument(
        "--version",
        action="version",
        version=f"Content Generation Pipeline v{__version__}"
    )
    
    return parser.parse_args()


def setup_logging_for_cli(verbose: bool, debug: bool) -> None:
    """Configure logging based on CLI flags."""
    if debug:
        level = "DEBUG"
    elif verbose:
        level = "INFO"
    else:
        level = "WARNING"  # Quiet mode for clean output
    
    setup_logging(
        level=level,
        format_type="human",
        enable_console=False  # We'll use rich for console output
    )


def validate_environment() -> None:
    """Validate that required environment variables are set."""
    try:
        Config.validate()
    except ValueError as e:
        console.print(Panel(
            f"[red]❌ Error: {str(e)}[/red]\n\n"
            "[yellow]Please set your API key in one of these ways:[/yellow]\n"
            "  1. Add to .env file: OPENAI_API_KEY=your_key_here\n"
            "  2. Set environment variable: export OPENAI_API_KEY=your_key_here\n\n"
            "[cyan]Get your API key at: https://platform.openai.com/api-keys[/cyan]",
            title="Configuration Error",
            border_style="red"
        ))
        sys.exit(1)


def create_output_directory(output_dir: str) -> Path:
    """Create output directory if it doesn't exist."""
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    return output_path


def save_outputs(result: Dict[str, Any], output_dir: Path, formats: list) -> Dict[str, str]:
    """Save outputs in requested formats."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    output_files = {}
    
    # Save final content
    if "markdown" in formats or "all" in formats:
        content_file = output_dir / f"final_content_{timestamp}.md"
        content_file.write_text(result.get("final_content", ""))
        output_files["content_md"] = str(content_file)
    
    # Save metadata as JSON
    if "json" in formats or "all" in formats:
        import json
        
        metadata_file = output_dir / f"metadata_{timestamp}.json"
        metadata = {
            "request_id": result.get("request_id"),
            "started_at": result.get("started_at"),
            "seo_metadata": result.get("seo_metadata"),
            "execution_times": result.get("execution_times"),
            "word_count": len(result.get("final_content", "").split())
        }
        metadata_file.write_text(json.dumps(metadata, indent=2))
        output_files["metadata"] = str(metadata_file)
        
        # Also save brief
        brief_file = output_dir / f"brief_{timestamp}.json"
        brief_file.write_text(json.dumps(result.get("brief", {}), indent=2))
        output_files["brief"] = str(brief_file)
    
    # Save as HTML (if requested)
    if "html" in formats or "all" in formats:
        html_file = output_dir / f"final_content_{timestamp}.html"
        html_content = generate_html(result)
        html_file.write_text(html_content)
        output_files["content_html"] = str(html_file)
    
    return output_files


def generate_html(result: Dict[str, Any]) -> str:
    """Generate HTML version of the content."""
    content = result.get("final_content", "")
    metadata = result.get("seo_metadata", {})
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="description" content="{metadata.get('meta_description', '')}">
    <title>{metadata.get('meta_title', 'Generated Content')}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            line-height: 1.6;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            color: #333;
        }}
        h1, h2, h3 {{ color: #2c3e50; }}
        code {{ background: #f4f4f4; padding: 2px 6px; border-radius: 3px; }}
        pre {{ background: #f4f4f4; padding: 15px; border-radius: 5px; overflow-x: auto; }}
    </style>
</head>
<body>
{content}
</body>
</html>"""
    return html


def run_pipeline(args: argparse.Namespace) -> None:
    """Run the content generation pipeline."""
    
    # Create output directory
    output_dir = create_output_directory(args.output_dir)
    
    # Create workflow
    app = create_content_workflow()
    
    # Prepare settings
    settings = {}
    if args.word_count:
        settings["word_count"] = args.word_count
    if args.tone:
        settings["tone"] = args.tone
    
    # Initialize state
    initial_state = initialize_state(
        content_request=args.request,
        settings=settings if settings else None
    )
    
    # Create progress tracker
    progress = PipelineProgress(console)
    formatter = OutputFormatter(console)
    
    # Show header
    console.print(Panel(
        f"[bold cyan]Content Request:[/bold cyan] {args.request}\n"
        f"[bold cyan]Request ID:[/bold cyan] {initial_state['request_id'][:8]}...",
        title="Content Generation Pipeline",
        border_style="cyan"
    ))
    console.print()
    
    try:
        # Run pipeline with progress tracking
        with progress.live_display():
            # Execute workflow
            result = app.invoke(initial_state)
            
            # Update progress for each completed agent
            for agent, duration in result.get("execution_times", {}).items():
                progress.complete_agent(agent.capitalize(), duration)
        
        # Check for errors
        if result.get("errors"):
            formatter.display_error(Exception("; ".join(result["errors"])))
            sys.exit(1)
        
        # Save outputs
        formats = [args.format] if args.format != "all" else ["markdown", "json", "html"]
        output_files = save_outputs(result, output_dir, formats)
        
        # Display results
        formatter.display_success(result, output_files)
        
        # Show verbose output if requested
        if args.verbose:
            formatter.display_verbose_output(result)
        
    except KeyboardInterrupt:
        console.print("\n[yellow]⚠️  Pipeline interrupted by user[/yellow]")
        sys.exit(130)
    
    except Exception as e:
        formatter.display_error(e)
        if args.debug:
            console.print_exception()
        sys.exit(1)


def main():
    """Main entry point for CLI."""
    # Parse arguments
    args = parse_arguments()
    
    # Setup logging
    setup_logging_for_cli(args.verbose, args.debug)
    
    # Validate environment
    validate_environment()
    
    # Run pipeline
    run_pipeline(args)


if __name__ == "__main__":
    main()
