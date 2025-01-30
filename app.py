from flask import Flask, request, jsonify, render_template
from elasticsearch import Elasticsearch

app = Flask(__name__)
es = Elasticsearch("http://localhost:9200")
INDEX_NAME = "games"

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
                "details.maxplayers": {"lt": int(maxplayers)}
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
                "details.playingtime": {"lt": int(playingtime)}
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

if __name__ == "__main__":
    app.run(debug=True)
