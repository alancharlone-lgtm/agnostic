
import json
import datetime
import re

def to_local(utc_str):
    try:
        # GCP formats often have more or less precision, let's normalize
        utc_str = utc_str.replace('Z', '')
        if '.' in utc_str:
            base, frac = utc_str.split('.')
            frac = (frac + '000000')[:6]
            utc_str = f"{base}.{frac}"
        else:
            utc_str = f"{utc_str}.000000"
            
        dt = datetime.datetime.strptime(utc_str, '%Y-%m-%dT%H:%M:%S.%f')
        dt = dt - datetime.timedelta(hours=3) # Argentina UTC-3
        return dt.strftime('%H:%M:%S.%f')[:-3]
    except Exception as e:
        return utc_str

def analyze():
    try:
        # gcloud on Windows often outputs in UTF-16
        with open('last_session_raw.json', 'r', encoding='utf-16') as f:
            logs = json.load(f)
    except Exception as e:
        try:
            with open('last_session_raw.json', 'r', encoding='utf-8') as f:
                logs = json.load(f)
        except Exception as e2:
            print(f"Error loading logs: {e2}")
            return

    # Sort by timestamp (ascending)
    logs.sort(key=lambda x: x.get('timestamp', ''))

    print(f"\n{'HORA (ARG)':<12} | {'EVENTO':<20} | {'DETALLE'}")
    print("-" * 120)

    for entry in logs:
        payload = entry.get('textPayload', '')
        timestamp = entry.get('timestamp', '')
        local_time = to_local(timestamp)

        # 1. Proactive Injections
        if 'DEBUG INJECTION' in payload:
            type_inj = "V-LOOP" if "V-LOOP" in payload else "NUDGE"
            print(f"{local_time:<12} | INYECCIÓN {type_inj:<9} | {payload[:80]}...")

        # 2. Tool Executions
        elif 'DEBUG TOOL START' in payload:
            print(f"{local_time:<12} | TOOL START          | {payload.replace('DEBUG TOOL START: ', '')}")
        elif 'DEBUG TOOL END' in payload:
            print(f"{local_time:<12} | TOOL END            | {payload.replace('DEBUG TOOL END: ', '')}")
        
        # 3. Dialogues
        elif 'DEBUG TRANSCRIPT INPUT' in payload:
            text = payload.replace('DEBUG TRANSCRIPT INPUT: ', '').strip()
            print(f"{local_time:<12} | USUARIO             | {text}")
        elif 'DEBUG TRANSCRIPT OUTPUT' in payload:
            text = payload.replace('DEBUG TRANSCRIPT OUTPUT: ', '').strip()
            print(f"{local_time:<12} | IA RESPUESTA        | {text}")
        
        # 4. Errors
        elif 'DEBUG ERROR' in payload:
            print(f"{local_time:<12} | ERROR               | {payload[:80]}...")

if __name__ == "__main__":
    analyze()
