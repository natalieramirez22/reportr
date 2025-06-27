import os
import json
from openai import AzureOpenAI

def analyze_files_with_llm(file_paths, client: AzureOpenAI):
    """Analyze code files using an LLM and return a list of security issues as JSON."""
    code_samples = []
    for path in file_paths:
        with open(path, "r") as f:
            code_samples.append(f.read())

    prompt = (
    "You are a security analysis assistant. "
    "Analyze the following code for security vulnerabilities. "
    "For each issue you find, output a JSON object with these keys: "
    "'severity' (must be one of: high, medium, low, info), "
    "'description' (a short explanation of the issue), "
    "and 'cwe_id' (if known, otherwise null). "
    "Return ONLY a JSON array of issues, with NO extra explanation, text, or formatting. "
    "Do NOT include any markdown, comments, or prose—just the JSON array. "
    "If no issues are found, return an empty JSON array: [].\n\n"
    "Code samples:\n"
    + "\n\n".join(code_samples)
)

    response = client.chat.completions.create(
        model="reportr",  # deployed model name
        messages=[{"role": "user", "content": prompt}],
        max_tokens=1024,
        temperature=0.7,
    )

    content = response.choices[0].message.content
    print("LLM response:", repr(content))  # Keep for debugging

    try:
        issues = json.loads(content)
    except Exception:
        print("Failed to parse LLM response as JSON.")
        issues = []

    return issues

def create_llm_file_scan(client: AzureOpenAI, file_paths: list) -> list:
    """
    Create a security scan of code files using an LLM.
    
    Args:
        client (AzureOpenAI): The OpenAI client instance.
        file_paths (list): List of file paths to analyze.
    
    Returns:
        list: A list of security issues found in the files.
    """
    if not file_paths:
        raise ValueError("No file paths provided for analysis.")

    issues = analyze_files_with_llm(file_paths, client)
    return issues