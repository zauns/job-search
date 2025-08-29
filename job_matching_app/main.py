"""
Main entry point for the Job Matching Application
"""
import click
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.prompt import Prompt, IntPrompt, Confirm
from rich.columns import Columns
from rich.layout import Layout
from rich.align import Align

from .config import ensure_directories, get_settings
from .database import init_db
from .services.resume_service import ResumeService, LaTeXCompilationError
from .services.job_listing_service import JobListingService
from .services.ai_matching_service import AIMatchingService

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


@resume.command("adapt")
@click.argument("resume_id", type=int)
@click.argument("job_id", type=int)
def adapt_resume(resume_id, job_id):
    """Adapt a resume for a specific job using AI"""
    from .services.latex_editor_service import LaTeXEditorService
    
    resume_service = ResumeService()
    job_service = JobListingService()
    editor_service = LaTeXEditorService()
    
    # Verify resume exists
    resume_obj = resume_service.get_resume_by_id(resume_id)
    if not resume_obj:
        console.print(f"[red]Error:[/red] Resume with ID {resume_id} not found")
        return
    
    # Verify job exists
    job_obj = job_service.get_job_by_id(job_id)
    if not job_obj:
        console.print(f"[red]Error:[/red] Job with ID {job_id} not found")
        return
    
    console.print(f"\n[bold]Adapting Resume for Job:[/bold]")
    console.print(f"• Resume: {resume_obj.filename}")
    console.print(f"• Job: {job_obj.title} at {job_obj.company}")
    
    try:
        with console.status("[bold green]Adapting resume with AI..."):
            draft_id = resume_service.adapt_resume_for_job(resume_id, job_id)
        
        console.print(f"[green]✓[/green] Resume adapted successfully!")
        console.print(f"• Draft ID: {draft_id}")
        
        # Get draft info
        draft_info = resume_service.get_adapted_resume_draft(draft_id)
        if draft_info:
            console.print(f"• Status: {draft_info['status']}")
            console.print(f"• Created: {draft_info['created_at']}")
        
        # Ask if user wants to edit the adapted resume
        if click.confirm("\nWould you like to review and edit the adapted resume?"):
            _interactive_resume_editor(editor_service, draft_id)
        
    except Exception as e:
        console.print(f"[red]Error adapting resume:[/red] {e}")


@resume.command("drafts")
@click.argument("resume_id", type=int)
def list_drafts(resume_id):
    """List all adapted resume drafts for a resume"""
    resume_service = ResumeService()
    
    # Verify resume exists
    resume_obj = resume_service.get_resume_by_id(resume_id)
    if not resume_obj:
        console.print(f"[red]Error:[/red] Resume with ID {resume_id} not found")
        return
    
    drafts = resume_service.get_adapted_resume_drafts_for_resume(resume_id)
    
    if not drafts:
        console.print(f"[yellow]No adapted drafts found for resume: {resume_obj.filename}[/yellow]")
        return
    
    table = Table(title=f"Adapted Resume Drafts for: {resume_obj.filename}")
    table.add_column("Draft ID", style="cyan", no_wrap=True)
    table.add_column("Job", style="magenta")
    table.add_column("Company", style="blue")
    table.add_column("Status", style="green")
    table.add_column("Created", style="yellow")
    
    for draft in drafts:
        table.add_row(
            str(draft['id']),
            draft['job_title'],
            draft['job_company'],
            draft['status'],
            draft['created_at'].strftime("%Y-%m-%d %H:%M")
        )
    
    console.print(table)


@resume.command("edit-draft")
@click.argument("draft_id", type=int)
def edit_draft(draft_id):
    """Edit an adapted resume draft"""
    from .services.latex_editor_service import LaTeXEditorService
    
    editor_service = LaTeXEditorService()
    
    # Verify draft exists
    draft_info = editor_service.get_adapted_resume_for_editing(draft_id)
    if not draft_info:
        console.print(f"[red]Error:[/red] Adapted resume draft with ID {draft_id} not found")
        return
    
    console.print(f"\n[bold]Editing Adapted Resume Draft:[/bold]")
    console.print(f"• Draft ID: {draft_info['id']}")
    console.print(f"• Original Resume: {draft_info['original_resume_filename']}")
    console.print(f"• Job: {draft_info['job_title']} at {draft_info['job_company']}")
    console.print(f"• Status: {draft_info['status']}")
    
    _interactive_resume_editor(editor_service, draft_id)


