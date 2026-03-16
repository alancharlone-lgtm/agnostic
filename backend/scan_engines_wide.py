
import google.cloud.discoveryengine_v1beta as discoveryengine

def list_engines(project_id):
    client = discoveryengine.EngineServiceClient()
    parent = f"projects/{project_id}/locations/global/collections/default_collection"
    print(f"Listing engines in {parent}")
    try:
        for engine in client.list_engines(parent=parent):
            print(f"ENGINE: {engine.display_name} | {engine.name}")
    except Exception as e:
        print(f"Global Error: {e}")

    parent_us = f"projects/{project_id}/locations/us-central1/collections/default_collection"
    print(f"Listing engines in {parent_us}")
    try:
        from google.api_core.client_options import ClientOptions
        client_us = discoveryengine.EngineServiceClient(client_options=ClientOptions(api_endpoint="us-central1-discoveryengine.googleapis.com"))
        for engine in client_us.list_engines(parent=parent_us):
            print(f"ENGINE: {engine.display_name} | {engine.name}")
    except Exception as e:
        print(f"US Error: {e}")

if __name__ == "__main__":
    list_engines("stok-7bc5c")
