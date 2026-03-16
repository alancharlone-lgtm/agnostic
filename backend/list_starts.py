
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

def list_starts():
    try:
        with open('session_full_validation_raw.json', 'r', encoding='utf-16') as f:
            logs = json.load(f)
    except:
        with open('session_full_validation_raw.json', 'r', encoding='utf-8') as f:
            logs = json.load(f)

    logs.sort(key=lambda x: x.get('timestamp', ''))
    
    print("LISTADO DE INICIOS DE SESIÓN (V-LOOP):")
    for l in logs:
        payload = l.get('textPayload', '')
        if 'V-LOOP: Iniciando' in payload:
            print(f"{to_local(l.get('timestamp'))} | {payload}")

if __name__ == "__main__":
    list_starts()
