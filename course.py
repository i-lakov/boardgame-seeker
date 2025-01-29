import json
import os
from elasticsearch import Elasticsearch

# Connect to Elasticsearch and load settings
es = Elasticsearch("http://localhost:9200")

with open("index_settings.json", "r") as file:
    index_settings = json.load(file)

data_dir = "data"
index_name = "games"

# Define the index mapping for structured fields
index_settings = {
    "mappings": {
        "properties": {
            "id": {"type": "integer"},
            "details.maxplayers": {"type": "integer"},
            "details.minage": {"type": "integer"},
            "details.minplayers": {"type": "integer"},
            "details.name": {"type": "text"},
            "details.playingtime": {"type": "integer"},
            "attributes.boardgamecategory": {"type": "keyword"},
            "attributes.boardgamemechanic": {"type": "keyword"},
            "details.description": {"type": "text"}
        }
    }
}

# Check if the index already exists
if not es.indices.exists(index=index_name):
    # Create the index with the specified settings
    es.indices.create(index=index_name, body=index_settings)
    print(f"Index '{index_name}' created with custom settings.")

# Walk through all directories and nested directories
for root, dirs, files in os.walk(data_dir):
    for filename in files:
        file_path = os.path.join(root, filename)
        
        # Open the file and read its content line by line
        with open(file_path, 'r', encoding='utf-8') as file:
            lines = file.readlines()

        # If file is empty, skip
        if not lines:
            continue

        rel_file_path = os.path.relpath(file_path, data_dir)

        for line_number, line in enumerate(lines, start=1):
            line = line.strip()
            if not line:  # Skip empty lines
                continue
            
            doc_id = f"{rel_file_path}:{line_number}"

            # Check if this line is already indexed
            if es.exists(index=index_name, id=doc_id):
                #print(f"Line {line_number} in '{rel_file_path}' already indexed, skipping...")
                continue
            
            # Create document for this line
            doc = {
                "file_name": rel_file_path,
                "line_number": line_number,
                "content": line
            }
            
            # Index the line
            es.index(index=index_name, id=doc_id, body=doc)
            print(f"Indexed line {line_number} in '{rel_file_path}': {line}")

print("Indexing complete!")
es.indices.refresh(index=index_name)

# Search the index
query = {
    "query": {
        "match": {
            "content": "catan"  # Example search keyword
        }
    }
}

response = es.search(index=index_name, body=query)

print("\nSearch Results:")
for hit in response["hits"]["hits"]:
    print(f"Line {hit['_source']['line_number']}, Score: {hit['_score']}")
    print(f"  {hit['_source']['content']}\n")

# Count documents in the index
count = es.count(index=index_name)
print(f"Total lines indexed in '{index_name}': {count['count']}")

# Prompt the user if they want to delete the index
delete_index = input(f"\nDo you want to delete the index '{index_name}'? (y/N): ").strip().upper()

if delete_index == 'Y':
    if es.indices.exists(index=index_name):
        es.indices.delete(index=index_name)
        print(f"\nIndex '{index_name}' deleted.")
    else:
        print(f"Index '{index_name}' does not exist.")
else:
    print("Index deletion skipped.")
