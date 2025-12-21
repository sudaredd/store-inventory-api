import google.generativeai as genai
import os

genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

try:
    print("Listing models...")
    with open('models.txt', 'w') as f:
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(m.name)
                f.write(m.name + '\n')
except Exception as e:
    print(f"Error listing models: {e}")
    with open('models_error.txt', 'w') as f:
        f.write(str(e))
