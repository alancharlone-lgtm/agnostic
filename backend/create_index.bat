@echo off
gcloud alpha firestore indexes composite create --collection-group=repair_knowledge_base --query-scope=COLLECTION --field-config="vector-config={\"dimension\":768,\"flat\":\"{}\"},field-path=embedding" --project=stok-7bc5c --quiet
