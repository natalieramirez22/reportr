import os
import argparse
from openai import AzureOpenAI
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

# Set up Azure OpenAI client
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version="2024-02-15-preview",
    azure_endpoint="https://natalie-design-agent-resource.cognitiveservices.azure.com/"
)

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

# Summarize a directory using the model
def summarize_directory(path, files):
    file_list = "\n".join(files)
    prompt = (
        f"You are a helpful assistant that summarizes code repositories for onboarding purposes.\n"
        f"Here is a list of Python files in the directory '{path}':\n{file_list}\n"
        f"Provide a concise 2-3 sentence summary of what this directory likely does. "
        f"Focus only on the most important functionality and avoid verbose or repetitive details."
    )
    response = client.chat.completions.create(
        model="reportr",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that summarizes code repositories."},
            {"role": "user", "content": prompt}
        ]
    )
    return response.choices[0].message.content

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

# Run the summarization
def run_reportr(repo_path):
    print("📂 Directory Tree:\n")
    print_tree(repo_path)

    print("\n🧠 Summaries:\n")
    directory_map = collect_python_files(repo_path)
    for path, files in directory_map.items():
        print(f"\n📁 Directory: {path}")
        summary = summarize_directory(path, files)
        print(f"📝 Summary:\n{summary}")
        

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Reportr CLI")
    parser.add_argument("--path", type=str, default=".", help="Path to the local repo directory")
    args = parser.parse_args()

    run_reportr(args.path)
