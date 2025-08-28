#!/usr/bin/env python3
"""
Setup script for Ollama integration with the job matching application
"""
import sys
import os
import subprocess
import time
import requests
from typing import List, Dict, Optional

# Add the project root to the Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from job_matching_app.services import AIMatchingService


class OllamaSetup:
    """Helper class for setting up Ollama"""
    
    def __init__(self):
        self.ollama_host = "http://localhost:11434"
        self.recommended_models = [
            {"name": "llama3.2:3b", "description": "Recommended - Good balance of speed and quality", "size": "~2GB"},
            {"name": "llama3.2:1b", "description": "Fastest - Good for quick testing", "size": "~1GB"},
            {"name": "gemma:2b", "description": "Google's model - Good for text processing", "size": "~1.4GB"},
            {"name": "llama3.1:8b", "description": "Best quality - Requires more resources", "size": "~4.7GB"},
        ]
    
    def check_ollama_installed(self) -> bool:
        """Check if Ollama is installed"""
        try:
            result = subprocess.run(['ollama', '--version'], 
                                  capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False
    
    def check_ollama_running(self) -> bool:
        """Check if Ollama service is running"""
        try:
            response = requests.get(f"{self.ollama_host}/api/tags", timeout=5)
            return response.status_code == 200
        except:
            return False
    
    def get_available_models(self) -> List[Dict]:
        """Get list of available models"""
        try:
            result = subprocess.run(['ollama', 'list'], 
                                  capture_output=True, text=True)
            if result.returncode == 0:
                lines = result.stdout.strip().split('\n')[1:]  # Skip header
                models = []
                for line in lines:
                    if line.strip():
                        parts = line.split()
                        if parts:
                            models.append({
                                'name': parts[0],
                                'size': parts[1] if len(parts) > 1 else 'Unknown'
                            })
                return models
            return []
        except:
            return []
    
    def start_ollama_service(self) -> bool:
        """Start Ollama service"""
        try:
            print("Starting Ollama service...")
            # On Windows, Ollama usually starts automatically after installation
            # But we can try to start it manually
            subprocess.Popen(['ollama', 'serve'], 
                           stdout=subprocess.DEVNULL, 
                           stderr=subprocess.DEVNULL)
            
            # Wait a bit for service to start
            time.sleep(3)
            return self.check_ollama_running()
        except:
            return False
    
    def pull_model(self, model_name: str) -> bool:
        """Pull a model from Ollama"""
        try:
            print(f"Downloading model: {model_name}")
            print("This may take several minutes depending on model size...")
            
            result = subprocess.run(['ollama', 'pull', model_name], 
                                  capture_output=False, text=True)
            return result.returncode == 0
        except:
            return False
    
    def test_model(self, model_name: str) -> bool:
        """Test a model with a simple prompt"""
        try:
            print(f"Testing model: {model_name}")
            result = subprocess.run([
                'ollama', 'run', model_name, 
                'Extract 3 keywords from: Python developer with Django experience'
            ], capture_output=True, text=True, timeout=30)
            
            if result.returncode == 0 and result.stdout.strip():
                print(f"✅ Model test successful: {result.stdout.strip()}")
                return True
            return False
        except:
            return False
    
    def setup_interactive(self):
        """Interactive setup process"""
        print("🚀 Ollama Setup for Job Matching Application")
        print("=" * 50)
        
        # Check if Ollama is installed
        if not self.check_ollama_installed():
            print("❌ Ollama is not installed on your system.")
            print("\n📥 To install Ollama:")
            print("1. Go to https://ollama.com/download")
            print("2. Download and install Ollama for Windows")
            print("3. Restart your terminal/PowerShell")
            print("4. Run this script again")
            return False
        
        print("✅ Ollama is installed")
        
        # Check if service is running
        if not self.check_ollama_running():
            print("⚠️  Ollama service is not running. Attempting to start...")
            if not self.start_ollama_service():
                print("❌ Could not start Ollama service.")
                print("Try running 'ollama serve' in another terminal window.")
                return False
        
        print("✅ Ollama service is running")
        
        # Check available models
        available_models = self.get_available_models()
        print(f"\n📋 Currently installed models: {len(available_models)}")
        
        if available_models:
            for model in available_models:
                print(f"  - {model['name']} ({model['size']})")
        else:
            print("  No models installed")
        
        # Recommend models to install
        print(f"\n💡 Recommended models for keyword extraction:")
        for i, model in enumerate(self.recommended_models, 1):
            installed = any(m['name'].startswith(model['name'].split(':')[0]) 
                          for m in available_models)
            status = "✅ Installed" if installed else "⬇️  Available"
            print(f"  {i}. {model['name']} - {model['description']} ({model['size']}) [{status}]")
        
        # Ask user which model to install
        print(f"\n🤔 Which model would you like to install/test?")
        print("Enter the number (1-4), or 'skip' to continue with existing models:")
        
        choice = input("Your choice: ").strip().lower()
        
        if choice == 'skip':
            print("Skipping model installation...")
        elif choice.isdigit() and 1 <= int(choice) <= len(self.recommended_models):
            model_idx = int(choice) - 1
            model_name = self.recommended_models[model_idx]['name']
            
            # Check if already installed
            if any(m['name'].startswith(model_name.split(':')[0]) for m in available_models):
                print(f"Model {model_name} appears to be already installed.")
                test_choice = input("Test the model? (y/n): ").strip().lower()
                if test_choice == 'y':
                    self.test_model(model_name)
            else:
                # Install the model
                if self.pull_model(model_name):
                    print(f"✅ Successfully installed {model_name}")
                    self.test_model(model_name)
                else:
                    print(f"❌ Failed to install {model_name}")
        else:
            print("Invalid choice, skipping model installation...")
        
        return True
    
    def test_application_integration(self):
        """Test the application's AI integration"""
        print(f"\n🧪 Testing Application AI Integration")
        print("-" * 40)
        
        try:
            ai_service = AIMatchingService()
            model_info = ai_service.get_model_info()
            
            print(f"AI Service Status: {model_info['status']}")
            if model_info['status'] == 'available':
                print(f"Using Model: {model_info['model']}")
                print(f"Model Size: {model_info.get('size', 'Unknown')}")
                
                # Test keyword extraction
                sample_text = """
                Senior Software Engineer with 5 years of experience in Python development.
                Expertise in Django, React, PostgreSQL, and Docker containerization.
                Experience with AWS cloud services and microservices architecture.
                """
                
                print(f"\n🔍 Testing keyword extraction...")
                result = ai_service.extract_resume_keywords(sample_text)
                
                print(f"Language Detected: {result.language_detected}")
                print(f"Confidence: {result.confidence}")
                print(f"Keywords: {result.keywords}")
                
                print("✅ AI-powered extraction working correctly!")
                    
            else:
                print(f"Status: {model_info['status']}")
                print(f"Fallback: {model_info['fallback']}")
                print("⚠️  AI service not available, using rule-based extraction")
                
        except Exception as e:
            print(f"❌ Error testing application integration: {e}")
            return False
        
        return True


def main():
    """Main setup function"""
    setup = OllamaSetup()
    
    try:
        # Run interactive setup
        if setup.setup_interactive():
            # Test application integration
            setup.test_application_integration()
            
            print(f"\n🎉 Setup Complete!")
            print("=" * 50)
            print("Next steps:")
            print("1. Run 'python scripts/test_ai_integration.py' to test the full integration")
            print("2. Use the job matching application with AI-powered keyword extraction")
            print("3. Check the documentation in 'docs/ollama_setup_guide.md' for more details")
            
        else:
            print(f"\n❌ Setup incomplete. Please follow the installation instructions.")
            return 1
            
    except KeyboardInterrupt:
        print(f"\n\n⏹️  Setup cancelled by user.")
        return 1
    except Exception as e:
        print(f"\n❌ Unexpected error during setup: {e}")
        return 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())