
from google.cloud import dialogflowcx_v3 as dialogflow

def scan_all_regions(project_id):
    # Common regions for Dialogflow CX
    regions = [
        "global", "us-central1", "us-east1", "us-west1", 
        "europe-west1", "europe-west2", "europe-west3",
        "asia-northeast1", "asia-southeast1", "australia-southeast1"
    ]
    
    for loc in regions:
        print(f"Scanning {project_id} in {loc}...")
        try:
            if loc == "global":
                endpoint = "dialogflow.googleapis.com"
            else:
                endpoint = f"{loc}-dialogflow.googleapis.com"
            
            client = dialogflow.AgentsClient(client_options={"api_endpoint": endpoint})
            parent = f"projects/{project_id}/locations/{loc}"
            
            for agent in client.list_agents(parent=parent):
                print(f"  FOUND: {agent.display_name} | {agent.name}")
                if "Orquestador" in agent.display_name:
                    print("  >>> MATCH! <<<")
        except Exception as e:
            # print(f"  Error in {loc}: {e}")
            pass

if __name__ == "__main__":
    scan_all_regions("agnostic-live-agent-6192")
    print("-" * 30)
    scan_all_regions("stok-7bc5c")
