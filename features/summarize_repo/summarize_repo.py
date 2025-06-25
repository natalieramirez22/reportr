import os
import json

# Walk the repo and collect relevant files by directory
def collect_relevant_files(repo_path):
    directory_map = {}
    SKIP_DIRS = {'venv', '.git', '__pycache__'}
    INCLUDED_EXTENSIONS = {'.py', '.md', '.txt'}

    for root, dirs, files in os.walk(repo_path):
        # Skip hidden and irrelevant directories
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith('.')]
        relevant_files = [f for f in files if os.path.splitext(f)[1] in INCLUDED_EXTENSIONS]
        if relevant_files:
            directory_map[root] = relevant_files
    return directory_map

# Load prompt template from prompt.txt and inject file contents
def load_prompt_template(path, file_contents):
    prompt_path = os.path.join(os.path.dirname(__file__), 'prompt.txt')
    with open(prompt_path, 'r') as f:
        prompt_template = json.load(f)

    # Replace placeholders
    for message in prompt_template:
        if '{path}' in message['content']:
            message['content'] = message['content'].replace('{path}', path)
        if '{file_contents}' in message['content']:
            message['content'] = message['content'].replace('{file_contents}', file_contents)
    return prompt_template

# Summarize a directory using the model
def summarize_directory(path, files, client):
    file_contents = ""
    for file in files:
        file_path = os.path.join(path, file)
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            file_contents += f"\n\n📄 File: {file}\n{content}"
        except Exception as e:
            file_contents += f"\n\n📄 File: {file}\n# Error reading file: {e}"

    messages = load_prompt_template(path, file_contents)
    response = client.chat.completions.create(
        model="reportr",
        messages=messages
    )
    # print json dumps of prompt
    # print(json.dumps(messages, indent=2))
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
        elif os.path.isfile(full_path):
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
            
            print(f"Processing item: {item} at path: {full_path}")

            if os.path.isdir(full_path):
                if item in SKIP_DIRS or item.startswith('.'):
                    continue
                tree_output.append(f"{prefix}📁 {item}")
                capture_tree(full_path, prefix + "    ")
            elif os.path.isfile(full_path):
                tree_output.append(f"{prefix}📄 {item}")

            # print(tree_output)

    capture_tree(repo_path)
    summary_parts.append("\n".join(tree_output))

    # Add summaries for each directory
    summary_parts.append("\n🧠 Summaries:")
    directory_map = collect_relevant_files(repo_path)

    print(f"directory path: {directory_map}")

    for path, files in directory_map.items():
        summary_parts.append(f"\n📁 Directory: {path}")
        summary = summarize_directory(path, files, client)
        summary_parts.append(f"📝 Summary:\n{summary}")

    return "\n".join(summary_parts)
