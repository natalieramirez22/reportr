import os
import openai
from openai import AzureOpenAI
from dotenv import load_dotenv
load_dotenv()

# Set up the Azure OpenAI client
client = AzureOpenAI(
    api_key=os.getenv("AZURE_OPENAI_KEY"),
    api_version="2024-02-15-preview",
    azure_endpoint="https://natalie-design-agent-resource.cognitiveservices.azure.com/"
)

# Function to summarize a repo
def summarize_repo():
    response = client.chat.completions.create(
        model="reportr",  # This is your deployment name
        messages=[
            {"role": "system", "content": "You are a helpful assistant that summarizes code repositories."},
            {"role": "user", "content": "Summarize the purpose of this Python repo."}
        ]
    )
    print(response.choices[0].message.content)

if __name__ == "__main__":
    summarize_repo()
