
import json
import subprocess
from datetime import datetime
import sys

# Force UTF-8 for printing to redirected files
sys.stdout.reconfigure(encoding='utf-8')

def fetch_logs():
    cmd = [
        "gcloud", "logging", "read",
        "resource.type=cloud_run_revision AND resource.labels.service_name=agnostic-live-backend",
        "--limit", "300",
        "--format", "json(textPayload,timestamp)"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', shell=True)
    if result.returncode != 0:
        print(f"Error fetching logs: {result.stderr}")
        return []
    try:
        return json.loads(result.stdout)
    except Exception as e:
        print(f"Error parsing JSON: {e}")
        return []

logs = fetch_logs()
if not logs:
    exit()

logs.sort(key=lambda x: x["timestamp"])

print("--- SESSION TIMELINE ---")
for log in logs:
    ts_str = log["timestamp"]
    ts = datetime.fromisoformat(ts_str.replace("Z", "+00:00"))
    payload = log.get("textPayload", "")
    
    if payload is None: continue

    if "Incoming WebSocket connection" in payload:
        print(f"[{ts}] [SESSION] START")
    elif "V-LOOP TURNO 1" in payload:
        print(f"[{ts}] [V-LOOP] Greeting Triggered")
    elif "V-LOOP TURNO 2A" in payload:
        print(f"[{ts}] [V-LOOP] Verbal Fill Triggered")
    elif "V-LOOP TURNO 2B" in payload:
        print(f"[{ts}] [V-LOOP] ADK Silent Triggered")
    elif "DEBUG TRANSCRIPT INPUT" in payload:
        print(f"[{ts}] [USER] {payload.replace('DEBUG TRANSCRIPT INPUT: ', '')}")
    elif "DEBUG TRANSCRIPT OUTPUT" in payload:
        print(f"[{ts}] [AI] {payload.replace('DEBUG TRANSCRIPT OUTPUT: ', '')}")
    elif "DEBUG TOOL START" in payload:
        print(f"[{ts}] [TOOL START] {payload.split(': ')[1] if ': ' in payload else payload}")
    elif "DEBUG TOOL END" in payload:
        print(f"[{ts}] [TOOL END] {payload.split(': ')[1] if ': ' in payload else payload}")
