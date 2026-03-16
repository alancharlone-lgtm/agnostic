
from google.cloud import discoveryengine_v1beta as discoveryengine
from google.cloud import dialogflowcx_v3 as dialogflow

def check_agnostic_project(project_id):
    print(f"\n--- Checking {project_id} ---")
    
    # Discovery Engine
    client = discoveryengine.EngineServiceClient()
    for loc in ["global", "us-central1"]:
        parent = f"projects/{project_id}/locations/{loc}/collections/default_collection"
        try:
            for engine in client.list_engines(parent=parent):
                print(f"[DE] {engine.display_name} | {engine.name}")
        except: pass

    # Dialogflow CX
    cx_client = dialogflow.AgentsClient()
    for loc in ["global", "us-central1"]:
        parent = f"projects/{project_id}/locations/{loc}"
        try:
            for agent in cx_client.list_agents(parent=parent):
                print(f"[CX] {agent.display_name} | {agent.name}")
        except: pass

if __name__ == "__main__":
    check_agnostic_project("gen-lang-client-0189612712")
    check_agnostic_project("agnostic-live-agent-6192")
