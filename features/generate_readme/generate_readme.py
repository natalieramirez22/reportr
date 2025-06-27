import os
import json
import openai
from openai import AzureOpenAI
from dotenv import load_dotenv
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
import re

def analyze_repository_structure(repo_path="."):
    """
    Analyze the repository structure to understand the project type and content
    """
    repo_path = Path(repo_path)
    analysis = {
        'repo_name': repo_path.name,
        'files': [],
        'directories': [],
        'file_extensions': {},
        'has_requirements': False,
        'has_package_json': False,
        'has_dockerfile': False,
        'has_makefile': False,
        'has_readme': False,
        'has_license': False,
        'has_tests': False,
        'has_docs': False,
        'main_language': None,
        'project_type': 'unknown'
    }
    
    # Common file patterns to look for
    important_files = [
        'requirements.txt', 'package.json', 'Dockerfile', 'Makefile', 
        'README.md', 'README.txt', 'LICENSE', 'LICENSE.txt', 'setup.py',
        'pyproject.toml', 'Cargo.toml', 'go.mod', 'pom.xml', 'build.gradle',
        '.gitignore', 'docker-compose.yml', 'docker-compose.yaml'
    ]
    
    # Walk through the repository
    for root, dirs, files in os.walk(repo_path):
        # Skip hidden directories and common ignore patterns
        dirs[:] = [d for d in dirs if not d.startswith('.') and d not in ['__pycache__', 'node_modules', 'venv', 'env', '.git']]
        
        rel_root = Path(root).relative_to(repo_path)
        
        for file in files:
            if file.startswith('.'):
                continue
                
            file_path = rel_root / file
            analysis['files'].append(str(file_path))
            
            # Check file extension
            ext = file_path.suffix.lower()
            if ext:
                analysis['file_extensions'][ext] = analysis['file_extensions'].get(ext, 0) + 1
            
            # Check for important files
            if file.lower() in [f.lower() for f in important_files]:
                if file.lower() in ['requirements.txt', 'pyproject.toml', 'setup.py']:
                    analysis['has_requirements'] = True
                elif file.lower() == 'package.json':
                    analysis['has_package_json'] = True
                elif file.lower() == 'dockerfile':
                    analysis['has_dockerfile'] = True
                elif file.lower() == 'makefile':
                    analysis['has_makefile'] = True
                elif file.lower().startswith('readme'):
                    analysis['has_readme'] = True
                elif file.lower().startswith('license'):
                    analysis['has_license'] = True
        
        # Check for test directories
        if any(test_dir in str(rel_root).lower() for test_dir in ['test', 'tests', 'spec', 'specs']):
            analysis['has_tests'] = True
        
        # Check for documentation directories
        if any(doc_dir in str(rel_root).lower() for doc_dir in ['doc', 'docs', 'documentation']):
            analysis['has_docs'] = True
    
    # Determine main language and project type
    if analysis['file_extensions']:
        main_ext = max(analysis['file_extensions'].items(), key=lambda x: x[1])[0]
        analysis['main_language'] = main_ext
        
        if main_ext in ['.py', '.pyx']:
            analysis['project_type'] = 'python'
        elif main_ext in ['.js', '.jsx', '.ts', '.tsx']:
            analysis['project_type'] = 'javascript'
        elif main_ext in ['.java']:
            analysis['project_type'] = 'java'
        elif main_ext in ['.go']:
            analysis['project_type'] = 'go'
        elif main_ext in ['.rs']:
            analysis['project_type'] = 'rust'
        elif main_ext in ['.cpp', '.c', '.h', '.hpp']:
            analysis['project_type'] = 'cpp'
        elif main_ext in ['.cs']:
            analysis['project_type'] = 'csharp'
        elif main_ext in ['.php']:
            analysis['project_type'] = 'php'
        elif main_ext in ['.rb']:
            analysis['project_type'] = 'ruby'
        elif main_ext in ['.swift']:
            analysis['project_type'] = 'swift'
        elif main_ext in ['.kt']:
            analysis['project_type'] = 'kotlin'
    
    return analysis

