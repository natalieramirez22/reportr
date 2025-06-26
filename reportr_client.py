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
from features.summarize_repo.summarize_repo import (
    summarize_by_folder,
    summarize_entire_directory,
)

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
        epilog="""
            Examples:
            python reportr_client.py progress-report
            python reportr_client.py progress-report --username "msft-alias"
            python reportr_client.py progress-report --days 60 --detailed
            python reportr_client.py progress-report --branch "develop"
            python reportr_client.py progress-report --branch "feature/new-feature" --username "dev1" --username "dev2"
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
    progress_parser.add_argument(
        "--branch",
        type=str,
        help="Specify which branch to analyze (default: tries main, then master, then all branches)",
    )

    # generate-readme subcommand
    readme_parser = subparsers.add_parser(
        "generate-readme", help="Generate a README file for the current repository"
    )

    # summarize-by-folder subcommand
    summarize_folder_parser = subparsers.add_parser(
        "summarize-by-folder",
        help="Summarize the repository using directory-by-directory approach",
    )
    summarize_folder_parser.add_argument(
        "--path",
        type=str,
        default=".",
        help="Path to the local repository or directory to summarize (default: current directory)",
    )

    # summarize-entire-directory subcommand
    summarize_entire_parser = subparsers.add_parser(
        "summarize-entire-directory",
        help="Summarize the repository using the entire structure as JSON context",
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
    elif args.command == "summarize-by-folder":
        summarize_by_folder(client, repo_path=args.path)

    # if 'summarize-entire-directory' command is provided, summarize using JSON structure
    elif args.command == "summarize-entire-directory":
        summarize_entire_directory(client, repo_path=args.path)


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
    execute_features(args)


if __name__ == "__main__":
    main()
