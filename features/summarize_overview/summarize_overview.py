import os
import json
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn


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
                repo_content[item] = {"type": "folder", "contents": subfolder_content}
            elif os.path.isfile(full_path):
                # only include files with specified extensions
                if os.path.splitext(item)[1] in INCLUDED_EXTENSIONS:
                    try:
                        with open(full_path, "r", encoding="utf-8") as file:
                            content = file.read()
                        repo_content[item] = {"type": "file", "content": content}
                    except Exception as e:
                        repo_content[item] = {
                            "type": "file",
                            "content": f"# Error reading file: {e}",
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
    text = re.sub(r"\*\*(.*?)\*\*", r"[bold bright_white]\1[/bold bright_white]", text)

    # Replace `code text` with Rich markup, but only if properly closed
    # This prevents issues with unclosed backticks causing everything to be treated as code
    text = re.sub(r"`([^`\n]+)`", r"[cornsilk1]\1[/cornsilk1]", text)

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
        return (
            False,
            f"Repository has {total_files} files (limit: {MAX_FILES}). Consider excluding some directories.",
            {
                "files": total_files,
                "size_mb": total_size_mb,
                "large_files": large_files,
            },
        )

    if total_size_mb > MAX_TOTAL_SIZE_MB:
        return (
            False,
            f"Repository size is {total_size_mb:.1f}MB (limit: {MAX_TOTAL_SIZE_MB}MB). Consider excluding large files.",
            {
                "files": total_files,
                "size_mb": total_size_mb,
                "large_files": large_files,
            },
        )

    return (
        True,
        f"Repository validated: {total_files} files, {total_size_mb:.1f}MB",
        {"files": total_files, "size_mb": total_size_mb, "large_files": large_files},
    )


def load_prompt_template(structure_json):
    """Load prompt template from prompt.txt and inject repository structure"""
    prompt_path = os.path.join(os.path.dirname(__file__), "prompt.txt")
    with open(prompt_path, "r", encoding="utf-8") as f:
        prompt_template = json.load(f)

    # Replace placeholders
    for message in prompt_template:
        if "{structure_json}" in message["content"]:
            message["content"] = message["content"].replace(
                "{structure_json}", structure_json
            )
    return prompt_template


def summarize_overview(client, repo_path="."):
    """
    Summarize the repository using the raw JSON structure as context.
    More efficient for large repositories as it sends the structure directly.

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

    # Build the complete repository structure
    repo_structure = build_repo_structure(repo_path)

    # Convert to JSON string
    structure_json = json.dumps(repo_structure, indent=2, ensure_ascii=False)

    # Load prompt template and inject repository structure
    messages = load_prompt_template(structure_json)

    console = Console()
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Generating AI analysis...", total=None)
            progress.update(task, description="Generating full directory analysis...")
            response = client.chat.completions.create(
                model="reportr", messages=messages, max_tokens=2000, temperature=0.7
            )
            raw_summary = response.choices[0].message.content
            progress.update(task, description="Full directory analysis complete!")
    except Exception as e:
        console.print(f"[red]Error generating AI analysis: {e}[/red]")
        return f"Error: Could not analyze repository"

    # Format the response with Rich markup for better presentation
    formatted_parts = []

    # Add a decorated header
    formatted_parts.append("[bold sky_blue1]Full Directory Analysis[/bold sky_blue1]\n")

    # Add repository info
    repo_name = os.path.basename(os.path.abspath(repo_path))
    formatted_parts.append(f"[bold plum2]Directory:[/bold plum2] {repo_name}")
    formatted_parts.append(
        f"[bold plum2]Analysis Method:[/bold plum2] Summarized Overview"
    )
    formatted_parts.append(f"[bold plum2]Path:[/bold plum2] {repo_path}\n")

    # Add the main summary - use plain text with some basic formatting instead of full markdown
    formatted_parts.append("[bold sky_blue1]Detailed Analysis:[/bold sky_blue1]")
    # Process the summary with simplified, consistent formatting
    lines = raw_summary.split("\n")
    processed_lines = []
    in_numbered_list = False
    current_list_number = 0

    for line in lines:
        original_line = line
        line = line.strip()

        if not line:
            processed_lines.append("")
            in_numbered_list = False
            current_list_number = 0
            continue

        # Check for markdown headers (## Section Name) - these are our main section headers
        if line.startswith("## "):
            # Remove the markdown symbols and format as a main header
            header_text = line[3:].strip()
            formatted_line = format_markdown_text(header_text)
            processed_lines.append(f"\n[bold green]{formatted_line}[/bold green]")
            in_numbered_list = False
            current_list_number = 0
        # Handle numbered lists (lines starting with numbers)
        elif line.startswith(
            ("1. ", "2. ", "3. ", "4. ", "5. ", "6. ", "7. ", "8. ", "9. ")
        ):
            # Find the number and get the rest
            space_index = line.find(" ")
            number_part = line[: space_index + 1]
            text_content = line[space_index + 1 :].strip()
            formatted_line = format_markdown_text(text_content)
            processed_lines.append(
                f"    [bold bright_white]{number_part}[/bold bright_white][white]{formatted_line}[/white]"
            )
            in_numbered_list = True
            current_list_number = int(number_part.replace(".", "").strip())
        # Color code bullet points (lines starting with -)
        elif line.startswith("- "):
            # Remove the dash and get the text
            text_content = line[2:].strip()
            formatted_line = format_markdown_text(text_content)
            if in_numbered_list:
                # This is a sub-bullet under a numbered item - use white, not bright_black
                processed_lines.append(f"        ◦ [white]{formatted_line}[/white]")
            else:
                # This is a top-level bullet
                processed_lines.append(f"    • [white]{formatted_line}[/white]")
        # Check if this line looks like it should be indented under a numbered item
        elif in_numbered_list and (
            original_line.startswith("  ")
            or original_line.startswith("\t")
            or line.startswith("◦")
        ):
            # This is continuation text under a numbered item
            formatted_line = format_markdown_text(line)
            if line.startswith("◦"):
                # Already has bullet point
                processed_lines.append(f"        [white]{formatted_line}[/white]")
            else:
                # Add bullet point
                processed_lines.append(f"        ◦ [white]{formatted_line}[/white]")
        # Regular text - keep as is but format markdown
        else:
            formatted_line = format_markdown_text(line)
            # Make sure all regular text is properly colored (not greyed out)
            if formatted_line and not formatted_line.startswith("["):
                # Add white color if no color formatting is already present
                processed_lines.append(f"[white]{formatted_line}[/white]")
            else:
                processed_lines.append(formatted_line)
            in_numbered_list = False
            current_list_number = 0

    # Join the processed lines and add to formatted parts
    formatted_parts.append("\n".join(processed_lines))

    # Add some repository statistics
    formatted_parts.append("\n[bold sky_blue1]Directory Statistics:[/bold sky_blue1]")

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
    formatted_parts.append(f"├── [green]Total Directories:[/green] {total_folders}")

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
        formatted_parts.append(f"└── [green]File Types:[/green]")
        for ext, count in sorted(file_types.items(), key=lambda x: x[1], reverse=True)[
            :5
        ]:  # Top 5 file types
            formatted_parts.append(f"    ├── {ext}: {count} files")

    return "\n".join(formatted_parts)
