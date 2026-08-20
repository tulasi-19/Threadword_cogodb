# Threadwork

A people/colleague network explorer, backed by CognoDB — built for the Wexa AI take-home assignment.

Threadwork lets you browse a directory of people, see who's directly connected to whom, get "people you may know" suggestions through mutual connections, trace the shortest chain of connections between two people, find people nearby in the network who share your skills, and **ask a direct connection for a referral**.

## Why a graph database?

The core questions this app answers are all about **relationships between people**, not attributes of any single person:

* "Who do I know, and who do *they* know?" — a 2-hop traversal
* "What's the shortest chain of connections between me and this other person?" — a variable-length path of unknown depth
* "Who's within a few hops of me who happens to share a skill I have?" — a bounded-depth traversal filtered by a property on the far end

In a relational schema, a friendship graph is normally modeled as a self-referencing join table (`connections(person\_id, friend\_id)`). Answering "friends of friends" already requires a self-join; going deeper (3+ hops) or asking for a shortest path of *unknown* length requires a recursive CTE, and most relational engines have no native shortest-path operator at all — you'd hand-roll a breadth-first search in application code or a stored procedure. Every extra hop makes the SQL harder to write, harder to read, and slower, because each hop is another join.

In Cypher, none of that complexity shows up in the query. A friends-of-friends query is one `MATCH` pattern. A shortest path of unknown length is `shortestPath((a)-\[:FRIENDS\_WITH\*..6]-(b))` — one line. The query *looks like* the relationship it's describing. That's the whole case for a graph database here: the data model matches the questions being asked, so the queries stay simple as they get more relationally interesting, instead of getting harder.

## Data model

```
        WORKS\_AT                              HAS\_SKILL
 (Person) ─────────► (Company)      (Person) ─────────► (Skill)

                    FRIENDS\_WITH (undirected)
         (Person) ◄───────────────────────► (Person)
```

**Nodes**

|Label|Properties|
|-|-|
|`Person`|`id`, `name`, `city`|
|`Company`|`name`|
|`Skill`|`name`|

**Relationships**

|Type|Direction|Meaning|
|-|-|-|
|`FRIENDS\_WITH`|undirected|two people are connected|
|`WORKS\_AT`|`Person` → `Company`|current employer|
|`HAS\_SKILL`|`Person` → `Skill`|a skill this person has|
|`REQUESTED\_REFERRAL`|`Person` → `Person`, property `status`|a referral request between two directly connected people|

`Person.id` and `Company.name` / `Skill.name` are unique constraints (see `network/seed\_data.py`), so `MERGE` never creates duplicate nodes when the seed script re-runs.

## Project structure

```
connectweb/            Django project settings/urls
network/                the one Django app
  graph\_db.py           CognoDB driver singleton + connection error handling
  queries.py             every Cypher query used by the app, in one place
  seed\_data.py           loads realistic sample data into CognoDB
  views.py                wires queries to templates, catches DB-down errors
  urls.py
  templates/network/     HTML templates
  static/network/        CSS
requirements.txt
.env.example             template for required environment variables
```

## Setup

### 1\. Create a CognoDB instance

1. Sign up at [console.cognodb.com](https://console.cognodb.com/signup) (free, no card required).
2. Create a free `c0` instance and pick a region.
3. Copy the `bolt+s://...` connection URI and the generated password for the `cognodb` user — the password is shown only once.

### 2\. Install dependencies

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\\Scripts\\activate
pip install -r requirements.txt
```

### 3\. Configure environment variables

```bash
cp .env.example .env
```

Edit `.env` and fill in `COGNODB\_URI` and `COGNODB\_PASSWORD` from step 1. `.env` is git-ignored — never commit it.

### 4\. Load sample data

```bash
python manage.py shell -c "from network.seed\_data import run; run()"
```

This clears any existing graph data and loads \~30 people, 5 companies, 10 skills, and a randomized friendship network.

### 5\. Run the app

```bash
python manage.py runserver
```

Visit `http://127.0.0.1:8000/`.

If CognoDB is unreachable (wrong credentials, instance paused, no network), the app shows a clear in-page error banner instead of crashing — every view is wrapped to catch this.

## The main queries, explained

All queries live in `network/queries.py` and are run through `run\_query()` in `network/graph\_db.py`, which always passes values as **bound parameters** — never string-concatenated into the Cypher text.

* **`get\_direct\_connections`** — 1-hop: a person's immediate friends.
* **`get\_mutual\_connections`** — the 2-hop traversal required by the assignment: friends-of-friends who aren't already direct connections, ranked by how many mutual friends they share. This is the "people you may know" feature.
* **`get\_shortest\_path`** — uses Cypher's `shortestPath()` over a variable-length `FRIENDS\_WITH\*..6` pattern. This is the query that's awkward in a relational database: SQL has no native shortest-path operator, so this would normally mean a recursive CTE or application-side BFS.
* **`find\_people\_by\_shared\_skill\_within\_hops`** — a bounded-depth traversal (`FRIENDS\_WITH\*1..3`) combined with a property filter on the far end (shared `Skill`). Also awkward relationally, since the join depth is a *variable*, not a fixed number of table joins.
* **`request\_referral`** — creates a `REQUESTED\_REFERRAL` relationship, but only if a `FRIENDS\_WITH` relationship already exists between the two people. The eligibility check and the write happen in a single pattern match, rather than a separate "is this a valid connection?" query against a join table followed by an insert.

Since the app has no login system, profile pages include a "You are" dropdown so a visitor can pick which person they're currently browsing as — that identity is who a referral request is sent from, and whose sent/received requests are shown.

## Notes

* Django's own `sqlite3` database is only used for Django's built-in admin/session machinery — no application data (people, connections, skills) is ever stored there. All graph data lives in CognoDB.
* `find\_people\_by\_shared\_skill\_within\_hops` takes its hop-count bound (`max\_hops`) as a Python format value rather than a bound Cypher parameter, because Cypher's variable-length relationship syntax (`\*1..N`) doesn't accept parameters for the bound itself — this is a documented Cypher limitation, not a case of unparameterised user input. The value passed is an internal integer, never raw user text.

## Screenshots

*Add screenshots of the directory, a person's profile, and the path finder here before submitting.*

*## Screenshots*



*\*\*Directory\*\**

*!\[Directory](screenshots/Directory.png)*



*\*\*Person profile\*\**

*!\[Profile](screenshots/Profile.png)*



*\*\*Path finder\*\**

*!\[Path finder](screenshots/Find path.png)*



*\*\*Referral request\*\**

*!\[Referral](screenshots/Connections.png)*



*\*\*Referral request\*\**

*!\[Referral](screenshots/Searchingname.png)*



*\*\*Referral request\*\**

*!\[Referral](screenshots/Search.png)*



## Demo

* Hosted demo: *https://threadword-cogodb.onrender.com*
* Screen recording: *https://drive.google.com/file/d/1i8TXjVSpdCg7qnh5VeWi4Beyze\_QoyuZ/view?usp=sharing*

