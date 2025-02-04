from elasticsearch import Elasticsearch

es = Elasticsearch("http://localhost:9200")

INDEX_NAME = "games"

mapping = {
    "properties": {
        "description_vector": {
            "type": "dense_vector",
            "dims": 384  # Dimensions of the 'all-MiniLM-L6-v2' model
        }
    }
}

# Update the index mapping
es.indices.put_mapping(index=INDEX_NAME, body=mapping)

# RUN ONLY ONCE IN THE BEGINNING