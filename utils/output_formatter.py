"""
Output formatting utilities for the CLI.

Provides user-friendly display of pipeline results and errors.
"""

from typing import Dict, Any, Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich.markdown import Markdown


class OutputFormatter:
    """Format and display pipeline outputs in a user-friendly way."""
    
    def __init__(self, console: Console):
        """
        Initialize output formatter.
        
        Args:
            console: Rich console instance
        """
        self.console = console
    
    def display_success(self, result: Dict[str, Any], output_files: Dict[str, str]) -> None:
        """
        Display successful completion with results.
        
        Args:
            result: Pipeline result dictionary
            output_files: Dictionary of output file paths
        """
        # Success header
        self.console.print()
        self.console.print(Panel(
            "[bold green]✓ Content Generation Complete![/bold green]",
            border_style="green"
        ))
        self.console.print()
        
        # Content preview
        self._display_content_preview(result.get("final_content", ""))
        
        # Execution summary
        self._display_execution_summary(
            result.get("execution_times", {}),
            result.get("final_content", "")
        )
        
        # SEO metadata
        if result.get("seo_metadata"):
            self._display_metadata(result["seo_metadata"])
        
        # Output files
        self._display_output_files(output_files)
        
        self.console.print()
    
    def display_error(self, error: Exception) -> None:
        """
        Display error in user-friendly format.
        
        Args:
            error: Exception that occurred
        """
        self.console.print()
        
        error_msg = str(error)
        
        # Provide helpful suggestions based on error type
        suggestion = self._get_error_suggestion(error)
        
        panel_content = f"[bold red]❌ Content generation failed[/bold red]\n\n"
        panel_content += f"[yellow]Error:[/yellow] {error_msg}\n"
        
        if suggestion:
            panel_content += f"\n[cyan]Suggestion:[/cyan] {suggestion}"
        
        self.console.print(Panel(
            panel_content,
            title="Error",
            border_style="red"
        ))
        self.console.print()
    
    def display_verbose_output(self, result: Dict[str, Any]) -> None:
        """
        Display detailed verbose output.
        
        Args:
            result: Pipeline result dictionary
        """
        self.console.print(Panel(
            "[bold cyan]Verbose Output[/bold cyan]",
            border_style="cyan"
        ))
        
        # Research findings
        if result.get("research_findings"):
            self.console.print("\n[bold]📚 Research Findings:[/bold]")
            self.console.print(result["research_findings"][:500] + "..." 
                             if len(result["research_findings"]) > 500 
                             else result["research_findings"])
        
        # Retrieved documents
        if result.get("retrieved_documents"):
            self.console.print(f"\n[bold]📄 Retrieved Documents:[/bold] {len(result['retrieved_documents'])} documents")
            for i, doc in enumerate(result["retrieved_documents"][:3], 1):
                self.console.print(f"  {i}. {doc.get('title', 'Untitled')}")
        
        # Edit notes
        if result.get("edit_notes"):
            self.console.print("\n[bold]✏️  Edit Notes:[/bold]")
            self.console.print(result["edit_notes"])
        
        # Agent logs
        if result.get("agent_logs"):
            self.console.print(f"\n[bold]📋 Agent Logs:[/bold] {len(result['agent_logs'])} entries")
        
        self.console.print()
    
    def _display_content_preview(self, content: str, max_length: int = 500) -> None:
        """
        Show preview of generated content.
        
        Args:
            content: Full content text
            max_length: Maximum characters to show
        """
        preview = content[:max_length]
        if len(content) > max_length:
            preview += "..."
        
        self.console.print("[bold]📝 Content Preview:[/bold]")
        self.console.print(Panel(
            preview,
            border_style="blue",
            padding=(1, 2)
        ))
        self.console.print()
    
    def _display_execution_summary(self, execution_times: Dict[str, float], content: str) -> None:
        """
        Show execution time summary.
        
        Args:
            execution_times: Dictionary of agent execution times
            content: Generated content for word count
        """
        total_time = sum(execution_times.values())
        word_count = len(content.split())
        
        self.console.print("[bold]📊 Execution Summary:[/bold]")
        
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")
        
        table.add_row("Total Time:", f"{total_time:.1f}s")
        table.add_row("Word Count:", f"{word_count:,} words")
        
        self.console.print(table)
        
        # Agent execution times
        if execution_times:
            self.console.print("\n[bold]Agent Execution Times:[/bold]")
            time_table = Table(show_header=False, box=None, padding=(0, 2))
            time_table.add_column("Agent", style="cyan", width=15)
            time_table.add_column("Time", style="yellow")
            
            for agent, duration in execution_times.items():
                time_table.add_row(f"  {agent.capitalize()}:", f"{duration:.1f}s")
            
            self.console.print(time_table)
        
        self.console.print()
    
    def _display_metadata(self, metadata: Dict[str, Any]) -> None:
        """
        Format and display SEO metadata.
        
        Args:
            metadata: SEO metadata dictionary
        """
        self.console.print("[bold]🎯 SEO Metadata:[/bold]")
        
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Field", style="cyan")
        table.add_column("Value", style="white")
        
        if metadata.get("meta_title"):
            table.add_row("Title:", metadata["meta_title"])
        
        if metadata.get("meta_description"):
            desc = metadata["meta_description"]
            if len(desc) > 100:
                desc = desc[:100] + "..."
            table.add_row("Description:", desc)
        
        if metadata.get("slug"):
            table.add_row("Slug:", metadata["slug"])
        
        if metadata.get("keywords"):
            keywords = metadata["keywords"]
            if isinstance(keywords, list):
                keywords = ", ".join(keywords[:5])
            table.add_row("Keywords:", keywords)
        
        self.console.print(table)
        self.console.print()
    
    def _display_output_files(self, output_files: Dict[str, str]) -> None:
        """
        Display output file locations.
        
        Args:
            output_files: Dictionary of file type to file path
        """
        self.console.print("[bold]📁 Output Files:[/bold]")
        
        table = Table(show_header=False, box=None, padding=(0, 2))
        table.add_column("Type", style="cyan")
        table.add_column("Path", style="green")
        
        file_labels = {
            "content_md": "Content (Markdown):",
            "content_html": "Content (HTML):",
            "metadata": "Metadata:",
            "brief": "Brief:"
        }
        
        for file_type, file_path in output_files.items():
            label = file_labels.get(file_type, f"{file_type}:")
            table.add_row(label, file_path)
        
        self.console.print(table)
    
    def _get_error_suggestion(self, error: Exception) -> Optional[str]:
        """
        Get helpful suggestion based on error type.
        
        Args:
            error: Exception that occurred
            
        Returns:
            Suggestion string or None
        """
        error_str = str(error).lower()
        
        if "api key" in error_str or "authentication" in error_str:
            return "Check your OPENAI_API_KEY in the .env file"
        
        if "rate limit" in error_str:
            return "Wait a moment and try again, or check your API quota"
        
        if "timeout" in error_str:
            return "The request timed out. Try again or check your internet connection"
        
        if "connection" in error_str:
            return "Check your internet connection and try again"
        
        if "vector" in error_str or "chroma" in error_str:
            return "Try running 'python data/ingest.py' to initialize the vector database"
        
        return "Run with --debug flag for more details"
    
    def display_header(self, request: str, request_id: str) -> None:
        """
        Display pipeline header.
        
        Args:
            request: Content request
            request_id: Unique request ID
        """
        self.console.print(Panel(
            f"[bold cyan]Content Request:[/bold cyan] {request}\n"
            f"[bold cyan]Request ID:[/bold cyan] {request_id[:8]}...",
            title="Content Generation Pipeline",
            border_style="cyan"
        ))
        self.console.print()
