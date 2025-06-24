import os
import openai
from openai import AzureOpenAI
from dotenv import load_dotenv
import json
from pathlib import Path

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
    print("Analyzing repository structure...")
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
        with open(prompt_path, 'r') as f:
            prompt_template = f.read()
        
        # Replace the placeholder with actual data
        messages = eval(prompt_template.replace('{analysis_context}', f'"{analysis_context}"'))
        
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
    response = client.chat.completions.create(
        model="reportr",
        messages=messages,
        max_tokens=3000,
        temperature=0.7
    )
    
    return response.choices[0].message.content 

def write_to_readme_file(readme_content, output_path="TEST_README.md"):
    """
    Write the generated README content to a file
    """
    try:
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(readme_content)
        print(f"README file written successfully to {output_path}")
        return True
    except Exception as e:
        print(f"Error writing README file: {e}")
        return False 