@resume.command("compile-draft")
@click.argument("draft_id", type=int)
@click.option("--output", "-o", help="Output PDF file path")
def compile_draft(draft_id, output):
    """Compile an adapted resume draft to PDF"""
    from .services.latex_editor_service import LaTeXEditorService
    
    editor_service = LaTeXEditorService()
    
    # Verify draft exists
    draft_info = editor_service.get_adapted_resume_for_editing(draft_id)
    if not draft_info:
        console.print(f"[red]Error:[/red] Adapted resume draft with ID {draft_id} not found")
        return
    
    console.print(f"\n[bold]Compiling Adapted Resume Draft:[/bold]")
    console.print(f"• Draft ID: {draft_info['id']}")
    console.print(f"• Job: {draft_info['job_title']} at {draft_info['job_company']}")
    
    try:
        with console.status("[bold green]Compiling LaTeX to PDF..."):
            success, message, pdf_content = editor_service.compile_and_save_pdf(draft_id, output)
        
        if success:
            console.print(f"[green]✓[/green] {message}")
        else:
            console.print(f"[red]Compilation Error:[/red] {message}")
        
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")


def _interactive_resume_editor(editor_service, draft_id):
    """Interactive resume editor interface"""
    while True:
        # Get current draft info
        draft_info = editor_service.get_adapted_resume_for_editing(draft_id)
        if not draft_info:
            console.print(f"[red]Error:[/red] Draft not found")
            return
        
        console.print(f"\n[bold]Resume Editor - Draft {draft_id}[/bold]")
        console.print(f"• Job: {draft_info['job_title']} at {draft_info['job_company']}")
        console.print(f"• Status: {draft_info['status']}")
        console.print(f"• Content length: {len(draft_info['adapted_latex_content']):,} characters")
        
        # Show menu
        console.print("\n[bold]Editor Options:[/bold]")
        console.print("1. View LaTeX content")
        console.print("2. Validate LaTeX")
        console.print("3. Preview compilation")
        console.print("4. Edit content (external editor)")
        console.print("5. Get editing suggestions")
        console.print("6. Compile to PDF")
        console.print("7. Exit editor")
        
        choice = click.prompt("\nSelect option", type=int, default=7)
        
        if choice == 1:
            _view_latex_content(draft_info['adapted_latex_content'])
        elif choice == 2:
            _validate_latex_content(editor_service, draft_info['adapted_latex_content'])
        elif choice == 3:
            _preview_compilation(editor_service, draft_info['adapted_latex_content'])
        elif choice == 4:
            _edit_latex_content(editor_service, draft_id, draft_info['adapted_latex_content'])
        elif choice == 5:
            _show_editing_suggestions(editor_service, draft_info['adapted_latex_content'])
        elif choice == 6:
            _compile_draft_interactive(editor_service, draft_id)
        elif choice == 7:
            console.print("[green]Exiting resume editor.[/green]")
            break
        else:
            console.print("[red]Invalid option. Please try again.[/red]")


def _view_latex_content(latex_content):
    """Display LaTeX content"""
    console.print("\n[bold]LaTeX Content:[/bold]")
    console.print(Panel(latex_content, title="LaTeX Source", border_style="blue"))
    click.pause("\nPress any key to continue...")


def _validate_latex_content(editor_service, latex_content):
    """Validate LaTeX content and show results"""
    validation = editor_service.validate_latex_content(latex_content)
    
    console.print(f"\n[bold]LaTeX Validation Results:[/bold]")
    
    if validation.is_valid:
        console.print("[green]✓ LaTeX content is valid![/green]")
    else:
        console.print("[red]✗ LaTeX content has errors:[/red]")
        for error in validation.errors:
            console.print(f"  • [red]{error}[/red]")
    
    if validation.warnings:
        console.print("\n[yellow]Warnings:[/yellow]")
        for warning in validation.warnings:
            console.print(f"  • [yellow]{warning}[/yellow]")
    
    click.pause("\nPress any key to continue...")


