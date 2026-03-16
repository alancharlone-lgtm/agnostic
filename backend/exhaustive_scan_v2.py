
from google.cloud import discoveryengine_v1beta as discoveryengine

def scan_all_engines(project_id):
    client = discoveryengine.EngineServiceClient()
    locations = ["global", "us", "eu", "us-central1"]
    
    for loc in locations:
        print(f"Scanning engines in {project_id} / {loc}")
        try:
            parent = f"projects/{project_id}/locations/{loc}/collections/default_collection"
            request = discoveryengine.ListEnginesRequest(parent=parent)
            engines = client.list_engines(request=request)
            for engine in engines:
                print(f"FOUND: {engine.display_name} | {engine.name}")
        except Exception as e:
            # print(f"Error in {loc}: {e}")
            pass

def scan_all_cx(project_id):
    from google.cloud import dialogflowcx_v3 as dialogflow
    client = dialogflow.AgentsClient()
    locations = ["global", "us-central1", "us-east1"]
    for loc in locations:
        print(f"Scanning CX in {project_id} / {loc}")
        try:
            if loc != "global":
                c_options = {"api_endpoint": f"{loc}-dialogflow.googleapis.com"}
                loc_client = dialogflow.AgentsClient(client_options=c_options)
            else:
                loc_client = client
            parent = f"projects/{project_id}/locations/{loc}"
            for agent in loc_client.list_agents(parent=parent):
                print(f"FOUND CX: {agent.display_name} | {agent.name}")
        except Exception as e:
            pass

if __name__ == "__main__":
    scan_all_engines("stok-7bc5c")
    scan_all_cx("stok-7bc5c")
