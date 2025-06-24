import os
from openai import AzureOpenAI
from dotenv import load_dotenv
from features.progress_report.progress_report import create_progress_report

load_dotenv()

def create_client():
    """Create and return an Azure OpenAI client"""
    return AzureOpenAI(
        api_key=os.getenv("AZURE_OPENAI_KEY"),
        api_version="2024-02-15-preview",
        azure_endpoint="https://natalie-design-agent-resource.cognitiveservices.azure.com/"
    )

if __name__ == "__main__":
    # Create the client
    client = create_client()
    
    # Call the progress report function
    report = create_progress_report(client)
    print(report)
