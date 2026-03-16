
from google.cloud import dialogflowcx_v3 as dialogflow

def list_all_cx_agents():
    projects = ["stok-7bc5c", "agnostic-live-agent-6192", "gen-lang-client-0189612712"]
    locations = ["global", "us-central1"]
    
    client = dialogflow.AgentsClient()
    
    for project_id in projects:
        for location in locations:
            parent = f"projects/{project_id}/locations/{location}"
            print(f"Checking {parent}...")
            try:
                if location != "global":
                    c_options = {"api_endpoint": f"{location}-dialogflow.googleapis.com"}
                    loc_client = dialogflow.AgentsClient(client_options=c_options)
                else:
                    loc_client = client
                
                request = dialogflow.ListAgentsRequest(parent=parent)
                page_result = loc_client.list_agents(request=request)
                
                for response in page_result:
                    print(f"Found: {response.display_name} in {parent}")
                    if "Orquestador_Principal_Reparaciones" in response.display_name:
                        print(">>> MATCH! <<<")
            except Exception as e:
                print(f"Error in {parent}: {e}")

if __name__ == "__main__":
    list_all_cx_agents()