def generate_readme(client, repo_path="."):
    """
    Generate a comprehensive README file for a repository based on its structure and content
    """
    repo_analysis = analyze_repository_structure(repo_path)
    
    # Prepare the analysis data for the LLM
    analysis_context = f"""
Repository Analysis:
Name: {repo_analysis['repo_name']}
Project Type: {repo_analysis['project_type']}
Main Language: {repo_analysis['main_language']}

Repository Structure:
- Total Files: {len(repo_analysis['files'])}
- File Extensions: {dict(list(repo_analysis['file_extensions'].items())[:10])}  # Top 10 extensions

Key Files Present:
- Requirements/Dependencies: {repo_analysis['has_requirements']}
- Package Configuration: {repo_analysis['has_package_json']}
- Docker Support: {repo_analysis['has_dockerfile']}
- Build System: {repo_analysis['has_makefile']}
- Existing README: {repo_analysis['has_readme']}
- License: {repo_analysis['has_license']}
- Tests: {repo_analysis['has_tests']}
- Documentation: {repo_analysis['has_docs']}

Files in Repository:
{chr(10).join(repo_analysis['files'][:50])}  # First 50 files
"""
    
    # Load the prompt template
    prompt_path = os.path.join(os.path.dirname(__file__), 'prompt.txt')
    try:
        with open(prompt_path, 'r', encoding='utf-8') as f:
            messages = json.load(f)

        # Inject analysis context into the prompt
        for message in messages:
            if '{analysis_context}' in message.get("content", ""):
                message["content"] = message["content"].replace("{analysis_context}", analysis_context)
        
    except Exception as e:
        print(f"Error loading prompt template: {e}")
        # Fallback to hardcoded prompt
        messages = [
            {
                "role": "system", 
                "content": """You are a helpful assistant that generates comprehensive, professional README files for software projects. 
                Analyze the repository structure and create a README that includes:
                1. Project title and description
                2. Features and capabilities
                3. Installation instructions
                4. Usage examples
                5. Configuration options
                6. Contributing guidelines
                7. License information
                8. Any other relevant sections based on the project type
                
                Write in clear, professional markdown format suitable for GitHub or similar platforms.
                Make the README engaging and informative for potential users and contributors."""
            },
            {
                "role": "user", 
                "content": f"Generate a comprehensive README file for this repository based on the following analysis:\n\n{analysis_context}"
            }
        ]
    
    # Generate the README using the LLM
    console = Console()
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Generating AI analysis...", total=None)
            progress.update(task, description="Generating README...")
            
            response = client.chat.completions.create(
                model="reportr",
                messages=messages,
                max_tokens=3000,
                temperature=0.7
            )
            
            progress.update(task, description="README generation complete!")
    except Exception as e:
        console.print(f"[red]Error generating README: {e}[/red]")
        return f"Error: Could not generate README"
    
    # Format the README content with Rich styling
    readme_content = response.choices[0].message.content
    formatted_readme = format_markdown_readme(readme_content)
    
    return formatted_readme 

def write_to_readme_file(readme_content, output_path="GENERATED_README.md"):
    """
    Write the generated README content to a file
    """
    console = Console()
    try:
        # Strip Rich formatting before writing to file
        clean_content = re.sub(r'\[/?[^\]]*\]', '', readme_content)
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(clean_content)
        console.print(f"[bold white]\nREADME file written successfully to {output_path}\n[/bold white]")
        return True
    except Exception as e:
        console.print(f"[red]Error writing README file: {e}[/red]")
        return False

def format_markdown_readme(markdown_text):
    """
    Format markdown text with Rich styling for display
    """
    if not markdown_text:
        return markdown_text
    
    formatted_text = markdown_text
    
    # Format code blocks first (including # comments inside them)
    # ```code``` -> [cornsilk1]```code```[/cornsilk1]
    def format_code_block(match):
        code_content = match.group(1)
        # Format # comments inside code blocks as wheat1
        code_content = re.sub(r'^(\s*)# (.*)$', r'\1[wheat1]# \2[/wheat1]', code_content, flags=re.MULTILINE)
        return f'[cornsilk1]```{code_content}```[/cornsilk1]'
    
    formatted_text = re.sub(r'```([^`]+)```', format_code_block, formatted_text, flags=re.DOTALL)
    
    # `inline code` -> [cornsilk1]`inline code`[/cornsilk1]
    formatted_text = re.sub(r'`([^`\n]+)`', r'[cornsilk1]`\1`[/cornsilk1]', formatted_text)
    
    # Now format headers with different colors - process from most specific to least specific
    # ### Header and beyond -> [green]### Header[/green] (do these first)
    formatted_text = re.sub(r'^### (.*?)$', r'[green]### \1[/green]', formatted_text, flags=re.MULTILINE)
    formatted_text = re.sub(r'^#### (.*?)$', r'[green]#### \1[/green]', formatted_text, flags=re.MULTILINE)
    formatted_text = re.sub(r'^##### (.*?)$', r'[green]##### \1[/green]', formatted_text, flags=re.MULTILINE)
    formatted_text = re.sub(r'^###### (.*?)$', r'[green]###### \1[/green]', formatted_text, flags=re.MULTILINE)
    
    # ## Header -> [sky_blue1]## Header[/sky_blue1]
    formatted_text = re.sub(r'^## (.*?)$', r'[sky_blue1]## \1[/sky_blue1]', formatted_text, flags=re.MULTILINE)
    
    # # Header -> [plum2]# Header[/plum2] (single # only, not ## or ### and not inside code blocks)
    # Negative lookahead to avoid matching inside already formatted code blocks
    formatted_text = re.sub(r'^# (?!#)(?![^[]*\[/cornsilk1\])(.*?)$', r'[plum2]# \1[/plum2]', formatted_text, flags=re.MULTILINE)
    
    return formatted_text