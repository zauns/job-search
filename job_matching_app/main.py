"""
Main entry point for the Job Matching Application
"""
import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

from .config import ensure_directories, get_settings
from .database import init_db
from .services.resume_service import ResumeService, LaTeXCompilationError

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
    resume_service = ResumeService()
    
    console.print("\n[bold]Application Status:[/bold]")
    console.print(f"• App Directory: {settings.app_dir}")
    console.print(f"• Database: {settings.database_url}")
    console.print(f"• Ollama Host: {settings.ollama_host}")
    console.print(f"• Jobs per page: {settings.jobs_per_page}")
    
    # Check LaTeX installation
    latex_installed, latex_info = resume_service.check_latex_installation()
    latex_status = "[green]✓[/green]" if latex_installed else "[red]✗[/red]"
    console.print(f"• LaTeX: {latex_status} {latex_info}")


@main.group()
def resume():
    """Resume management commands"""
    pass


@resume.command("upload")
@click.argument("file_path", type=click.Path(exists=True))
@click.option("--filename", help="Custom filename for the resume")
def upload_resume(file_path, filename):
    """Upload a LaTeX resume"""
    resume_service = ResumeService()
    
    try:
        with console.status("[bold green]Uploading resume..."):
            uploaded_resume = resume_service.upload_latex_resume(file_path, filename)
        
        console.print(f"[green]✓[/green] Resume uploaded successfully!")
        console.print(f"• ID: {uploaded_resume.id}")
        console.print(f"• Filename: {uploaded_resume.filename}")
        console.print(f"• Content length: {len(uploaded_resume.latex_content)} characters")
        
    except FileNotFoundError as e:
        console.print(f"[red]Error:[/red] {e}")
    except ValueError as e:
        console.print(f"[red]Error:[/red] {e}")
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")


@resume.command("list")
def list_resumes():
    """List all uploaded resumes"""
    resume_service = ResumeService()
    resumes = resume_service.get_all_resumes()
    
    if not resumes:
        console.print("[yellow]No resumes found.[/yellow]")
        return
    
    table = Table(title="Uploaded Resumes")
    table.add_column("ID", style="cyan", no_wrap=True)
    table.add_column("Filename", style="magenta")
    table.add_column("Keywords", style="green")
    table.add_column("Content Length", justify="right", style="blue")
    
    for resume in resumes:
        keywords_count = len(resume.all_keywords)
        keywords_text = f"{keywords_count} keywords" if keywords_count > 0 else "No keywords"
        
        table.add_row(
            str(resume.id),
            resume.filename,
            keywords_text,
            f"{len(resume.latex_content):,} chars"
        )
    
    console.print(table)


@resume.command("compile")
@click.argument("resume_id", type=int)
@click.option("--output", "-o", help="Output PDF file path")
def compile_resume(resume_id, output):
    """Compile a resume to PDF"""
    resume_service = ResumeService()
    
    # Get resume
    resume_obj = resume_service.get_resume_by_id(resume_id)
    if not resume_obj:
        console.print(f"[red]Error:[/red] Resume with ID {resume_id} not found")
        return
    
    try:
        with console.status("[bold green]Compiling LaTeX to PDF..."):
            pdf_content = resume_service.compile_to_pdf(resume_obj.latex_content, output)
        
        if output:
            console.print(f"[green]✓[/green] PDF saved to: {output}")
        else:
            console.print(f"[green]✓[/green] PDF compiled successfully ({len(pdf_content):,} bytes)")
        
    except LaTeXCompilationError as e:
        console.print(f"[red]Compilation Error:[/red] {e}")
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")


@resume.command("delete")
@click.argument("resume_id", type=int)
@click.confirmation_option(prompt="Are you sure you want to delete this resume?")
def delete_resume(resume_id):
    """Delete a resume"""
    resume_service = ResumeService()
    
    success = resume_service.delete_resume(resume_id)
    if success:
        console.print(f"[green]✓[/green] Resume {resume_id} deleted successfully")
    else:
        console.print(f"[red]Error:[/red] Resume with ID {resume_id} not found")


@resume.command("show")
@click.argument("resume_id", type=int)
def show_resume(resume_id):
    """Show resume details"""
    resume_service = ResumeService()
    
    resume_obj = resume_service.get_resume_by_id(resume_id)
    if not resume_obj:
        console.print(f"[red]Error:[/red] Resume with ID {resume_id} not found")
        return
    
    console.print(f"\n[bold]Resume Details:[/bold]")
    console.print(f"• ID: {resume_obj.id}")
    console.print(f"• Filename: {resume_obj.filename}")
    console.print(f"• Content length: {len(resume_obj.latex_content):,} characters")
    console.print(f"• Extracted keywords: {len(resume_obj.extracted_keywords)}")
    console.print(f"• User keywords: {len(resume_obj.user_keywords)}")
    console.print(f"• Total keywords: {len(resume_obj.all_keywords)}")
    
    if resume_obj.all_keywords:
        console.print(f"\n[bold]Keywords:[/bold]")
        for keyword in resume_obj.all_keywords:
            console.print(f"  • {keyword}")


