import os
import json

# Walk the repo and collect Python files by directory
def collect_python_files(repo_path):
    directory_map = {}
    SKIP_DIRS = {'venv', '.git', '__pycache__'}

    for root, dirs, files in os.walk(repo_path):
        # Skip hidden and irrelevant directories
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith('.')]
        py_files = [f for f in files if f.endswith(".py")]
        if py_files:
            directory_map[root] = py_files
    return directory_map

# Load prompt template from prompt.txt
def load_prompt_template(path, file_list):
    prompt_path = os.path.join(os.path.dirname(__file__), 'prompt.txt')
    with open(prompt_path, 'r') as f:
        prompt_template = json.load(f)

    # Replace placeholders
    for message in prompt_template:
        if '{path}' in message['content']:
            message['content'] = message['content'].replace('{path}', path)
        if '{file_list}' in message['content']:
            message['content'] = message['content'].replace('{file_list}', file_list)
    return prompt_template

# Summarize a directory using the model
def summarize_directory(path, files, client):
    file_list = "\n".join(files)
    messages = load_prompt_template(path, file_list)
    response = client.chat.completions.create(
        model="reportr",
        messages=messages
    )
    return response.choices[0].message.content

# Print directory tree
def print_tree(root_path, prefix=""):
    SKIP_DIRS = {'venv', '.git', '__pycache__'}
    for item in sorted(os.listdir(root_path)):
        full_path = os.path.join(root_path, item)
        if os.path.isdir(full_path):
            if item in SKIP_DIRS or item.startswith('.'):
                continue
            print(f"{prefix}📁 {item}")
            print_tree(full_path, prefix + "    ")
        elif item.endswith(".py"):
            print(f"{prefix}📄 {item}")

# Main function to be called by the client
def summarize_repo(client, repo_path="."):
    """
    Summarize the repository structure and contents.
    
    Args:
        client: Azure OpenAI client instance
        repo_path: Path to the repository (default: current directory)
    
    Returns:
        str: Summary of the repository
    """
    summary_parts = []
    
    # Add directory tree
    summary_parts.append("📂 Directory Tree:")
    tree_output = []
    def capture_tree(root_path, prefix=""):
        SKIP_DIRS = {'venv', '.git', '__pycache__'}
        for item in sorted(os.listdir(root_path)):
            full_path = os.path.join(root_path, item)
            if os.path.isdir(full_path):
                if item in SKIP_DIRS or item.startswith('.'):
                    continue
                tree_output.append(f"{prefix}📁 {item}")
                capture_tree(full_path, prefix + "    ")
            elif item.endswith(".py"):
                tree_output.append(f"{prefix}📄 {item}")
    
    capture_tree(repo_path)
    summary_parts.append("\n".join(tree_output))
    
    # Add summaries for each directory
    summary_parts.append("\n🧠 Summaries:")
    directory_map = collect_python_files(repo_path)
    for path, files in directory_map.items():
        summary_parts.append(f"\n📁 Directory: {path}")
        summary = summarize_directory(path, files, client)
        summary_parts.append(f"📝 Summary:\n{summary}")
    
    return "\n".join(summary_parts)
