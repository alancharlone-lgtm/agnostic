import os
from google import genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY", "")
client = genai.Client(api_key=api_key)

print("Listing models...")
try:
    for model in client.models.list():
        print(f"Model ID: {model.name}")
except Exception as e:
    import traceback
    print(f"Error listing models: {e}")
    traceback.print_exc()
