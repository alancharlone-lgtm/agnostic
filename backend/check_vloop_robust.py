
import json
import datetime

def audit_vloop_session():
    try:
        with open('final_session_audit.json', 'r', encoding='utf-16') as f:
            logs = json.load(f)
    except:
        with open('final_session_audit.json', 'r', encoding='utf-8') as f:
            logs = json.load(f)

    logs.sort(key=lambda x: x.get('timestamp', ''))
    
    found_vloop = False
    count_after = 0
    
    print(f"{'TIMESTAMP':<30} | {'PAYLOAD'}")
    print("-" * 150)
    
    for l in logs:
        payload = l.get('textPayload', '')
        if not payload: continue
        
        # Look for the last V-LOOP start in the logs
        if 'V-LOOP: Iniciando' in payload:
            found_vloop = True
            count_after = 0
            print("\n--- NUEVA SESIÓN DETECTADA ---")

        if found_vloop:
            relevant = any(term in payload for term in ['V-LOOP', 'DEBUG TRANSCRIPT', 'DEBUG TOOL'])
            if relevant:
                print(f"{l.get('timestamp'):<30} | {payload[:120]}")
            
            count_after += 1
            if count_after > 200: # Look at 200 logs after start
                found_vloop = False 

if __name__ == "__main__":
    audit_vloop_session()