def _preview_compilation(editor_service, latex_content):
    """Preview LaTeX compilation"""
    console.print("\n[bold]Compilation Preview:[/bold]")
    
    with console.status("[bold green]Testing compilation..."):
        success, message = editor_service.preview_latex_compilation(latex_content)
    
    if success:
        console.print(f"[green]✓ {message}[/green]")
    else:
        console.print(f"[red]✗ {message}[/red]")
    
    click.pause("\nPress any key to continue...")


def _edit_latex_content(editor_service, draft_id, current_content):
    """Edit LaTeX content using external editor"""
    import tempfile
    import os
    
    console.print("\n[bold]External Editor Mode:[/bold]")
    console.print("Opening LaTeX content in external editor...")
    
    # Create temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.tex', delete=False) as f:
        f.write(current_content)
        temp_file = f.name
    
    try:
        # Open in external editor
        click.edit(filename=temp_file)
        
        # Read back the content
        with open(temp_file, 'r', encoding='utf-8') as f:
            edited_content = f.read()
        
        # Check if content was changed
        if edited_content != current_content:
            console.print("\n[bold]Content was modified.[/bold]")
            
            # Validate the edited content
            validation = editor_service.validate_latex_content(edited_content)
            if not validation.is_valid:
                console.print("[red]Warning: Edited content has validation errors:[/red]")
                for error in validation.errors:
                    console.print(f"  • [red]{error}[/red]")
                
                if not click.confirm("Save anyway?"):
                    console.print("[yellow]Changes discarded.[/yellow]")
                    return
            
            # Save the changes
            success, errors = editor_service.save_edited_resume(draft_id, edited_content)
            if success:
                console.print("[green]✓ Changes saved successfully![/green]")
            else:
                console.print("[red]Failed to save changes:[/red]")
                for error in errors:
                    console.print(f"  • [red]{error}[/red]")
        else:
            console.print("[yellow]No changes made.[/yellow]")
    
    finally:
        # Clean up temporary file
        try:
            os.unlink(temp_file)
        except:
            pass


def _show_editing_suggestions(editor_service, latex_content):
    """Show LaTeX editing suggestions"""
    suggestions = editor_service.get_latex_editing_suggestions(latex_content)
    
    console.print("\n[bold]LaTeX Editing Suggestions:[/bold]")
    
    if suggestions:
        for i, suggestion in enumerate(suggestions, 1):
            console.print(f"{i}. {suggestion}")
    else:
        console.print("[green]No specific suggestions - your LaTeX looks good![/green]")
    
    # Show template suggestions
    templates = editor_service.get_latex_template_suggestions()
    console.print("\n[bold]Template Suggestions:[/bold]")
    for template in templates:
        console.print(f"• [cyan]{template['name']}[/cyan]: {template['description']}")
        console.print(f"  Example: [dim]{template['example']}[/dim]")
    
    click.pause("\nPress any key to continue...")


def _compile_draft_interactive(editor_service, draft_id):
    """Interactive PDF compilation"""
    console.print("\n[bold]PDF Compilation:[/bold]")
    
    output_path = click.prompt("Enter output PDF path (or press Enter for default)", default="", show_default=False)
    if not output_path:
        output_path = None
    
    try:
        with console.status("[bold green]Compiling to PDF..."):
            success, message, pdf_content = editor_service.compile_and_save_pdf(draft_id, output_path)
        
        if success:
            console.print(f"[green]✓ {message}[/green]")
        else:
            console.print(f"[red]✗ {message}[/red]")
    
    except Exception as e:
        console.print(f"[red]Compilation error:[/red] {e}")
    
    click.pause("\nPress any key to continue...")


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


