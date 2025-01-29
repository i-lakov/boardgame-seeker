import json
import os
import csv
from elasticsearch import Elasticsearch

# Connect to Elasticsearch and load settings
es = Elasticsearch("http://localhost:9200")

with open("index_settings.json", "r") as file:
    index_settings = json.load(file)

# Read CSV file and index each row
csv_file = "data/data_boardgames.csv"
index_name = "games"

# Create index if it does not exist
if not es.indices.exists(index=index_name):
    es.indices.create(index=index_name, body=index_settings)
    print(f"Index '{index_name}' created with custom settings.")

with open(csv_file, newline='', encoding='utf-8-sig') as file:
    reader = csv.DictReader(file, delimiter=';')

    for row in reader:
        doc_id = row["id"]

        if es.exists(index=index_name, id=doc_id):
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
        es.index(index=index_name, id=doc_id, body=doc)
        print(f"Indexed game: {row['details.name']}")

print("Indexing complete!")
es.indices.refresh(index=index_name)

# Search the index
query = {
    "query": {
        "range": {
            "details.maxplayers": {
                "lt": 5
            }
        }
    },
    "size": 50  # Limit total results
}

response = es.search(index=index_name, body=query)

print("\nSearch Results:")
for hit in response["hits"]["hits"]:
    print(f"Game: {hit['_source']['details']['name']}, Max Players: {hit['_source']['details']['maxplayers']}, Score: {hit['_score']}")

# Count documents in the index
count = es.count(index=index_name)
print(f"Total lines indexed in '{index_name}': {count['count']}")

# Prompt the user if they want to delete the index
#delete_index = input(f"\nDo you want to delete the index '{index_name}'? (y/N): ").strip().upper()

#if delete_index == 'Y':
#    if es.indices.exists(index=index_name):
#        es.indices.delete(index=index_name)
#        print(f"\nIndex '{index_name}' deleted.")
#    else:
#        print(f"Index '{index_name}' does not exist.")
#else:
print("Index deletion skipped.")
