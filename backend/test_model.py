import os
import asyncio
from google import genai
from google.genai import types

api_key = os.environ.get("GEMINI_API_KEY", "")
client = genai.Client(api_key=api_key)

async def test_nano_banana():
    print("Testing Nano Banana 2 (Gemini 3.1 Flash Image Preview)...")
    try:
        # We'll use a dummy black image for testing if we don't have a real one
        # but let's just try to call it.
        # If the model name is wrong, it should fail immediately with 404 or similar.
        response = await client.aio.models.generate_content(
            model="gemini-3.1-flash-image-preview",
            contents=["What is this model?"]
        )
        print("Success!")
        print(response.text)
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_nano_banana())
