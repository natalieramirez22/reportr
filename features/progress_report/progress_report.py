import os
import json
from git import Repo
from datetime import datetime, timedelta


def get_git_history(repo_path=".", days_back=30, contributor_filter=None):
    """
    Extract git history information from the repository
    Args:
        repo_path: Path to the repository
        days_back: Number of days to look back (0 for all time)
        contributor_filter: Optional list of contributor names to filter by
    """
    try:
        repo = Repo(repo_path)

        # Get commits from the last N days
        since_date = datetime.now() - timedelta(days=days_back)
        commits = list(repo.iter_commits("main", since=since_date))

        if not commits:
            # If no commits in main, try master branch
            commits = list(repo.iter_commits("master", since=since_date))

        if not commits:
            # If still no commits, get all commits
            commits = list(repo.iter_commits())

        # Collect commit information
        commit_data = []
        contributors = {}

        for commit in commits:
            # Skip merge commits for cleaner analysis
            if len(commit.parents) > 1:
                continue

            author_name = commit.author.name
            author_email = commit.author.email

            # Filter by contributor if specified
            if contributor_filter and author_name not in contributor_filter:
                continue

            commit_date = datetime.fromtimestamp(commit.committed_date)
            commit_message = commit.message.strip()

            # Count contributions per author
            if author_name not in contributors:
                contributors[author_name] = {
                    "email": author_email,
                    "commits": 0,
                    "lines_added": 0,
                    "lines_deleted": 0,
                    "files_changed": 0,
                    "commit_messages": [],
                }

            contributors[author_name]["commits"] += 1
            contributors[author_name]["commit_messages"].append(commit_message)

            # Get stats for this commit
            lines_added = 0
            lines_deleted = 0
            files_changed = 0
            try:
                stats = commit.stats
                lines_added = stats.total["insertions"]
                lines_deleted = stats.total["deletions"]
                files_changed = len(stats.files)
                contributors[author_name]["lines_added"] += lines_added
                contributors[author_name]["lines_deleted"] += lines_deleted
                contributors[author_name]["files_changed"] += files_changed
            except:
                pass

            commit_data.append(
                {
                    "hash": commit.hexsha[:8],
                    "author": author_name,
                    "date": commit_date.strftime("%Y-%m-%d %H:%M:%S"),
                    "message": commit_message,
                    "lines_added": lines_added,
                    "lines_deleted": lines_deleted,
                    "files_changed": files_changed,
                }
            )

        return {
            "repo_name": (
                str(repo.working_dir).split("/")[-1] if repo.working_dir else "Unknown"
            ),
            "total_commits": len(commit_data),
            "contributors": contributors,
            "commits": commit_data,
            "period": f"Last {days_back} days" if days_back > 0 else "All time",
            "filtered_by": (
                contributor_filter if contributor_filter else "All contributors"
            ),
        }

    except Exception as e:
        print(f"Error accessing git repository: {e}")
        return None


def create_contributor_summary(client, git_data, contributor_name):
    """
    Create a detailed summary for a specific contributor
    """
    if contributor_name not in git_data["contributors"]:
        return f"Contributor '{contributor_name}' not found in the repository."

    contributor_data = git_data["contributors"][contributor_name]
    contributor_commits = [
        c for c in git_data["commits"] if c["author"] == contributor_name
    ]

    summary_context = f"""
    Contributor Analysis: {contributor_name}
    Email: {contributor_data['email']}
    Period: {git_data['period']}
    
    Summary Statistics:
    - Total Commits: {contributor_data['commits']}
    - Lines Added: {contributor_data['lines_added']}
    - Lines Deleted: {contributor_data['lines_deleted']}
    - Files Changed: {contributor_data['files_changed']}
    - Net Lines: {contributor_data['lines_added'] - contributor_data['lines_deleted']}
    
    Recent Commit Messages:
    """

    for commit in contributor_commits[:15]:  # Show last 15 commits
        summary_context += f"""
    - {commit['date']} ({commit['hash']})
      {commit['message']}
      +{commit['lines_added']} -{commit['lines_deleted']} lines, {commit['files_changed']} files
    """

    # Create a specialized prompt for contributor analysis
    contributor_prompt = [
        {
            "role": "system",
            "content": "You are an expert at analyzing developer contributions. Create a detailed, professional summary of a contributor's work that includes: 1. Overall contribution assessment 2. Development patterns and focus areas 3. Code quality indicators (based on commit patterns) 4. Key achievements and notable changes 5. Recommendations or observations about their work style. Write in clear, professional language.",
        },
        {
            "role": "user",
            "content": f"Analyze this contributor's work and create a detailed summary:\n\n{summary_context}",
        },
    ]

    response = client.chat.completions.create(
        model="reportr", messages=contributor_prompt, max_tokens=1500, temperature=0.7
    )

    return response.choices[0].message.content


def create_progress_report(
    client,
    repo_path=".",
    days_back=30,
    contributor_filter=None,
    include_contributor_summaries=False,
):
    """
    Create a comprehensive progress report for a git repository
    Args:
        client: The LLM client
        repo_path: Path to the repository
        days_back: Number of days to look back (0 for all time)
        contributor_filter: Optional list of contributor names to filter by
        include_contributor_summaries: Whether to include detailed summaries for each contributor
    """
    print("Analyzing git repository...")
    git_data = get_git_history(repo_path, days_back, contributor_filter)

    if not git_data:
        print("Could not analyze git repository. Make sure you're in a git repository.")
        return

    # Prepare the data for the LLM
    report_context = f"""
        Repository: {git_data['repo_name']}
        Analysis Period: {git_data['period']}
        Filter: {git_data['filtered_by']}
        Total Commits: {git_data['total_commits']}

        Contributors ({len(git_data['contributors'])}):
    """

    for author, stats in git_data["contributors"].items():
        report_context += f"""
        - {author} ({stats['email']})
        - Commits: {stats['commits']}
        - Lines Added: {stats['lines_added']}
        - Lines Deleted: {stats['lines_deleted']}
        - Files Changed: {stats['files_changed']}
        - Net Lines: {stats['lines_added'] - stats['lines_deleted']}
        """

    report_context += "\nRecent Commits:\n"
    for commit in git_data["commits"][:20]:  # Show last 20 commits
        report_context += f"""
- {commit['date']} - {commit['author']} ({commit['hash']})
  {commit['message']}
  +{commit['lines_added']} -{commit['lines_deleted']} lines, {commit['files_changed']} files
"""

    # Load the prompt template
    prompt_path = os.path.join(os.path.dirname(__file__), "prompt.txt")
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
        print(f"Error loading prompt template: {e}")
        return

    # Generate the main report using the LLM
    response = client.chat.completions.create(
        model="reportr", messages=messages, max_tokens=2000, temperature=0.7
    )

    main_report = response.choices[0].message.content

    # Add contributor summaries if requested
    if include_contributor_summaries and git_data["contributors"]:
        main_report += (
            "\n\n" + "=" * 50 + "\nDETAILED CONTRIBUTOR SUMMARIES\n" + "=" * 50 + "\n"
        )

        for contributor_name in git_data["contributors"].keys():
            contributor_summary = create_contributor_summary(
                client, git_data, contributor_name
            )
            main_report += f"\n\n{contributor_summary}\n"
            main_report += "-" * 50

    return main_report
