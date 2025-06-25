import os
import json
import argparse
from openai import AzureOpenAI
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Set up Azure OpenAI client
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version="2024-02-15-preview",
    azure_endpoint="https://natalie-design-agent-resource.cognitiveservices.azure.com/",
)


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
    # print json dumps of prompt
    # print(json.dumps(messages, indent=2))
    return response.choices[0].message.content


# Print directory tree
def print_tree(root_path, prefix=""):
    SKIP_DIRS = {"venv", ".git", "__pycache__"}

    for item in sorted(os.listdir(root_path)):
        full_path = os.path.join(root_path, item)
        if os.path.isdir(full_path):
            if item in SKIP_DIRS or item.startswith("."):
                continue
            print(f"{prefix}📁 {item}")
            # print_tree(full_path, prefix + "    ")
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
        SKIP_DIRS = {"venv", ".git", "__pycache__"}

        for item in sorted(os.listdir(root_path)):
            full_path = os.path.join(root_path, item)

            print(f"Processing item: {item} at path: {full_path}")

            if os.path.isdir(full_path):
                if item in SKIP_DIRS or item.startswith("."):
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

    for path, files in directory_map.items():
        summary_parts.append(f"\n📁 Directory: {path}")
        summary = summarize_directory(path, files, client)
        summary_parts.append(f"📝 Summary:\n{summary}")

    return "\n".join(summary_parts)


# build a nested dictionary structure of the repository
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
                repo_content[item] = _build_structure(full_path)
            elif os.path.isfile(full_path):
                # only include files with specified extensions
                if os.path.splitext(item)[1] in INCLUDED_EXTENSIONS:
                    try:
                        with open(full_path, "r", encoding="utf-8") as file:
                            content = file.read()
                        repo_content[item] = {"content": content}
                    except Exception as e:
                        repo_content[item] = {"content": f"# Error reading file: {e}"}

        return repo_content

    return _build_structure(repo_path)


def save_repo_structure_to_json(repo_path, output_file="repo_structure.json"):
    """
    Build a nested dictionary structure representing the repository and save it to a JSON file.

    Args:
        repo_path: Path to the repository
        output_file: Name of the output JSON file (default: repo_structure.json)

    Returns:
        str: Path to the created JSON file
    """
    # Build the structure
    repo_structure = build_repo_structure(repo_path)

    # Save to JSON file
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(repo_structure, f, indent=2, ensure_ascii=False)

    return output_file


def summarize_repo_with_json_structure(client, repo_path="."):
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