@main.group()
def jobs():
    """Job listing management commands"""
    pass


@jobs.command("list")
@click.option("--page", "-p", default=1, help="Page number")
@click.option("--per-page", default=None, type=int, help="Jobs per page")
@click.option("--sort-by", default="scraped_at", help="Sort field (scraped_at, title, company)")
@click.option("--sort-order", default="desc", type=click.Choice(['asc', 'desc']), help="Sort order")
@click.option("--company", help="Filter by company name")
@click.option("--location", help="Filter by location")
@click.option("--remote-type", type=click.Choice(['remote', 'onsite', 'hybrid']), help="Filter by remote type")
@click.option("--experience-level", type=click.Choice(['intern', 'junior', 'mid', 'senior', 'lead', 'manager']), help="Filter by experience level")
@click.option("--source-site", help="Filter by source site")
@click.option("--interactive", "-i", is_flag=True, help="Interactive job browsing mode")
def list_jobs(page, per_page, sort_by, sort_order, company, location, remote_type, experience_level, source_site, interactive):
    """List job listings with pagination and filtering"""
    job_service = JobListingService()
    
    # Build filters
    filters = {}
    if company:
        filters['company'] = company
    if location:
        filters['location'] = location
    if remote_type:
        filters['remote_type'] = remote_type
    if experience_level:
        filters['experience_level'] = experience_level
    if source_site:
        filters['source_site'] = source_site
    
    if interactive:
        _interactive_job_browser(job_service, filters, sort_by, sort_order, per_page)
    else:
        _display_job_listings_page(job_service, page, per_page, sort_by, sort_order, filters)


@jobs.command("search")
@click.argument("search_term")
@click.option("--page", "-p", default=1, help="Page number")
@click.option("--per-page", default=None, type=int, help="Jobs per page")
@click.option("--sort-by", default="scraped_at", help="Sort field")
@click.option("--sort-order", default="desc", type=click.Choice(['asc', 'desc']), help="Sort order")
@click.option("--interactive", "-i", is_flag=True, help="Interactive search results browsing")
def search_jobs(search_term, page, per_page, sort_by, sort_order, interactive):
    """Search job listings by title, company, or description"""
    job_service = JobListingService()
    
    if interactive:
        _interactive_search_browser(job_service, search_term, sort_by, sort_order, per_page)
    else:
        job_listings, total_count, total_pages = job_service.search_jobs(
            search_term, page, per_page, sort_by, sort_order
        )
        
        console.print(f"\n[bold]Search Results for '{search_term}':[/bold]")
        _display_job_listings(job_listings, page, total_pages, total_count)


@jobs.command("show")
@click.argument("job_id", type=int)
@click.option("--resume-id", type=int, help="Show compatibility with specific resume")
def show_job(job_id, resume_id):
    """Show detailed information about a specific job"""
    job_service = JobListingService()
    
    if resume_id:
        job_listing, job_match = job_service.get_job_with_match(job_id, resume_id)
    else:
        job_listing = job_service.get_job_by_id(job_id)
        job_match = None
    
    if not job_listing:
        console.print(f"[red]Error:[/red] Job with ID {job_id} not found")
        return
    
    _display_job_details(job_listing, job_match)


@jobs.command("match")
@click.argument("resume_id", type=int)
@click.option("--page", "-p", default=1, help="Page number")
@click.option("--per-page", default=None, type=int, help="Jobs per page")
@click.option("--min-compatibility", type=float, help="Minimum compatibility score (0.0-1.0)")
@click.option("--interactive", "-i", is_flag=True, help="Interactive job matching browser")
def match_jobs(resume_id, page, per_page, min_compatibility, interactive):
    """Show job listings ranked by compatibility with a resume"""
    resume_service = ResumeService()
    job_service = JobListingService()
    
    # Verify resume exists
    resume_obj = resume_service.get_resume_by_id(resume_id)
    if not resume_obj:
        console.print(f"[red]Error:[/red] Resume with ID {resume_id} not found")
        return
    
    # Build filters
    filters = {}
    if min_compatibility is not None:
        filters['min_compatibility'] = min_compatibility
    
    if interactive:
        _interactive_match_browser(job_service, resume_id, resume_obj.filename, filters, per_page)
    else:
        job_matches, total_count, total_pages = job_service.get_job_listings_with_matches(
            resume_id, page, per_page, "compatibility_score", "desc", filters
        )
        
        console.print(f"\n[bold]Job Matches for Resume: {resume_obj.filename}[/bold]")
        _display_job_matches(job_matches, page, total_pages, total_count)


