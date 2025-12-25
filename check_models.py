import os
from google import genai
from dotenv import load_dotenv

load_dotenv()

def list_models():
    try:
        client = genai.Client(api_key=os.environ.get("GEMINI_API_KEY"))
        print("Listing available models...")
        for m in client.models.list():
            print(f"- {m.name}")
    except Exception as e:
        print(f"Error listing models: {e}")

if __name__ == "__main__":
    list_models()
