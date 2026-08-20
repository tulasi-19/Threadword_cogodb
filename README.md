# Threadwork

A people/colleague network explorer, backed by CognoDB — built for the Wexa AI take-home assignment.

Threadwork lets you browse a directory of people, see who's directly connected to whom, get "people you may know" suggestions through mutual connections, trace the shortest chain of connections between two people, find people nearby in the network who share your skills, and **ask a direct connection for a referral**.

## Why a graph database?

The core questions this app answers are all about **relationships between people**, not attributes of any single person:

- "Who do I know, and who do *they* know?" — a 2-hop traversal
- "What's the shortest chain of connections between me and this other person?" — a variable-length path of unknown depth
- "Who's within a few hops of me who happens to share a skill I have?" — a bounded-depth traversal filtered by a property on the far end

In a relational schema, a friendship graph is normally modeled as a self-referencing join table (`connections(person_id, friend_id)`). Answering "friends of friends" already requires a self-join; going deeper (3+ hops) or asking for a shortest path of *unknown* length requires a recursive CTE, and most relational engines have no native shortest-path operator at all — you'd hand-roll a breadth-first search in application code or a stored procedure. Every extra hop makes the SQL harder to write, harder to read, and slower, because each hop is another join.

In Cypher, none of that complexity shows up in the query. A friends-of-friends query is one `MATCH` pattern. A shortest path of unknown length is `shortestPath((a)-[:FRIENDS_WITH*..6]-(b))` — one line. The query *looks like* the relationship it's describing. That's the whole case for a graph database here: the data model matches the questions being asked, so the queries stay simple as they get more relationally interesting, instead of getting harder.

## Data model

```
        WORKS_AT                              HAS_SKILL
 (Person) ─────────► (Company)      (Person) ─────────► (Skill)

                    FRIENDS_WITH (undirected)
         (Person) ◄───────────────────────► (Person)
```

**Nodes**
| Label | Properties |
|---|---|
| `Person` | `id`, `name`, `city` |
| `Company` | `name` |
| `Skill` | `name` |

**Relationships**
| Type | Direction | Meaning |
|---|---|---|
| `FRIENDS_WITH` | undirected | two people are connected |
| `WORKS_AT` | `Person` → `Company` | current employer |
| `HAS_SKILL` | `Person` → `Skill` | a skill this person has |
| `REQUESTED_REFERRAL` | `Person` → `Person`, property `status` | a referral request between two directly connected people |

`Person.id` and `Company.name` / `Skill.name` are unique constraints (see `network/seed_data.py`), so `MERGE` never creates duplicate nodes when the seed script re-runs.

## Project structure

```
connectweb/            Django project settings/urls
network/                the one Django app
  graph_db.py           CognoDB driver singleton + connection error handling
  queries.py             every Cypher query used by the app, in one place
  seed_data.py           loads realistic sample data into CognoDB
  views.py                wires queries to templates, catches DB-down errors
  urls.py
  templates/network/     HTML templates
  static/network/        CSS
requirements.txt
.env.example             template for required environment variables
```

## Setup

### 1. Create a CognoDB instance
1. Sign up at [console.cognodb.com](https://console.cognodb.com/signup) (free, no card required).
2. Create a free `c0` instance and pick a region.
3. Copy the `bolt+s://...` connection URI and the generated password for the `cognodb` user — the password is shown only once.

### 2. Install dependencies
```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### 3. Configure environment variables
```bash
cp .env.example .env
```
Edit `.env` and fill in `COGNODB_URI` and `COGNODB_PASSWORD` from step 1. `.env` is git-ignored — never commit it.

### 4. Load sample data
```bash
python manage.py shell -c "from network.seed_data import run; run()"
```
This clears any existing graph data and loads ~30 people, 5 companies, 10 skills, and a randomized friendship network.

### 5. Run the app
```bash
python manage.py runserver
```
Visit `http://127.0.0.1:8000/`.

If CognoDB is unreachable (wrong credentials, instance paused, no network), the app shows a clear in-page error banner instead of crashing — every view is wrapped to catch this.

## The main queries, explained

All queries live in `network/queries.py` and are run through `run_query()` in `network/graph_db.py`, which always passes values as **bound parameters** — never string-concatenated into the Cypher text.

- **`get_direct_connections`** — 1-hop: a person's immediate friends.
- **`get_mutual_connections`** — the 2-hop traversal required by the assignment: friends-of-friends who aren't already direct connections, ranked by how many mutual friends they share. This is the "people you may know" feature.
- **`get_shortest_path`** — uses Cypher's `shortestPath()` over a variable-length `FRIENDS_WITH*..6` pattern. This is the query that's awkward in a relational database: SQL has no native shortest-path operator, so this would normally mean a recursive CTE or application-side BFS.
- **`find_people_by_shared_skill_within_hops`** — a bounded-depth traversal (`FRIENDS_WITH*1..3`) combined with a property filter on the far end (shared `Skill`). Also awkward relationally, since the join depth is a *variable*, not a fixed number of table joins.
- **`request_referral`** — creates a `REQUESTED_REFERRAL` relationship, but only if a `FRIENDS_WITH` relationship already exists between the two people. The eligibility check and the write happen in a single pattern match, rather than a separate "is this a valid connection?" query against a join table followed by an insert.

Since the app has no login system, profile pages include a "You are" dropdown so a visitor can pick which person they're currently browsing as — that identity is who a referral request is sent from, and whose sent/received requests are shown.

## Notes

- Django's own `sqlite3` database is only used for Django's built-in admin/session machinery — no application data (people, connections, skills) is ever stored there. All graph data lives in CognoDB.
- `find_people_by_shared_skill_within_hops` takes its hop-count bound (`max_hops`) as a Python format value rather than a bound Cypher parameter, because Cypher's variable-length relationship syntax (`*1..N`) doesn't accept parameters for the bound itself — this is a documented Cypher limitation, not a case of unparameterised user input. The value passed is an internal integer, never raw user text.

## Screenshots

_Add screenshots of the directory, a person's profile, and the path finder here before submitting._

## Demo

- Hosted demo: _add your link here_
- Screen recording: _add your link here_