@jobs.command("stats")
def job_stats():
    """Show job listing statistics"""
    job_service = JobListingService()
    stats = job_service.get_job_statistics()
    
    console.print("\n[bold]Job Listing Statistics:[/bold]")
    console.print(f"• Total Jobs: {stats['total_jobs']:,}")
    
    if stats['remote_type_distribution']:
        console.print("\n[bold]Remote Type Distribution:[/bold]")
        for remote_type, count in stats['remote_type_distribution'].items():
            percentage = (count / stats['total_jobs']) * 100
            console.print(f"  • {remote_type.title()}: {count:,} ({percentage:.1f}%)")
    
    if stats['experience_level_distribution']:
        console.print("\n[bold]Experience Level Distribution:[/bold]")
        for level, count in stats['experience_level_distribution'].items():
            percentage = (count / stats['total_jobs']) * 100
            console.print(f"  • {level.title()}: {count:,} ({percentage:.1f}%)")
    
    if stats['source_site_distribution']:
        console.print("\n[bold]Source Site Distribution:[/bold]")
        for site, count in stats['source_site_distribution'].items():
            percentage = (count / stats['total_jobs']) * 100
            console.print(f"  • {site.title()}: {count:,} ({percentage:.1f}%)")


def _interactive_job_browser(job_service, filters, sort_by, sort_order, per_page):
    """Interactive job browsing interface"""
    current_page = 1
    selected_job_id = None
    
    while True:
        # Display current page
        job_listings, total_count, total_pages = job_service.get_job_listings_paginated(
            current_page, per_page, sort_by, sort_order, filters
        )
        
        console.clear()
        console.print(f"[bold blue]Job Listings Browser[/bold blue] (Page {current_page}/{total_pages})")
        
        if not job_listings:
            console.print("[yellow]No jobs found matching your criteria.[/yellow]")
            break
        
        _display_job_listings(job_listings, current_page, total_pages, total_count)
        
        # Show navigation options
        console.print("\n[bold]Navigation Options:[/bold]")
        options = []
        if current_page > 1:
            options.append("p) Previous page")
        if current_page < total_pages:
            options.append("n) Next page")
        options.extend([
            "g) Go to page",
            "s) Select job for details",
            "f) Change filters",
            "q) Quit"
        ])
        
        console.print(" | ".join(options))
        
        choice = Prompt.ask("\nSelect option", default="q").lower()
        
        if choice == 'q':
            break
        elif choice == 'p' and current_page > 1:
            current_page -= 1
        elif choice == 'n' and current_page < total_pages:
            current_page += 1
        elif choice == 'g':
            try:
                page_num = IntPrompt.ask(f"Enter page number (1-{total_pages})", default=current_page)
                if 1 <= page_num <= total_pages:
                    current_page = page_num
                else:
                    console.print(f"[red]Invalid page number. Must be between 1 and {total_pages}[/red]")
                    click.pause()
            except (ValueError, click.Abort):
                continue
        elif choice == 's':
            try:
                job_id = IntPrompt.ask("Enter job ID to view details")
                job_listing = job_service.get_job_by_id(job_id)
                if job_listing:
                    console.clear()
                    _display_job_details(job_listing)
                    click.pause("\nPress any key to continue...")
                else:
                    console.print(f"[red]Job with ID {job_id} not found[/red]")
                    click.pause()
            except (ValueError, click.Abort):
                continue
        elif choice == 'f':
            filters = _get_filter_options(job_service)


