import json
import csv
import datetime
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

search_log_index = "popular_searches"

if not es.indices.exists(index=search_log_index):
    es.indices.create(index=search_log_index)
    print(f"Index '{search_log_index}' created for logging search terms.")

def log_search_game(game_id: str):
    doc_id = str(game_id)
    try:
        es.update(
            index=search_log_index,
            id=doc_id,
            body={
                "script": {
                    "source": "ctx._source.count += 1",
                    "lang": "painless"
                },
                "upsert": {
                    "game_id": game_id,
                    "count": 1,
                    "timestamp": datetime.datetime.now().isoformat()
                }
            }
        )
        print(f"Logged search for game id: '{game_id}'")
    except Exception as e:
        print("Error logging search term:", e)

def search_game_by_id(game_id: str):
    log_search_game(game_id)
    es.indices.refresh(index=search_log_index)
    return search_game_by_id_without_log(game_id)

def search_game_by_id_without_log(game_id: str):
    query = {
        "query": {
            "match": {
                "id": game_id
            }
        }
    }
    response = es.search(index=index_name, body=query)
    return response["hits"]["hits"][0]['_source']

def get_popular_searches(limit: int = 10):
    query = {
        "query": {"match_all": {}},
        "sort": [{"count": {"order": "desc"}}],
        "size": limit
    }
    response = es.search(index=search_log_index, body=query)
    
    print("\nPopular Searches:")
    for hit in response["hits"]["hits"]:
        source = hit["_source"]
        game = search_game_by_id_without_log(source["game_id"])
        print(f"Game ID: {game['details']['name']}, Search Count: {source['count']}")


# Prompt the user if they want to delete the index
#delete_index = input(f"\nDo you want to delete the index '{index_name}'? (y/N): ").strip().upper()

#if delete_index == 'Y':
#    if es.indices.exists(index=index_name):
#        es.indices.delete(index=index_name)
#        print(f"\nIndex '{index_name}' deleted.")
#    else:
#        print(f"Index '{index_name}' does not exist.")
#else:
#print("Index deletion skipped.")


# --- More Like This Logic ---
catan = search_game_by_id("13")
more_like_this = {
    "query": {
        "bool": {
            "must": [
                {
                    "more_like_this": {
                        "fields": [
                            "details.description",
                            "attributes.boardgamecategory",
                            "attributes.boardgamemechanic"
                        ],
                        "like": [
                            {
                                "_index": index_name,
                                "_id": catan["id"]
                            }
                        ],
                        "min_term_freq": 1,
                        "max_query_terms": 12
                    }
                },
                {
                    "term": {
                        "details.minplayers": catan["details"]["minplayers"]
                    }
                },
                {
                    "term": {
                        "details.maxplayers": catan["details"]["maxplayers"]
                    }
                },
                {
                    "term": {
                        "details.playingtime": catan["details"]["playingtime"]
                    }
                }
            ]
        }
    }
}

# Execute the recommendation query
recommendations = es.search(index=index_name, body=more_like_this)

print("\nRecommended Games based on previous game:")
for hit in recommendations["hits"]["hits"]:
    print(f"Game: {hit['_source']['details']['name']}, Max Players: {hit['_source']['details']['maxplayers']}, Min Players: {hit['_source']['details']['minplayers']}, Playtime: {hit['_source']['details']['playingtime']}, Score: {hit['_score']}")

# Most searched games
get_popular_searches()