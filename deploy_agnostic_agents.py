import os
from google.cloud import dialogflowcx_v3 as dialogflowcx

# CONFIGURATION
PROJECT_ID = "stok-7bc5c"
LOCATION = "global"

# Define the 3 agents to create based on Agnostic modes
AGENTS_TO_CREATE = [
    {"display_name": "Agnostic-Industrial", "description": "Modo Industrial: Mantenimiento Crítico en Fábricas"},
    {"display_name": "Agnostic-Residencial", "description": "Modo Residencial: Reparaciones ágiles en terreno"},
    {"display_name": "Agnostic-AprendizHogar", "description": "Modo Hogar: Tutor paso a paso para usuarios sin experiencia"}
]

def create_agent(agent_data):
    """Programmatically creates a new Dialogflow CX Agent."""
    display_name = agent_data["display_name"]
    description = agent_data["description"]
    print(f"\nGenerando Agente: '{display_name}'...")
    
    client_options = None
    if LOCATION != "global":
        client_options = {"api_endpoint": f"{LOCATION}-dialogflow.googleapis.com"}
        
    client = dialogflowcx.AgentsClient(client_options=client_options)
    parent = f"projects/{PROJECT_ID}/locations/{LOCATION}"
    
    agent = dialogflowcx.Agent(
        display_name=display_name,
        default_language_code="es",
        time_zone="America/Argentina/Buenos_Aires",
        description=description
    )
    
    try:
        response = client.create_agent(
            request={"parent": parent, "agent": agent}
        )
        print(f"[{display_name}] Creado con exito.")
        # Generar el link directo a la consola
        agent_short_id = response.name.split("/")[-1]
        console_link = f"https://dialogflow.cloud.google.com/cx/projects/{PROJECT_ID}/locations/{LOCATION}/agents/{agent_short_id}"
        print(f"Link Directo a la Consola: {console_link}")
        return response.name
    except Exception as e:
        print(f"[{display_name}] Error: {e}")
        return None

def main():
    print("--- Instalador Automático de Agentes Agnostic para Vertex AI ---")
    print(f"Conectando al proyecto: {PROJECT_ID}")
    
    for agent_data in AGENTS_TO_CREATE:
        create_agent(agent_data)
        
    print("\n--- ¡Proceso de automatización finalizado! ---")
    print("Podés hacer clic en los enlaces de arriba para entrar directamente al diseñador de cada modo.")

if __name__ == "__main__":
    main()
