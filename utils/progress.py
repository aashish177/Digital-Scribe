"""
Progress display utilities for the CLI using rich library.

Provides real-time progress tracking for the content generation pipeline.
"""

from typing import Dict, Optional
from contextlib import contextmanager

from rich.console import Console
from rich.table import Table
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn


class PipelineProgress:
    """Track and display progress for the content generation pipeline."""
    
    def __init__(self, console: Console):
        """
        Initialize progress tracker.
        
        Args:
            console: Rich console instance
        """
        self.console = console
        self.agents = ["Planner", "Researcher", "Writer", "Editor", "SEO"]
        self.status = {agent: "pending" for agent in self.agents}
        self.times = {agent: None for agent in self.agents}
        self.current_agent = None
        self.live = None
    
    def start_agent(self, agent_name: str) -> None:
        """
        Mark agent as running.
        
        Args:
            agent_name: Name of the agent starting execution
        """
        self.current_agent = agent_name
        self.status[agent_name] = "running"
    
    def complete_agent(self, agent_name: str, duration: float) -> None:
        """
        Mark agent as complete with execution time.
        
        Args:
            agent_name: Name of the agent that completed
            duration: Execution time in seconds
        """
        self.status[agent_name] = "done"
        self.times[agent_name] = duration
        if self.current_agent == agent_name:
            self.current_agent = None
    
    def fail_agent(self, agent_name: str, error: str) -> None:
        """
        Mark agent as failed.
        
        Args:
            agent_name: Name of the agent that failed
            error: Error message
        """
        self.status[agent_name] = "failed"
        if self.current_agent == agent_name:
            self.current_agent = None
    
    def render(self) -> Table:
        """
        Render current status as a table.
        
        Returns:
            Rich Table with current pipeline status
        """
        table = Table(show_header=True, header_style="bold cyan", border_style="cyan")
        table.add_column("Agent", style="cyan", width=15)
        table.add_column("Status", width=20)
        table.add_column("Time", justify="right", width=10)
        
        for agent in self.agents:
            status = self.status[agent]
            time_str = f"{self.times[agent]:.1f}s" if self.times[agent] else "-"
            
            # Status with icon
            if status == "done":
                status_display = "[green]✓ Done[/green]"
            elif status == "running":
                status_display = "[yellow]⋯ Running[/yellow]"
            elif status == "failed":
                status_display = "[red]✗ Failed[/red]"
            else:  # pending
                status_display = "[dim]Pending[/dim]"
            
            table.add_row(agent, status_display, time_str)
        
        # Add overall progress bar
        completed = sum(1 for s in self.status.values() if s == "done")
        total = len(self.agents)
        progress_pct = int((completed / total) * 100)
        
        # Progress bar
        bar_width = 40
        filled = int((completed / total) * bar_width)
        bar = "━" * filled + "╸" + "─" * (bar_width - filled - 1) if filled < bar_width else "━" * bar_width
        
        table.add_row(
            "",
            f"[cyan]Overall Progress:[/cyan]",
            f"{progress_pct}%"
        )
        table.add_row(
            "",
            f"[cyan]{bar}[/cyan]",
            f"{completed}/{total}"
        )
        
        return table
    
    @contextmanager
    def live_display(self):
        """
        Context manager for live progress display.
        
        Usage:
            with progress.live_display():
                # Run pipeline
                pass
        """
        with Live(self.render(), console=self.console, refresh_per_second=4) as live:
            self.live = live
            try:
                yield self
            finally:
                # Final update
                live.update(self.render())
                self.live = None
    
    def update_display(self) -> None:
        """Update the live display if active."""
        if self.live:
            self.live.update(self.render())
    
    def get_total_time(self) -> float:
        """
        Get total execution time.
        
        Returns:
            Total time in seconds
        """
        return sum(t for t in self.times.values() if t is not None)
    
    def get_summary(self) -> Dict[str, any]:
        """
        Get execution summary.
        
        Returns:
            Dictionary with execution statistics
        """
        return {
            "total_time": self.get_total_time(),
            "agents_completed": sum(1 for s in self.status.values() if s == "done"),
            "agents_failed": sum(1 for s in self.status.values() if s == "failed"),
            "execution_times": {
                agent: time for agent, time in self.times.items() if time is not None
            }
        }


class SimpleSpinner:
    """Simple spinner for individual operations."""
    
    def __init__(self, console: Console, text: str):
        """
        Initialize spinner.
        
        Args:
            console: Rich console instance
            text: Text to display with spinner
        """
        self.console = console
        self.text = text
        self.progress = None
        self.task = None
    
    def __enter__(self):
        """Start spinner."""
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            TimeElapsedColumn(),
            console=self.console
        )
        self.progress.start()
        self.task = self.progress.add_task(self.text, total=None)
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop spinner."""
        if self.progress:
            self.progress.stop()
        return False
    
    def update(self, text: str):
        """Update spinner text."""
        if self.progress and self.task is not None:
            self.progress.update(self.task, description=text)
