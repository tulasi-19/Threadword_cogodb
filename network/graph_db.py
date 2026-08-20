"""
Thin wrapper around the official Neo4j Python driver, pointed at CognoDB.

CognoDB speaks openCypher over the Bolt protocol and is fully compatible
with the standard Neo4j driver, so no custom SDK is needed here.

This module exposes:
    - get_driver()          -> a lazily-created, process-wide driver instance
    - run_query(query, **params) -> executes a parameterised Cypher query
    - GraphDBUnavailable    -> raised (and caught by views) when the
                                database can't be reached, so the app can
                                degrade gracefully instead of crashing.
"""

from django.conf import settings
from neo4j import GraphDatabase
from neo4j.exceptions import ServiceUnavailable, AuthError

_driver = None


class GraphDBUnavailable(Exception):
    """Raised when CognoDB can't be reached or credentials are missing/invalid."""
    pass


def get_driver():
    """Return a cached driver instance, creating it on first use."""
    global _driver

    if _driver is not None:
        return _driver

    if not settings.COGNODB_URI or not settings.COGNODB_PASSWORD:
        raise GraphDBUnavailable(
            "CognoDB connection details are missing. Set COGNODB_URI and "
            "COGNODB_PASSWORD in your .env file."
        )

    try:
        _driver = GraphDatabase.driver(
            settings.COGNODB_URI,
            auth=(settings.COGNODB_USER, settings.COGNODB_PASSWORD),
        )
        _driver.verify_connectivity()
        return _driver
    except AuthError as exc:
        raise GraphDBUnavailable(
            "CognoDB rejected the provided credentials. Check COGNODB_USER "
            "and COGNODB_PASSWORD."
        ) from exc
    except ServiceUnavailable as exc:
        raise GraphDBUnavailable(
            "Could not reach CognoDB. Check COGNODB_URI and your network "
            "connection, and make sure the instance is running."
        ) from exc


def run_query(query, **params):
    """
    Run a parameterised Cypher query and return a list of plain dicts.

    Always use this (never string-concatenate Cypher) so user input is
    passed as bound parameters, not interpolated into the query text.
    """
    try:
        driver = get_driver()
        with driver.session() as session:
            result = session.run(query, **params)
            return [record.data() for record in result]
    except (ServiceUnavailable, AuthError) as exc:
        raise GraphDBUnavailable(f"CognoDB query failed: {exc}") from exc
