"""What the API offers, and what it refuses, without a file server behind it.

Three things are worth checking here and nowhere else.

The **error envelope**, because every screen renders errors through it and a
route that answers in some other shape reaches the user as an untranslated
English sentence under a German heading.

The **gate**, because a route that forgot its dependency is a route anyone can
call. Enumerated from the application rather than listed by hand: a list is a
place to forget the route somebody adds next week.

And the **parameters as declared**, read off ``app.openapi()``. That catches a
class of mistake nothing else does — a value the logic layer supports but the
route wired shut, or a default that quietly changed. The schema is read from
the object, not fetched: what is served is a deployment decision, and a test
that depends on it would break for the wrong reason if that decision changed.
"""

from __future__ import annotations

from typing import Any

import pytest
from fastapi.testclient import TestClient

from samfscon.auth.session import reset_auth_state
from samfscon.main import app

# Everything under here needs a signed-in session. Read from the schema rather
# than written down, so a route added later is covered without anybody
# remembering to add it.
PUBLIC = {
    "/api/v1/health",
    "/api/v1/info",
    "/api/v1/servers",
    "/api/v1/servers/probe",
    "/api/v1/auth/login",
    # Answers "am I signed in?" — it has to be callable when the answer is no.
    "/api/v1/auth/session",
    # Ends a session that may already be gone; refusing that is unhelpful.
    "/api/v1/auth/logout",
}


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client
    reset_auth_state()


def schema() -> dict[str, Any]:
    return app.openapi()


def guarded_routes() -> list[tuple[str, str]]:
    """Every (method, path) that is not deliberately public."""
    found: list[tuple[str, str]] = []
    for path, operations in schema()["paths"].items():
        if path in PUBLIC:
            continue
        for method in operations:
            if method in {"get", "post", "put", "patch", "delete"}:
                found.append((method, path))
    return sorted(found)


# ---------------------------------------------------------------------------
# The gate
# ---------------------------------------------------------------------------


def test_there_is_something_to_check() -> None:
    """A guard over an empty list passes and proves nothing."""
    assert len(guarded_routes()) >= 15


@pytest.mark.parametrize(("method", "path"), guarded_routes())
def test_no_route_answers_without_a_session(client: TestClient, method: str, path: str) -> None:
    # A path parameter is filled with something syntactically fine; the point
    # is that the refusal arrives before anything looks at it.
    response = client.request(method, path.replace("{name}", "example"))

    assert response.status_code in {401, 403}, (
        f"{method.upper()} {path} answered {response.status_code} with no session"
    )


