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
from utils.output_manager import OutputManager
from utils.quality import QualityAnalyzer
from utils.audit import AuditLogger

# Version
__version__ = "0.3.0"

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
  
  # Debug mode with all formats and quality report
  python cli.py --request "Indoor gardening" --debug --format all --quality-report
  
  # Organized output with audit log
  python cli.py --request "Productivity tips" --organized-output --audit-log
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
    
    # New flags for Phase 2C
    parser.add_argument(
        "--quality-report",
        action="store_true",
        help="Generate detailed quality analysis report"
    )
    
    parser.add_argument(
        "--audit-log",
        action="store_true",
        help="Save detailed audit log"
    )
    
    parser.add_argument(
        "--organized-output",
        action="store_true",
        help="Organize outputs in structured directories (timestamp-based)"
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


def run_pipeline(args: argparse.Namespace) -> None:
    """Run the content generation pipeline."""
    
    # Initialize output manager
    output_manager = OutputManager(Path(args.output_dir))
    
    # Determine session directory
    if args.organized_output:
        # Create structured session directory
        try:
            # We need a request ID first, but we can generate a temporary ID or use timestamp
            # Better approach: generate ID here
            from utils.logger import generate_request_id
            request_id = generate_request_id()
            session_dir = output_manager.create_session_directory(request_id, args.request)
        except Exception as e:
            console.print(f"[red]Error creating session directory: {str(e)}[/red]")
            session_dir = Path(args.output_dir)
            request_id = None
            session_dir.mkdir(parents=True, exist_ok=True)
    else:
        # Use flat output directory
        session_dir = Path(args.output_dir)
        session_dir.mkdir(parents=True, exist_ok=True)
        request_id = None
    
    # Initialize audit logger if requested
    audit_logger = None
    if args.audit_log:
        audit_logger = AuditLogger(request_id or "pending", args.request)
        audit_logger.set_settings({
            "word_count": args.word_count,
            "tone": args.tone,
            "format": args.format
        })
    
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
    
    # Update request ID if we generated one earlier
    if request_id:
        initial_state["request_id"] = request_id
    
    # Update audit logger with final request ID
    if audit_logger:
        audit_logger.request_id = initial_state["request_id"]
    
    # Create progress tracker
    progress = PipelineProgress(console)
    formatter = OutputFormatter(console)
    
    # Show header
    formatter.display_header(args.request, initial_state["request_id"])
    
    try:
        # Run pipeline with progress tracking
        with progress.live_display():
            # Execute workflow
            result = app.invoke(initial_state)
            
            # Update progress for each completed agent
            for agent, duration in result.get("execution_times", {}).items():
                progress.complete_agent(agent.capitalize(), duration)
                
                # Log to audit trail
                if audit_logger:
                    tokens = result.get("token_usage", {}).get(agent, 0)
                    audit_logger.log_agent_complete(agent, "Completed", duration, tokens)
        
        # Check for errors
        if result.get("errors"):
            formatter.display_error(Exception("; ".join(result["errors"])))
            if audit_logger:
                for error in result["errors"]:
                    audit_logger.log_agent_error("Pipeline", error, 0)
            sys.exit(1)
            
        # Perform quality analysis if requested
        quality_report = None
        if args.quality_report:
            analyzer = QualityAnalyzer()
            quality_report = analyzer.analyze(
                content=result.get("final_content", ""),
                metadata=result.get("seo_metadata", {}),
                brief=result.get("brief", {})
            ).to_dict()
        
        # Save outputs
        formats = [args.format] if args.format != "all" else ["markdown", "json", "html"]
        
        if args.organized_output:
            # Use sophisticated output manager
            output_files = output_manager.save_all_outputs(
                result=result,
                session_dir=session_dir,
                formats=formats,
                quality_report=quality_report,
                audit_log=audit_logger
            )
        else:
            # Simple save (legacy mode)
            from cli import save_outputs as simple_save
            output_files = simple_save(result, session_dir, formats)
            
            # Save extra reports if requested but not using organized output
            if quality_report:
                import json
                q_file = session_dir / f"quality_report_{result['request_id'][:8]}.json"
                q_file.write_text(json.dumps(quality_report, indent=2), encoding="utf-8")
                output_files["quality_report"] = str(q_file)
            
            if audit_logger:
                a_file = session_dir / f"audit_log_{result['request_id'][:8]}.json"
                audit_logger.save_audit_log(a_file, result)
                output_files["audit_log"] = str(a_file)
        
        # Display results with quality info
        formatter.display_success(result, output_files)
        
        if quality_report:
            # Add quality display method to formatter or print manually
            console.print(Panel(
                f"[bold]Overall Quality Score:[/bold] {quality_report['overall_score']}/100\n\n"
                f"Readability: {quality_report['readability']['score']}/100\n"
                f"SEO: {quality_report['seo']['score']}/100\n"
                f"Alignment: {quality_report['alignment']['score']}/100",
                title="Quality Analysis",
                border_style="green"
            ))
            
            if quality_report.get('recommendations'):
                console.print("\n[bold yellow]Recommendations:[/bold yellow]")
                for rec in quality_report['recommendations']:
                    console.print(f"• {rec}")
                console.print()
        
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
