import os
import openai
from openai import AzureOpenAI
from dotenv import load_dotenv
from git import Repo
from datetime import datetime, timedelta
import argparse
import json

def get_git_history(repo_path=".", days_back=30):
    """
    Extract git history information from the repository
    """
    try:
        repo = Repo(repo_path)
        
        # Get commits from the last N days
        since_date = datetime.now() - timedelta(days=days_back)
        commits = list(repo.iter_commits('main', since=since_date))
        
        if not commits:
            # If no commits in main, try master branch
            commits = list(repo.iter_commits('master', since=since_date))
        
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
            commit_date = datetime.fromtimestamp(commit.committed_date)
            commit_message = commit.message.strip()
            
            # Count contributions per author
            if author_name not in contributors:
                contributors[author_name] = {
                    'email': author_email,
                    'commits': 0,
                    'lines_added': 0,
                    'lines_deleted': 0
                }
            
            contributors[author_name]['commits'] += 1
            
            # Get stats for this commit
            lines_added = 0
            lines_deleted = 0
            try:
                stats = commit.stats
                lines_added = stats.total['insertions']
                lines_deleted = stats.total['deletions']
                contributors[author_name]['lines_added'] += lines_added
                contributors[author_name]['lines_deleted'] += lines_deleted
            except:
                pass
            
            commit_data.append({
                'hash': commit.hexsha[:8],
                'author': author_name,
                'date': commit_date.strftime('%Y-%m-%d %H:%M:%S'),
                'message': commit_message,
                'lines_added': lines_added,
                'lines_deleted': lines_deleted
            })
        
        return {
            'repo_name': str(repo.working_dir).split('/')[-1] if repo.working_dir else 'Unknown',
            'total_commits': len(commit_data),
            'contributors': contributors,
            'commits': commit_data,
            'period': f"Last {days_back} days" if days_back > 0 else "All time"
        }
        
    except Exception as e:
        print(f"Error accessing git repository: {e}")
        return None

def create_progress_report(client, repo_path=".", days_back=30):
    """
    Create a comprehensive progress report for a git repository
    """
    print("Analyzing git repository...")
    git_data = get_git_history(repo_path, days_back)
    
    if not git_data:
        print("Could not analyze git repository. Make sure you're in a git repository.")
        return
    
    # Prepare the data for the LLM
    report_context = f"""
Repository: {git_data['repo_name']}
Analysis Period: {git_data['period']}
Total Commits: {git_data['total_commits']}

Contributors ({len(git_data['contributors'])}):
"""
    
    for author, stats in git_data['contributors'].items():
        report_context += f"""
- {author} ({stats['email']})
  - Commits: {stats['commits']}
  - Lines Added: {stats['lines_added']}
  - Lines Deleted: {stats['lines_deleted']}
"""
    
    report_context += "\nRecent Commits:\n"
    for commit in git_data['commits'][:20]:  # Show last 20 commits
        report_context += f"""
- {commit['date']} - {commit['author']} ({commit['hash']})
  {commit['message']}
  +{commit['lines_added']} -{commit['lines_deleted']} lines
"""
    
    # Load the prompt template
    prompt_path = os.path.join(os.path.dirname(__file__), 'prompt.txt')
    try:
        with open(prompt_path, 'r') as f:
            prompt_template = f.read()
        
        # Replace the placeholder with actual data
        messages = eval(prompt_template.replace('{report_context}', f'"{report_context}"'))
        
    except Exception as e:
        print(f"Error loading prompt template: {e}")
        # Fallback to hardcoded prompt
        messages = [
            {
                "role": "system", 
                "content": """You are a helpful assistant that creates clear, professional progress reports for software development projects. 
                Analyze the git history data provided and create a comprehensive progress report that includes:
                1. Executive summary of development activity
                2. Key contributors and their contributions
                3. Major changes and improvements made
                4. Development patterns and trends
                5. Summary of code changes (additions/deletions)
                
                Write in clear, professional language suitable for stakeholders and team members."""
            },
            {
                "role": "user", 
                "content": f"Create a progress report for this repository based on the following git history data:\n\n{report_context}"
            }
        ]
    
    # Generate the report using the LLM
    response = client.chat.completions.create(
        model="reportr",
        messages=messages,
        max_tokens=2000,
        temperature=0.7
    )
    
    return response.choices[0].message.content 