
from google.cloud import discoveryengine_v1beta as discoveryengine
from google.api_core.client_options import ClientOptions

def list_all_available_engines(project_id):
    locations = ["global", "us", "eu"]
    for loc in locations:
        print(f"--- SCANNING engines in {loc} ---")
        try:
            client_options = None
            if loc != 'global':
                client_options = ClientOptions(api_endpoint=f"{loc}-discoveryengine.googleapis.com")
            
            client = discoveryengine.EngineServiceClient(client_options=client_options)
            parent = f"projects/{project_id}/locations/{loc}/collections/default_collection"
            
            request = discoveryengine.ListEnginesRequest(parent=parent)
            page_result = client.list_engines(request=request)
            
            found = False
            for response in page_result:
                print(f"FOUND ENGINE: {response.display_name} | {response.name}")
                found = True
            if not found:
                print("No engines found.")
        except Exception as e:
            print(f"Error in {loc}: {e}")

if __name__ == "__main__":
    list_all_available_engines("stok-7bc5c")
