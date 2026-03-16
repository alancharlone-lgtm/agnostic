
from google.cloud import aiplatform
from google.cloud import discoveryengine

def list_vertex_resources(project_id):
    print(f"Buscando en AI Platform (Vertex AI Study) - {project_id}")
    try:
        # Check Reasoning Engines
        client = aiplatform.gapic.ReasoningEngineServiceClient()
        parent = f"projects/{project_id}/locations/us-central1"
        for re in client.list_reasoning_engines(parent=parent):
            print(f"[Reasoning Engine] {re.display_name} | {re.name}")
    except Exception as e:
        print(f"Error AI Platform: {e}")

    print(f"\nBuscando en Discovery Engine v1 - {project_id}")
    try:
        client = discoveryengine.EngineServiceClient()
        parent = f"projects/{project_id}/locations/global/collections/default_collection"
        request = discoveryengine.ListEnginesRequest(parent=parent)
        for engine in client.list_engines(request=request):
            print(f"[Engine v1] {engine.display_name} | {engine.name}")
    except Exception as e:
        print(f"Error Engine v1: {e}")

if __name__ == "__main__":
    list_vertex_resources("stok-7bc5c")
