#!/usr/bin/env python3
"""
Database cleansing script for Job Matching App

This script provides utilities to clean and maintain the database,
including clearing specific tables and resetting data.
"""

import sys
import argparse
from pathlib import Path
from typing import List, Optional
from rich.console import Console
from rich.table import Table
from rich.prompt import Confirm, Prompt
from rich.panel import Panel

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from job_matching_app.database import get_db_context, engine
from job_matching_app.models import (
    Resume, AdaptedResumeDraft, JobListing, JobMatch
)
from sqlalchemy import text, inspect

console = Console()


def get_table_info():
    """Get information about all tables in the database"""
    inspector = inspect(engine)
    tables = inspector.get_table_names()
    
    table_info = {}
    with get_db_context() as db:
        for table in tables:
            try:
                result = db.execute(text(f"SELECT COUNT(*) FROM {table}"))
                count = result.scalar()
                table_info[table] = count
            except Exception as e:
                table_info[table] = f"Error: {e}"
    
    return table_info


def show_database_status():
    """Show current database status"""
    console.print(Panel.fit(
        "[bold blue]Database Status[/bold blue]",
        border_style="blue"
    ))
    
    table_info = get_table_info()
    
    if not table_info:
        console.print("[yellow]No tables found in database[/yellow]")
        return
    
    table = Table(title="Database Tables")
    table.add_column("Table Name", style="cyan", no_wrap=True)
    table.add_column("Record Count", justify="right", style="magenta")
    
    for table_name, count in table_info.items():
        table.add_row(table_name, str(count))
    
    console.print(table)


def clear_table(table_name: str, model_class=None) -> bool:
    """Clear all records from a specific table"""
    try:
        with get_db_context() as db:
            if model_class:
                # Use SQLAlchemy model if provided
                deleted_count = db.query(model_class).count()
                db.query(model_class).delete()
                console.print(f"[green]✓[/green] Cleared {deleted_count} records from {table_name}")
            else:
                # Use raw SQL for tables without models
                result = db.execute(text(f"SELECT COUNT(*) FROM {table_name}"))
                count = result.scalar()
                db.execute(text(f"DELETE FROM {table_name}"))
                console.print(f"[green]✓[/green] Cleared {count} records from {table_name}")
            
            return True
    except Exception as e:
        console.print(f"[red]Error clearing {table_name}:[/red] {e}")
        return False


def clear_resumes():
    """Clear all resume data"""
    console.print("[yellow]Clearing resume data...[/yellow]")
    
    # Clear adapted resume drafts first (foreign key dependency)
    clear_table("adapted_resume_drafts", AdaptedResumeDraft)
    
    # Clear job matches that reference resumes
    clear_table("job_matches", JobMatch)
    
    # Clear resumes
    clear_table("resumes", Resume)


def clear_job_listings():
    """Clear all job listing data"""
    console.print("[yellow]Clearing job listing data...[/yellow]")
    
    # Clear job matches first (foreign key dependency)
    clear_table("job_matches", JobMatch)
    
    # Clear job listings
    clear_table("job_listings", JobListing)


def clear_job_matches():
    """Clear all job match data"""
    console.print("[yellow]Clearing job match data...[/yellow]")
    clear_table("job_matches", JobMatch)


def clear_all_data():
    """Clear all data from all tables"""
    console.print("[yellow]Clearing all application data...[/yellow]")
    
    # Clear in order to respect foreign key constraints
    clear_table("job_matches", JobMatch)
    clear_table("adapted_resume_drafts", AdaptedResumeDraft)
    clear_table("job_listings", JobListing)
    clear_table("resumes", Resume)


def reset_database():
    """Reset the entire database (drop and recreate tables)"""
    console.print("[yellow]Resetting database...[/yellow]")
    
    try:
        # Import models to ensure they're registered
        from job_matching_app import models  # noqa: F401
        from job_matching_app.database import Base
        
        # Drop all tables
        Base.metadata.drop_all(bind=engine)
        console.print("[green]✓[/green] Dropped all tables")
        
        # Recreate all tables
        Base.metadata.create_all(bind=engine)
        console.print("[green]✓[/green] Recreated all tables")
        
        return True
    except Exception as e:
        console.print(f"[red]Error resetting database:[/red] {e}")
        return False


