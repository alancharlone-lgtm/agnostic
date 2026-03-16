
import json
import datetime

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

def read_active():
    try:
        with open('recent_logs.json', 'r', encoding='utf-16') as f:
            logs = json.load(f)
    except:
        try:
            with open('recent_logs.json', 'r', encoding='utf-8') as f:
                logs = json.load(f)
        except: return

    logs.sort(key=lambda x: x.get('timestamp', ''))
    
    for l in logs:
        payload = l.get('textPayload', '')
        if not payload: continue
        local_time = to_local(l.get('timestamp'))
        
        # Filtramos solo lo más relevante para el usuario "en tiempo real"
        if any(term in payload for term in ['V-LOOP', 'DEBUG TRANSCRIPT', 'DEBUG TOOL']):
            print(f"[{local_time}] {payload}")

if __name__ == "__main__":
    read_active()
