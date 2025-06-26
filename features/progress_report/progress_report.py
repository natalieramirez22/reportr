import os
import json
import re
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from functions.git_history import get_git_history

# initialize rich console
console = Console()


def format_markdown_to_rich(markdown_text: str) -> str:
    """
    Convert markdown formatting to Rich text formatting
    """
    if not markdown_text:
        return markdown_text

    # Convert markdown to Rich formatting
    formatted_text = markdown_text

    # Bold text: **text** or __text__ -> [bold]text[/bold]
    formatted_text = re.sub(r"\*\*(.*?)\*\*", r"[bold]\1[/bold]", formatted_text)
    formatted_text = re.sub(r"__(.*?)__", r"[bold]\1[/bold]", formatted_text)

    # Italic text: *text* or _text_ -> [italic]text[/italic]
    formatted_text = re.sub(r"\*(.*?)\*", r"[italic]\1[/italic]", formatted_text)
    formatted_text = re.sub(r"_(.*?)_", r"[italic]\1[/italic]", formatted_text)

    # Code blocks: `code` -> [code]code[/code]
    formatted_text = re.sub(r"`([^`]+)`", r"[code]\1[/code]", formatted_text)

    # Headers: # Header -> [bold cyan]Header[/bold cyan]
    formatted_text = re.sub(
        r"^### (.*?)$", r"[bold cyan]\1[/bold cyan]", formatted_text, flags=re.MULTILINE
    )
    formatted_text = re.sub(
        r"^## (.*?)$", r"[bold blue]\1[/bold blue]", formatted_text, flags=re.MULTILINE
    )
    formatted_text = re.sub(
        r"^# (.*?)$",
        r"[bold magenta]\1[/bold magenta]",
        formatted_text,
        flags=re.MULTILINE,
    )

    # Lists: - item -> • item
    formatted_text = re.sub(r"^- (.*?)$", r"• \1", formatted_text, flags=re.MULTILINE)

    # Emphasis on key metrics: numbers and percentages
    formatted_text = re.sub(r"(\d+%)", r"[bold green]\1[/bold green]", formatted_text)
    formatted_text = re.sub(
        r"(\d+ commits)", r"[bold yellow]\1[/bold yellow]", formatted_text
    )
    formatted_text = re.sub(
        r"(\d+ files)", r"[bold blue]\1[/bold blue]", formatted_text
    )

    return formatted_text


# !GIT HISTORY HELPER FUNCTIONS
def create_repository_overview(git_data, branch):
    """Create a Rich panel for repository overview"""
    repo_overview = Panel(
        f"[bold]Repository:[/bold] {git_data['repo_name']}\n"
        f"[bold]Branch:[/bold] {branch}\n"
        f"[bold]Analysis Period:[/bold] {git_data['period']}\n"
        f"[bold]Filter:[/bold] {git_data['filtered_by']}\n"
        f"[bold]Total Commits:[/bold] {git_data['total_commits']}",
        title="Repository Overview",
        border_style="cyan",
        padding=(1, 2),
    )

    return repo_overview


def create_contributor_summary(git_data):
    """Create a Rich table for contributors summary"""
    contributors_table = Table(title="Contributors Summary", title_justify="left")
    contributors_table.add_column("Contributor", style="cyan", no_wrap=True)
    contributors_table.add_column("Commits", style="magenta", justify="right")
    contributors_table.add_column("Lines Added", style="green", justify="right")
    contributors_table.add_column("Lines Deleted", style="red", justify="right")
    contributors_table.add_column("Files Changed", style="yellow", justify="right")
    contributors_table.add_column("Net Lines", style="blue", justify="right")

    for author, stats in git_data["contributors"].items():
        net_lines = stats["lines_added"] - stats["lines_deleted"]
        net_color = "green" if net_lines >= 0 else "red"
        contributors_table.add_row(
            author,
            str(stats["commits"]),
            f"+{stats['lines_added']}",
            f"-{stats['lines_deleted']}",
            str(stats["files_changed"]),
            f"[{net_color}]{net_lines:+}[/{net_color}]",
        )

    return contributors_table


