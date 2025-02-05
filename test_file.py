from elasticsearch import Elasticsearch
from constants import INDEX_NAME
es = Elasticsearch("http://localhost:9200")

game_id = '13'
game = es.get(index=INDEX_NAME, id=game_id)
print(game['_source'])