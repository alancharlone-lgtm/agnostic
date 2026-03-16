"""
debug_visual_guide.py
Tests the full visual guide generation chain step by step.
"""
import asyncio
import os
import base64
import httpx

API_KEY = os.environ.get("GEMINI_API_KEY", "")

# 1x1 red pixel JPEG
DUMMY_JPEG_B64 = "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAFAABAAAAAAAAAAAAAAAAAAAACf/EABQQAQAAAAAAAAAAAAAAAAAAAAD/xAAUAQEAAAAAAAAAAAAAAAAAAAAA/8QAFBEBAAAAAAAAAAAAAAAAAAAAAP/aAAwDAQACEQMRAD8AJQAB/9k="

async def test_direct_api():
    """Test calling Gemini image API directly (same as proxy tool in main.py)"""
    print("=== TEST 1: Direct Gemini Image API ===")
    
    gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image-preview:generateContent?key={API_KEY}"
    
    payload = {
        "contents": [{
            "parts": [
                {"text": "Draw a red arrow pointing to the center of this image. Keep the original image intact."},
                {"inline_data": {"mime_type": "image/jpeg", "data": DUMMY_JPEG_B64}}
            ]
        }],
        "generationConfig": {
            "responseModalities": ["TEXT", "IMAGE"]
        },
        "safetySettings": [
            {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
            {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
        ]
    }
    
    async with httpx.AsyncClient(timeout=60.0) as client:
        print(f"Sending request to: {gemini_url}")
        resp = await client.post(gemini_url, json=payload)
        print(f"Status code: {resp.status_code}")
        
        if resp.status_code == 200:
            data = resp.json()
            candidate = data.get("candidates", [{}])[0]
            parts = candidate.get("content", {}).get("parts", [])
            print(f"Response parts count: {len(parts)}")
            for i, part in enumerate(parts):
                if "text" in part:
                    print(f"  Part {i} (text): {part['text'][:200]}")
                if "inlineData" in part:
                    img_b64 = part["inlineData"]["data"]
                    print(f"  Part {i} (image): FOUND! {len(img_b64)} chars of base64")
                    # Save to file to verify
                    with open("test_output_image.jpg", "wb") as f:
                        f.write(base64.b64decode(img_b64))
                    print("  -> Saved image to test_output_image.jpg")
        else:
            print(f"ERROR response: {resp.text[:500]}")

async def test_with_sdk():
    """Test using official SDK - alternative approach"""
    print("\n=== TEST 2: Using Official SDK ===")
    from google import genai
    from google.genai import types
    
    client = genai.Client(api_key=API_KEY)
    img_bytes = base64.b64decode(DUMMY_JPEG_B64)
    
    try:
        response = await client.aio.models.generate_content(
            model="gemini-3.1-flash-image-preview",
            contents=[
                types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"),
                types.Part.from_text(text="Draw a red arrow pointing to the center of this image.")
            ],
            config=types.GenerateContentConfig(
                response_modalities=["TEXT", "IMAGE"]
            )
        )
        parts = response.candidates[0].content.parts
        print(f"Response parts count: {len(parts)}")
        for i, part in enumerate(parts):
            if part.text:
                print(f"  Part {i} (text): {part.text[:200]}")
            if getattr(part, 'inline_data', None):
                print(f"  Part {i} (image): FOUND! {len(part.inline_data.data)} bytes")
                with open("test_output_sdk.jpg", "wb") as f:
                    f.write(part.inline_data.data)
                print("  -> Saved image to test_output_sdk.jpg")
    except Exception as e:
        print(f"SDK error: {e}")
        import traceback
        traceback.print_exc()

async def test_adk_vision_chain():
    """Test the full ADK vision agent chain"""
    print("\n=== TEST 3: Full ADK Vision Chain ===")
    import sys, os
    os.environ["GOOGLE_API_KEY"] = API_KEY
    
    from google.adk.apps import App
    from google.adk.runners import Runner
    from google.adk.sessions.in_memory_session_service import InMemorySessionService
    from google.genai import types
    
    img_bytes = base64.b64decode(DUMMY_JPEG_B64)
    
    # Simulate the generar_guia_visual_nanobanana proxy tool
    async def generar_guia_visual_nanobanana(prompt_tecnico: str) -> str:
        print(f"  [PROXY TOOL] Called with prompt: {prompt_tecnico[:100]}...")
        gemini_url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-3.1-flash-image-preview:generateContent?key={API_KEY}"
        img_b64 = base64.b64encode(img_bytes).decode('utf-8')
        payload = {
            "contents": [{"parts": [
                {"text": prompt_tecnico},
                {"inline_data": {"mime_type": "image/jpeg", "data": img_b64}}
            ]}],
            "generationConfig": {"responseModalities": ["TEXT", "IMAGE"]},
            "safetySettings": [
                {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
                {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"}
            ]
        }
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(gemini_url, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                parts = data.get("candidates", [{}])[0].get("content", {}).get("parts", [])
                for part in parts:
                    if "inlineData" in part:
                        with open("test_adk_output.jpg", "wb") as f:
                            f.write(base64.b64decode(part["inlineData"]["data"]))
                        return "Imagen generada y guardada correctamente en test_adk_output.jpg"
                return "No se generó imagen, respuesta solo texto"
            return f"Error API: {resp.status_code} - {resp.text[:200]}"
    
    from adk_vision_guide_v2 import get_vision_agent
    vision_root_agent = get_vision_agent(drawing_tool=generar_guia_visual_nanobanana)
    
    msg = types.Content(
        role="user",
        parts=[
            types.Part.from_bytes(data=img_bytes, mime_type="image/jpeg"),
            types.Part.from_text(text=(
                "Analiza esta imagen (es una heladera con bornes C, S, R) y generá la guía visual de ensamblaje.\n"
                "TAREA: Conexión de compresor Tecumseh\n"
                "INSTRUCCIÓN: El especialista analizará y el Director Visual llamará a 'generar_guia_visual_nanobanana'."
            ))
        ]
    )
    
    app = App(name="vision_test_app", root_agent=vision_root_agent)
    runner = Runner(app=app, session_service=InMemorySessionService(), auto_create_session=True)
    
    print("Running ADK vision chain...")
    final_text = ""
    async for event in runner.run_async(user_id="test_user", session_id="test_session", new_message=msg):
        if hasattr(event, "content") and event.content:
            for part in event.content.parts:
                if getattr(part, "text", None):
                    print(f"  [AGENT OUTPUT] {part.text[:200]}")
                    final_text += part.text
    
    print(f"\n=== RESULT: {final_text[:300] if final_text else 'No text output'} ===")

if __name__ == "__main__":
    asyncio.run(test_direct_api())
    asyncio.run(test_with_sdk())
    asyncio.run(test_adk_vision_chain())
