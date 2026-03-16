
from google.cloud import discoveryengine_v1beta as discoveryengine
from google.api_core.client_options import ClientOptions

def try_id_everywhere(project_id, base_id):
    ids = [base_id, base_id.replace("_", "-"), base_id.split("_")[-1]]
    locations = ["global", "us", "eu", "us-central1"]
    
    for loc in locations:
        print(f"\n--- Checking loc: {loc} ---")
        try:
            client_options = None
            if loc != "global":
                client_options = ClientOptions(api_endpoint=f"{loc}-discoveryengine.googleapis.com")
            client = discoveryengine.EngineServiceClient(client_options=client_options)
            
            for engine_id in ids:
                name = f"projects/{project_id}/locations/{loc}/collections/default_collection/engines/{engine_id}"
                print(f"  Trying: {name}")
                try:
                    engine = client.get_engine(name=name)
                    print(f"  >>> ¡ENCONTRADO! Display: {engine.display_name}")
                    return name
                except:
                    pass
        except:
            pass
    return None

if __name__ == "__main__":
    try_id_everywhere("stok-7bc5c", "agent_1771938686136")
