import google.adk
import os
import glob
p = google.adk.__path__[0]
for root, dirs, files in os.walk(p):
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            with open(path, 'r', encoding='utf-8', errors='ignore') as file:
                for idx, line in enumerate(file):
                    if 'class InvocationContext' in line:
                        print(f"Found in {path}:{idx+1}")