def create_commits_table(git_data, max_commits=10):
    """Create a Rich table for recent commits"""
    if not git_data["commits"]:
        return None

    commits_table = Table(
        title=f"Recent Commits (Last {max_commits})", title_justify="left"
    )
    commits_table.add_column("Date", style="cyan", no_wrap=True)
    commits_table.add_column("Author", style="magenta")
    commits_table.add_column("Hash", style="yellow", no_wrap=True)
    commits_table.add_column("Message", style="white")
    commits_table.add_column("Changes", style="blue", justify="right")

    for commit in git_data["commits"][:max_commits]:
        changes = f"+{commit['lines_added']} -{commit['lines_deleted']} ({commit['files_changed']} files)"
        commits_table.add_row(
            commit["date"][:10],  # Just the date part
            commit["author"],
            commit["hash"],
            (
                commit["message"][:50] + "..."
                if len(commit["message"]) > 50
                else commit["message"]
            ),
            changes,
        )

    return commits_table


# ! MAIN FUNCTION
def create_progress_report(
    client,
    repo_path=".",
    days_back=30,
    contributor_filter=None,
    include_contributor_summaries=False,
    branch=None,
):
    """
    Create a comprehensive progress report for a git repository
    Args:
        client: The LLM client
        repo_path: Path to the repository
        days_back: Number of days to look back (0 for all time)
        contributor_filter: Optional list of contributor names to filter by
        include_contributor_summaries: Whether to include detailed summaries for each contributor
        branch: Optional branch name to analyze
    """
    console.print("[bold blue]🚀 Generating Progress Report[/bold blue]")

    git_data = get_git_history(repo_path, days_back, contributor_filter, branch)
    # console.print(f"Git Data: {git_data}")

    if not git_data:
        console.print(
            "[red]❌ Could not analyze git repository. Make sure you're in a git repository.[/red]"
        )
        return

    # create repository overview
    repo_overview = create_repository_overview(git_data, branch)
    console.print(repo_overview)
    console.print("\n")

    # create contributor summary
    contributor_summary = create_contributor_summary(git_data)
    console.print(contributor_summary)
    console.print("\n")

    # create and display the commit history
    commit_history = create_commits_table(git_data, max_commits=20)
    console.print(commit_history)
    console.print("\n")

    # prepare the data for the LLM call
    branch_info = f" (Branch: {branch})" if branch else ""
    report_context = f"""
        Repository: {git_data['repo_name']}{branch_info}
        Analysis Period: {git_data['period']}
        Filter: {git_data['contributor']}
        Total Commits: {git_data['total_commits']}
    """

    report_context += "\nRecent Commits:\n"
    for commit in git_data["commits"][:20]:  # Show last 20 commits
        report_context += f"""
            - {commit['date']} - {commit['author']} ({commit['hash']})
            {commit['message']}
            +{commit['lines_added']} -{commit['lines_deleted']} lines, {commit['files_changed']} files, diffs: {commit['diffs']}
        """

    # Load the prompt template
    prompt_path = os.path.join(os.path.dirname(__file__), "prompts/specific_user.txt")
    messages = None
    try:
        with open(prompt_path, "r") as f:
            prompt_template = f.read()

        # Escape the report_context to make it JSON-safe
        escaped_context = json.dumps(report_context)
        # Remove the outer quotes since we're inserting into a string
        escaped_context = escaped_context[1:-1]

        # Replace the placeholder with actual data
        prompt_template = prompt_template.replace("{report_context}", escaped_context)
        messages = json.loads(prompt_template)
    except Exception as e:
        console.print(f"[red]Error loading prompt template: {e}[/red]")
        return

    # console.print(f"LLM Message: {messages}")

    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Generating AI analysis...", total=None)
            progress.update(task, description="Generating AI analysis...")

            response = client.chat.completions.create(
                model="reportr", messages=messages, max_tokens=2000, temperature=0.7
            )

            main_report = response.choices[0].message.content

            progress.update(task, description="AI analysis complete!")
    except Exception as e:
        console.print(f"[red]Error generating AI analysis: {e}[/red]")
        return

    # Format the markdown in the AI-generated report
    formatted_report = format_markdown_to_rich(main_report)

    # display the main report in a panel
    main_report_panel = Panel(
        formatted_report,
        title="📊 AI-Generated Progress Report",
        border_style="blue",
        padding=(1, 2),
    )
    console.print(main_report_panel)

    # Add contributor summaries if requested
    if include_contributor_summaries and git_data["contributors"]:
        console.print(
            "\n[bold cyan]🔍 Generating Detailed Contributor Summaries...[/bold cyan]"
        )

        for contributor_name in git_data["contributors"].keys():
            contributor_summary = create_contributor_summary(git_data)
            main_report += f"\n\n{contributor_summary}\n"
            main_report += "-" * 50

    console.print("[bold green]✅ Progress report generation complete![/bold green]")
    return main_report
