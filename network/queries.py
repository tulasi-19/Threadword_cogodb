"""
All Cypher queries used by the app, kept in one place for clarity.
Every query is parameterised — no string-concatenated Cypher anywhere.
"""

from .graph_db import run_query


def get_all_people():
    """List every person, for the directory / search page."""
    query = """
    MATCH (p:Person)
    RETURN p.id AS id, p.name AS name, p.city AS city
    ORDER BY p.name
    """
    return run_query(query)


def get_person_profile(person_id):
    """A single person's own details, company, and skills."""
    query = """
    MATCH (p:Person {id: $person_id})
    OPTIONAL MATCH (p)-[:WORKS_AT]->(c:Company)
    OPTIONAL MATCH (p)-[:HAS_SKILL]->(s:Skill)
    RETURN p.id AS id, p.name AS name, p.city AS city,
           c.name AS company,
           collect(DISTINCT s.name) AS skills
    """
    rows = run_query(query, person_id=person_id)
    return rows[0] if rows else None


def get_direct_connections(person_id):
    """1-hop: this person's direct friends/colleagues."""
    query = """
    MATCH (p:Person {id: $person_id})-[:FRIENDS_WITH]-(friend:Person)
    RETURN DISTINCT friend.id AS id, friend.name AS name, friend.city AS city
    ORDER BY friend.name
    """
    return run_query(query, person_id=person_id)


def get_mutual_connections(person_id):
    """
    2-hop traversal: friends-of-friends who are NOT already a direct
    connection — i.e. "people you may know" suggestions, with a count of
    how many mutual friends each one shares with you.
    """
    query = """
    MATCH (p:Person {id: $person_id})-[:FRIENDS_WITH]-(mutual:Person)
          -[:FRIENDS_WITH]-(suggestion:Person)
    WHERE suggestion.id <> $person_id
      AND NOT (p)-[:FRIENDS_WITH]-(suggestion)
    RETURN suggestion.id AS id, suggestion.name AS name,
           count(DISTINCT mutual) AS mutual_count,
           collect(DISTINCT mutual.name)[0..3] AS sample_mutuals
    ORDER BY mutual_count DESC, suggestion.name
    LIMIT 10
    """
    return run_query(query, person_id=person_id)


def get_shortest_path(from_id, to_id):
    """
    Shortest path between two people through the FRIENDS_WITH network.
    This is the kind of query a relational database handles awkwardly —
    it would require a recursive/self-join query of unknown depth, whereas
    Cypher expresses it directly with shortestPath().
    """
    query = """
    MATCH (a:Person {id: $from_id}), (b:Person {id: $to_id}),
          path = shortestPath((a)-[:FRIENDS_WITH*..6]-(b))
    RETURN [n IN nodes(path) | {id: n.id, name: n.name}] AS people,
           length(path) AS hops
    """
    rows = run_query(query, from_id=from_id, to_id=to_id)
    return rows[0] if rows else None


def find_people_by_shared_skill_within_hops(person_id, max_hops=3):
    """
    Variable-length, attribute-filtered traversal: people within N hops in
    the network who share at least one skill with this person. This is
    the "awkward in SQL" query — in a relational schema it needs a
    recursive CTE of unknown, caller-specified depth joined back against a
    skills table; here it's one Cypher pattern with a bounded variable
    length relationship.
    """
    query = """
    MATCH (p:Person {id: $person_id})-[:HAS_SKILL]->(s:Skill)
    MATCH (p)-[:FRIENDS_WITH*1..%d]-(other:Person)-[:HAS_SKILL]->(s)
    WHERE other.id <> $person_id
    RETURN DISTINCT other.id AS id, other.name AS name,
           collect(DISTINCT s.name) AS shared_skills
    ORDER BY size(shared_skills) DESC, other.name
    LIMIT 15
    """ % max_hops
    return run_query(query, person_id=person_id)


def search_people(term):
    """Case-insensitive search by name, used by the search box."""
    query = """
    MATCH (p:Person)
    WHERE toLower(p.name) CONTAINS toLower($term)
    RETURN p.id AS id, p.name AS name, p.city AS city
    ORDER BY p.name
    LIMIT 20
    """
    return run_query(query, term=term)


def request_referral(from_id, to_id):
    """
    Create a referral request from one person to another — but only if
    they're already directly connected (FRIENDS_WITH). This is another
    place the graph model pays off: "are these two people connected?" is
    a single relationship check, not a join against a separate table.

    Returns True if the request was created, False if they aren't
    connected (so the request is refused) or a request already exists.
    """
    query = """
    MATCH (a:Person {id: $from_id})-[:FRIENDS_WITH]-(b:Person {id: $to_id})
    WHERE NOT (a)-[:REQUESTED_REFERRAL]->(b)
    MERGE (a)-[r:REQUESTED_REFERRAL {status: 'pending'}]->(b)
    RETURN r
    """
    rows = run_query(query, from_id=from_id, to_id=to_id)
    return len(rows) > 0


def get_referral_status(from_id, to_id):
    """Has from_id already requested a referral from to_id?"""
    query = """
    MATCH (a:Person {id: $from_id})-[r:REQUESTED_REFERRAL]->(b:Person {id: $to_id})
    RETURN r.status AS status
    """
    rows = run_query(query, from_id=from_id, to_id=to_id)
    return rows[0]["status"] if rows else None


def get_sent_referral_requests(person_id):
    """Referral requests this person has sent to their connections."""
    query = """
    MATCH (p:Person {id: $person_id})-[r:REQUESTED_REFERRAL]->(target:Person)
    RETURN target.id AS id, target.name AS name, r.status AS status
    ORDER BY target.name
    """
    return run_query(query, person_id=person_id)


def get_received_referral_requests(person_id):
    """Referral requests this person has received from their connections."""
    query = """
    MATCH (requester:Person)-[r:REQUESTED_REFERRAL]->(p:Person {id: $person_id})
    RETURN requester.id AS id, requester.name AS name, r.status AS status
    ORDER BY requester.name
    """
    return run_query(query, person_id=person_id)