def interactive_cleanse():
    """Interactive database cleansing menu"""
    while True:
        console.print("\n" + "="*50)
        console.print("[bold cyan]Database Cleansing Menu[/bold cyan]")
        console.print("="*50)
        
        show_database_status()
        
        console.print("\n[bold]Available Actions:[/bold]")
        console.print("1. Clear resume data")
        console.print("2. Clear job listing data")
        console.print("3. Clear job match data")
        console.print("4. Clear all data")
        console.print("5. Reset database (drop/recreate tables)")
        console.print("6. Show database status")
        console.print("7. Exit")
        
        choice = Prompt.ask(
            "\nSelect an action",
            choices=["1", "2", "3", "4", "5", "6", "7"],
            default="7"
        )
        
        if choice == "1":
            if Confirm.ask("Are you sure you want to clear all resume data?"):
                clear_resumes()
        elif choice == "2":
            if Confirm.ask("Are you sure you want to clear all job listing data?"):
                clear_job_listings()
        elif choice == "3":
            if Confirm.ask("Are you sure you want to clear all job match data?"):
                clear_job_matches()
        elif choice == "4":
            if Confirm.ask("Are you sure you want to clear ALL data?"):
                clear_all_data()
        elif choice == "5":
            if Confirm.ask("Are you sure you want to reset the entire database?"):
                reset_database()
        elif choice == "6":
            continue  # Will show status at top of loop
        elif choice == "7":
            console.print("[green]Goodbye![/green]")
            break


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(
        description="Database cleansing utilities for Job Matching App",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
AVAILABLE ACTIONS:
  status                    Show database status with table record counts
  clear <target>           Clear specific data from database
  reset                    Reset entire database (drop/recreate tables)
  interactive              Interactive menu mode (default)

CLEAR TARGETS:
  resumes                  Clear all resume data (resumes, drafts, matches)
  jobs                     Clear all job listing data (jobs, matches)
  matches                  Clear only job match data
  all                      Clear all data from all tables

OPTIONS:
  --force                  Skip confirmation prompts (use with caution)

EXAMPLES:
  python scripts/db_cleanse.py status
  python scripts/db_cleanse.py clear resumes
  python scripts/db_cleanse.py clear jobs --force
  python scripts/db_cleanse.py clear all
  python scripts/db_cleanse.py reset
  python scripts/db_cleanse.py interactive

WINDOWS SHORTCUT:
  db_cleanse.bat           Same as python scripts/db_cleanse.py interactive
        """
    )
    
    parser.add_argument(
        "action",
        nargs="?",
        default="interactive",
        choices=["status", "clear", "reset", "interactive"],
        help="Action to perform"
    )
    
    parser.add_argument(
        "target",
        nargs="?",
        choices=["resumes", "jobs", "matches", "all"],
        help="Target for clear action (resumes, jobs, matches, all)"
    )
    
    parser.add_argument(
        "--force",
        action="store_true",
        help="Skip confirmation prompts"
    )
    
    args = parser.parse_args()
    
    try:
        if args.action == "status":
            show_database_status()
        
        elif args.action == "clear":
            if not args.target:
                console.print("[red]Error:[/red] Target required for clear action")
                console.print("Use: python scripts/db_cleanse.py clear <target>")
                console.print("Targets: resumes, jobs, matches, all")
                return 1
            
            # Confirm action unless --force is used
            if not args.force:
                if not Confirm.ask(f"Are you sure you want to clear {args.target} data?"):
                    console.print("[yellow]Operation cancelled[/yellow]")
                    return 0
            
            if args.target == "resumes":
                clear_resumes()
            elif args.target == "jobs":
                clear_job_listings()
            elif args.target == "matches":
                clear_job_matches()
            elif args.target == "all":
                clear_all_data()
        
        elif args.action == "reset":
            if not args.force:
                if not Confirm.ask("Are you sure you want to reset the entire database?"):
                    console.print("[yellow]Operation cancelled[/yellow]")
                    return 0
            
            reset_database()
        
        elif args.action == "interactive":
            interactive_cleanse()
        
        return 0
        
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user[/yellow]")
        return 1
    except Exception as e:
        console.print(f"[red]Unexpected error:[/red] {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())