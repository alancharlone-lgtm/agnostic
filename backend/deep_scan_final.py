
from google.cloud import discoveryengine_v1 as discoveryengine
import sys

def deep_scan_engines(project_id):
    client = discoveryengine.EngineServiceClient()
    locations = ["global", "us-central1"]
    
    for loc in locations:
        parent = f"projects/{project_id}/locations/{loc}/collections/default_collection"
        print(f"\nScanning Discovery Engine in {parent}...")
        try:
            request = discoveryengine.ListEnginesRequest(parent=parent)
            page_result = client.list_engines(request=request)
            for response in page_result:
                print(f"FOUND ENGINE: {response.display_name} | {response.name}")
        except Exception as e:
            print(f"Error listing engines in {loc}: {e}")

    # Check for Dialogflow CX too, just in case
    from google.cloud import dialogflowcx_v3 as dialogflow
    cx_client = dialogflow.AgentsClient()
    for loc in ["global", "us-central1"]:
        parent = f"projects/{project_id}/locations/{loc}"
        print(f"\nScanning Dialogflow CX in {parent}...")
        try:
            request = dialogflow.ListAgentsRequest(parent=parent)
            page_result = cx_client.list_agents(request=request)
            for agent in page_result:
                print(f"FOUND CX AGENT: {agent.display_name} | {agent.name}")
        except Exception as e:
            print(f"Error listing CX in {loc}: {e}")

if __name__ == "__main__":
    deep_scan_engines("stok-7bc5c")
