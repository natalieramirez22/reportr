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
    formatted_text = re.sub(
        r"\*\*(.*?)\*\*", r"[bold sky_blue1]\1[/bold sky_blue1]", formatted_text
    )
    formatted_text = re.sub(
        r"__(.*?)__", r"[bold sky_blue1]\1[/bold sky_blue1]", formatted_text
    )

    # Code blocks: `code` -> [code]code[/code]
    formatted_text = re.sub(r"`([^`]+)`", r"[cornsilk1]\1[/cornsilk1]", formatted_text)

    # Headers: # Header -> [bold pink1]Header[/bold pink1]
    formatted_text = re.sub(
        r"^#### (.*?)$",
        r"[bold pink1]\1[/bold pink1]",
        formatted_text,
        flags=re.MULTILINE,
    )
    formatted_text = re.sub(
        r"^### (.*?)$",
        r"[bold plum2]\1[/bold plum2]",
        formatted_text,
        flags=re.MULTILINE,
    )
    formatted_text = re.sub(
        r"^## (.*?)$",
        r"[bold pink1]\1[/bold pink1]",
        formatted_text,
        flags=re.MULTILINE,
    )
    formatted_text = re.sub(
        r"^# (.*?)$",
        r"[bold plum2]\1[/bold plum2]",
        formatted_text,
        flags=re.MULTILINE,
    )

    # Lists: - item -> • item
    formatted_text = re.sub(r"^- (.*?)$", r"• \1", formatted_text, flags=re.MULTILINE)

    # Emphasis on key metrics: numbers and percentages
    formatted_text = re.sub(r"(\d+%)", r"[bold]\1[/bold]", formatted_text)
    formatted_text = re.sub(r"(\d+ commits)", r"[bold]\1[/bold]", formatted_text)
    formatted_text = re.sub(r"(\d+ files)", r"[bold]\1[/bold]", formatted_text)

    return formatted_text


# !GIT HISTORY HELPER FUNCTIONS
def create_repository_overview(git_data, branch):
    """Create a Rich panel for repository overview"""
    repo_overview = Panel(
        f"[bold sky_blue1]Repository:[/bold sky_blue1] {git_data['repo_name']}\n"
        f"[bold sky_blue1]Branch:[/bold sky_blue1] {branch}\n"
        f"[bold sky_blue1]Analysis Period:[/bold sky_blue1] {git_data['period']}\n"
        f"[bold sky_blue1]Filter:[/bold sky_blue1] {git_data['filtered_by']}\n"
        f"[bold sky_blue1]Total Commits:[/bold sky_blue1] {git_data['total_commits']}",
        title="Repository Overview",
        border_style="plum2",
        title_align="left",
        padding=(1, 2),
    )

    return repo_overview


def create_contributor_summary(git_data):
    """Create a Rich table for contributors summary"""
    contributors_table = Table(title="Contributors Summary", title_justify="left")
    contributors_table.add_column("Contributor", style="sky_blue1", no_wrap=True)
    contributors_table.add_column("Commits", style="pink1", justify="right")
    contributors_table.add_column("Lines Added", style="green", justify="right")
    contributors_table.add_column("Lines Deleted", style="white", justify="right")
    contributors_table.add_column("Files Changed", style="plum2", justify="right")
    contributors_table.add_column("Net Lines", style="cornsilk1", justify="right")

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
    commits_table.add_column("Date", style="sky_blue1", no_wrap=True)
    commits_table.add_column("Author", style="pink1")
    commits_table.add_column("Hash", style="plum2", no_wrap=True)
    commits_table.add_column("Message", style="cornsilk1")
    commits_table.add_column("Changes", style="green", justify="right")

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


def clean_repetitive_content(text):
    """
    Clean up repetitive content in AI-generated reports
    """
    if not text:
        return text

    # Split into lines and remove duplicate consecutive lines
    lines = text.split("\n")
    cleaned_lines = []
    prev_line = None

    for line in lines:
        line = line.strip()
        if line != prev_line:
            cleaned_lines.append(line)
            prev_line = line

    # Remove excessive separators
    cleaned_text = "\n".join(cleaned_lines)
    cleaned_text = re.sub(r"---\s*\n\s*---\s*\n\s*---", "---", cleaned_text)

    # Remove excessive "Summary:" sections
    cleaned_text = re.sub(
        r"(\[bold skyblue1\]Summary:\[/bold skyblue1\].*?)(?=\[bold skyblue1\]Summary:\[/bold skyblue1\])",
        r"\1",
        cleaned_text,
        flags=re.DOTALL,
    )

    return cleaned_text


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

    console.print("[bold sky_blue1]🚀 Generating Progress Report[/bold sky_blue1]")

    git_data = get_git_history(repo_path, days_back, contributor_filter, branch)
    # console.print(f"Git Data: {git_data}")

    if not git_data:
        console.print(
            "[red]Could not analyze git repository. Make sure you're in a git repository.[/red]"
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
        with open(prompt_path, "r", encoding="utf-8") as f:
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
                model="reportr",
                messages=messages,
                max_tokens=1500,  # Reduced from 2000 to prevent repetitive output
                temperature=0.5,  # Reduced from 0.7 for more focused output
            )

            main_report = response.choices[0].message.content

            # Clean up repetitive content
            main_report = clean_repetitive_content(main_report)

            progress.update(task, description="AI analysis complete!")
    except Exception as e:
        console.print(f"[red]Error generating AI analysis: {e}[/red]")
        return

    # Format the markdown in the AI-generated report
    formatted_report = format_markdown_to_rich(main_report)

    # display the main report in a panel
    main_report_panel = Panel(
        formatted_report,
        title=" AI-Generated Progress Report",
        title_align="left",
        border_style="plum2",
        padding=(1, 2),
    )
    console.print(main_report_panel)

    # Add contributor summaries if requested
    if include_contributor_summaries and git_data["contributors"]:
        console.print(
            "\n[bold pink1]🔍 Generating Detailed Contributor Summaries...[/bold pink1]"
        )

        for contributor_name in git_data["contributors"].keys():
            contributor_summary = create_contributor_summary(git_data)
            main_report += f"\n\n{contributor_summary}\n"
            main_report += "-" * 50

    console.print("[bold green]Progress report generation complete![/bold green]")
    return main_report
