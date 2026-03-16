
from google.cloud import discoveryengine_v1beta as discoveryengine
from google.api_core.client_options import ClientOptions

def check_project_detailed(project_id):
    locations = ["global", "us-central1", "eu"]
    for location in locations:
        print(f"--- Checking Discovery Engine in {project_id} / {location} ---")
        try:
            client_options = None
            if location != 'global':
                client_options = ClientOptions(api_endpoint=f"{location}-discoveryengine.googleapis.com")
            
            client = discoveryengine.EngineServiceClient(client_options=client_options)
            parent = f"projects/{project_id}/locations/{location}/collections/default_collection"
            
            request = discoveryengine.ListEnginesRequest(parent=parent)
            page_result = client.list_engines(request=request)
            
            found = False
            for response in page_result:
                print(f"FOUND: {response.display_name} ({response.name})")
                found = True
            if not found:
                print("No engines found in this location.")
        except Exception as e:
            if "Discovery Engine API has not been used" in str(e):
                print("API disabled.")
            else:
                print(f"Error: {e}")

if __name__ == "__main__":
    check_project_detailed("agnostic-live-agent-6192")
    print("\n" + "="*50 + "\n")
    check_project_detailed("stok-7bc5c")
