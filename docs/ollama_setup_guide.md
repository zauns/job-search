# Ollama Setup Guide for Job Matching App

## Overview
This guide will help you install and configure Ollama to enable AI-powered keyword extraction in the job matching application.

## Step 1: Install Ollama

### Windows Installation
1. **Download Ollama for Windows:**
   - Go to [https://ollama.com/download](https://ollama.com/download)
   - Download the Windows installer
   - Run the installer and follow the setup wizard

2. **Alternative - Using Package Manager:**
   ```powershell
   # Using Chocolatey (if you have it installed)
   choco install ollama
   
   # Using Scoop (if you have it installed)
   scoop install ollama
   ```

3. **Verify Installation:**
   ```powershell
   ollama --version
   ```

## Step 2: Download and Install Models

### Recommended Models for Keyword Extraction

1. **Llama 3.2 3B (Recommended - Fast and Efficient):**
   ```powershell
   ollama pull llama3.2:3b
   ```

2. **Llama 3.2 1B (Lighter, faster):**
   ```powershell
   ollama pull llama3.2:1b
   ```

3. **Llama 3.1 8B (More capable, requires more resources):**
   ```powershell
   ollama pull llama3.1:8b
   ```

4. **Gemma 2B (Google's model, good for text processing):**
   ```powershell
   ollama pull gemma:2b
   ```

### Check Available Models
```powershell
ollama list
```

## Step 3: Test Ollama Installation

### Basic Test
```powershell
ollama run llama3.2:3b "Extract keywords from this text: I am a Python developer with Django experience"
```

### Test with the Job Matching App
```powershell
# Navigate to your project directory
cd path/to/job-matching-app

# Run the AI integration test script
python scripts/test_ai_integration.py
```

## Step 4: Configure the Application

### Option 1: Use Default Model (llama3.2:3b)
No configuration needed - the app will automatically use this model if available.

### Option 2: Configure Custom Model
Create or update your `.env` file:
```env
OLLAMA_MODEL=llama3.2:1b  # or your preferred model
OLLAMA_HOST=http://localhost:11434  # default Ollama host
```

### Option 3: Programmatic Configuration
Update your application code to use a specific model:
```python
from job_matching_app.services import AIMatchingService

# Use a specific model
ai_service = AIMatchingService(model_name="gemma:2b")
```

## Step 5: Performance Considerations

### System Requirements
- **Minimum RAM:** 8GB (for 3B models)
- **Recommended RAM:** 16GB+ (for 8B+ models)
- **Storage:** 2-8GB per model
- **CPU:** Modern multi-core processor

### Model Selection Guide
| Model | Size | RAM Usage | Speed | Quality |
|-------|------|-----------|-------|---------|
| llama3.2:1b | ~1GB | ~2GB | Fast | Good |
| llama3.2:3b | ~2GB | ~4GB | Medium | Better |
| llama3.1:8b | ~4.7GB | ~8GB | Slower | Best |
| gemma:2b | ~1.4GB | ~3GB | Fast | Good |

## Step 6: Troubleshooting

### Common Issues

1. **"ollama command not found"**
   - Restart your terminal/PowerShell after installation
   - Check if Ollama is in your PATH environment variable

2. **"Connection refused" or "Service unavailable"**
   - Make sure Ollama service is running: `ollama serve`
   - Check if port 11434 is available

3. **Model not found**
   - List available models: `ollama list`
   - Pull the required model: `ollama pull model_name`

4. **Out of memory errors**
   - Try a smaller model (1b or 2b)
   - Close other applications to free up RAM

### Verify Everything Works
```powershell
# Check Ollama service
ollama list

# Test the job matching app
python scripts/test_ai_integration.py

# Run the full test suite
python -m pytest tests/test_ai_matching_service.py -v
```

## Step 7: Using the Application

Once Ollama is set up, the job matching application will automatically:
1. Detect available Ollama models
2. Use AI for keyword extraction from resumes
3. Provide clear error messages if Ollama becomes unavailable
4. Support both Portuguese and English content

### Example Usage
```python
from job_matching_app.services import ResumeService

resume_service = ResumeService()

# Upload a resume
resume = resume_service.upload_latex_resume("path/to/resume.tex")

# Extract keywords with AI
result = resume_service.extract_keywords_with_ai(resume.id)

print(f"Keywords: {result.keywords}")
print(f"Language: {result.language_detected}")
```

## Additional Resources

- [Ollama Documentation](https://github.com/ollama/ollama)
- [Available Models](https://ollama.com/library)
- [Model Performance Comparisons](https://ollama.com/blog/llama3.2)

## Support

If you encounter issues:
1. Check the troubleshooting section above
2. Run the test script to verify functionality
3. Check application logs for detailed error messages
4. Ensure Ollama service is running and properly configured for full functionality