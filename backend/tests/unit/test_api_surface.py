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
