"""
Main entry point for the Job Matching Application
"""
import click
from rich.console import Console
from rich.panel import Panel

from .config import ensure_directories, get_settings
from .database import init_db

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def main():
    """Job Matching Application - AI-powered job search and resume adaptation"""
    # Ensure directories exist
    ensure_directories()
    
    # Initialize database
    init_db()
    
    console.print(Panel.fit(
        "[bold blue]Job Matching Application[/bold blue]\n"
        "AI-powered job search and resume adaptation",
        border_style="blue"
    ))


@main.command()
def status():
    """Show application status"""
    settings = get_settings()
    
    console.print("\n[bold]Application Status:[/bold]")
    console.print(f"• App Directory: {settings.app_dir}")
    console.print(f"• Database: {settings.database_url}")
    console.print(f"• Ollama Host: {settings.ollama_host}")
    console.print(f"• Jobs per page: {settings.jobs_per_page}")


if __name__ == "__main__":
    main()