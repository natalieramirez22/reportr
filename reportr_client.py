import os
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
from help_command import show_help

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
            branch=args.branch,
        )
        results.append(("Progress Report", report))

    # if 'generate-readme' command is provided, generate a README file
    elif args.command == "generate-readme":
        readme = generate_readme(client)
        write_to_readme_file(readme)
        results.append(("README", readme))

    # if 'summarize-by-folder' command is provided, summarize using directory-by-directory approach
    elif args.command == "summarize-details":
        summary = summarize_details(client, repo_path=args.path)
        results.append(("Repository Directory Summary", summary))
    
    # if 'summarize-entire-directory' command is provided, summarize entire directory
    elif args.command == "summarize-overview":
        summary = summarize_overview(client, repo_path=args.path)
        results.append(("Repository Summary", summary))

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
