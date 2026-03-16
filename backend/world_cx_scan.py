
from google.cloud import dialogflowcx_v3 as dialogflow

def scan_cx_everywhere(project_id):
    # Expanded list of regions
    regions = [
        "global", "us", "eu", "us-central1", "us-east1", "us-west1",
        "europe-west1", "europe-west2", "europe-west3", "europe-west9",
        "asia-northeast1", "asia-northeast3", "asia-southeast1",
        "australia-southeast1", "asia-south1", "me-central1"
    ]
    
    for loc in regions:
        print(f"Checking {loc}...")
        try:
            endpoint = "dialogflow.googleapis.com" if loc == "global" else f"{loc}-dialogflow.googleapis.com"
            client = dialogflow.AgentsClient(client_options={"api_endpoint": endpoint})
            parent = f"projects/{project_id}/locations/{loc}"
            
            for agent in client.list_agents(parent=parent):
                print(f"  FOUND: {agent.display_name} | {agent.name}")
                if "Orquestador" in agent.display_name:
                    print("  >>> MATCH FOUND! <<<")
        except:
            pass

if __name__ == "__main__":
    scan_cx_everywhere("stok-7bc5c")
