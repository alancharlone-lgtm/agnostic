import json
import datetime

# Hora local de Argentina (UTC-3)
def to_local(utc_str):
    try:
        dt = datetime.datetime.strptime(utc_str.replace('Z', ''), '%Y-%m-%dT%H:%M:%S.%f')
        dt = dt - datetime.timedelta(hours=3)
        return dt.strftime('%H:%M:%S.%f')[:-3]
    except:
        return utc_str

with open('final_test_utf8.json', 'r', encoding='utf-8-sig') as f:
    logs = json.load(f)

# Sort logs by timestamp just in case
logs.sort(key=lambda x: x.get('timestamp', ''))

print(f"{'HORA (ARG)':<12} | {'TIPO':<15} | {'CONTENIDO'}")
print("-" * 120)

current_type = None
current_content = []
current_time = None

def flush_current():
    global current_type, current_content, current_time
    if current_type and current_content:
        content_str = " ".join(current_content).replace("  ", " ").strip()
        if current_type == "HERRAMIENTA":
            print(f"{current_time:<12} | {current_type:<15} | {content_str}")
        else:
            print(f"{current_time:<12} | {current_type:<15} | {content_str}")
    current_content = []

for entry in logs:
    payload = entry.get('textPayload', '')
    timestamp = entry.get('timestamp', '')
    local_time = to_local(timestamp)
    
    if 'DEBUG TRANSCRIPT INPUT' in payload:
        text = payload.replace('DEBUG TRANSCRIPT INPUT: ', '').strip()
        if current_type != "USUARIO":
            flush_current()
            current_type = "USUARIO"
            current_time = local_time
        current_content.append(text)
        
    elif 'DEBUG TRANSCRIPT OUTPUT' in payload:
        text = payload.replace('DEBUG TRANSCRIPT OUTPUT: ', '').strip()
        if current_type != "IA":
            flush_current()
            current_type = "IA"
            current_time = local_time
        current_content.append(text)
        
    elif 'DEBUG TOOL START' in payload:
        flush_current()
        text = payload.replace('DEBUG TOOL START: ', '').strip()
        print(f"{local_time:<12} | HERRAMIENTA    | INICIO: {text}")
        current_type = None
        
    elif 'DEBUG TOOL END' in payload:
        flush_current()
        text = payload.replace('DEBUG TOOL END: ', '').strip()
        print(f"{local_time:<12} | HERRAMIENTA    | FIN: {text}")
        current_type = None
        
    elif 'DEBUG TRANSCRIPT:' in payload and not ('INPUT' in payload or 'OUTPUT' in payload):
        # These are usually thoughts
        if '**' in payload:
            flush_current()
            text = payload.replace('DEBUG TRANSCRIPT: ', '').strip()
            # print(f"{local_time:<12} | PENSAMIENTO   | {text}") # Hidden to keep dialogues clean unless needed
            current_type = None

flush_current()
