
from google.cloud import dialogflowcx_v3 as dialogflow

def scan_cx_regions(project_id):
    regions = ["global", "us", "eu", "us-central1", "us-east1"]
    for loc in regions:
        print(f"--- Checking CX in {loc} ---")
        try:
            endpoint = "dialogflow.googleapis.com" if loc == "global" else f"{loc}-dialogflow.googleapis.com"
            client = dialogflow.AgentsClient(client_options={"api_endpoint": endpoint})
            parent = f"projects/{project_id}/locations/{loc}"
            for agent in client.list_agents(parent=parent):
                print(f"  AGENT: {agent.display_name} | {agent.name}")
        except Exception as e:
            # print(f"Error: {e}")
            pass

if __name__ == "__main__":
    scan_cx_regions("stok-7bc5c")
