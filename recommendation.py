import datetime
from constants import *
from elasticsearch import Elasticsearch

es = Elasticsearch("http://localhost:9200")

def log_search_game(game_id: str):
    doc_id = str(game_id)
    try:
        es.update(
            index=GAMES_SITE_DATA,
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
    es.indices.refresh(index=GAMES_SITE_DATA)
    return search_game_by_id_without_log(game_id)

def search_game_by_id_without_log(game_id: str):
    query = {
        "query": {
            "match": {
                "id": game_id
            }
        }
    }
    response = es.search(index=INDEX_NAME, body=query)
    return response["hits"]["hits"][0]['_source']

def get_popular_searches(limit: int = 10):
    query = {
        "query": {"match_all": {}},
        "sort": [{"count": {"order": "desc"}}],
        "size": limit
    }
    response = es.search(index=GAMES_SITE_DATA, body=query)
    
    print("\nPopular Searches:")
    for hit in response["hits"]["hits"]:
        source = hit["_source"]
        game = search_game_by_id_without_log(source["game_id"])
        print(f"Game ID: {game['details']['name']}, Search Count: {source['count']}")

def more_like_this(game_id: str):
    game = search_game_by_id_without_log(game_id)
    query = {
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
                                    "_index": INDEX_NAME,
                                    "_id": game["id"]
                                }
                            ],
                            "min_term_freq": 1,
                            "max_query_terms": 12
                        }
                    },
                    {
                        "term": {
                            "details.minplayers": game["details"]["minplayers"]
                        }
                    },
                    {
                        "term": {
                            "details.maxplayers": game["details"]["maxplayers"]
                        }
                    },
                    {
                        "term": {
                            "details.playingtime": game["details"]["playingtime"]
                        }
                    }
                ]
            }
        }
    }
    response = es.search(index=INDEX_NAME, body=query)
    similar_games = [hit["_source"] for hit in response["hits"]["hits"]]
    return similar_games