def test_health_answers_without_one_and_says_which_version(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    assert response.status_code == 200

    body = response.json()
    assert body["status"] == "ok"
    # The version reaches a reader here, which is why it is checked against the
    # one place it is written rather than against a literal.
    from samfscon import __version__

    assert body["version"] == __version__


# ---------------------------------------------------------------------------
# The envelope
# ---------------------------------------------------------------------------


def test_a_refusal_arrives_in_the_shape_every_screen_reads(client: TestClient) -> None:
    response = client.get("/api/v1/shares")
    assert response.status_code in {401, 403}

    error = response.json()["error"]
    # code is what the interface translates; message is the fallback for a code
    # no catalogue has yet.
    assert isinstance(error["code"], str) and error["code"]
    assert isinstance(error["message"], str) and error["message"]


def test_a_body_the_schema_rejects_arrives_in_the_same_shape(client: TestClient) -> None:
    """FastAPI's own 422 does not use the envelope unless it is made to."""
    response = client.post("/api/v1/auth/login", json={"username": "only"})
    assert response.status_code == 422
    assert "error" in response.json(), (
        "a validation failure answers in FastAPI's shape, not the console's"
    )


# ---------------------------------------------------------------------------
# The parameters, as the routes actually declare them
# ---------------------------------------------------------------------------


def parameters_of(path: str, method: str = "get") -> dict[str, dict[str, Any]]:
    operation = schema()["paths"][path][method]
    return {entry["name"]: entry for entry in operation.get("parameters", [])}


def test_a_directory_listing_defaults_to_the_share_root() -> None:
    """Not to a required parameter: the root is where a browser starts."""
    parameters = parameters_of("/api/v1/files")
    assert parameters["share"]["required"] is True
    assert parameters["path"]["required"] is False


def test_effective_access_asks_for_all_three_of_its_inputs() -> None:
    """It answers "may this account do this here", and drops none of them."""
    parameters = parameters_of("/api/v1/permissions/effective")
    assert parameters["share"]["required"] is True
    assert parameters["sid"]["required"] is True
    # The path is optional; absent means the share's own root.
    assert "path" in parameters


def test_the_option_catalogue_takes_the_language_it_is_rendered_in() -> None:
    """The explanations are translated server-side, so the route has to know."""
    assert "language" in parameters_of("/api/v1/shares/catalogue")


# ---------------------------------------------------------------------------
# The server settings
# ---------------------------------------------------------------------------


def test_the_configuration_routes_are_registered() -> None:
    """A router written and never included fails as a 404.

    Which reads, from the browser, exactly like a mistake in the front end.
    Both halves of the registration are needed — the import tuple and the
    include_router line — and only this notices when one of them is missing.
    """
    paths = schema()["paths"]
    assert "/api/v1/config" in paths
    assert "/api/v1/config/catalogue" in paths
    assert "patch" in paths["/api/v1/config"]


def test_the_global_catalogue_takes_the_language_it_is_rendered_in() -> None:
    """The same gap the share catalogue closed, on the settings side."""
    parameters = parameters_of("/api/v1/config/catalogue")
    assert "language" in parameters
    # And nothing else: the mode comes from the session, not from the caller.
    # A mode in the query string would be a fact with two owners.
    assert "mode" not in parameters


def test_the_catalogue_language_is_a_closed_set() -> None:
    """Declared as a pattern, so an unknown value is refused rather than defaulted.

    Read off the schema rather than by calling: what the route accepts is what
    it declares, and a runtime `if` inside the handler would not appear here.
    """
    language = parameters_of("/api/v1/config/catalogue")["language"]
    assert language["schema"].get("pattern") == "^(de|en)$"


def test_a_configuration_write_is_refused_without_the_csrf_header(client: TestClient) -> None:
    """VerifiedSession, not CurrentSession — the double-submit lives there.

    Without a session this is a 401 either way, so the check that matters is
    the declaration: the write must not be reachable through the dependency
    that skips the CSRF header.
    """
    import inspect

    from samfscon.api.v1 import config

    signature = inspect.signature(config.update_config)
    annotations = {str(p.annotation) for p in signature.parameters.values()}
    assert any("VerifiedSession" in a for a in annotations)
    assert any("VerifiedWorker" in a for a in annotations)
    assert not any("CurrentSession" in a for a in annotations)

    response = client.patch("/api/v1/config", json={"options": {}})
    assert response.status_code == 401


# ---------------------------------------------------------------------------
# What answers before anyone signs in
# ---------------------------------------------------------------------------


def test_info_carries_only_what_the_sign_in_form_reads(client: TestClient) -> None:
    """Reachable without a session, so held to exactly what the form uses.

    It used to describe the deployment — default server, realm, workgroup, the
    SMB floor — and count the administrators signed in right now. The form read
    none of it. A field added here later is a field the whole network can read.
    """
    response = client.get("/api/v1/info")
    assert response.status_code == 200
    assert set(response.json()) == {"version", "allow_standalone"}


def test_the_api_documentation_is_not_served_by_default(client: TestClient) -> None:
    """A map of every route and parameter, reachable without a session.

    Switched on with SAMFSCON_API_DOCS=1. The schema itself is still built
    in-process — app.openapi() is what the tests above read.
    """
    assert client.get("/api/docs").status_code == 404
    assert client.get("/api/openapi.json").status_code == 404


def _api_routes(routes) -> list:
    """Every APIRoute under *routes*, however deeply routers are included.

    Walked rather than read off app.routes: recent FastAPI keeps an included
    router as one object, so app.routes holds a single entry and a loop over it
    finds nothing. The first version of the test below did exactly that and
    passed — with the two routes it exists to catch still unchecked.
    """
    from fastapi.routing import APIRoute

    found: list = []
    for route in routes:
        if isinstance(route, APIRoute):
            found.append(route)
        elif getattr(route, "original_router", None) is not None:
            found.extend(_api_routes(route.original_router.routes))
        elif getattr(route, "routes", None):
            found.extend(_api_routes(route.routes))
    return found


def test_every_state_changing_verb_carries_the_csrf_check() -> None:
    """The rule is by method, not by effect.

    The two identity lookups are POST and change nothing, and they were the two
    that skipped the double-submit check. Read-only today; but a POST route
    without it is the template somebody copies for the next one that writes.
    Enumerated from the application, so a route added later is held to it too.
    """
    import inspect

    from samfscon.main import app

    # Signing in and out cannot carry a token the server has not issued yet or
    # has just withdrawn, and the probe answers before anyone has a session.
    exempt = ("/auth/login", "/auth/logout", "/servers/probe")
    routes = _api_routes(app.routes)
    writing = [
        route
        for route in routes
        if route.methods & {"POST", "PUT", "PATCH", "DELETE"}
        and not route.path.endswith(exempt)
    ]
    # A guard over an empty list passes and proves nothing — which is how the
    # first version of this test got through.
    assert len(writing) >= 15, f"found only {len(writing)} state-changing routes"

    unchecked = []
    for route in writing:
        annotations = " ".join(
            str(p.annotation) for p in inspect.signature(route.endpoint).parameters.values()
        )
        if "VerifiedSession" not in annotations and "VerifiedWorker" not in annotations:
            unchecked.append(f"{sorted(route.methods)} {route.path}")
    assert not unchecked, f"state-changing routes without the CSRF check: {unchecked}"
