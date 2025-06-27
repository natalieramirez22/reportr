# Reportr - Repository Reporter

A Python CLI tool that uses AI to generate progress reports, README files, code summaries, and security insights for your Git repository.

## Features

- **Git History Analysis**: Analyzes commit history, contributors, and code changes
- **Progress Reports**: Generates professional progress reports using AI
- **Flexible Time Periods**: Can analyze recent commits or entire repository history
- **Contributor Statistics**: Tracks commits, lines added/deleted per contributor
- **Multiple Output Modes**: Progress reports or simple summaries
- **Modular Architecture**: Features are separated into individual modules for easy maintenance

## Project Structure

``` txt
reportr/
├── reportr.py                         # CLI entry point for running features
├── requirements.txt                   # Python dependencies
├── README.md                          # Project documentation
├── features/                          # Core features (reports, summaries, scans)
│   ├── code_quality/                  # Code security and quality scans
│   │   ├── codeql_cwe_insights.py     # CodeQL insights + CWE enrichment
│   │   ├── cwe_information.csv        # CWE metadata for scans
│   │   ├── llm_file_scan.py           # LLM-based file security scan
│   │   └── security_scan_summary.py   # Formats scan summaries by severity
│   ├── generate_readme/               # README generator feature
│   │   ├── generate_readme.py         # Creates README from repo structure
│   │   └── prompt.txt                 # Prompt template for LLM
│   ├── progress_report/               # Git activity reports
│   │   ├── progress_report.py         # Analyzes and summarizes commits
│   │   └── prompts/
│   │       ├── general_report.txt     # General team report prompt
│   │       └── specific_user.txt      # Single-user report prompt
│   ├── summarize_details/             # Folder-level summaries
│   │   ├── summarize_details.py       # LLM summary of subdirectory
│   │   └── prompt.txt                 # Prompt for detailed summary
│   └── summarize_overview/            # Repo-wide summary
│       ├── summarize_overview.py      # Full structure + summary
│       └── prompt.txt                 # Prompt for overview
├── functions/                         # Shared utility modules
│   ├── git_history.py                 # Git analysis helpers
│   └── help_command.py                # CLI help screen
├── tests/                             # Example vulnerable code
│   ├── random_test_file.json          # Sample scan result
│   └── random_test_file.py            # Flask app with security flaws
└── venv/                              # Python virtual environment
```

## Installation

1. Clone this repository
2. Activate a virtual environment:

   ```
   python -m venv venv && source venv/bin/activate
   ```

3. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

4. Set up your environment variables in a `.env` file:

   ```
   AZURE_OPENAI_KEY=your_azure_openai_key_here
   ```

## Available Commands:

   - `progress-report`: Generate a progress report
   - `generate-readme`: Generate a README file
   - `summarize-details`: Detailed directory analysis
   - `summarize-overview`: Repository overview
   - `llm-file-scan`: AI-powered security scan of code files or folders
   - `security-scan-summary`: Summarize security scan results by severity
   - `codeql-cwe-summary`: Top CWEs, risk score, and executive summary from CodeQL results


## Command Line Options

   - `--path`
      - Path to repository or directory (default: current directory)
      - Usage: All features except security
   - `--files`
      - List of files or directories to scan
      - Usage: `llm-file-scan` command
   - `--input`
      - Specify path to JSON file for scan summary commands
      - Usage: `security-scan` and `codeql-insights` commands
   - `--username`
      - Filter by contributor username
      - Usage: `progress-report` command
   - `--days`
      - Days to look back (default: 30)
      - Usage: `progress-report` command
   - `--branch`
      - Specify branch for filtering
      - Usage: `progress-report` command

## Output

Reportr can generate:

- AI-powered progress reports with contributor insights and commit trends  
- Detailed Git activity summaries filtered by user, branch, or timeframe  
- Repository-wide or folder-specific summaries for onboarding and code comprehension  
- Professional, project-type-aware README files  
- Code security scan results with CWE enrichment and LLM-generated remediation tips  
- Richly formatted terminal output for all reports

## Architecture

The application uses a modular architecture where:

- **Main Client** (`reportr.py`): Handles command-line interface and orchestrates features
- **Feature Modules**: Each feature is in its own directory with implementation and prompt files
- **Client Injection**: The Azure OpenAI client is injected into each feature function for better testability and modularity
- **Prompt Templates**: AI prompts are stored in separate `.txt` files for easy customization

## Requirements

- Python 3.7+
- Git repository with commit history
- Azure OpenAI API access
- Internet connection for API calls
