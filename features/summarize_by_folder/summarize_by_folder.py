import os
import json
from openai import AzureOpenAI
from dotenv import load_dotenv
from rich.console import Console
from rich.tree import Tree

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
    
    # Replace `code text` with Rich markup, but only if properly closed
    # This prevents issues with unclosed backticks causing everything to be treated as code
    text = re.sub(r'`([^`\n]+)`', r'[cornsilk1]\1[/cornsilk1]', text)
    
    return text

# Repository size limits to prevent excessive costs
MAX_FILES = 500  # Maximum number of files to process
MAX_TOTAL_SIZE_MB = 50  # Maximum total file size in MB
MAX_SINGLE_FILE_SIZE_KB = 500  # Maximum single file size in KB

def validate_repo_size(repo_path):
    """
    Validate repository size to prevent excessive API costs.
    
    Args:
        repo_path: Path to the repository
        
    Returns:
        tuple: (is_valid, message, stats)
    """
    SKIP_DIRS = {"venv", ".git", "__pycache__", "node_modules", "dist", "build"}
    INCLUDED_EXTENSIONS = {
        ".py", ".md", ".txt", ".json", ".js", ".jsx", ".ts", ".tsx", ".cs", ".rs", 
        ".go", ".java", ".php", ".rb", ".swift", ".kt", ".cpp", ".c", ".h", ".hpp", 
        ".sh", ".bat", ".yml", ".yaml", ".xml", ".html", ".css", ".scss", ".less", 
        ".sass", ".sql", ".csv", ".tsv", ".jsonl"
    }
    
    total_files = 0
    total_size = 0
    large_files = []
    
    for root, dirs, files in os.walk(repo_path):
        # Skip irrelevant directories
        dirs[:] = [d for d in dirs if d not in SKIP_DIRS and not d.startswith(".")]
        
        for file in files:
            if os.path.splitext(file)[1] in INCLUDED_EXTENSIONS:
                file_path = os.path.join(root, file)
                try:
                    file_size = os.path.getsize(file_path)
                    total_files += 1
                    total_size += file_size
                    
                    # Check individual file size
                    if file_size > MAX_SINGLE_FILE_SIZE_KB * 1024:
                        large_files.append((file_path, file_size))
                        
                except (OSError, IOError):
                    continue
    
    total_size_mb = total_size / (1024 * 1024)
    
    # Validation checks
    if total_files > MAX_FILES:
        return False, f"Repository has {total_files} files (limit: {MAX_FILES}). Consider excluding some directories.", {
            'files': total_files, 'size_mb': total_size_mb, 'large_files': large_files
        }
    
    if total_size_mb > MAX_TOTAL_SIZE_MB:
        return False, f"Repository size is {total_size_mb:.1f}MB (limit: {MAX_TOTAL_SIZE_MB}MB). Consider excluding large files.", {
            'files': total_files, 'size_mb': total_size_mb, 'large_files': large_files
        }
    
    return True, f"Repository validated: {total_files} files, {total_size_mb:.1f}MB", {
        'files': total_files, 'size_mb': total_size_mb, 'large_files': large_files
    }

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
    # Validate repository size first
    is_valid, message, stats = validate_repo_size(repo_path)
    if not is_valid:
        return f"[red]Error: {message}[/red]\n\nRepository stats:\n- Files: {stats['files']}\n- Size: {stats['size_mb']:.1f}MB\n\nConsider using .gitignore patterns or excluding large directories to reduce size."
    
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
        # Add directory header - don't decorate the path value
        summary_parts.append(f"\n[bold yellow]Directory:[/bold yellow] {path}")
        
        # Get the raw summary
        summary = summarize_directory(path, files, client)
        
        # Add summary header
        summary_parts.append("[bold green]Summary:[/bold green]")
        
        # Process each line with proper formatting similar to summarize_entire_directory
        lines = summary.split('\n')
        in_numbered_list = False
        
        for line in lines:
            original_line = line
            line = line.strip()
            
            if not line:
                summary_parts.append("")
                in_numbered_list = False
                continue
                
            # Check for markdown headers (## Section Name)
            if line.startswith('## '):
                header_text = line[3:].strip()
                formatted_line = format_markdown_text(header_text)
                summary_parts.append(f"\n[bold green]{formatted_line}[/bold green]")
                in_numbered_list = False
            # Handle numbered lists
            elif line.startswith(('1. ', '2. ', '3. ', '4. ', '5. ', '6. ', '7. ', '8. ', '9. ')):
                space_index = line.find(' ')
                number_part = line[:space_index + 1]
                text_content = line[space_index + 1:].strip()
                formatted_line = format_markdown_text(text_content)
                summary_parts.append(f"    [bold cyan]{number_part}[/bold cyan][white]{formatted_line}[/white]")
                in_numbered_list = True
            # Handle bullet points
            elif line.startswith('- '):
                text_content = line[2:].strip()
                formatted_line = format_markdown_text(text_content)
                if in_numbered_list:
                    summary_parts.append(f"        ◦ [white]{formatted_line}[/white]")
                else:
                    summary_parts.append(f"    • [white]{formatted_line}[/white]")
            # Handle continuation text under numbered items
            elif in_numbered_list and (original_line.startswith('  ') or original_line.startswith('\t') or line.startswith('◦')):
                formatted_line = format_markdown_text(line)
                if line.startswith('◦'):
                    summary_parts.append(f"        [white]{formatted_line}[/white]")
                else:
                    summary_parts.append(f"        ◦ [white]{formatted_line}[/white]")
            # Regular text
            else:
                formatted_line = format_markdown_text(line)
                # Ensure all text has proper color formatting
                if formatted_line and not formatted_line.startswith('['):
                    summary_parts.append(f"[white]{formatted_line}[/white]")
                else:
                    summary_parts.append(formatted_line)
                in_numbered_list = False

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
