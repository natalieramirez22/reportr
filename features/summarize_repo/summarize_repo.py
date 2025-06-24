import os
import openai
from openai import AzureOpenAI
from dotenv import load_dotenv

def summarize_repo(client):
    """
    Summarize the purpose of a Python repository
    """
    # Load the prompt template
    prompt_path = os.path.join(os.path.dirname(__file__), 'prompt.txt')
    try:
        with open(prompt_path, 'r') as f:
            prompt_template = f.read()
        
        # Use the prompt template
        messages = eval(prompt_template)
        
    except Exception as e:
        print(f"Error loading prompt template: {e}")
        # Fallback to hardcoded prompt
        messages = [
            {"role": "system", "content": "You are a helpful assistant that summarizes code repositories."},
            {"role": "user", "content": "Summarize the purpose of this Python repo."}
        ]
    
    response = client.chat.completions.create(
        model="reportr",
        messages=messages,
        max_tokens=1000,
        temperature=0.7
    )
    
    return response.choices[0].message.content
