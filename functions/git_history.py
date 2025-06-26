from datetime import datetime, timedelta
from git import Repo
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
import os
from collections import defaultdict
import re

console = Console()


def get_commit_diffs_by_file(repo_path=".", commit_hash=None):
    """
    Returns a dictionary of file diffs for a specific commit.
    Args:
        repo_path: Path to the Git repository
        commit_hash: The hash of the commit to analyze
    Returns:
        A dictionary where keys are filenames and values are the diff text
    """
    try:
        repo = Repo(repo_path)
        commit = repo.commit(commit_hash)

        diffs = {}
        parent = commit.parents[0] if commit.parents else None

        if parent:
            diff_index = parent.diff(commit, create_patch=True)
        else:
            # Initial commit (no parent)
            diff_index = commit.diff(None, create_patch=True)

        for diff in diff_index:
            if diff.a_path:
                file_path = diff.a_path
            elif diff.b_path:
                file_path = diff.b_path
            else:
                continue

            # Handle both bytes and string diff content
            if hasattr(diff, "diff") and diff.diff:
                if isinstance(diff.diff, bytes):
                    diffs[file_path] = diff.diff.decode("utf-8", errors="replace")
                else:
                    diffs[file_path] = str(diff.diff)
            else:
                diffs[file_path] = "No diff content available"

        return diffs

    except Exception as e:
        console.print(f"[red]Error getting diffs: {e}[/red]")
        return {}


def analyze_diff_for_lines(diff_content):
    """
    Analyze diff content to count lines added and deleted
    """
    lines_added = 0
    lines_deleted = 0

    if diff_content:
        # Count lines starting with + (added) and - (deleted)
        for line in diff_content.split("\n"):
            if line.startswith("+") and not line.startswith("+++"):
                lines_added += 1
            elif line.startswith("-") and not line.startswith("---"):
                lines_deleted += 1

    return lines_added, lines_deleted


def analyze_commit_message(message):
    """
    Categorize commit message to determine commit type
    """
    message_lower = message.lower()

    if any(word in message_lower for word in ["fix", "bug", "issue", "error"]):
        return "fix"
    elif any(word in message_lower for word in ["feat", "add", "implement", "new"]):
        return "feature"
    elif any(word in message_lower for word in ["refactor", "clean", "restructure"]):
        return "refactor"
    elif any(word in message_lower for word in ["doc", "readme", "comment"]):
        return "docs"
    else:
        return "other"


def get_repository_structure(repo_path="."):
    """
    Get a basic overview of repository structure
    """
    try:
        structure = []
        for root, dirs, files in os.walk(repo_path):
            # Skip .git directory
            if ".git" in root:
                continue

            # Get relative path
            rel_path = os.path.relpath(root, repo_path)
            if rel_path == ".":
                structure.append(f"Root: {len(files)} files")
            else:
                structure.append(f"{rel_path}/: {len(files)} files")

            # Limit depth to avoid too much detail
            if len(rel_path.split(os.sep)) > 2:
                continue

        return structure[:10]  # Limit to first 10 entries
    except Exception as e:
        return [f"Error reading structure: {e}"]


def get_git_history(repo_path=".", days_back=30, contributor_filter=None, branch=None):
    """
    Extract comprehensive git history information from the repository
    Args:
        repo_path: Path to the repository
        days_back: Number of days to look back (0 for all time)
        contributor_filter: Optional list of contributor names to filter by
        branch: Optional branch name to analyze (default: tries main, then master, then all branches)
    """
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Analyzing git repository...", total=None)

            repo = Repo(repo_path)

            # get repo commits for the last x days
            since_date = datetime.now() - timedelta(days=days_back)

            # Use specified branch, or try main/master, or get all commits
            if branch:
                try:
                    commits = list(repo.iter_commits(branch, since=since_date))
                    if not commits:
                        console.print(
                            f"[yellow]Warning: No commits found in branch '{branch}' for the specified time period.[/yellow]"
                        )
                except Exception as e:
                    console.print(f"[red]Error accessing branch '{branch}': {e}[/red]")
                    return None
            else:
                # Try main branch first
                try:
                    commits = list(repo.iter_commits("main", since=since_date))
                except:
                    commits = []

                if not commits:
                    # If no commits in main, try master branch
                    try:
                        commits = list(repo.iter_commits("master", since=since_date))
                    except:
                        commits = []

                if not commits:
                    # If still no commits, get all commits from all branches
                    commits = list(repo.iter_commits())

            progress.update(task, description="Processing commits...")

            # Initialize data structures
            commit_information = []
            contributors = defaultdict(
                lambda: {
                    "commits": 0,
                    "lines_added": 0,
                    "lines_deleted": 0,
                    "files_changed": 0,
                }
            )

            file_changes = defaultdict(int)
            file_types = defaultdict(int)
            commit_types = defaultdict(int)
            day_activity = defaultdict(int)
            total_lines_added = 0
            total_lines_deleted = 0
            total_files_changed = 0

            for commit in commits:
                # skip merge commits
                if len(commit.parents) > 1:
                    continue

                author_name = commit.author.name
                author_email = commit.author.email

                # Filter by contributor if specified
                if contributor_filter and author_name not in contributor_filter:
                    continue

                commit_date = datetime.fromtimestamp(commit.committed_date)
                commit_message = commit.message.strip()
                commit_diffs = get_commit_diffs_by_file(repo_path, commit.hexsha)

                # Analyze diff for line counts
                lines_added = 0
                lines_deleted = 0
                files_changed = len(commit_diffs)

                for file_path, diff_content in commit_diffs.items():
                    file_added, file_deleted = analyze_diff_for_lines(diff_content)
                    lines_added += file_added
                    lines_deleted += file_deleted

                    # Track file changes
                    file_changes[file_path] += 1

                    # Track file types
                    file_ext = os.path.splitext(file_path)[1]
                    if file_ext:
                        file_types[file_ext] += 1

                # Categorize commit
                commit_type = analyze_commit_message(commit_message)
                commit_types[commit_type] += 1

                # Track day activity
                day_key = commit_date.strftime("%A")
                day_activity[day_key] += 1

                # Update totals
                total_lines_added += lines_added
                total_lines_deleted += lines_deleted
                total_files_changed += files_changed

                # Update contributor stats
                contributors[author_name]["commits"] += 1
                contributors[author_name]["lines_added"] += lines_added
                contributors[author_name]["lines_deleted"] += lines_deleted
                contributors[author_name]["files_changed"] += files_changed

                commit_information.append(
                    {
                        "hash": commit.hexsha,
                        "author": author_name,
                        "date": commit_date.strftime("%Y-%m-%d %H:%M:%S"),
                        "message": commit_message,
                        "diffs": commit_diffs,
                        "lines_added": lines_added,
                        "lines_deleted": lines_deleted,
                        "files_changed": files_changed,
                    }
                )

        history = {
            "repo_name": (
                str(repo.working_dir).split("/")[-1] if repo.working_dir else "Unknown"
            ),
            "total_commits": len(commit_information),
            "commits": commit_information,
            "period": f"Last {days_back} days" if days_back > 0 else "All time",
            "contributor": (
                contributor_filter if contributor_filter else "All contributors"
            ),
            "filtered_by": (
                contributor_filter if contributor_filter else "All contributors"
            ),
            "contributors": dict(contributors),
            "repository_structure": get_repository_structure(repo_path),
        }

        # console.print(f"History: {history}")

        return history

    except Exception as e:
        console.print(f"[red]Error accessing git repository: {e}[/red]")
        return None