def _interactive_search_browser(job_service, search_term, sort_by, sort_order, per_page):
    """Interactive search results browser"""
    current_page = 1
    
    while True:
        job_listings, total_count, total_pages = job_service.search_jobs(
            search_term, current_page, per_page, sort_by, sort_order
        )
        
        console.clear()
        console.print(f"[bold blue]Search Results for '{search_term}'[/bold blue] (Page {current_page}/{total_pages})")
        
        if not job_listings:
            console.print("[yellow]No jobs found matching your search.[/yellow]")
            break
        
        _display_job_listings(job_listings, current_page, total_pages, total_count)
        
        # Show navigation options
        console.print("\n[bold]Navigation Options:[/bold]")
        options = []
        if current_page > 1:
            options.append("p) Previous page")
        if current_page < total_pages:
            options.append("n) Next page")
        options.extend([
            "g) Go to page",
            "s) Select job for details",
            "q) Quit"
        ])
        
        console.print(" | ".join(options))
        
        choice = Prompt.ask("\nSelect option", default="q").lower()
        
        if choice == 'q':
            break
        elif choice == 'p' and current_page > 1:
            current_page -= 1
        elif choice == 'n' and current_page < total_pages:
            current_page += 1
        elif choice == 'g':
            try:
                page_num = IntPrompt.ask(f"Enter page number (1-{total_pages})", default=current_page)
                if 1 <= page_num <= total_pages:
                    current_page = page_num
                else:
                    console.print(f"[red]Invalid page number. Must be between 1 and {total_pages}[/red]")
                    click.pause()
            except (ValueError, click.Abort):
                continue
        elif choice == 's':
            try:
                job_id = IntPrompt.ask("Enter job ID to view details")
                job_listing = job_service.get_job_by_id(job_id)
                if job_listing:
                    console.clear()
                    _display_job_details(job_listing)
                    click.pause("\nPress any key to continue...")
                else:
                    console.print(f"[red]Job with ID {job_id} not found[/red]")
                    click.pause()
            except (ValueError, click.Abort):
                continue


def _interactive_match_browser(job_service, resume_id, resume_filename, filters, per_page):
    """Interactive job matching browser"""
    current_page = 1
    
    while True:
        job_matches, total_count, total_pages = job_service.get_job_listings_with_matches(
            resume_id, current_page, per_page, "compatibility_score", "desc", filters
        )
        
        console.clear()
        console.print(f"[bold blue]Job Matches for: {resume_filename}[/bold blue] (Page {current_page}/{total_pages})")
        
        if not job_matches:
            console.print("[yellow]No job matches found.[/yellow]")
            break
        
        _display_job_matches(job_matches, current_page, total_pages, total_count)
        
        # Show navigation options
        console.print("\n[bold]Navigation Options:[/bold]")
        options = []
        if current_page > 1:
            options.append("p) Previous page")
        if current_page < total_pages:
            options.append("n) Next page")
        options.extend([
            "g) Go to page",
            "s) Select job for details",
            "f) Change filters",
            "q) Quit"
        ])
        
        console.print(" | ".join(options))
        
        choice = Prompt.ask("\nSelect option", default="q").lower()
        
        if choice == 'q':
            break
        elif choice == 'p' and current_page > 1:
            current_page -= 1
        elif choice == 'n' and current_page < total_pages:
            current_page += 1
        elif choice == 'g':
            try:
                page_num = IntPrompt.ask(f"Enter page number (1-{total_pages})", default=current_page)
                if 1 <= page_num <= total_pages:
                    current_page = page_num
                else:
                    console.print(f"[red]Invalid page number. Must be between 1 and {total_pages}[/red]")
                    click.pause()
            except (ValueError, click.Abort):
                continue
        elif choice == 's':
            try:
                job_id = IntPrompt.ask("Enter job ID to view details")
                job_listing, job_match = job_service.get_job_with_match(job_id, resume_id)
                if job_listing:
                    console.clear()
                    _display_job_details(job_listing, job_match)
                    click.pause("\nPress any key to continue...")
                else:
                    console.print(f"[red]Job with ID {job_id} not found[/red]")
                    click.pause()
            except (ValueError, click.Abort):
                continue
        elif choice == 'f':
            filters = _get_match_filter_options(job_service, filters)


