import os
import json
import argparse
from openai import AzureOpenAI
from dotenv import load_dotenv
from rich.console import Console
from rich.tree import Tree
from rich.text import Text
from rich.markdown import Markdown

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
    raw_summary = response.choices[0].message.content
    
    # Format the response with Rich markup for better presentation
    formatted_parts = []
    
    # Add a decorated header
    formatted_parts.append("[bold sky_blue1]Repository Analysis Summary[/bold sky_blue1]\n")
    
    # Add repository info
    repo_name = os.path.basename(os.path.abspath(repo_path))
    formatted_parts.append(f"[bold yellow]Repository:[/bold yellow] {repo_name}")
    formatted_parts.append(f"[bold yellow]Analysis Method:[/bold yellow] Complete JSON Structure Analysis")
    formatted_parts.append(f"[bold yellow]Path:[/bold yellow] {repo_path}\n")
    
    # Add the main summary - use plain text with some basic formatting instead of full markdown
    formatted_parts.append("[bold sky_blue1]Detailed Analysis:[/bold sky_blue1]")
     # Process the summary to add some basic formatting with proper line wrapping
    lines = raw_summary.split('\n')
    processed_lines = []

    for line in lines:
        original_line = line
        line = line.strip()
        
        if not line:
            processed_lines.append("")
            continue
            
        # Color code numbered headers (1., 2., etc.) - these are section headers - CHECK FIRST
        # Only treat as section headers if they are at the start and don't have too much text after
        if (line.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')) and 
            len(line.split()) <= 8 and ':' not in line):
            formatted_line = format_markdown_text(line)
            processed_lines.append(f"\n[bold green]{formatted_line}[/bold green]")
        # Check for section headers that might be getting caught as bullets
        # These are important headers that should be styled like main sections
        elif (line.lower().startswith(('main technologies', 'entry points', 'file organization', 'technologies and patterns', 'getting started')) or
              (len(line.split()) <= 6 and line.endswith(('Technologies', 'Patterns', 'Started', 'Structure', 'Organization')))):
            formatted_line = format_markdown_text(line)
            processed_lines.append(f"\n[bold sky_blue1]{formatted_line}[/bold sky_blue1]")
        # Color code bullet points - handle various indentation levels but normalize to bullet
        elif line.startswith(('•', '-', '*')) or original_line.lstrip().startswith(('•', '-', '*')):
            # Determine indentation level
            indent_level = len(original_line) - len(original_line.lstrip())
            
            # Remove the original bullet character and get the text
            text_content = line[1:].strip() if line.startswith(('•', '-', '*')) else original_line.lstrip()[1:].strip()
            formatted_line = format_markdown_text(text_content)
            
            if indent_level == 0:
                # Top-level bullet
                processed_lines.append(f"    • [white]{formatted_line}[/white]")
            elif indent_level <= 4:
                # First level indent - normal white
                processed_lines.append(f"      • [white]{formatted_line}[/white]")
            else:
                # Deeper indentation - dimmed
                spaces = ' ' * (indent_level + 2)
                processed_lines.append(f"{spaces}• [dim white]{formatted_line}[/dim white]")
        # Handle numbered steps/items within sections (longer numbered lines or indented)
        elif (line.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')) or 
              original_line.lstrip().startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.'))):
            # Determine indentation level
            indent_level = len(original_line) - len(original_line.lstrip())
            
            # Extract the numbered content
            if line.startswith(('1.', '2.', '3.', '4.', '5.', '6.', '7.', '8.', '9.')):
                # Find the number and get the rest
                num_end = line.find('.') + 1
                number_part = line[:num_end]
                text_content = line[num_end:].strip()
            else:
                stripped_line = original_line.lstrip()
                num_end = stripped_line.find('.') + 1
                number_part = stripped_line[:num_end]
                text_content = stripped_line[num_end:].strip()
            
            formatted_line = format_markdown_text(text_content)
            
            if indent_level == 0:
                # Top-level numbered item - make these green to match section headers
                processed_lines.append(f"    {number_part} [bold green]{formatted_line}[/bold green]")
            else:
                # Indented numbered item
                spaces = ' ' * (indent_level + 2)
                processed_lines.append(f"{spaces}{number_part} [white]{formatted_line}[/white]")
        # Headers that end with colons
        elif line.endswith(':') and len(line.split()) <= 6:
            formatted_line = format_markdown_text(line)
            processed_lines.append(f"[bold yellow]{formatted_line}[/bold yellow]")
        # Color code comments (lines starting with #) in dim text
        elif line.startswith('#'):
            formatted_line = format_markdown_text(line)
            processed_lines.append(f"[dim white]{formatted_line}[/dim white]")
        # Regular text - keep as is but format markdown
        else:
            formatted_line = format_markdown_text(line)
            processed_lines.append(formatted_line)
    
    # Join the processed lines and add to formatted parts
    formatted_parts.append('\n'.join(processed_lines))
    
    # Add some repository statistics
    formatted_parts.append("\n[bold sky_blue1]Repository Statistics:[/bold sky_blue1]")
    
    # Count files and folders
    def count_items(structure):
        files = 0
        folders = 0
        for name, content in structure.items():
            if isinstance(content, dict):
                if content.get("type") == "file":
                    files += 1
                elif content.get("type") == "folder":
                    folders += 1
                    sub_files, sub_folders = count_items(content.get("contents", {}))
                    files += sub_files
                    folders += sub_folders
        return files, folders
    
    total_files, total_folders = count_items(repo_structure)
    formatted_parts.append(f"├── [green]Total Files:[/green] {total_files}")
    formatted_parts.append(f"├── [yellow]Total Directories:[/yellow] {total_folders}")
    
    # Count file types
    file_types = {}
    def count_file_types(structure):
        for name, content in structure.items():
            if isinstance(content, dict):
                if content.get("type") == "file":
                    ext = os.path.splitext(name)[1] or "no extension"
                    file_types[ext] = file_types.get(ext, 0) + 1
                elif content.get("type") == "folder":
                    count_file_types(content.get("contents", {}))
    
    count_file_types(repo_structure)
    if file_types:
        formatted_parts.append(f"└── [cyan]File Types:[/cyan]")
        for ext, count in sorted(file_types.items(), key=lambda x: x[1], reverse=True)[:5]:  # Top 5 file types
            formatted_parts.append(f"    ├── {ext}: {count} files")
    
    return "\n".join(formatted_parts)

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
            file_contents += f"\n\nFile: {file}\n{content}"
        except Exception as e:
            file_contents += f"\n\nFile: {file}\n# Error reading file: {e}"

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

    # Add directory tree using a simple text-based approach
    repo_structure = build_repo_structure(repo_path)
    
    summary_parts.append("[bold sky_blue1]Directory Tree:[/bold sky_blue1]")
    tree_output = []
    
    def build_text_tree(structure, prefix="", is_last=True):
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
            
            if isinstance(content, dict) and content.get("type") == "file":
                # This is a file
                tree_output.append(f"{current_prefix}[green]{name}[/green]")
            elif isinstance(content, dict) and content.get("type") == "folder":
                # This is a directory
                tree_output.append(f"{current_prefix}[bold yellow]{name}/[/bold yellow]")
                build_text_tree(content.get("contents", {}), next_prefix, is_last_item)

    build_text_tree(repo_structure)
    summary_parts.append("\n".join(tree_output))

    # Add summaries for each directory
    summary_parts.append("\n[bold sky_blue1]Summaries:[/bold sky_blue1]")
    directory_map = collect_relevant_files(repo_path)

    for path, files in directory_map.items():
        summary_parts.append(f"\n[bold yellow]Directory:[/bold yellow] {path}")
        summary = summarize_directory(path, files, client)
        summary_parts.append(f"[bold green]Summary:[/bold green]\n{summary}")

    return "\n".join(summary_parts)

# Print directory tree
def print_tree(root_path, prefix=""):
    """
    Print directory tree using Rich Tree formatting.
    
    Args:
        root_path: Path to the repository root
        prefix: Indentation prefix for tree display (unused with Rich)
    """
    console = Console()
    repo_structure = build_repo_structure(root_path)
    
    # Create Rich tree structure
    tree = Tree(f"[bold blue]{os.path.basename(root_path) or root_path}[/bold blue]", style="bold blue")
    
    def build_rich_tree(structure, parent_node):
        for name, content in sorted(structure.items()):
            if isinstance(content, dict) and content.get("type") == "file":
                # This is a file - green color
                parent_node.add(f"[green]{name}[/green]")
            elif isinstance(content, dict) and content.get("type") == "folder":
                # This is a directory - yellow color with slash
                folder_node = parent_node.add(f"[bold yellow]{name}/[/bold yellow]")
                build_rich_tree(content.get("contents", {}), folder_node)
    
    build_rich_tree(repo_structure, tree)
    console.print(tree)

def format_markdown_text(text):
    """
    Format markdown-style text with Rich markup for **bold** and `code` elements.
    
    Args:
        text: Text that may contain **bold** or `code` markdown
        
    Returns:
        str: Text with Rich markup applied
    """
    import re
    
    # Replace **bold text** with Rich bold markup in bright white
    text = re.sub(r'\*\*(.*?)\*\*', r'[bold bright_white]\1[/bold bright_white]', text)
    
    # Replace `code text` with Rich markup in bright yellow
    text = re.sub(r'`(.*?)`', r'[bright_yellow]\1[/bright_yellow]', text)
    
    return text
