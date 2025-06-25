import os
import argparse
from openai import AzureOpenAI
from dotenv import load_dotenv
from features.progress_report.progress_report import create_progress_report
from features.generate_readme.generate_readme import (
    generate_readme,
    write_to_readme_file,
)
from features.summarize_repo.summarize_repo import (
    summarize_repo,
    save_repo_structure_to_json,
    summarize_repo_with_json_structure,
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
            python reportr_client.py --progress-report
            python reportr_client.py --generate-readme
            python reportr_client.py --summarize-repo --path /path/to/repo
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

    # 'summarize-repo' arg to summarize the purpose of the current repository
    parser.add_argument(
        "--summarize-repo",
        action="store_true",
        help="Summarize the purpose of the current repository (directory-by-directory approach)",
    )

    # 'summarize-repo-structure' arg to summarize using formatted structure
    parser.add_argument(
        "--summarize-repo-structure",
        action="store_true",
        help="Summarize the repository using the entire structure as formatted context",
    )

    # 'summarize-repo-json' arg to summarize using JSON structure
    parser.add_argument(
        "--summarize-repo-json",
        action="store_true",
        help="Summarize the repository using the raw JSON structure (most efficient for large repos)",
    )

    # 'path' argument to specify the local path to the repository or directory
    parser.add_argument(
        "--path",
        type=str,
        default=".",
        help="Path to the local repository or directory to summarize (default: current directory)",
    )

    # 'save-json' argument to save repository structure to JSON file
    parser.add_argument(
        "--save-json",
        type=str,
        help="Save repository structure to JSON file (specify filename or use default: repo_structure.json)",
        nargs="?",
        const="repo_structure.json",
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

    # if 'summarize-repo' is provided, summarize the purpose of the current repository
    if args.summarize_repo:
        summary = summarize_repo(client, repo_path=args.path)
        results.append(("Repository Summary", summary))

    # if 'summarize-repo-json' is provided, summarize using JSON structure
    if args.summarize_repo_json:
        summary = summarize_repo_with_json_structure(client, repo_path=args.path)
        results.append(("Repository JSON Structure Summary", summary))

    # if 'save-json' is provided, save repository structure to JSON file
    if args.save_json:
        output_file = save_repo_structure_to_json(args.path, args.save_json)
        results.append(
            ("JSON Structure", f"Repository structure saved to: {output_file}")
        )

    return results


def main():
    """Main function to handle CLI arguments and execute features"""

    # parse the arguments
    args = parse_arguments()

    # if no command provided but summarize-repo flag is used, execute it
    if not args.command and (
        args.summarize_repo or args.summarize_repo_json or args.save_json
    ):
        results = execute_features(args)
        # print the results
        for title, content in results:
            print(f"{title.upper()}\n\n{content}\n\n\n\n")
        return

    # if no command provided, show help
    if not args.command:
        parser = argparse.ArgumentParser(
            description="Reportr - AI-powered repository analysis and documentation tool"
        )
        parser.print_help()
        return

    # execute the requested features
    results = execute_features(args)

    # print the results
    for title, content in results:
        print(f"{title.upper()}\n\n{content}\n\n\n\n")


if __name__ == "__main__":
    main()
