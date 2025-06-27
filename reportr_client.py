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
from features.summarize_details.summarize_details import (
    summarize_details,
)
from features.summarize_overview.summarize_overview import (
    summarize_overview,
)
from functions.help_command import show_help

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
        api_key=os.getenv("AZURE_OPENAI_KEY"),
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
        add_help=False,  # Disable default help to use our Rich styled help
        epilog="""
            Examples:
            python reportr_client.py generate-readme
            python reportr_client.py summarize-details --path /path/to/repo
            python reportr_client.py summarize-overviews --path /path/to/repo
            python reportr_client.py progress-report --username "msft-alias"
            python reportr_client.py progress-report --days 60 --detailed
            python reportr_client.py progress-report --branch "develop"
            python reportr_client.py progress-report --branch "feature/new-feature" --username "dev1" --username "dev2"
        """,
    )

    # Add help argument manually
    parser.add_argument(
        "-h", "--help", 
        action="store_true", 
        help="Show this help message and exit"
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

    progress_parser.add_argument(
        "--branch",
        type=str,
        help="Specify which branch to analyze (default: tries main, then master, then all branches)",
    )

    # generate-readme subcommand
    readme_parser = subparsers.add_parser(
        "generate-readme", help="Generate a README file for the current repository"
    )

    # summarize-details subcommand
    summarize_folder_parser = subparsers.add_parser(
        "summarize-details", help="Summarize a sub-directory with a focus on details"
    )
    summarize_folder_parser.add_argument(
        "--path",
        type=str,
        default=".",
        help="Path to the local repository or directory to summarize (default: current directory)",
    )

    # summarize-overview subcommand
    summarize_entire_parser = subparsers.add_parser(
        "summarize-overview", help="Summarize the repository overview and structure"
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

    # if 'progress-report' command is provided, generate a progress report
    if args.command == "progress-report":
        create_progress_report(
            client,
            days_back=args.days,
            contributor_filter=args.username,
            branch=args.branch,
            use_specific_user_prompt=bool(args.username),
        )

    # if 'generate-readme' command is provided, generate a README file
    elif args.command == "generate-readme":
        readme = generate_readme(client)
        write_to_readme_file(readme)

    # if 'summarize-by-folder' command is provided, summarize using directory-by-directory approach
    elif args.command == "summarize-details":
        summary = summarize_details(client, repo_path=args.path)
        results.append(("Repository Directory Summary", summary))

    # if 'summarize-entire-directory' command is provided, summarize entire directory
    elif args.command == "summarize-overview":
        summary = summarize_overview(client, repo_path=args.path)
        results.append(("Repository Summary", summary))

   # if 'llm-file-scan' command is provided, analyze files with LLM
    elif args.command == "llm-file-scan":
        from features.code_quality.llm_file_scan import collect_code_files_from_path, create_llm_file_scan
        all_files = []
        for path in args.files:
            all_files.extend(collect_code_files_from_path(path, exts={'.py'}))  # or whatever extensions you want

        issues = create_llm_file_scan(client, args.files)
        # print("LLM Security Issues Output:")
        # print(json.dumps(issues, indent=2))
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

    # Check if help was requested or no command provided
    if (hasattr(args, 'help') and args.help) or not args.command:
        show_help()
        return

    # execute the requested features
    results = execute_features(args)

    # only apply rich formatting for summarize commands
    if args.command in ["summarize-details", "summarize-overview"]:
        console = Console()

        # print the results with rich formatting
        for title, content in results:
            panel = Panel(
                content,
                title=f"[bold sky_blue1]{title}[/bold sky_blue1]",
                title_align="left",
                border_style="plum2",
                padding=(1, 2),
                expand=False,
                width=min(120, console.size.width - 4),
            )
            console.print(panel)
            console.print()




if __name__ == "__main__":
    main()
