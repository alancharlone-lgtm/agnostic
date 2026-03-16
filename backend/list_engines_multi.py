
from google.cloud import discoveryengine_v1beta as discoveryengine

def list_engines_loc(project_id, location):
    client = discoveryengine.EngineServiceClient()
    parent = f"projects/{project_id}/locations/{location}/collections/default_collection"
    
    print(f"Buscando motores en {location}: {parent}")
    try:
        request = discoveryengine.ListEnginesRequest(parent=parent)
        page_result = client.list_engines(request=request)
        
        for response in page_result:
            print(f"---")
            print(f"Nombre: {response.display_name}")
            print(f"ID completo: {response.name}")
    except Exception as e:
        print(f"Error en {location}: {e}")

if __name__ == "__main__":
    list_engines_loc("stok-7bc5c", "us-central1")
    list_engines_loc("stok-7bc5c", "global")