def _display_job_listings_page(job_service, page, per_page, sort_by, sort_order, filters):
    """Display a single page of job listings"""
    job_listings, total_count, total_pages = job_service.get_job_listings_paginated(
        page, per_page, sort_by, sort_order, filters
    )
    
    if not job_listings:
        console.print("[yellow]No jobs found matching your criteria.[/yellow]")
        return
    
    console.print(f"\n[bold]Job Listings (Page {page}/{total_pages}):[/bold]")
    _display_job_listings(job_listings, page, total_pages, total_count)


def _display_job_listings(job_listings, current_page, total_pages, total_count):
    """Display job listings in a formatted table"""
    table = Table(title=f"Job Listings ({total_count:,} total)")
    table.add_column("ID", style="cyan", no_wrap=True, width=6)
    table.add_column("Title", style="bold", width=30)
    table.add_column("Company", style="magenta", width=20)
    table.add_column("Location", style="green", width=25)
    table.add_column("Tags", style="blue", width=30)
    
    for job in job_listings:
        tags = " | ".join(job.display_tags[:4])  # Limit to 4 tags
        table.add_row(
            str(job.id),
            job.title[:30] + "..." if len(job.title) > 30 else job.title,
            job.company[:20] + "..." if len(job.company) > 20 else job.company,
            job.display_location[:25] + "..." if len(job.display_location) > 25 else job.display_location,
            tags
        )
    
    console.print(table)
    console.print(f"\nPage {current_page} of {total_pages} | Total: {total_count:,} jobs")


def _display_job_matches(job_matches, current_page, total_pages, total_count):
    """Display job matches with compatibility scores"""
    table = Table(title=f"Job Matches ({total_count:,} total)")
    table.add_column("ID", style="cyan", no_wrap=True, width=6)
    table.add_column("Score", style="bold red", width=8)
    table.add_column("Title", style="bold", width=25)
    table.add_column("Company", style="magenta", width=18)
    table.add_column("Location", style="green", width=20)
    table.add_column("Tags", style="blue", width=25)
    
    for job_listing, job_match in job_matches:
        if job_match:
            score_text = f"{job_match.compatibility_percentage}%"
            score_style = "bold red" if job_match.compatibility_score >= 0.7 else "yellow" if job_match.compatibility_score >= 0.4 else "dim"
        else:
            score_text = "N/A"
            score_style = "dim"
        
        tags = " | ".join(job_listing.display_tags[:3])  # Limit to 3 tags for space
        
        table.add_row(
            str(job_listing.id),
            f"[{score_style}]{score_text}[/{score_style}]",
            job_listing.title[:25] + "..." if len(job_listing.title) > 25 else job_listing.title,
            job_listing.company[:18] + "..." if len(job_listing.company) > 18 else job_listing.company,
            job_listing.display_location[:20] + "..." if len(job_listing.display_location) > 20 else job_listing.display_location,
            tags
        )
    
    console.print(table)
    console.print(f"\nPage {current_page} of {total_pages} | Total: {total_count:,} matches")


