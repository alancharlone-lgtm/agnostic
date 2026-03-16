import os
import asyncio
import base64
from google import genai
from google.genai import types

api_key = os.environ.get("GEMINI_API_KEY", "")
client = genai.Client(api_key=api_key)

async def test_image_generation():
    print("Testing Image Generation with Gemini 3.1 Flash Image Preview...")
    
    # Create a small dummy JPEG
    dummy_image = b'\xff\xd8\xff\xdb\x00C\x00\x08\x06\x06\x07\x06\x05\x08\x07\x07\x07\t\t\x08\n\x0c\x14\r\x0c\x0b\x0b\x0c\x19\x12\x13\x0f\x14\x1d\x1a\x1f\x1e\x1d\x1a\x1c\x1c $.\x27" #\x1c\x1c(7),01444\x1f\x1f?\x45\x44\x38\x41\x31\x44\x43\x44\x44\x44\xff\xc0\x00\x11\x08\x00\x01\x00\x01\x03\x01"\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x15\x00\x01\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x08\xff\xc4\x00\x14\x10\x01\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00?\x00\x00\xff\xd9'

    prompt = "Add a red arrow to this image."
    
    try:
        response = await client.aio.models.generate_content(
            model="gemini-3.1-flash-image-preview",
            contents=[
                types.Part.from_bytes(data=dummy_image, mime_type="image/jpeg"),
                types.Part.from_text(text=prompt)
            ]
        )
        
        print(f"Response Parts: {len(response.candidates[0].content.parts)}")
        for i, part in enumerate(response.candidates[0].content.parts):
            if part.text:
                print(f"Part {i} (Text): {part.text[:100]}...")
            if part.inline_data:
                print(f"Part {i} (Inline Data): Found data!")
            if getattr(part, 'file_data', None):
                print(f"Part {i} (File Data): Found data!")
        
        if hasattr(response, 'generated_images'):
            print(f"Generated Images: {len(response.generated_images)}")
            
    except Exception as e:
        print(f"Failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_image_generation())
