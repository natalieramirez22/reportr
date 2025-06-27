import os
import json
import argparse
from openai import AzureOpenAI
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from features.progress_report.progress_report import create_progress_report
from features.generate_readme.generate_readme import (
    generate_readme,
    write_to_readme_file,
)
from features.summarize_repo.summarize_repo import (
    summarize_by_folder,
    summarize_entire_directory,
)

from features.code_quality.llm_file_scan import create_llm_file_scan
from features.code_quality.security_scan_summary import (
    generate_security_scan_summary as summary_text,
)
from features.code_quality.codeql_cwe_insights import (
    generate_security_scan_summary as summary_json,
)

from features.code_quality.codeql_cwe_insights import generate_codeql_cwe_insights

# load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()


# create the azure openai client
def create_client():
    """Create and return an Azure OpenAI client"""

    return AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_API_KEY"),
        api_version="2024-02-15-preview",
        azure_endpoint="https://natalie-design-agent-resource.cognitiveservices.azure.com/",
    )


# parse the arguments from the command line
def parse_arguments():
    """Parse and return command line arguments"""

    # create the parser
    parser = argparse.ArgumentParser(
        description="Reportr - AI-powered repository analysis and documentation tool",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
            Examples:
            python reportr_client.py progress-report
            python reportr_client.py generate-readme
            python reportr_client.py summarize-by-folder --path /path/to/repo
            python reportr_client.py summarize-entire-directory --path /path/to/repo
        """,
    )

    # create subparsers for different commands
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # progress-report subcommand
    progress_parser = subparsers.add_parser(
        "progress-report", help="Generate a progress report for the current repository"
    )
    progress_parser.add_argument(
        "--username",
        action="append",
        help="Filter by specific contributor username(s). Can be used multiple times.",
    )
    progress_parser.add_argument(
        "--days",
        type=int,
        default=30,
        help="Number of days to look back (default: 30, use 0 for all time)",
    )
    progress_parser.add_argument(
        "--detailed", action="store_true", help="Include detailed contributor summaries"
    )

    # generate-readme subcommand
    readme_parser = subparsers.add_parser(
        "generate-readme", help="Generate a README file for the current repository"
    )

    # summarize-by-folder subcommand
    summarize_folder_parser = subparsers.add_parser(
        "summarize-by-folder", help="Summarize the repository using directory-by-directory approach"
    )
    summarize_folder_parser.add_argument(
        "--path",
        type=str,
        default=".",
        help="Path to the local repository or directory to summarize (default: current directory)",
    )

    # summarize-entire-directory subcommand
    summarize_entire_parser = subparsers.add_parser(
        "summarize-entire-directory", help="Summarize the repository using the entire structure as JSON context"
    )
    summarize_entire_parser.add_argument(
        "--path",
        type=str,
        default=".",
        help="Path to the local repository or directory to summarize (default: current directory)",
    )

    # llm-file-scan subcommand
    llm_scan_parser = subparsers.add_parser(
        "llm-file-scan", help="Analyze code files for security issues using LLM"
    )
    llm_scan_parser.add_argument(
        "--files",
        nargs="+",
        required=True,
        help="List of code files to analyze"
    )

    # security-scan-summary subcommand
    # This command is for summarizing security scan results in text format
    sec_scan_parser = subparsers.add_parser(
        "security-scan-summary", help="Summarize security scan results (text output)"
    )
    sec_scan_parser.add_argument(
        "--input",
        required=True,
        help="Path to a JSON file with scan results"
    )

    # codeql-cwe-summary subcommand
    # This command is for summarizing security scan results in JSON format
    codeql_parser = subparsers.add_parser(
        "codeql-cwe-summary", help="Summarize CodeQL scan results (JSON output)"
    )
    codeql_parser.add_argument(
        "--input",
        required=True,
        help="Path to a JSON file with scan results"
    )

    return parser.parse_args()


# execute the features based on the provided arguments
def execute_features(args):
    """Execute the requested features based on parsed arguments"""

    # create the client
    client = create_client()

    results = []

    # if 'progress-report' command is provided, generate a progress report
    if args.command == "progress-report":
        report = create_progress_report(
            client,
            days_back=args.days,
            contributor_filter=args.username,
            include_contributor_summaries=args.detailed,
        )
        results.append(("Progress Report", report))

    # if 'generate-readme' command is provided, generate a README file
    elif args.command == "generate-readme":
        readme = generate_readme(client)
        write_to_readme_file(readme)
        results.append(("README", readme))

    # if 'summarize-by-folder' command is provided, summarize using directory-by-directory approach
    elif args.command == "summarize-by-folder":
        summary = summarize_by_folder(client, repo_path=args.path)
        results.append(("Repository Directory Summary", summary))
    
    # if 'summarize-entire-directory' command is provided, summarize using JSON structure
    elif args.command == "summarize-entire-directory":
        summary = summarize_entire_directory(client, repo_path=args.path)
        results.append(("Repository JSON Structure Summary", summary))

   # if 'llm-file-scan' command is provided, analyze files with LLM
    elif args.command == "llm-file-scan":
        issues = create_llm_file_scan(client, args.files)
        print("LLM Security Issues Output:")
        print(json.dumps(issues, indent=2))
        results.append(("LLM Security Issues", json.dumps(issues, indent=2)))

    # if 'security-scan-summary' command is provided, summarize security scan results in text format
    elif args.command == "security-scan-summary":
        from features.code_quality.security_scan_summary import SecurityScanResult
        with open(args.input) as f:
            raw = json.load(f)
        # Convert dicts to SecurityScanResult objects
        scan_results = [SecurityScanResult(**issue) for issue in raw]
        summary = summary_text(scan_results)
        results.append(("Security Scan Summary (Text)", summary))

    elif args.command == "codeql-cwe-summary":
        with open(args.input) as f:
            scan_results = json.load(f)
        summary = generate_codeql_cwe_insights(scan_results, client)
        results.append(("CodeQL CWE Insights", summary))
           

    return results


def main():
    """Main function to handle CLI arguments and execute features"""

    # parse the arguments
    args = parse_arguments()

    # if no command provided, show help
    if not args.command:
        parser = argparse.ArgumentParser(
            description="Reportr - AI-powered repository analysis and documentation tool"
        )
        parser.print_help()
        return

    # execute the requested features
    results = execute_features(args)

    # Create Rich console for beautiful output
    console = Console()

    # print the results with Rich formatting
    for title, content in results:
        # Create a styled panel for each result with better width management
        panel = Panel(
            content,
            title=f"[bold blue]{title}[/bold blue]",
            title_align="left",
            border_style="blue",
            padding=(1, 2),
            expand=False,
            width=min(120, console.size.width - 4)  # Responsive width with max limit
        )
        console.print(panel)
        console.print()  # Add some spacing between panels


if __name__ == "__main__":
    main()