def _display_job_details(job_listing, job_match=None):
    """Display detailed information about a job listing"""
    console.print(f"\n[bold blue]Job Details - ID: {job_listing.id}[/bold blue]")
    
    # Create main info panel
    info_lines = [
        f"[bold]Title:[/bold] {job_listing.title}",
        f"[bold]Company:[/bold] {job_listing.company}",
        f"[bold]Location:[/bold] {job_listing.display_location}",
    ]
    
    if job_listing.experience_level:
        info_lines.append(f"[bold]Experience Level:[/bold] {job_listing.experience_level.value.title()}")
    
    if job_listing.source_site:
        info_lines.append(f"[bold]Source:[/bold] {job_listing.source_site.title()}")
    
    info_lines.append(f"[bold]Scraped:[/bold] {job_listing.scraped_at.strftime('%Y-%m-%d %H:%M')}")
    
    console.print(Panel("\n".join(info_lines), title="Job Information", border_style="blue"))
    
    # Display compatibility if available
    if job_match:
        match_lines = [
            f"[bold]Compatibility Score:[/bold] {job_match.compatibility_percentage}% ({job_match.match_quality})",
            f"[bold]Matching Keywords:[/bold] {len(job_match.matching_keywords)}",
            f"[bold]Missing Keywords:[/bold] {len(job_match.missing_keywords)}",
        ]
        
        if job_match.matching_keywords:
            match_lines.append(f"[bold]Matches:[/bold] {', '.join(job_match.matching_keywords[:10])}")
        
        if job_match.missing_keywords:
            match_lines.append(f"[bold]Missing:[/bold] {', '.join(job_match.missing_keywords[:10])}")
        
        console.print(Panel("\n".join(match_lines), title="Compatibility Analysis", border_style="green"))
    
    # Display technologies
    if job_listing.technologies:
        tech_text = ", ".join(job_listing.technologies)
        console.print(Panel(tech_text, title="Technologies", border_style="yellow"))
    
    # Display description (truncated)
    description = job_listing.description
    if len(description) > 1000:
        description = description[:1000] + "..."
    
    console.print(Panel(description, title="Job Description", border_style="cyan"))
    
    # Display URLs
    url_lines = []
    if job_listing.source_url:
        url_lines.append(f"[bold]Source URL:[/bold] {job_listing.source_url}")
    if job_listing.application_url:
        url_lines.append(f"[bold]Apply URL:[/bold] {job_listing.application_url}")
    
    if url_lines:
        console.print(Panel("\n".join(url_lines), title="Links", border_style="magenta"))


def _get_filter_options(job_service):
    """Interactive filter selection"""
    available_filters = job_service.get_available_filters()
    filters = {}
    
    console.print("\n[bold]Available Filters:[/bold]")
    
    # Company filter
    if Confirm.ask("Filter by company?", default=False):
        console.print("\nTop companies:")
        for i, company in enumerate(available_filters['companies'][:10], 1):
            console.print(f"{i}. {company}")
        
        company = Prompt.ask("Enter company name (or partial name)", default="")
        if company:
            filters['company'] = company
    
    # Location filter
    if Confirm.ask("Filter by location?", default=False):
        console.print("\nTop locations:")
        for i, location in enumerate(available_filters['locations'][:10], 1):
            console.print(f"{i}. {location}")
        
        location = Prompt.ask("Enter location (or partial name)", default="")
        if location:
            filters['location'] = location
    
    # Remote type filter
    if Confirm.ask("Filter by remote type?", default=False):
        remote_type = Prompt.ask(
            "Select remote type",
            choices=['remote', 'onsite', 'hybrid'],
            default=None
        )
        if remote_type:
            filters['remote_type'] = remote_type
    
    # Experience level filter
    if Confirm.ask("Filter by experience level?", default=False):
        experience_level = Prompt.ask(
            "Select experience level",
            choices=['intern', 'junior', 'mid', 'senior', 'lead', 'manager'],
            default=None
        )
        if experience_level:
            filters['experience_level'] = experience_level
    
    return filters


def _get_match_filter_options(job_service, current_filters):
    """Interactive filter selection for job matches"""
    filters = current_filters.copy()
    
    console.print("\n[bold]Match Filter Options:[/bold]")
    
    # Minimum compatibility filter
    if Confirm.ask("Set minimum compatibility score?", default=False):
        try:
            min_score = float(Prompt.ask("Enter minimum score (0.0-1.0)", default="0.0"))
            if 0.0 <= min_score <= 1.0:
                filters['min_compatibility'] = min_score
            else:
                console.print("[red]Invalid score. Must be between 0.0 and 1.0[/red]")
        except ValueError:
            console.print("[red]Invalid score format[/red]")
    
    # Add other filters
    other_filters = _get_filter_options(job_service)
    filters.update(other_filters)
    
    return filters


if __name__ == "__main__":
    main()