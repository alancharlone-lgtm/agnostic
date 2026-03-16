
from google.cloud import discoveryengine_v1 as discoveryengine

def list_engines_v1(project_id):
    client = discoveryengine.EngineServiceClient()
    for loc in ["global", "us", "eu"]:
        print(f"Scanning v1 engines in {loc}...")
        try:
            parent = f"projects/{project_id}/locations/{loc}/collections/default_collection"
            for engine in client.list_engines(parent=parent):
                print(f"  V1 ENGINE: {engine.display_name} | {engine.name}")
        except: pass

if __name__ == "__main__":
    list_engines_v1("stok-7bc5c")
