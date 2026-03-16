
from google.cloud import discoveryengine_v1beta as discoveryengine

def list_engines_for_real(project_id):
    client = discoveryengine.EngineServiceClient()
    # Testing many locations that are common for vertex agents
    locations = ["global", "us", "eu", "us-central1", "us-east1"]
    
    for loc in locations:
        print(f"Checking Engine in {loc}...")
        try:
            from google.api_core.client_options import ClientOptions
            if loc == "global":
                endpoint = "discoveryengine.googleapis.com"
            else:
                endpoint = f"{loc}-discoveryengine.googleapis.com"
            
            loc_client = discoveryengine.EngineServiceClient(client_options=ClientOptions(api_endpoint=endpoint))
            parent = f"projects/{project_id}/locations/{loc}/collections/default_collection"
            
            for engine in loc_client.list_engines(parent=parent):
                print(f"  FOUND ENGINE: {engine.display_name} ({engine.name})")
        except Exception as e:
            # print(f"  Error in {loc}: {e}")
            pass

def list_data_stores(project_id):
    client = discoveryengine.DataStoreServiceClient()
    locations = ["global", "us", "eu", "us-central1"]
    for loc in locations:
        print(f"Checking Data Stores in {loc}...")
        try:
            from google.api_core.client_options import ClientOptions
            if loc == "global":
                endpoint = "discoveryengine.googleapis.com"
            else:
                endpoint = f"{loc}-discoveryengine.googleapis.com"
            
            loc_client = discoveryengine.DataStoreServiceClient(client_options=ClientOptions(api_endpoint=endpoint))
            parent = f"projects/{project_id}/locations/{loc}/collections/default_collection"
            
            for ds in loc_client.list_data_stores(parent=parent):
                print(f"  FOUND DATA STORE: {ds.display_name} ({ds.name})")
        except: pass

if __name__ == "__main__":
    list_engines_for_real("stok-7bc5c")
    list_data_stores("stok-7bc5c")
