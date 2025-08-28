# Job Matching Application

An AI-powered job matching application that uses web scraping, natural language processing, and machine learning to find job opportunities compatible with your resume and automatically adapt your resume for specific positions.

## Features

- **LaTeX Resume Processing**: Upload and process LaTeX resumes
- **AI-Powered Analysis**: Extract keywords and analyze resume content using local Ollama
- **Web Scraping**: Collect job listings from multiple job sites
- **Intelligent Matching**: Match jobs based on resume compatibility
- **Resume Adaptation**: Automatically adapt resumes for specific job requirements
- **Multilingual Support**: Support for Portuguese and English content

## Requirements

- Python 3.11+
- LaTeX distribution (for PDF compilation)
- Ollama (for AI processing)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd job-matching-app
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
make install-dev
```

4. Copy environment configuration:
```bash
cp .env.example .env
```

5. Initialize the database:
```bash
make init-db
```

## Usage

### Quick Start Scripts

The application includes convenient scripts for easy operation:

#### Application Runner (`scripts/run_app.py`)

**Show help and available commands:**
```bash
python scripts/run_app.py help
```

**Check application status:**
```bash
python scripts/run_app.py status
```

**Check LaTeX installation:**
```bash
python scripts/run_app.py latex
```

**Resume management:**
```bash
# List all uploaded resumes
python scripts/run_app.py resume list

# Upload a LaTeX resume
python scripts/run_app.py resume upload path/to/resume.tex

# Show resume details
python scripts/run_app.py resume show <resume_id>

# Compile resume to PDF
python scripts/run_app.py resume compile <resume_id>

# Delete a resume
python scripts/run_app.py resume delete <resume_id>
```

**Windows users can use the batch file:**
```cmd
run_app.bat status
run_app.bat resume list
```

#### Database Management (`scripts/db_cleanse.py`)

**Interactive database management (recommended):**
```bash
python scripts/db_cleanse.py interactive
```

**Show database status:**
```bash
python scripts/db_cleanse.py status
```

**Clear specific data:**
```bash
# Clear resume data
python scripts/db_cleanse.py clear resumes

# Clear job listing data
python scripts/db_cleanse.py clear jobs

# Clear job match data
python scripts/db_cleanse.py clear matches

# Clear all data
python scripts/db_cleanse.py clear all

# Reset entire database (drop/recreate tables)
python scripts/db_cleanse.py reset
```

**Windows users can use the batch file:**
```cmd
db_cleanse.bat
db_cleanse.bat status
```

### Direct CLI Commands

You can also use the application directly:

```bash
python -m job_matching_app.main status
python -m job_matching_app.main resume list
python -m job_matching_app.main check-latex
```

### Development

Run tests:
```bash
make test
```

Run tests with coverage:
```bash
make test-cov
```

Format code:
```bash
make format
```

Lint code:
```bash
make lint
```

## Project Structure

```
job_matching_app/
├── job_matching_app/          # Main application package
│   ├── models/                # Database models
│   ├── services/              # Business logic services
│   ├── controllers/           # Application controllers
│   ├── utils/                 # Utility functions
│   ├── config.py              # Configuration settings
│   ├── database.py            # Database setup
│   └── main.py                # Main entry point
├── tests/                     # Test files
├── alembic/                   # Database migrations
├── requirements.txt           # Python dependencies
└── README.md                  # This file
```

## Script Features

### Application Runner Features
- **Development Mode**: Automatic environment setup and configuration
- **Status Monitoring**: Check application health and dependencies
- **LaTeX Validation**: Verify LaTeX installation and functionality
- **Resume Management**: Complete CRUD operations for resume handling
- **Cross-Platform**: Works on Windows, macOS, and Linux
- **Rich Output**: Colored console output with progress indicators

### Database Cleansing Features
- **Interactive Menu**: Safe, guided database operations
- **Selective Clearing**: Target specific data types (resumes, jobs, matches)
- **Safety Confirmations**: Prevent accidental data loss
- **Foreign Key Awareness**: Handles table dependencies correctly
- **Status Overview**: View current database state and record counts
- **Complete Reset**: Drop and recreate all tables when needed

### Safety Measures
- **Confirmation Prompts**: All destructive operations require confirmation
- **Error Handling**: Comprehensive error messages and recovery
- **Dependency Management**: Automatic virtual environment detection
- **Backup Recommendations**: Clear warnings before data deletion

## Configuration

The application uses environment variables for configuration. Copy `.env.example` to `.env` and modify as needed:

- `DATABASE_URL`: Database connection string
- `OLLAMA_HOST`: Ollama service URL
- `OLLAMA_MODEL`: AI model to use
- `JOBS_PER_PAGE`: Number of jobs to display per page

## License

MIT License