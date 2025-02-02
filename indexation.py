import json
import csv
from constants import *
from elasticsearch import Elasticsearch

# Connect to Elasticsearch and load settings
es = Elasticsearch("http://localhost:9200")
with open(SETTINGS_PATH, "r") as file:
    index_settings = json.load(file)

# Create index if it does not exist
if not es.indices.exists(index=INDEX_NAME):
    es.indices.create(index=INDEX_NAME, body=index_settings)
    print(f"Index '{INDEX_NAME}' created with custom settings.")

    with open(CSV_FILE, newline='', encoding='utf-8-sig') as file:
        reader = csv.DictReader(file, delimiter=';')

        for row in reader:
            doc_id = row["id"]

            if es.exists(index=INDEX_NAME, id=doc_id):
                continue
            
            doc = {
                "id": int(row["id"]),
                "details": {
                    "maxplayers": int(row["details.maxplayers"]),
                    "minage": int(row["details.minage"]),
                    "minplayers": int(row["details.minplayers"]),
                    "name": row["details.name"],
                    "playingtime": int(row["details.playingtime"]),
                    "description": row["details.description"]
                },
                "attributes": {
                    "boardgamecategory": row["attributes.boardgamecategory"].split(","),
                    "boardgamemechanic": row["attributes.boardgamemechanic"].split(",")
                }
            }

            # Index the document
            es.index(index=INDEX_NAME, id=doc_id, body=doc)
            print(f"Indexed game: {row['details.name']}")

    print("Indexing complete!")
    es.indices.refresh(index=INDEX_NAME)

if not es.indices.exists(index=SEARCH_LOG_INDEX):
    es.indices.create(index=SEARCH_LOG_INDEX)
    print(f"Index '{SEARCH_LOG_INDEX}' created for logging search terms.")

# Prompt the user if they want to delete the index
delete_index = input(f"\nDo you want to delete the index '{INDEX_NAME}'? (y/N): ").strip().upper()

if delete_index == 'Y':
   if es.indices.exists(index=INDEX_NAME):
       es.indices.delete(index=INDEX_NAME)
       print(f"\nIndex '{INDEX_NAME}' deleted.")
   else:
       print(f"Index '{INDEX_NAME}' does not exist.")
else:
    print("Index deletion skipped.")