# Reportr - Git Repository Progress Reporter

A Python tool that uses Azure OpenAI to generate comprehensive progress reports for git repositories by analyzing commit history, contributors, and code changes.

## Features

- **Git History Analysis**: Analyzes commit history, contributors, and code changes
- **Progress Reports**: Generates professional progress reports using AI
- **Flexible Time Periods**: Can analyze recent commits or entire repository history
- **Contributor Statistics**: Tracks commits, lines added/deleted per contributor
- **Multiple Output Modes**: Progress reports or simple summaries
- **Modular Architecture**: Features are separated into individual modules for easy maintenance

## Project Structure

```
reportr/
├── reportr-client.py          # Main client application
├── requirements.txt           # Python dependencies
├── README.md                  # This file
├── features/                  # Feature modules
│   ├── progress-report/       # Git progress report feature
│   │   ├── progress-report.py # Progress report implementation
│   │   └── prompt.txt         # AI prompt template
│   └── summarize-repo/        # Repository summary feature
│       ├── summarize-repo.py  # Summary implementation
│       └── prompt.txt         # AI prompt template
└── venv/                      # Virtual environment
```

## Installation

1. Clone this repository
2. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

3. Set up your environment variables in a `.env` file:

   ```
   AZURE_OPENAI_KEY=your_azure_openai_key_here
   ```

## Usage

### Basic Progress Report

Generate a progress report for the current repository (last 30 days):

```bash
python reportr-client.py
```

### Custom Time Period

Generate a report for the last 7 days:

```bash
python reportr-client.py --days 7
```

Generate a report for all time:

```bash
python reportr-client.py --days 0
```

### Different Repository Path

Analyze a different repository:

```bash
python reportr-client.py --repo-path /path/to/other/repo
```

### Simple Summary Mode

Get a simple repository summary instead of a progress report:

```bash
python reportr-client.py --mode summary
```

## Command Line Options

- `--repo-path`: Path to the git repository (default: current directory)
- `--days`: Number of days to look back (default: 30, use 0 for all time)
- `--mode`: Mode selection - 'progress' or 'summary' (default: progress)

## Output

The progress report includes:

- Executive summary of development activity
- Key contributors and their contributions
- Major changes and improvements made
- Development patterns and trends
- Summary of code changes (additions/deletions)

## Architecture

The application uses a modular architecture where:

- **Main Client** (`reportr-client.py`): Handles command-line interface and orchestrates features
- **Feature Modules**: Each feature is in its own directory with implementation and prompt files
- **Client Injection**: The Azure OpenAI client is injected into each feature function for better testability and modularity
- **Prompt Templates**: AI prompts are stored in separate `.txt` files for easy customization

## Requirements

- Python 3.7+
- Git repository with commit history
- Azure OpenAI API access
- Internet connection for API calls
