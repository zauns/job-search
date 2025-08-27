#!/usr/bin/env python3
"""
Development environment setup script
"""
import subprocess
import sys
import os
from pathlib import Path


def run_command(command, description):
    """Run a command and handle errors"""
    print(f"🔄 {description}...")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        if e.stdout:
            print(f"STDOUT: {e.stdout}")
        if e.stderr:
            print(f"STDERR: {e.stderr}")
        return False


def main():
    """Setup development environment"""
    print("🚀 Setting up Job Matching App Development Environment\n")
    
    # Check if we're in a virtual environment
    if sys.prefix == sys.base_prefix:
        print("⚠️  Warning: You're not in a virtual environment!")
        print("It's recommended to create and activate a virtual environment first:")
        print("  python -m venv venv")
        print("  venv\\Scripts\\activate  # Windows")
        print("  source venv/bin/activate  # Linux/Mac")
        print()
        
        response = input("Continue anyway? (y/N): ")
        if response.lower() != 'y':
            print("Setup cancelled.")
            return 1
    
    # Install dependencies
    if not run_command("pip install -r requirements.txt", "Installing dependencies"):
        return 1
    
    # Install package in development mode
    if not run_command("pip install -e .", "Installing package in development mode"):
        return 1
    
    # Create .env file if it doesn't exist
    if not Path(".env").exists():
        if Path(".env.example").exists():
            run_command("copy .env.example .env", "Creating .env file from template")
        else:
            print("⚠️  .env.example not found, skipping .env creation")
    
    # Initialize database
    if not run_command("alembic upgrade head", "Initializing database"):
        print("⚠️  Database initialization failed, but continuing...")
    
    print("\n🎉 Development environment setup complete!")
    print("\nYou can now run:")
    print("  python -m job_matching_app.main --help")
    print("  make test")
    print("  make run")
    
    return 0


if __name__ == "__main__":
    sys.exit(main())