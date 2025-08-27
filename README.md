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

### Basic Commands

Check application status:
```bash
python -m job_matching_app.main status
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

## Configuration

The application uses environment variables for configuration. Copy `.env.example` to `.env` and modify as needed:

- `DATABASE_URL`: Database connection string
- `OLLAMA_HOST`: Ollama service URL
- `OLLAMA_MODEL`: AI model to use
- `JOBS_PER_PAGE`: Number of jobs to display per page

## License

MIT License