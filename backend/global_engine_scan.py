
import subprocess
import json
from google.cloud import discoveryengine_v1beta as discoveryengine

def get_all_projects_v2():
    try:
        res = subprocess.run(["gcloud", "projects", "list", "--format=json"], capture_output=True, text=True)
        return json.loads(res.stdout)
    except:
        return []

def scan_engines_everywhere():
    projects = get_all_projects_v2()
    client = discoveryengine.EngineServiceClient()
    
    for p in projects:
        project_id = p['projectId']
        print(f"\nChecking {project_id}...")
        for location in ['global', 'us-central1']:
            parent = f"projects/{project_id}/locations/{location}/collections/default_collection"
            try:
                request = discoveryengine.ListEnginesRequest(parent=parent)
                page_result = client.list_engines(request=request)
                for response in page_result:
                    print(f"FOUND ENGINE: {response.display_name} | {response.name}")
                    if "agent_1771938686136" in response.name or "Orquestador" in response.display_name:
                         print(">>> MATCH FOUND! <<<")
            except:
                pass

if __name__ == "__main__":
    scan_engines_everywhere()
