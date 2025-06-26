import os
import json
import argparse
from openai import AzureOpenAI
from dotenv import load_dotenv

# build a nested dictionary structure of the repository
# used for both summarize_by_folder and summarize_entire_directory functions
def build_repo_structure(repo_path):
    """
    Build a nested dictionary structure representing the repository.

    Args:
        repo_path: Path to the repository

    Returns:
        dict: Nested dictionary with folder names as keys and lists of file dictionaries as values
    """
    SKIP_DIRS = {"venv", ".git", "__pycache__", "node_modules", "dist", "build"}
    INCLUDED_EXTENSIONS = {
        ".py",
        ".md",
        ".txt",
        ".json",
        ".js",
        ".jsx",
        ".ts",
        ".tsx",
        ".cs",
        ".rs",
        ".go",
        ".java",
        ".php",
        ".rb",
        ".swift",
        ".kt",
        ".cpp",
        ".c",
        ".h",
        ".hpp",
        ".sh",
        ".bat",
        ".yml",
        ".yaml",
        ".xml",
        ".html",
        ".css",
        ".scss",
        ".less",
        ".sass",
        ".sql",
        ".csv",
        ".tsv",
        ".jsonl",
    }

    def _build_structure(path):
        repo_content = {}

        for item in sorted(os.listdir(path)):
            full_path = os.path.join(path, item)

            if os.path.isdir(full_path):
                if item in SKIP_DIRS or item.startswith("."):
                    continue
                # recursively build structure for subdirectories
                subfolder_content = _build_structure(full_path)
                repo_content[item] = {
                    "type": "folder",
                    "contents": subfolder_content
                }
            elif os.path.isfile(full_path):
                # only include files with specified extensions
                if os.path.splitext(item)[1] in INCLUDED_EXTENSIONS:
                    try:
                        with open(full_path, "r", encoding="utf-8") as file:
                            content = file.read()
                        repo_content[item] = {
                            "type": "file",
                            "content": content
                        }
                    except Exception as e:
                        repo_content[item] = {
                            "type": "file",
                            "content": f"# Error reading file: {e}"
                        }

        return repo_content

    return _build_structure(repo_path)

def summarize_entire_directory(client, repo_path="."):
    """
    Summarize the repository using the raw JSON structure as context.
    More efficient for large repositories as it sends the structure directly.

    Args:
        client: Azure OpenAI client instance
        repo_path: Path to the repository (default: current directory)

    Returns:
        str: Summary of the repository
    """
    # Build the complete repository structure
    repo_structure = build_repo_structure(repo_path)

    # Convert to JSON string
    structure_json = json.dumps(repo_structure, indent=2, ensure_ascii=False)

    # Create a new prompt for the entire repository
    messages = [
        {
            "role": "system",
            "content": "You are a precise and confident assistant that deeply understands codebases and summarizes them for onboarding engineers. You will receive a JSON structure representing a repository and should analyze it comprehensively.",
        },
        {
            "role": "user",
            "content": f"You are analyzing the entire repository structure represented as JSON:\n\n```json\n{structure_json}\n```\n\nPlease provide a comprehensive summary of this codebase including:\n1. Overall purpose and functionality\n2. Key components and their relationships\n3. Main technologies and patterns used\n4. Entry points and how to get started\n5. File organization and structure\n\nWrite a clear, confident summary that would help a new engineer understand the codebase quickly.",
        },
    ]

    response = client.chat.completions.create(model="reportr", messages=messages)
    return response.choices[0].message.content

# Load prompt template from prompt.txt and inject file contents
def load_prompt_template(path, file_contents):
    prompt_path = os.path.join(os.path.dirname(__file__), "prompt.txt")
    with open(prompt_path, "r") as f:
        prompt_template = json.load(f)

    # Replace placeholders
    for message in prompt_template:
        if "{path}" in message["content"]:
            message["content"] = message["content"].replace("{path}", path)
        if "{file_contents}" in message["content"]:
            message["content"] = message["content"].replace(
                "{file_contents}", file_contents
            )
    return prompt_template

# Walk the repo and collect relevant files by directory
def collect_relevant_files(repo_path):
    directory_map = {}
    SKIP_DIRS = {"venv", ".git", "__pycache__"}
    INCLUDED_EXTENSIONS = {".py", ".md", ".txt"}

    for root, dirs, files in os.walk(repo_path):
        # Skip hidden and irrelevant directories
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        relevant_files = [
            f for f in files if os.path.splitext(f)[1] in INCLUDED_EXTENSIONS
        ]
        if relevant_files:
            directory_map[root] = relevant_files
    return directory_map

# Summarize a directory using the model
def summarize_directory(path, files, client):
    file_contents = ""
    for file in files:
        file_path = os.path.join(path, file)
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
            file_contents += f"\n\n📄 File: {file}\n{content}"
        except Exception as e:
            file_contents += f"\n\n📄 File: {file}\n# Error reading file: {e}"

    messages = load_prompt_template(path, file_contents)
    response = client.chat.completions.create(model="reportr", messages=messages)
    return response.choices[0].message.content

# Main function to be called by the client
def summarize_by_folder(client, repo_path="."):
    """
    Summarize the repository structure and contents.

    Args:
        client: Azure OpenAI client instance
        repo_path: Path to the repository (default: current directory)

    Returns:
        str: Summary of the repository
    """
    summary_parts = []

    # Add directory tree using build_repo_structure
    summary_parts.append("📂 Directory Tree:")
    tree_output = []
    
    repo_structure = build_repo_structure(repo_path)
    
    def capture_tree_from_structure(structure, prefix="", is_last=True):
        items = list(sorted(structure.items()))
        for i, (name, content) in enumerate(items):
            is_last_item = (i == len(items) - 1)
            
            # Choose the appropriate tree character
            if prefix == "":
                # Root level
                current_prefix = "├── " if not is_last_item else "└── "
                next_prefix = "│   " if not is_last_item else "    "
            else:
                current_prefix = prefix + ("├── " if not is_last_item else "└── ")
                next_prefix = prefix + ("│   " if not is_last_item else "    ")
            
            tree_output.append(f"{current_prefix}{name}")
            
            # If it's a folder, recursively process its contents
            if isinstance(content, dict) and content.get("type") == "folder":
                capture_tree_from_structure(content.get("contents", {}), next_prefix, is_last_item)

    capture_tree_from_structure(repo_structure)
    summary_parts.append("\n".join(tree_output))

    # Add summaries for each directory
    summary_parts.append("\n🧠 Summaries:")
    directory_map = collect_relevant_files(repo_path)

    for path, files in directory_map.items():
        summary_parts.append(f"\n📁 Directory: {path}")
        summary = summarize_directory(path, files, client)
        summary_parts.append(f"📝 Summary:\n{summary}")

    return "\n".join(summary_parts)

# Print directory tree
def print_tree(root_path, prefix=""):
    """
    Print directory tree using the structure from build_repo_structure.
    
    Args:
        root_path: Path to the repository root
        prefix: Indentation prefix for tree display
    """
    repo_structure = build_repo_structure(root_path)
    
    def _print_structure(structure, current_prefix=""):
        for name, content in sorted(structure.items()):
            if isinstance(content, dict) and content.get("type") == "file":
                # This is a file
                print(f"{current_prefix}📄 {name}")
            elif isinstance(content, dict) and content.get("type") == "folder":
                # This is a directory
                print(f"{current_prefix}📁 {name}")
                _print_structure(content.get("contents", {}), current_prefix + "    ")
    
    _print_structure(repo_structure, prefix)
