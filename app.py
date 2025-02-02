from flask import Flask, request, jsonify, render_template
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
    response = es.search(index=SEARCH_LOG_INDEX, body=query)
    
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
    query = {
        "query": {
            "match": {
                "details.name": name
            }
        }
    }
    response = es.search(index=INDEX_NAME, body=query)
    game = response["hits"]["hits"][0]['_source']
    
    # Get similar games
    similar_games = more_like_this(game["id"])
    
    return jsonify({
        "game": game,
        "similar_games": similar_games
    })

if __name__ == "__main__":
    app.run(debug=True)