# ==================================
# RUN ONLY ONCE AFTER INDEXING FILES
# ==================================
from sentence_transformers import SentenceTransformer
from elasticsearch import Elasticsearch
from constants import *

model = SentenceTransformer('all-MiniLM-L6-v2')
es = Elasticsearch("http://localhost:9200")

# Fetch all games from Elasticsearch
games = es.search(index=INDEX_NAME, body={"query": {"match_all": {}}}, size=1000)

for game in games['hits']['hits']:
    game_id = game['_id']
    description = game['_source']['details']['description']
    
    # Generate embedding for the description
    embedding = model.encode(description).tolist()
    
    # Update the game document with the embedding
    es.update(
        index=INDEX_NAME,
        id=game_id,
        body={
            "doc": {
                "description_vector": embedding
            }
        }
    )
