"""
Seed script — loads realistic sample data into CognoDB.

Run with:
    python manage.py shell -c "from network.seed_data import run; run()"

or simply:
    python network/seed_data.py
(the __main__ block below sets up Django first for standalone use)
"""

import random

from .graph_db import run_query

COMPANIES = ["Aarohi Tech", "Nimbus Cloud", "Bluepeak Systems", "Vertex Labs", "Orion Softworks"]
CITIES = ["Vijayawada", "Hyderabad", "Bengaluru", "Chennai", "Pune", "Delhi"]
SKILLS = ["Python", "Django", "React", "SQL", "Cypher", "Data Analysis",
          "Machine Learning", "Cloud Infra", "UI Design", "Project Management"]

FIRST_NAMES = ["Aarav", "Priya", "Rohan", "Sneha", "Vikram", "Ananya", "Kiran",
               "Divya", "Arjun", "Meera", "Sai", "Lakshmi", "Karthik", "Isha",
               "Nikhil", "Pooja", "Rahul", "Swati", "Varun", "Neha"]
LAST_NAMES = ["Sharma", "Reddy", "Iyer", "Rao", "Gupta", "Nair", "Menon",
              "Verma", "Das", "Pillai"]


def _generate_people(n=30):
    people = []
    for i in range(1, n + 1):
        name = f"{random.choice(FIRST_NAMES)} {random.choice(LAST_NAMES)}"
        people.append({
            "id": f"p{i}",
            "name": name,
            "city": random.choice(CITIES),
            "company": random.choice(COMPANIES),
            "skills": random.sample(SKILLS, k=random.randint(2, 4)),
        })
    return people


def _generate_friendships(people, avg_friends=4):
    """Create a connected-ish random friendship graph (undirected, deduped)."""
    edges = set()
    ids = [p["id"] for p in people]
    for pid in ids:
        num_friends = random.randint(2, avg_friends + 2)
        others = random.sample([x for x in ids if x != pid], k=min(num_friends, len(ids) - 1))
        for other in others:
            edge = tuple(sorted((pid, other)))
            edges.add(edge)
    return list(edges)


def run(num_people=30):
    print("Clearing existing graph data...")
    run_query("MATCH (n) DETACH DELETE n")

    print("Creating constraints...")
    run_query("CREATE CONSTRAINT person_id IF NOT EXISTS FOR (p:Person) REQUIRE p.id IS UNIQUE")
    run_query("CREATE CONSTRAINT company_name IF NOT EXISTS FOR (c:Company) REQUIRE c.name IS UNIQUE")
    run_query("CREATE CONSTRAINT skill_name IF NOT EXISTS FOR (s:Skill) REQUIRE s.name IS UNIQUE")

    print(f"Generating {num_people} people...")
    people = _generate_people(num_people)

    print("Loading Company and Skill nodes...")
    for company in COMPANIES:
        run_query("MERGE (:Company {name: $name})", name=company)
    for skill in SKILLS:
        run_query("MERGE (:Skill {name: $name})", name=skill)

    print("Loading Person nodes and their WORKS_AT / HAS_SKILL edges...")
    for p in people:
        run_query(
            """
            MERGE (person:Person {id: $id})
            SET person.name = $name, person.city = $city
            WITH person
            MATCH (c:Company {name: $company})
            MERGE (person)-[:WORKS_AT]->(c)
            """,
            id=p["id"], name=p["name"], city=p["city"], company=p["company"],
        )
        for skill in p["skills"]:
            run_query(
                """
                MATCH (person:Person {id: $id}), (s:Skill {name: $skill})
                MERGE (person)-[:HAS_SKILL]->(s)
                """,
                id=p["id"], skill=skill,
            )

    print("Loading FRIENDS_WITH edges...")
    friendships = _generate_friendships(people)
    for a, b in friendships:
        run_query(
            """
            MATCH (p1:Person {id: $a}), (p2:Person {id: $b})
            MERGE (p1)-[:FRIENDS_WITH]-(p2)
            """,
            a=a, b=b,
        )

    print(f"Done. Loaded {len(people)} people, {len(friendships)} friendships, "
          f"{len(COMPANIES)} companies, {len(SKILLS)} skills.")


if __name__ == "__main__":
    import os
    import sys
    import django

    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "connectweb.settings")
    django.setup()

    run()
