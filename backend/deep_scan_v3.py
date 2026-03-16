
from google.cloud import discoveryengine_v1beta as discoveryengine
from google.api_core.client_options import ClientOptions

def deep_scan(project_id):
    client = discoveryengine.EngineServiceClient()
    locations = ["global", "us-central1"]
    
    for loc in locations:
        print(f"\n--- SCANNING {loc} ---")
        try:
            client_options = None
            if loc != 'global':
                client_options = ClientOptions(api_endpoint=f"{loc}-discoveryengine.googleapis.com")
            
            loc_client = discoveryengine.EngineServiceClient(client_options=client_options)
            parent = f"projects/{project_id}/locations/{loc}/collections/default_collection"
            
            request = discoveryengine.ListEnginesRequest(parent=parent)
            engines = loc_client.list_engines(request=request)
            for engine in engines:
                print(f"ENGINE: {engine.display_name} | {engine.name}")
        except Exception as e:
            print(f"Error in {loc}: {e}")

if __name__ == "__main__":
    deep_scan("stok-7bc5c")
