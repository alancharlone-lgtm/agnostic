
from google.cloud import discoveryengine_v1beta as discoveryengine

def list_datastores_all(project_id):
    client = discoveryengine.DataStoreServiceClient()
    locations = ["global", "us-central1", "us"]
    
    for loc in locations:
        print(f"\n--- Data Stores in {loc} ---")
        try:
            parent = f"projects/{project_id}/locations/{loc}/collections/default_collection"
            request = discoveryengine.ListDataStoresRequest(parent=parent)
            res = client.list_data_stores(request=request)
            for ds in res:
                print(f"DATA STORE: {ds.display_name} | {ds.name}")
        except Exception as e:
            # print(f"Error: {e}")
            pass

if __name__ == "__main__":
    list_datastores_all("stok-7bc5c")
