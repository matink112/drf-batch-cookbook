"""16. PUT: full-row replace (opt-in via batch_actions)."""

from __future__ import annotations

from _support import client, user
from saas import services
from saas.models import Project, Workspace

URL = "/projects/batch/"


def seed() -> None:
    team = Workspace.objects.create(id=1, name="Team")
    team.members.add(user("alice"))
    Project.objects.create(
        id=10, workspace=team, name="Launch", cost_center="RND", budget="500.00"
    )
    Project.objects.create(
        id=11, workspace=team, name="Migration", cost_center="LEGACY", budget="0"
    )


def walk() -> None:
    api = client("alice")

    # --8<-- [start:put_required]
    # PUT validates full rows: required fields must be sent.
    response = api.put(URL, [{"id": 10, "workspace": 1}])
    assert response.status_code == 400
    assert response.json() == [{"name": ["This field is required."]}]
    # --8<-- [end:put_required]

    # --8<-- [start:put]
    services.COST_CENTER_CALLS.clear()
    response = api.put(
        URL,
        [
            {"id": 10, "workspace": 1, "name": "Launch v2"},
            {"id": 11, "workspace": 1, "name": "Migration", "cost_center": "GENERAL"},
        ],
    )
    assert response.status_code == 200
    # Row 10 left the optional cost_center out: its stored "RND" was checked.
    assert [{"RND", "GENERAL"}] == services.COST_CENTER_CALLS
    launch = Project.objects.get(id=10)
    assert (launch.name, launch.cost_center, str(launch.budget)) == (
        "Launch v2",
        "RND",
        "500.00",
    )
    # --8<-- [end:put]

    # --8<-- [start:put_closed]
    response = api.put(
        URL, [{"id": 11, "workspace": 1, "name": "Migration", "cost_center": "LEGACY"}]
    )
    assert response.status_code == 400
    assert response.json() == [{"cost_center": ["Cost center 'LEGACY' is closed."]}]
    # --8<-- [end:put_closed]
