import os
import argparse
from openai import AzureOpenAI
from dotenv import load_dotenv
from features.progress_report.progress_report import create_progress_report
from features.generate_readme.generate_readme import (
    generate_readme,
    write_to_readme_file,
)
from features.summarize_repo.summarize_repo import summarize_repo

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

    # 'progress-report' arg to generate a report of commits, contributors, and other git history
    parser.add_argument(
        "--progress-report",
        action="store_true",
        help="Generate a progress report for the current repository",
    )

    # 'generate-readme' arg to generate a README file for the current repository
    parser.add_argument(
        "--generate-readme",
        action="store_true",
        help="Generate a README file for the current repository",
    )

    # 'summarize-repo' arg to summarize the purpose of the current repository
    parser.add_argument(
        "--summarize-repo",
        action="store_true",
        help="Summarize the purpose of the current repository",
    )

    # 'path' argument to specify the local path to the repository or directory
    parser.add_argument(
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

    # if 'progress-report' is provided, generate a progress report
    if args.progress_report:
        report = create_progress_report(client)
        results.append(("Progress Report", report))

    # if 'generate-readme' is provided, generate a README file
    if args.generate_readme:
        readme = generate_readme(client)
        write_to_readme_file(readme)
        results.append(("README", readme))

    # if 'summarize-repo' is provided, summarize the purpose of the current repository
    if args.summarize_repo:
        summary = summarize_repo(client, repo_path=args.path)
        results.append(("Repository Summary", summary))

    return results


def main():
    """Main function to handle CLI arguments and execute features"""

    # parse the arguments
    args = parse_arguments()

    # if no arguments provided, show help
    if not any([args.progress_report, args.generate_readme, args.summarize_repo]):
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
