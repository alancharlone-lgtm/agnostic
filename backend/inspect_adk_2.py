import google.adk
import google.adk.runners
print("google.adk.runners dir:", dir(google.adk.runners))
try:
    from google.adk import runners
    print("runners dir:", dir(runners))
except ImportError as e:
    print("Import error:", e)
