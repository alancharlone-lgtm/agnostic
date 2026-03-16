
import json
import datetime
import sys

# Ensure output can handle unicode or use ASCII
def to_local(utc_str):
    try:
        if not utc_str: return "00:00:00.000"
        utc_str = utc_str.replace('Z', '')
        if '.' in utc_str:
            base, frac = utc_str.split('.')
            frac = (frac + '000000')[:6]
            utc_str = f"{base}.{frac}"
        dt = datetime.datetime.strptime(utc_str, '%Y-%m-%dT%H:%M:%S.%f')
        dt = dt - datetime.timedelta(hours=3)
        return dt.strftime('%H:%M:%S.%f')[:-3]
    except: return utc_str

def tool_sequence_audit():
    try:
        with open('audit_1725_raw.json', 'r', encoding='utf-16') as f:
            logs = json.load(f)
    except:
        try:
            with open('audit_1725_raw.json', 'r', encoding='utf-8') as f:
                logs = json.load(f)
        except Exception as e:
            print(f"Error loading logs: {e}")
            return

    logs.sort(key=lambda x: x.get('timestamp', ''))

    print(f"\n{'HORA (ARG)':<12} | {'SISTEMA':<15} | {'EVENTO DE HERRAMIENTA'}")
    print("-" * 130)

    for entry in logs:
        payload = entry.get('textPayload', '')
        if not payload: continue
        local_time = to_local(entry.get('timestamp'))

        if '17:20' > local_time: continue

        if 'DEBUG TOOL START' in payload:
            content = payload.replace('DEBUG TOOL START: ', '')
            print(f"{local_time:<12} | CALL          | >> {content}")
        
        elif 'DEBUG ERROR executing tool' in payload:
            content = payload.replace('DEBUG ERROR executing tool ', '')
            print(f"{local_time:<12} | ERROR         | !! {content[:100]}")
            
        elif 'DEBUG TOOL END' in payload:
            content = payload.replace('DEBUG TOOL END: ', '')
            print(f"{local_time:<12} | RETURN        | OK {content}")

if __name__ == "__main__":
    tool_sequence_audit()
