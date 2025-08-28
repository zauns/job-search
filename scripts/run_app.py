#!/usr/bin/env python3
"""
Application runner script for Job Matching App

This script provides convenient ways to run the job matching application
with different configurations and environments.
"""

import os
import sys
import subprocess
import argparse
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))


def run_app_cli(*args):
    """Run the main CLI application"""
    cmd = [sys.executable, "-m", "job_matching_app.main"] + list(args)
    return subprocess.run(cmd, cwd=project_root)


def run_with_dev_server():
    """Run the application in development mode with auto-reload"""
    print("🚀 Starting Job Matching App in development mode...")
    print("📁 Project root:", project_root)
    print("🐍 Python executable:", sys.executable)
    print("-" * 50)
    
    # Set development environment
    os.environ["ENVIRONMENT"] = "development"
    
    # Run the main CLI
    return run_app_cli()


def run_status_check():
    """Run application status check"""
    print("🔍 Checking application status...")
    return run_app_cli("status")


def run_latex_check():
    """Check LaTeX installation"""
    print("📄 Checking LaTeX installation...")
    return run_app_cli("check-latex")


def show_click_help():
    """Show the native Click CLI help"""
    print("🔧 Showing native Click CLI help...")
    print("-" * 50)
    return run_app_cli("--help")


def test_latex_functionality():
    """Test LaTeX compilation functionality"""
    print("🧪 Testing LaTeX compilation functionality...")
    return subprocess.run([sys.executable, "scripts/test_latex_compilation.py"], cwd=project_root)


def test_resume_service():
    """Test resume service functionality"""
    print("🧪 Testing resume service functionality...")
    return subprocess.run([sys.executable, "-m", "pytest", "tests/test_resume_service.py", "-v"], cwd=project_root)


def show_help():
    """Show comprehensive help with all available commands and arguments"""
    print("📋 Job Matching App Runner")
    print("=" * 80)
    print("USAGE: python scripts/run_app.py <command> [arguments] [options]")
    print()
    
    print("🔧 SYSTEM COMMANDS:")
    print("  status                    - Show application status and configuration")
    print("  check-latex              - Check LaTeX installation and availability")
    print("  test-latex               - Run comprehensive LaTeX functionality test")
    print("  test-resume              - Run comprehensive resume service test")
    print("  dev                      - Run in development mode with enhanced logging")
    print("  click-help               - Show native Click CLI help")
    print("  help                     - Show this comprehensive help")
    print("  --detailed-help          - Same as 'help' command")
    print()
    
    print("📄 RESUME MANAGEMENT COMMANDS:")
    print("  resume list              - List all uploaded resumes with details")
    print("  resume upload <file>     - Upload a LaTeX resume file")
    print("    Arguments:")
    print("      <file>               - Path to LaTeX resume file (.tex)")
    print("    Options:")
    print("      --filename <name>    - Custom filename for the resume")
    print()
    print("  resume show <id>         - Show detailed information about a resume")
    print("    Arguments:")
    print("      <id>                 - Resume ID (integer)")
    print()
    print("  resume compile <id>      - Compile a resume to PDF")
    print("    Arguments:")
    print("      <id>                 - Resume ID (integer)")
    print("    Options:")
    print("      --output <path>      - Output PDF file path (now working!)")
    print("      -o <path>            - Short form of --output")
    print()
    print("  resume delete <id>       - Delete a resume (with confirmation)")
    print("    Arguments:")
    print("      <id>                 - Resume ID (integer)")
    print("    Note: Will prompt for confirmation before deletion")
    print()
    
    print("🔑 KEYWORD MANAGEMENT COMMANDS:")
    print("  resume keywords <id>     - Interactive keyword management interface")
    print("    Arguments:")
    print("      <id>                 - Resume ID (integer)")
    print("    Features:")
    print("      • Display AI-extracted and user-added keywords")
    print("      • Extract keywords using AI (Ollama)")
    print("      • Add custom keywords")
    print("      • Remove user keywords")
    print("      • Clear all user keywords")
    print()
    print("  resume extract-keywords <id> - Extract keywords using AI")
    print("    Arguments:")
    print("      <id>                 - Resume ID (integer)")
    print("    Note: Uses Ollama AI service for intelligent keyword extraction")
    print()
    print("  resume add-keyword <id> <keyword> - Add a custom keyword")
    print("    Arguments:")
    print("      <id>                 - Resume ID (integer)")
    print("      <keyword>            - Keyword to add (case-insensitive)")
    print("    Note: Prevents duplicate keywords")
    print()
    print("  resume remove-keyword <id> <keyword> - Remove a user keyword")
    print("    Arguments:")
    print("      <id>                 - Resume ID (integer)")
    print("      <keyword>            - Keyword to remove (case-insensitive)")
    print("    Note: Only removes user-added keywords, not AI-extracted ones")
    print()
    
    print("🎯 FUTURE COMMANDS (Coming Soon):")
    print("  jobs list                - List available job listings")
    print("  jobs search <keywords>   - Search for jobs by keywords")
    print("  jobs scrape              - Scrape new job listings")
    print("  match <resume_id>        - Find matching jobs for a resume")
    print("  adapt <resume_id> <job_id> - Adapt resume for specific job")
    print()
    
    print("📝 EXAMPLES:")
    print("  # Check system status")
    print("  python scripts/run_app.py status")
    print()
    print("  # Upload a resume")
    print("  python scripts/run_app.py resume upload my_resume.tex")
    print("  python scripts/run_app.py resume upload my_resume.tex --filename \"John Doe Resume\"")
    print()
    print("  # List and manage resumes")
    print("  python scripts/run_app.py resume list")
    print("  python scripts/run_app.py resume show 1")
    print("  python scripts/run_app.py resume compile 1 --output my_resume.pdf")
    print("  python scripts/run_app.py resume delete 1")
    print()
    print("  # Keyword management")
    print("  python scripts/run_app.py resume extract-keywords 1")
    print("  python scripts/run_app.py resume keywords 1")
    print("  python scripts/run_app.py resume add-keyword 1 \"docker\"")
    print("  python scripts/run_app.py resume remove-keyword 1 \"docker\"")
    print()
    print("  # Check LaTeX installation")
    print("  python scripts/run_app.py check-latex")
    print()
    
    print("🪟 WINDOWS SHORTCUTS:")
    print("  run_app.bat status       - Same as python scripts/run_app.py status")
    print("  run_app.bat resume list  - Same as python scripts/run_app.py resume list")
    print()
    
    print("💡 TIPS:")
    print("  • Use 'resume list' to see available resume IDs")
    print("  • LaTeX files must have .tex extension")
    print("  • PDF compilation requires LaTeX installation (pdflatex)")
    print("  • Use 'status' command to verify system configuration")
    print("  • All resume operations work with the local SQLite database")
    print()
    
    print("🔗 RELATED SCRIPTS:")
    print("  scripts/db_cleanse.py    - Database maintenance and cleanup")
    print("  scripts/setup_ollama.py  - Ollama AI service setup")
    print("  scripts/test_ai_integration.py - Test AI functionality")
    print()
    
    print("📚 HELP OPTIONS:")
    print("  python scripts/run_app.py help          - This comprehensive help")
    print("  python scripts/run_app.py --detailed-help - Same as above")
    print("  python scripts/run_app.py click-help    - Native Click CLI help")
    print("  python scripts/run_app.py -h            - Argparse help (this script)")
    print("  python scripts/run_app.py resume --help - Resume command help")


