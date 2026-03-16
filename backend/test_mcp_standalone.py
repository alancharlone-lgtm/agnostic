import asyncio
import os
import sys
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset, SseConnectionParams

os.environ["GEMINI_API_KEY"] = os.environ.get("GEMINI_API_KEY", "")

async def test_mcp():
    print("Conectando al servidor MCP...")
    mcp = MCPToolset(
        connection_params=SseConnectionParams(
            url="https://agnostic-mcp-server-532234202617.us-central1.run.app/sse"
        )
    )
    
    # Test MercadoLibre
    print("\nProbando MercadoLibre (Bomba Samsung)...")
    try:
        # Most MCP toolsets expose a call_tool method or similar
        # In ADK, McpToolset wraps the client.
        res_ml = await mcp.call_tool("buscar_en_mercadolibre", {"query": "bomba desagote samsung ww90ta046te"})
        print(f"Respuesta ML: {res_ml}")
    except Exception as e:
        print(f"Error ML: {e}")

    # Test Maps in Charlone
    print("\nProbando Maps en Coronel Charlone (-34.8690, -63.1481)...")
    try:
        res_maps = await mcp.call_tool("buscar_tiendas_maps", {
            "lat": -34.8690, 
            "lng": -63.1481, 
            "query": "repuestos lavarropas",
            "radio_km": 50 
        })
        print(f"Respuesta Maps: {res_maps}")
    except Exception as e:
        print(f"Error Maps: {e}")

if __name__ == "__main__":
    asyncio.run(test_mcp())
