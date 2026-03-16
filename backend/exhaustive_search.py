
from google.cloud import dialogflowcx_v3 as dialogflow
from google.cloud import discoveryengine_v1beta as discoveryengine

def search_everything(project_id):
    print(f"\nSearching EVERYTHING in project: {project_id}")
    
    # Check Dialogflow CX Agents
    cx_client = dialogflow.AgentsClient()
    for loc in ["global", "us-central1"]:
        parent = f"projects/{project_id}/locations/{loc}"
        try:
            print(f"  - Requesting CX Agents in {loc}...")
            # Use regional endpoint if needed
            opts = None
            if loc != "global":
                opts = {"api_endpoint": f"{loc}-dialogflow.googleapis.com"}
            client = dialogflow.AgentsClient(client_options=opts)
            
            for agent in client.list_agents(parent=parent):
                print(f"    [CX AGENT] Display: {agent.display_name} | Name: {agent.name}")
        except Exception as e:
            pass

    # Check Discovery Engine (Search/Conversation)
    de_client = discoveryengine.EngineServiceClient()
    for loc in ["global", "us-central1"]:
        parent = f"projects/{project_id}/locations/{loc}/collections/default_collection"
        try:
            print(f"  - Requesting Discovery Engines in {loc}...")
            opts = None
            if loc != "global":
                opts = {"api_endpoint": f"{loc}-discoveryengine.googleapis.com"}
            client = discoveryengine.EngineServiceClient(client_options=opts)
            
            for engine in client.list_engines(parent=parent):
                print(f"    [DE ENGINE] Display: {engine.display_name} | Name: {engine.name}")
        except Exception as e:
            pass

if __name__ == "__main__":
    search_everything("stok-7bc5c")
    search_everything("agnostic-live-agent-6192")