@resume.command("keywords")
@click.argument("resume_id", type=int)
def manage_keywords(resume_id):
    """Manage keywords for a resume (interactive mode)"""
    resume_service = ResumeService()
    
    # Get resume
    resume_obj = resume_service.get_resume_by_id(resume_id)
    if not resume_obj:
        console.print(f"[red]Error:[/red] Resume with ID {resume_id} not found")
        return
    
    console.print(f"\n[bold]Keyword Management for Resume: {resume_obj.filename}[/bold]")
    
    while True:
        # Display current keywords
        _display_keywords(resume_obj)
        
        # Show menu
        console.print("\n[bold]Options:[/bold]")
        console.print("1. Extract keywords with AI")
        console.print("2. Add keyword")
        console.print("3. Remove keyword")
        console.print("4. Clear user keywords")
        console.print("5. Exit")
        
        choice = click.prompt("\nSelect option", type=int, default=5)
        
        if choice == 1:
            _extract_keywords_interactive(resume_service, resume_obj)
        elif choice == 2:
            _add_keyword_interactive(resume_service, resume_obj)
        elif choice == 3:
            _remove_keyword_interactive(resume_service, resume_obj)
        elif choice == 4:
            _clear_user_keywords_interactive(resume_service, resume_obj)
        elif choice == 5:
            console.print("[green]Keyword management completed.[/green]")
            break
        else:
            console.print("[red]Invalid option. Please try again.[/red]")
        
        # Refresh resume object to get updated keywords
        resume_obj = resume_service.get_resume_by_id(resume_id)


@resume.command("extract-keywords")
@click.argument("resume_id", type=int)
def extract_keywords(resume_id):
    """Extract keywords from resume using AI"""
    resume_service = ResumeService()
    
    # Get resume
    resume_obj = resume_service.get_resume_by_id(resume_id)
    if not resume_obj:
        console.print(f"[red]Error:[/red] Resume with ID {resume_id} not found")
        return
    
    try:
        with console.status("[bold green]Extracting keywords with AI..."):
            result = resume_service.extract_keywords_with_ai(resume_id)
        
        console.print(f"[green]✓[/green] Keywords extracted successfully!")
        console.print(f"• Language detected: {result.language_detected}")
        console.print(f"• Confidence: {result.confidence:.2f}")
        console.print(f"• Fallback used: {'Yes' if result.fallback_used else 'No'}")
        console.print(f"• Keywords found: {len(result.keywords)}")
        
        if result.keywords:
            console.print("\n[bold]Extracted Keywords:[/bold]")
            for keyword in result.keywords:
                console.print(f"  • {keyword}")
        
    except Exception as e:
        console.print(f"[red]Error extracting keywords:[/red] {e}")


@resume.command("add-keyword")
@click.argument("resume_id", type=int)
@click.argument("keyword")
def add_keyword(resume_id, keyword):
    """Add a keyword to resume"""
    resume_service = ResumeService()
    
    # Get resume
    resume_obj = resume_service.get_resume_by_id(resume_id)
    if not resume_obj:
        console.print(f"[red]Error:[/red] Resume with ID {resume_id} not found")
        return
    
    success = resume_service.add_user_keyword(resume_id, keyword)
    if success:
        console.print(f"[green]✓[/green] Keyword '{keyword}' added successfully")
    else:
        console.print(f"[yellow]Keyword '{keyword}' already exists[/yellow]")


@resume.command("remove-keyword")
@click.argument("resume_id", type=int)
@click.argument("keyword")
def remove_keyword(resume_id, keyword):
    """Remove a keyword from resume"""
    resume_service = ResumeService()
    
    # Get resume
    resume_obj = resume_service.get_resume_by_id(resume_id)
    if not resume_obj:
        console.print(f"[red]Error:[/red] Resume with ID {resume_id} not found")
        return
    
    success = resume_service.remove_user_keyword(resume_id, keyword)
    if success:
        console.print(f"[green]✓[/green] Keyword '{keyword}' removed successfully")
    else:
        console.print(f"[yellow]Keyword '{keyword}' not found in user keywords[/yellow]")


