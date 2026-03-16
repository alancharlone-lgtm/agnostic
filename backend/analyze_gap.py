import json
import datetime

def to_local(utc_str):
    try:
        dt = datetime.datetime.strptime(utc_str.replace('Z', ''), '%Y-%m-%dT%H:%M:%S.%f')
        dt = dt - datetime.timedelta(hours=3)
        return dt.strftime('%H:%M:%S.%f')[:-3]
    except:
        return utc_str

with open('final_test_utf8.json', 'r', encoding='utf-8-sig') as f:
    logs = json.load(f)

logs.sort(key=lambda x: x.get('timestamp', ''))

print(f"{'HORA (ARG)':<12} | {'TIPO':<15} | {'CONTENIDO'}")
print("-" * 120)

# Filter specifically for the start of the session around 12:21:56
for entry in logs:
    payload = entry.get('textPayload', '')
    timestamp = entry.get('timestamp', '')
    local_time = to_local(timestamp)
    
    # Range of interest: 12:21:50 to 12:22:05
    if "12:21:5" in local_time or "12:22:0" in local_time:
        if 'DEBUG TRANSCRIPT' in payload:
            if 'INPUT' in payload:
                print(f"{local_time:<12} | AUDIO INPUT    | {payload.replace('DEBUG TRANSCRIPT INPUT: ', '').strip()}")
            elif 'OUTPUT' in payload:
                print(f"{local_time:<12} | AUDIO OUTPUT   | {payload.replace('DEBUG TRANSCRIPT OUTPUT: ', '').strip()}")
            else:
                print(f"{local_time:<12} | IA THOUGHT     | {payload.replace('DEBUG TRANSCRIPT: ', '').strip()}")
        elif 'DEBUG TOOL START' in payload:
            print(f"{local_time:<12} | TOOL START     | {payload.replace('DEBUG TOOL START: ', '').strip()}")
