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