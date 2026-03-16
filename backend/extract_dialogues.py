
import json
import datetime

def to_local(utc_str):
    try:
        utc_str = utc_str.replace('Z', '')
        if '.' in utc_str:
            base, frac = utc_str.split('.')
            frac = (frac + '000000')[:6]
            utc_str = f"{base}.{frac}"
        else:
            utc_str = f"{utc_str}.000000"
            
        dt = datetime.datetime.strptime(utc_str, '%Y-%m-%dT%H:%M:%S.%f')
        dt = dt - datetime.timedelta(hours=3)
        return dt.strftime('%H:%M:%S.%f')[:-3]
    except:
        return utc_str

def process_dialogues():
    try:
        with open('transcript_logs.json', 'r', encoding='utf-16') as f:
            logs = json.load(f)
    except:
        with open('transcript_logs.json', 'r', encoding='utf-8') as f:
            logs = json.load(f)

    logs.sort(key=lambda x: x.get('timestamp', ''))

    print("\n--- DIÁLOGOS DE LA SESIÓN ---")
    
    current_sender = None
    current_text = []
    current_time = None

    def flush():
        nonlocal current_sender, current_text, current_time
        if current_sender and current_text:
            msg = " ".join(current_text).replace("  ", " ").strip()
            if msg:
                print(f"[{current_time}] {current_sender}: {msg}")
        current_text = []

    for entry in logs:
        payload = entry.get('textPayload', '')
        timestamp = entry.get('timestamp', '')
        local_time = to_local(timestamp)

        if 'TRANSCRIPT INPUT' in payload:
            text = payload.replace('DEBUG TRANSCRIPT INPUT: ', '').strip()
            if current_sender != "USUARIO":
                flush()
                current_sender = "USUARIO"
                current_time = local_time
            current_text.append(text)
        elif 'TRANSCRIPT OUTPUT' in payload:
            text = payload.replace('DEBUG TRANSCRIPT OUTPUT: ', '').strip()
            if current_sender != "IA":
                flush()
                current_sender = "IA"
                current_time = local_time
            current_text.append(text)
    
    flush()

if __name__ == "__main__":
    process_dialogues()
