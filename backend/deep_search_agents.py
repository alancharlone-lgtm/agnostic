
import subprocess
import json
from google.cloud import discoveryengine_v1beta as discoveryengine

def get_all_projects():
    try:
        res = subprocess.run(["gcloud", "projects", "list", "--format=json"], capture_output=True, text=True)
        return json.loads(res.stdout)
    except:
        return []

def list_engines_for_all():
    projects = get_all_projects()
    client = discoveryengine.EngineServiceClient()
    
    for p in projects:
        project_id = p['projectId']
        for location in ['global', 'us-central1']:
            parent = f"projects/{project_id}/locations/{location}/collections/default_collection"
            print(f"Checking {project_id} ({location})...")
            try:
                request = discoveryengine.ListEnginesRequest(parent=parent)
                page_result = client.list_engines(request=request)
                for response in page_result:
                    print(f"FOUND ENGINE: {response.display_name} in {project_id}")
                    if "Orquestador" in response.display_name:
                         print(">>> MATCH! <<<")
            except Exception as e:
                # No imprimimos error para no saturar si es que la API está deshabilitada
                pass

if __name__ == "__main__":
    list_engines_for_all()
