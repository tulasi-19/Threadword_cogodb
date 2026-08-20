# This app's data lives entirely in CognoDB (a graph database), accessed
# via network/graph_db.py and network/queries.py using the official Neo4j
# driver with parameterised Cypher. There are intentionally no Django ORM
# models here — the graph is the data layer, not Django's relational DB.
