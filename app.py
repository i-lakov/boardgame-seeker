from flask import Flask, request, jsonify, render_template
from sentence_transformers import SentenceTransformer
from elasticsearch import Elasticsearch
from constants import *
from recommendation import *

app = Flask(__name__)
es = Elasticsearch("http://localhost:9200")

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/search", methods=["GET"])
def search():
    name = request.args.get("name", "")
    description = request.args.get("description", "")
    maxplayers = request.args.get("maxplayers", None)
    minage = request.args.get("minage", None)
    minplayers = request.args.get("minplayers", None)
    playingtime = request.args.get("playingtime", None)
    category = request.args.getlist("category")  # Supports multiple values
    mechanic = request.args.getlist("mechanic")  # Supports multiple values

    must_conditions = []

    # Fuzzy search for name
    if name:
        must_conditions.append({
            "match": {
                "details.name": {
                    "query": name,
                    "fuzziness": "AUTO"
                }
            }
        })

    # Fuzzy search for description
    if description:
        must_conditions.append({
            "match": {
                "details.description": {
                    "query": description,
                    "fuzziness": "AUTO"
                }
            }
        })

    # Numeric filters
    if maxplayers:
        must_conditions.append({
            "range": {
                "details.maxplayers": {"lte": int(maxplayers)}
            }
        })
    
    if minage:
        must_conditions.append({
            "range": {
                "details.minage": {"gte": int(minage)}
            }
        })
    
    if minplayers:
        must_conditions.append({
            "range": {
                "details.minplayers": {"gte": int(minplayers)}
            }
        })

    if playingtime:
        must_conditions.append({
            "range": {
                "details.playingtime": {"lte": int(playingtime)}
            }
        })

    # Match categories (list search)
    for cat in category:
        must_conditions.append({
            "term": {"attributes.boardgamecategory": cat}
        })

    # Match mechanics (list search)
    for mech in mechanic:
        must_conditions.append({
            "term": {"attributes.boardgamemechanic": mech}
        })

    query = {
        "query": {
            "bool": {
                "must": must_conditions
            }
        },
        "size": 50
    }

    response = es.search(index=INDEX_NAME, body=query)
    results = [
        {
            "name": hit["_source"]["details"]["name"],
            "maxplayers": hit["_source"]["details"]["maxplayers"],
            "minage": hit["_source"]["details"]["minage"],
            "minplayers": hit["_source"]["details"]["minplayers"],
            "playingtime": hit["_source"]["details"]["playingtime"],
            "categories": hit["_source"]["attributes"]["boardgamecategory"],
            "mechanics": hit["_source"]["attributes"]["boardgamemechanic"],
            "description": hit["_source"]["details"]["description"],
            "score": hit["_score"]
        }
        for hit in response["hits"]["hits"]
    ]

    return jsonify(results)

@app.route("/popular_searches")
def popular_searches():
    # Fetch popular searches from the SEARCH_LOG_INDEX
    query = {
        "query": {"match_all": {}},
        "sort": [{"count": {"order": "desc"}}],
        "size": 10
    }
    response = es.search(index=GAMES_SITE_DATA, body=query)
    
    # Fetch full game details for each popular search
    results = []
    for hit in response["hits"]["hits"]:
        game_id = hit["_source"]["game_id"]
        game_details = search_game_by_id_without_log(game_id)
        if game_details:
            results.append({
                "name": game_details["details"]["name"],
                "maxplayers": game_details["details"]["maxplayers"],
                "minage": game_details["details"]["minage"],
                "minplayers": game_details["details"]["minplayers"],
                "playingtime": game_details["details"]["playingtime"],
                "categories": game_details["attributes"]["boardgamecategory"],
                "mechanics": game_details["attributes"]["boardgamemechanic"],
                "description": game_details["details"]["description"],
                "count": hit["_source"]["count"]
            })
    
    return jsonify(results)

@app.route("/game/<name>")
def game_detail(name):
    query = {
        "query": {
            "match": {
                "details.name": name
            }
        }
    }
    response = es.search(index=INDEX_NAME, body=query)
    game = response["hits"]["hits"][0]['_source']
    
    # Log the search
    log_search_game(game["id"])
    
    # Get similar games
    similar_games = more_like_this(game["id"])
    
    return render_template("game_detail.html", game=game, similar_games=similar_games)

@app.route("/game_details/<name>")
def game_details(name):
    # Get game details
    game_query = {"query": {"match": {"details.name": name}}}
    game_response = es.search(index=INDEX_NAME, body=game_query)
    game = game_response["hits"]["hits"][0]['_source']
    
    try:
        log_response = es.get(index=GAMES_SITE_DATA, id=game["id"])
        reviews = log_response["_source"].get("reviews", [])
    except:
        reviews = []
    
    # Get similar games
    similar_games = more_like_this(game["id"])
    
    return jsonify({
        "game": game,
        "similar_games": similar_games,
        "reviews": reviews
    })

@app.route("/submit_review", methods=["POST"])
def submit_review():
    data = request.json
    game_id = data["game_id"]
    review_text = data["review_text"]
    
    try:
        es.update(
            index=GAMES_SITE_DATA,
            id=game_id,
            body={
                "script": {
                    "source": """
                        if (ctx._source.reviews == null) {
                            ctx._source.reviews = [];
                        }
                        ctx._source.reviews.add([
                            'text': params.review_text,
                            'timestamp': params.timestamp
                        ]);
                    """,
                    "lang": "painless",
                    "params": {
                        "review_text": review_text,
                        "timestamp": datetime.datetime.now().isoformat()
                    }
                },
                "upsert": {
                    "game_id": game_id,
                    "reviews": [
                        {
                            "text": review_text,
                            "timestamp": datetime.datetime.now().isoformat()
                        }
                    ]
                }
            }
        )
        return jsonify({"status": "success"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route("/semantic_search", methods=["GET"])
def semantic_search():
    query_text = request.args.get("query", "")

    model = SentenceTransformer("all-MiniLM-L6-v2")

    if not query_text:
        return jsonify({"error": "Query text is required"}), 400

    # Generate query embedding
    query_embedding = model.encode(query_text).tolist()

    # Build Elasticsearch k-NN search query
    es_query = {
        "size": 10,
        "knn": {
            "field": "description_vector",
            "query_vector": query_embedding,
            "k": 10,
            "num_candidates": 100
        }
    }



    # Perform the search
    response = es.search(index=INDEX_NAME, body=es_query)

    # Format the response
    results = [
        {
            "id": hit["_id"],
            "name": hit["_source"]["details"]["name"],
            "description": hit["_source"]["details"]["description"],
            "score": hit["_score"]
        }
        for hit in response["hits"]["hits"]
    ]

    return jsonify(results)

if __name__ == "__main__":
    app.run(debug=True)