def _display_keywords(resume_obj):
    """Display keywords in a formatted table"""
    table = Table(title=f"Keywords for {resume_obj.filename}")
    table.add_column("Type", style="cyan", no_wrap=True)
    table.add_column("Keywords", style="green")
    table.add_column("Count", justify="right", style="blue")
    
    # AI-extracted keywords
    if resume_obj.extracted_keywords:
        extracted_text = ", ".join(resume_obj.extracted_keywords)
        table.add_row("AI Extracted", extracted_text, str(len(resume_obj.extracted_keywords)))
    else:
        table.add_row("AI Extracted", "[dim]No keywords extracted[/dim]", "0")
    
    # User keywords
    if resume_obj.user_keywords:
        user_text = ", ".join(resume_obj.user_keywords)
        table.add_row("User Added", user_text, str(len(resume_obj.user_keywords)))
    else:
        table.add_row("User Added", "[dim]No user keywords[/dim]", "0")
    
    # Total
    all_keywords = resume_obj.all_keywords
    if all_keywords:
        total_text = ", ".join(sorted(all_keywords))
        table.add_row("Total Unique", total_text, str(len(all_keywords)))
    else:
        table.add_row("Total Unique", "[dim]No keywords[/dim]", "0")
    
    console.print(table)


def _extract_keywords_interactive(resume_service, resume_obj):
    """Interactive keyword extraction"""
    try:
        with console.status("[bold green]Extracting keywords with AI..."):
            result = resume_service.extract_keywords_with_ai(resume_obj.id)
        
        console.print(f"[green]✓[/green] Keywords extracted!")
        console.print(f"• Language: {result.language_detected}")
        console.print(f"• Confidence: {result.confidence:.2f}")
        console.print(f"• Fallback: {'Yes' if result.fallback_used else 'No'}")
        console.print(f"• Found: {len(result.keywords)} keywords")
        
        if result.keywords:
            console.print("\n[bold]New Keywords:[/bold]")
            for keyword in result.keywords:
                console.print(f"  • {keyword}")
        
    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")


def _add_keyword_interactive(resume_service, resume_obj):
    """Interactive keyword addition"""
    keyword = click.prompt("Enter keyword to add").strip()
    if not keyword:
        console.print("[red]Keyword cannot be empty[/red]")
        return
    
    success = resume_service.add_user_keyword(resume_obj.id, keyword)
    if success:
        console.print(f"[green]✓[/green] Added keyword: '{keyword}'")
    else:
        console.print(f"[yellow]Keyword '{keyword}' already exists[/yellow]")


def _remove_keyword_interactive(resume_service, resume_obj):
    """Interactive keyword removal"""
    if not resume_obj.user_keywords:
        console.print("[yellow]No user keywords to remove[/yellow]")
        return
    
    console.print("\n[bold]User Keywords:[/bold]")
    for i, keyword in enumerate(resume_obj.user_keywords, 1):
        console.print(f"{i}. {keyword}")
    
    try:
        choice = click.prompt("Enter number to remove (or 0 to cancel)", type=int)
        if choice == 0:
            return
        if 1 <= choice <= len(resume_obj.user_keywords):
            keyword = resume_obj.user_keywords[choice - 1]
            success = resume_service.remove_user_keyword(resume_obj.id, keyword)
            if success:
                console.print(f"[green]✓[/green] Removed keyword: '{keyword}'")
            else:
                console.print(f"[red]Failed to remove keyword: '{keyword}'[/red]")
        else:
            console.print("[red]Invalid selection[/red]")
    except (ValueError, click.Abort):
        console.print("[yellow]Operation cancelled[/yellow]")


def _clear_user_keywords_interactive(resume_service, resume_obj):
    """Interactive user keywords clearing"""
    if not resume_obj.user_keywords:
        console.print("[yellow]No user keywords to clear[/yellow]")
        return
    
    if click.confirm(f"Clear all {len(resume_obj.user_keywords)} user keywords?"):
        success = resume_service.clear_user_keywords(resume_obj.id)
        if success:
            console.print("[green]✓[/green] All user keywords cleared")
        else:
            console.print("[red]Failed to clear keywords[/red]")


@main.command("check-latex")
def check_latex():
    """Check LaTeX installation"""
    resume_service = ResumeService()
    latex_installed, latex_info = resume_service.check_latex_installation()
    
    if latex_installed:
        console.print(f"[green]✓ LaTeX is installed:[/green] {latex_info}")
    else:
        console.print(f"[red]✗ LaTeX not available:[/red] {latex_info}")
        console.print("\n[yellow]To install LaTeX:[/yellow]")
        console.print("• Windows: Install MiKTeX or TeX Live")
        console.print("• macOS: Install MacTeX")
        console.print("• Linux: Install texlive-full package")


if __name__ == "__main__":
    main()