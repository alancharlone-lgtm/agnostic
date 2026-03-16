import os
from google.cloud import dialogflowcx_v3 as dialogflowcx
from google.oauth2 import service_account

# CONFIGURATION
PROJECT_ID = "stok-7bc5c"
LOCATION = "global"  # You can change to 'us-central1' if needed
AGENT_DISPLAY_NAME = "Agnostic-Orchestrator"

def create_agent():
    """Programmatically creates a new Dialogflow CX Agent for Vertex AI Agent Builder."""
    print(f"Creating Agent '{AGENT_DISPLAY_NAME}' in project '{PROJECT_ID}'...")
    
    # 1. Initialize the client
    # The client options direct traffic to the correct region endpoint
    client_options = None
    if LOCATION != "global":
        client_options = {"api_endpoint": f"{LOCATION}-dialogflow.googleapis.com"}
        
    client = dialogflowcx.AgentsClient(client_options=client_options)
    
    # 2. Configure the agent
    parent = f"projects/{PROJECT_ID}/locations/{LOCATION}"
    
    # We specify English as default, though we act in Spanish, CX usually defaults to en.
    # Timezone America/Argentina/Buenos_Aires (for the timezone, it can be customized)
    agent = dialogflowcx.Agent(
        display_name=AGENT_DISPLAY_NAME,
        default_language_code="es",
        time_zone="America/Argentina/Buenos_Aires",
    )
    
    try:
        # Create the agent
        response = client.create_agent(
            request={"parent": parent, "agent": agent}
        )
        print(f"Agent created successfully!")
        print(f"Agent Name: {response.name}")
        return response.name
    except Exception as e:
        print(f"Error creating agent: {e}")
        return None

def main():
    print("--- Agnostic Vertex AI Deployer ---")
    print("This script uses the Google Cloud SDK to automate the creation of your Agent.")
    
    agent_id = create_agent()
    if agent_id:
        print(f"\nNext Steps: We are ready to use the ID '{agent_id}' to programmatically upload tools and instructions (Playbooks).")
        print("To proceed with Tools and Playbooks, we will use the Dialogflow CX Tool and Playbook API.")

if __name__ == "__main__":
    main()
