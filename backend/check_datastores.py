
from google.cloud import discoveryengine_v1beta as discoveryengine

def list_datastores(project_id):
    client = discoveryengine.DataStoreServiceClient()
    parent = f"projects/{project_id}/locations/global/collections/default_collection"
    
    print(f"Buscando Data Stores en: {parent}")
    try:
        request = discoveryengine.ListDataStoresRequest(parent=parent)
        page_result = client.list_data_stores(request=request)
        for ds in page_result:
            print(f"DS: {ds.display_name} | ID: {ds.name}")
    except Exception as e:
        print(f"Error global: {e}")

    parent_us = f"projects/{project_id}/locations/us-central1/collections/default_collection"
    print(f"Buscando Data Stores en: {parent_us}")
    try:
        from google.api_core.client_options import ClientOptions
        client_us = discoveryengine.DataStoreServiceClient(
            client_options=ClientOptions(api_endpoint="us-central1-discoveryengine.googleapis.com")
        )
        request = discoveryengine.ListDataStoresRequest(parent=parent_us)
        page_result = client_us.list_data_stores(request=request)
        for ds in page_result:
            print(f"DS: {ds.display_name} | ID: {ds.name}")
    except Exception as e:
        print(f"Error us-central1: {e}")

if __name__ == "__main__":
    list_datastores("stok-7bc5c")
    print("-" * 20)
    list_datastores("agnostic-live-agent-6192")
