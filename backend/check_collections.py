
from google.cloud import discoveryengine_v1beta as discoveryengine

def list_collections(project_id):
    client = discoveryengine.CollectionServiceClient()
    parent = f"projects/{project_id}/locations/global"
    print(f"Buscando colecciones en: {parent}")
    try:
        request = discoveryengine.ListCollectionsRequest(parent=parent)
        for col in client.list_collections(request=request):
            print(f"COLLECTION: {col.display_name} | {col.name}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    list_collections("stok-7bc5c")