def main():
    """Main entry point"""
    # Check if we have any arguments
    if len(sys.argv) == 1:
        show_help()
        return 0
    
    # Handle special cases that need argparse
    if "--detailed-help" in sys.argv:
        show_help()
        return 0
    
    # Get the first argument as command
    command = sys.argv[1]
    remaining_args = sys.argv[2:]
    
    # Handle different commands
    if command == "help":
        show_help()
        return 0
    elif command == "status":
        return run_status_check().returncode
    elif command == "latex" or command == "check-latex":
        return run_latex_check().returncode
    elif command == "dev":
        return run_with_dev_server().returncode
    elif command == "click-help":
        return show_click_help().returncode
    elif command == "test-latex":
        return subprocess.run([sys.executable, "scripts/test_latex_compilation.py"], cwd=project_root).returncode
    elif command == "test-resume":
        return subprocess.run([sys.executable, "-m", "pytest", "tests/test_resume_service.py", "-v"], cwd=project_root).returncode
    elif command == "resume":
        # Pass all remaining arguments directly to the CLI for resume commands
        return run_app_cli("resume", *remaining_args).returncode
    elif command in ["-h", "--help"]:
        # Show argparse-style help for the wrapper script
        print("Job Matching App Runner - Easy access to all application commands")
        print()
        print("USAGE: python scripts/run_app.py <command> [arguments] [options]")
        print()
        print("AVAILABLE COMMANDS:")
        print("  status                    Show application status")
        print("  check-latex              Check LaTeX installation")
        print("  dev                      Run in development mode")
        print("  resume <subcommand>      Resume management operations")
        print("  help                     Show detailed help information")
        print("  --detailed-help          Show comprehensive help with all commands")
        print()
        print("RESUME SUBCOMMANDS:")
        print("  list                     List all resumes")
        print("  upload <file>            Upload LaTeX resume")
        print("  show <id>                Show resume details")
        print("  compile <id>             Compile resume to PDF")
        print("  delete <id>              Delete resume")
        print()
        print("EXAMPLES:")
        print("  python scripts/run_app.py status")
        print("  python scripts/run_app.py resume upload my_resume.tex")
        print("  python scripts/run_app.py resume compile 1 --output resume.pdf")
        print()
        print("For comprehensive help: python scripts/run_app.py help")
        return 0
    else:
        # Pass through any other commands directly to the CLI
        return run_app_cli(command, *remaining_args).returncode


if __name__ == "__main__":
    sys.exit(main())