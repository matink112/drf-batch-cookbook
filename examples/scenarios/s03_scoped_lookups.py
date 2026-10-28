"""3. Scoped lookups: get_queryset() on the field, and on the view."""

from __future__ import annotations

from _support import client, user
from saas.models import Project, Workspace

URL = "/projects/batch/"


def seed() -> None:
    alice, bob = user("alice"), user("bob")
    mine = Workspace.objects.create(id=1, name="Alice's team")
    mine.members.add(alice)
    theirs = Workspace.objects.create(id=2, name="Bob's team")
    theirs.members.add(bob)
    old = Workspace.objects.create(id=3, name="Old team", archived=True)
    old.members.add(alice)
    Project.objects.create(id=20, workspace=theirs, name="Bob's project")


def walk() -> None:
    alice = client("alice")

    # --8<-- [start:post]
    response = alice.post(
        URL,
        [
            {"workspace": 1, "name": "Launch"},
            {"workspace": 2, "name": "Not mine"},  # Bob's workspace
            {"workspace": 3, "name": "Archived"},  # Alice's, but archived
        ],
    )
    assert response.status_code == 400
    assert response.json() == [
        {},
        {"workspace": ["Workspace 2 not found."]},
        {"workspace": ["Workspace 3 not found."]},
    ]
    # --8<-- [end:post]

    # --8<-- [start:patch]
    response = alice.patch(URL, [{"id": 20, "name": "Mine now"}])
    assert response.status_code == 404
    assert response.json() == [{"id": ["Object with id '20' not found."]}]
    # --8<-- [end:patch]

    response = alice.post(URL, [{"workspace": 1, "name": "Launch"}])
    assert response.status_code == 201
