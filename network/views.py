from django.shortcuts import render, redirect

from .graph_db import GraphDBUnavailable
from . import queries


def _render_with_db_guard(request, template, context_fn):
    """
    Shared error-handling wrapper: if CognoDB is unreachable, show a clear
    empty/error state instead of a stack trace.
    """
    try:
        context = context_fn()
        context["db_error"] = None
    except GraphDBUnavailable as exc:
        context = {"db_error": str(exc)}
    return render(request, template, context)


def home(request):
    def build_context():
        return {"people": queries.get_all_people()}
    return _render_with_db_guard(request, "network/home.html", build_context)


def search(request):
    term = request.GET.get("q", "").strip()

    def build_context():
        results = queries.search_people(term) if term else []
        return {"term": term, "results": results}
    return _render_with_db_guard(request, "network/search.html", build_context)


def profile(request, person_id):
    # This app has no login system, so "viewing_as" lets a visitor pick
    # which person they currently are, via a dropdown — that identity is
    # who a referral request would be sent from.
    if request.method == "POST":
        viewing_as = request.POST.get("as", "").strip()
        if viewing_as and viewing_as != person_id:
            try:
                queries.request_referral(viewing_as, person_id)
            except GraphDBUnavailable:
                pass
        return redirect(f"/person/{person_id}/?as={viewing_as}")

    viewing_as = request.GET.get("as", "").strip()

    def build_context():
        person = queries.get_person_profile(person_id)
        if not person:
            return {"person": None, "viewing_as": viewing_as}

        direct_connections = queries.get_direct_connections(person_id)
        is_connected = viewing_as in [c["id"] for c in direct_connections]
        already_requested = (
            queries.get_referral_status(viewing_as, person_id)
            if viewing_as and is_connected else None
        )

        context = {
            "person": person,
            "direct_connections": direct_connections,
            "suggestions": queries.get_mutual_connections(person_id),
            "skill_matches": queries.find_people_by_shared_skill_within_hops(person_id),
            "all_people": queries.get_all_people(),
            "viewing_as": viewing_as,
            "is_connected": is_connected,
            "already_requested": already_requested,
        }
        if viewing_as:
            context["sent_requests"] = queries.get_sent_referral_requests(viewing_as)
            context["received_requests"] = queries.get_received_referral_requests(viewing_as)
        return context

    return _render_with_db_guard(request, "network/profile.html", build_context)


def path_finder(request):
    from_id = request.GET.get("from", "").strip()
    to_id = request.GET.get("to", "").strip()

    def build_context():
        path = None
        if from_id and to_id:
            path = queries.get_shortest_path(from_id, to_id)
        return {
            "people": queries.get_all_people(),
            "from_id": from_id,
            "to_id": to_id,
            "path": path,
            "searched": bool(from_id and to_id),
        }
    return _render_with_db_guard(request, "network/path_finder.html", build_context)
