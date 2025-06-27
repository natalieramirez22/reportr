# Reportr - Repository Reporter

A Python CLI tool that uses AI to generate progress reports, README files, code summaries, and security insights for your Git repository.

## Features

- **Progress Reports**: Generates concise AI-powered reports including Git history analysis, contributor stats, code changes, and commit trends
- **README Generation**: Creates clean, professional README files tailored to your repo’s structure and detected project type
- **Summarize Overview**: Produces high-level summaries of the entire repository to help with onboarding and project understanding
- **Summarize Details**: Generates detailed summaries of specific directories or components for deeper insights
- **Security Scans**: Identifies potential vulnerabilities, enriches results with CWE insights, and provides remediation tips
- **Modular Architecture**: Organized feature modules for easy extension and maintenance
- **Styled Output**: All reports are formatted with Rich for clean, colorful, easy-to-read terminal output


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
