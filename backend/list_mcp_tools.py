import asyncio
import os
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.tools.mcp_tool.mcp_toolset import SseConnectionParams

async def list_mcp_tools():
    print("Conectando al servidor MCP...")
    toolset = MCPToolset(
        connection_params=SseConnectionParams(
            url="https://agnostic-mcp-server-532234202617.us-central1.run.app/sse",
            timeout=15.0
        )
    )
    
    # Trigger initialization (fetching manifest)
    try:
        # In ADK, tools are listed in toolset.tools after initialization
        # Let's try to access the underlying tools.
        print(f"Buscando herramientas en el toolset...")
        # Since it's a Toolset, it might have a list or dict of tools
        # Looking at previous logs, the LLM saw 'buscar_tiendas_maps', 'buscar_en_mercadolibre'
        
        # We can try to see what's in toolset
        tools = await toolset.get_tools()
        for tool in tools:
             print(f"- Herramienta encontrada: {tool.name}")
             
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(list_mcp_tools())
